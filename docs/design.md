# Delve — Deep Research Orchestrator Plugin

DATE: 2026-03-10
STATUS: approved
ARCHITECTURE: Approach C-prime (lean SKILL.md + references/)
VALIDATION: 3-model panel (Claude + Codex + Gemini) on each section

---

## Overview

Claude Code plugin for autonomous deep research. Stage-gated pipeline with parallel subagents, file-based checkpoints, claim-level verification, and resume support.

Pure SKILL.md plugin — no binaries, no scripts. Follows arbiter plugin pattern.

## Command Surface

```
/delve <topic>                              → full pipeline (default)
/delve <topic> --quick                      → scan + synthesize (skip deep dive & verify)
/delve <topic> --depth shallow|medium|deep  → intensity (2/4/6 agents, default: medium)
/delve <topic> --providers claude            → single-model (sensitivity routing)
/delve <topic> --output ~/custom/path.md    → custom output path
/delve resume [run_id]                      → resume from checkpoint
/delve status                               → list recent runs
/delve                                      → help
```

## Section 1: Plugin Structure

### Plugin Files

```
delve/
├── plugin.json
├── LICENSE
├── CHANGELOG.md
├── README.md
├── skills/
│   └── delve/
│       ├── SKILL.md                  # ~500-600 lines: orchestration, stages, resume, CLI
│       └── references/
│           ├── dive-prompt.md        # prompt for research subagents
│           ├── verify-prompt.md      # prompt for verification subagents
│           ├── claim-extraction-prompt.md  # prompt for claim decomposition
│           ├── synthesize-guide.md   # synthesis instructions
│           ├── checkpoint-schema.md  # artifact format documentation
│           └── security-policy.md    # prompt injection rules, sensitivity matrix
└── docs/
    └── design.md
```

### Runtime Artifacts (per-run, in tmpdir)

```
$RUN_DIR/                              # mktemp -d delve.XXXXXX
├── .lock/                             # mkdir atomic lock (NOT lease.json)
├── lease.json                         # metadata: pid, host, started_at, lease_id
├── manifest.json                      # frozen inputs + run_id + schema_version + original_request
├── state.json                         # REBUILDABLE index (NOT canonical)
├── events.jsonl                       # CANONICAL source of truth (append-only)
├── scan.done                          # stage completion marker
├── scan/
│   └── result.json                    # sources, relevance scores, decision_gate
├── decompose.done
├── decompose/
│   └── sub-tasks.json                 # keyed by q_<hash>, with priority, depends_on
├── dive.done
├── dive/
│   ├── q_a1b2c3/                      # hash ID (NOT ordinal)
│   │   ├── prompt.md                  # frozen prompt
│   │   ├── output.md                  # human-readable research
│   │   ├── output.json                # structured: claims[], citations[], confidence, gaps
│   │   └── status.json                # status, prompt_hash, model, attempt_id, input_hash
│   └── q_d4e5f6/ ...
├── verify.done
├── verify/
│   ├── claims.json                    # all claims with c_<hash> IDs
│   ├── verdicts/                      # per-claim verdict (ALL claims, not just contested)
│   │   ├── c_x1y2z3.json             # {claim, verdict, evidence, sources}
│   │   └── ...
│   └── summary.json                   # aggregate counts
└── output/
    ├── synthesis.md                   # final report
    └── synthesis.json                 # structured data + provenance
```

### Design Principles

- `events.jsonl` = canonical source of truth
- `state.json` / `status.json` = rebuildable indexes
- Hash IDs (`q_<hash>`, `c_<hash>`) for stable resume across decomposition changes
- Dual output per worker: `output.json` (structured contract) + `output.md` (human-readable)
- Atomic writes: temp file + `mv` rename
- `mkdir .lock` for concurrency (not PID-based lease)
- Stage done markers: artifact write → status update → `stage.done`

---

## Section 2: Pipeline Stages

### Stage 1: SCAN (inline, ~20-30s)

```
Input: topic (string)
Output: scan/result.json
```

- Check memory bank (existing `docs/research/`)
- WebSearch: 3-5 queries (topic + variations)
- WebFetch: top-5 results for preview
- Output: sources with relevance scores

**Decision gate** after scan:
- `full-run`: no prior research → proceed normally
- `extend`: partial prior research → focus on gaps
- `refresh`: prior research exists but stale → update with new sources
- `reuse`: comprehensive recent research → fast-path synthesize existing
- `no_evidence`: 0 sources found → abort or warn + first principles

If `--quick`: after scan → skip to SYNTHESIZE.

### Stage 2: DECOMPOSE (inline, ~5s)

```
Input: scan/result.json + topic
Output: decompose/sub-tasks.json
```

- LLM splits topic into 2-6 independent sub-questions (based on `--depth`)
- Each gets `q_<hash>` ID, priority (P0/P1/P2), rationale, estimated_sources
- `depends_on`: allowed only for `--depth deep` (topological execution waves)
- For shallow/medium: all sub-questions must be independent
- Filter: sub-questions covered by existing research → `skip: true`
- All-skipped → terminal status `synthesis_only`, synthesize existing docs

**HITL Checkpoint** (skipped with `--quick`):
```
Decomposed into N sub-questions:
1. [q_a1b2] How does X work? (P0, high)
2. [q_c3d4] What are alternatives to Y? (P1, medium)
Approve / Edit / Add / Remove?
```

### Stage 3: DIVE (parallel subagents, ~60-300s)

```
Input: decompose/sub-tasks.json (non-skipped)
Output: dive/q_<hash>/output.json + output.md per task
```

- Per sub-question: spawn `general-purpose` agent with `run_in_background: true`
- Prompt from `references/dive-prompt.md` + sub-question + sources from scan
- Cache reuse: scan results passed to dive agents (no re-fetch)
- Parallelism: 2 (shallow) / 3-4 (medium) / 5-6 (deep)
- For deep with `depends_on`: topological waves (wave 1 completes → wave 2 starts)
- Each agent: WebSearch + WebFetch + Read + analysis → output.json + output.md
- Timeout per worker: 120s (process-group kill, arbiter pattern)
- Collect via TaskOutput, write status.json per task

**Partial success policy (priority-weighted):**
- All P0 completed + weighted coverage ≥0.7 → proceed
- P0 failed → retry once. Still failed → ABORT
- <0.7 coverage → proceed with `completion: incomplete`
- 0 completed (and no usable prior research) → ABORT

### Stage 4: VERIFY (parallel subagents, ~60-120s)

```
Input: dive/q_*/output.json (all completed)
Output: verify/claims.json + verify/verdicts/c_<hash>.json
```

**Step 4a: Claim Extraction** (inline, explicit):
- Prompt from `references/claim-extraction-prompt.md` + `references/source-authority-rules.md`
- Decompose all dive outputs into atomic claims → `claims.json`
- Classify: factual, opinion, methodology, quantitative, time-sensitive
- Source independence check: deduplicate claims from same original source

**Step 4b: Verification** (parallel subagents):
- Prompt from `references/verify-prompt.md` + `references/source-authority-rules.md`: adversarial, "find flaws not confirm", tier-weighted verdicts
- Batch by topic (5-10 simple factual, 1-3 quantitative/high-impact)
- Verifiers work independently from synthesis (no anchoring)
- Verdict per claim: `verified` / `contested` / `rejected` / `uncertain`
- Web content treated as DATA, never as instructions (prompt injection policy)

**Depth-dependent:**
- `--quick`: skip entirely
- `--depth shallow`: verify top 30% claims (P0 only)
- `--depth medium`: all factual claims
- `--depth deep`: all factual + cross-check quantitative

### Stage 5: SYNTHESIZE (inline, ~15s)

```
Input: dive outputs + verify verdicts
Output: output/synthesis.md + output/synthesis.json
```

- Instructions from `references/synthesize-guide.md`
- Merge all dive outputs, annotate with verify verdicts
- Contested claims → present both sides with evidence
- Rejected claims → exclude or flag explicitly
- 3 blogs from same press release ≠ 3 confirmations (source independence)

Output structure:
```markdown
# <Topic> — Deep Research
## Key Findings (verified)
## Contested Points
## Sources
## Methodology (stages, agents, timing, quality)
```

- Copy to `docs/research/YYYY-MM-DD-<topic-slug>-<run_id_short>.md`
- High contested_ratio (>30%) → output as `draft`

### Depth Mapping (realistic estimates)

| Flag | Agents | Verify | HITL | Estimated time |
|------|--------|--------|------|----------------|
| `--quick` | 0 (inline) | skip | skip | ~60-90s |
| `--depth shallow` | 2 | top 30% | yes | ~3-5 min |
| `--depth medium` | 3-4 | all factual | yes | ~6-10 min |
| `--depth deep` | 5-6 | all + cross | yes | ~10-20 min |

---

## Section 3: Error Handling & Resume

### Error Categories

| Error | Stage | Action |
|-------|-------|--------|
| WebSearch unavailable | SCAN | Fallback: memory bank only + warn |
| 0 sources found | SCAN | Decision gate: `no_evidence` status |
| All sub-questions skipped | DECOMPOSE | Terminal: `synthesis_only` |
| Worker timeout (120s) | DIVE | Process-group kill, mark `timeout`, exit 124 |
| Worker crash | DIVE | Mark `error`, capture stderr |
| P0 sub-question failed | DIVE | Retry once → still failed → ABORT |
| <0.7 weighted coverage | DIVE | Proceed with `completion: incomplete` |
| Claim extraction fails | VERIFY | Skip verify, `verification: unverified` |
| Verifier disagrees | VERIFY | Mark `uncertain` |
| Prompt injection detected | DIVE/VERIFY | Strip, log to events.jsonl |
| Output name collision | SYNTHESIZE | `run_id_short` suffix (always present) |
| State corruption | RESUME | Graceful error + option to restart from scratch |
| Rate limit (429) | ANY | Exponential backoff, 3 retries |
| Schema version mismatch | RESUME | Warn, attempt migration or restart |
| Orchestrator crash | ANY | Resume from last `.done` marker |
| User cancel (SIGINT) | ANY | Mark `cancelled`, clean up workers |

### Concurrency Control

- `mkdir $RUN_DIR/.lock` — atomic lock (OS-level, no race)
- `lease.json` — metadata only: pid, host, started_at, lease_id
- On resume: if `.lock` exists → check lease.json PID → alive = "force?" / dead = acquire

### Resume Protocol

```
/delve resume [run_id]
```

1. Find run in `~/.cache/delve/runs/<run_id>.json` (per-run files, NOT single registry)
2. Check `.lock` directory + lease.json
3. Read `state.json` → determine current_stage via `.done` markers
4. Per-stage resume:
   - SCAN/DECOMPOSE → re-run (cheap, idempotent)
   - DIVE → check each `dive/q_*/status.json`, re-run only pending/error/timeout
   - VERIFY → check `verify/verdicts/c_*.json`, re-run only missing
   - SYNTHESIZE → re-run from completed artifacts
5. Cache validity: compare `input_hash` + `prompt_hash` + `schema_version`. Mismatch → invalidate downstream
6. Strict commit order: artifact write → status update → `stage.done` marker

### Run Registry

`~/.cache/delve/runs/<run_id>.json` — one file per run:
```json
{
  "run_id": "20260310T143000Z-12345",
  "topic": "autoresearch landscape",
  "depth": "medium",
  "status": "completed",
  "run_dir": "/tmp/delve.a1b2c3",
  "created_at": "2026-03-10T14:30:00Z",
  "completed_at": "2026-03-10T14:38:22Z",
  "output": "docs/research/2026-03-10-autoresearch-landscape-a1b2.md"
}
```

### Quality Model (dual axis)

**Verification status:**
| Label | Condition |
|-------|-----------|
| `verified` | ≥80% claims verified, 0 failed P0, >50% verified claims backed by T1/T2 sources, pipeline complete |
| `partially-verified` | 50-79% coverage, or degraded verify, or ≤50% T1/T2 backing |
| `unverified` | <50% coverage, verify skipped, or failed |

**Completion status:**
| Label | Condition |
|-------|-----------|
| `complete` | All stages ran, all P0 covered |
| `incomplete` | DIVE partial success (<100% workers) |
| `synthesis_only` | No new research, synthesized existing docs |
| `draft` | >30% contested ratio |
| `cancelled` | User interrupted |
| `no_evidence` | 0 sources, first-principles only |

Both stored in `synthesis.json` provenance + frontmatter of `synthesis.md`.

### Sensitivity Routing

`--providers claude` capability matrix:

| Capability | Status |
|-----------|--------|
| WebSearch/WebFetch | ALLOWED (public web, no sensitive data sent) |
| Codex/Gemini subagents | BLOCKED |
| External verification | BLOCKED (inline Claude-only verify) |
| Cross-model routing | BLOCKED |
| events.jsonl logging | Allowed but topic redacted |
| Max verification label | `partially-verified` (same-model not structurally independent) |

---

## Deferred to v2

- Knowledge graph output
- Cost/token estimation pre-run
- Recursive decomposition (sub-delve)
- Configurable draft threshold (currently 30%)
- Heartbeat in lease.json
- Crash-injection test matrix

---

## Sources

- Arbiter plugin: `~/.claude/plugins/cache/local/arbiter/0.3.0/skills/arbiter/SKILL.md`
- Arbiter diverge design: `docs/plans/2026-03-01-arbiter-diverge-design.md`
- Cross-model verification: `docs/research/2026-02-28-cross-model-verification-research.md`
- Anti-hallucination synthesis: `docs/research/2026-02-28-arbiter-anti-hallucination-synthesis.md`
- SkillsBench: `docs/research/2026-03-04-skill-discovery-survey.md`
- Autoresearch landscape: `docs/research/2026-03-10-autoresearch-landscape.md`
- Agent orchestration patterns: `docs/research/2026-02-26-agent-orchestration-patterns.md`
- Lessons (timeout portability): `.claude/memory/bank/lessons.md`
