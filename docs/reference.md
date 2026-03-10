# Reference

## Commands

### `/delve <topic>`

Run the full research pipeline on the given topic.

**Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--quick` | off | Skip DIVE and VERIFY stages (scan + synthesize only) |
| `--depth <level>` | `medium` | `shallow` (2 agents) / `medium` (3-4) / `deep` (5-6) |
| `--providers claude` | off | Single-model mode, no external AI calls |
| `--output <path>` | auto | Custom output path for synthesis report |

**Conflicts:** `--quick` + `--depth` -> depth is ignored (quick always skips dive/verify).

### `/delve resume [run_id]`

Resume an interrupted run from its last checkpoint. Without `run_id`, lists recent runs for selection.

### `/delve status`

List recent runs with their status, topic, depth, and output path.

## Constants

| Name | Value | Notes |
|------|-------|-------|
| CACHE_DIR | `~/.cache/delve/runs` | Run storage |
| WORKER_TIMEOUT_MS | 120000 | Per-agent timeout |
| COVERAGE_THRESHOLD | 0.7 | Min weighted coverage to proceed |
| CONTESTED_THRESHOLD | 0.3 | Above -> mark as `draft` |
| P_WEIGHTS | P0=3, P1=2, P2=1 | For coverage calculation |
| MAX_CLAIMS | shallow=20, medium=35, deep=60 | Depth-dependent claim limit |

## Output format

Reports are saved to `docs/research/YYYY-MM-DD-<topic-slug>-<run_id_short>.md` with YAML frontmatter:

```yaml
---
topic: <topic>
run_id: <run_id>
date: <YYYY-MM-DD>
depth: <shallow | medium | deep>
verification: <verified | partially-verified | unverified>
completion: <complete | incomplete | synthesis_only | draft | cancelled | no_evidence>
sources: <count>
claims_verified: <count>
claims_contested: <count>
---
```

Report sections: Key Findings, Contested Points, Gaps & Open Questions, Sources, Methodology.

## Quality labels

**verification_status** (uses `verified_ratio`, not `coverage`):
- `verified`: verified_ratio >= 0.8, 0 rejected among P0 claims, full pipeline
- `partially-verified`: 0.5-0.79, or degraded verify, or `--providers claude`
- `unverified`: < 0.5, or verify skipped/failed

**completion_status:**
- `complete`: all stages ran, all P0 sub-questions covered
- `incomplete`: DIVE had partial success
- `synthesis_only`: no new research, used existing docs
- `draft`: contested_ratio > 0.3
- `cancelled`: user interrupted
- `no_evidence`: 0 sources found

## Decision gates

| Gate | Condition | Action |
|------|-----------|--------|
| `no_evidence` | 0 sources + 0 existing research | Warn user, offer abort or first-principles |
| `reuse` | Comprehensive existing research < 30 days | Skip to SYNTHESIZE |
| `refresh` | Existing research > 30 days | DIVE focuses on deltas |
| `extend` | Partial existing research | DIVE focuses on uncovered aspects |
| `full-run` | No prior research | Full pipeline |

## Error handling

| Error | Stage | Action |
|-------|-------|--------|
| WebSearch unavailable | SCAN | Fallback to existing research, warn user |
| 0 sources found | SCAN | `no_evidence` gate |
| Worker timeout | DIVE | Mark timeout, retry P0 once |
| P0 failed after retry | DIVE | ABORT |
| Coverage < 0.7 | DIVE | Proceed with `incomplete` + warn |
| Claim extraction fails | VERIFY | Skip verify, mark `unverified` |
| Prompt injection detected | DIVE/VERIFY | Strip content, log event, continue |

## Troubleshooting

**"Run directory was cleaned up"** — The run completed or the cache was cleared. Start a new run.

**Resume re-dispatches all DIVE workers** — A prompt template changed since the original run, triggering cascade invalidation. This is expected behavior.

**Verification always returns `partially-verified`** — Check if `--providers claude` is active. Same-model verification is capped at `partially-verified` by design.

**HITL checkpoint not appearing** — Only shown in non-quick mode during DECOMPOSE. Quick mode skips directly to SYNTHESIZE.
