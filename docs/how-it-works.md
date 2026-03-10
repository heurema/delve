# How it works

## Architecture

Delve is a stage-gated orchestrator that runs inside Claude Code as a skill. It coordinates parallel subagents for research and verification while maintaining checkpointed state on disk.

```
User -> SKILL.md orchestrator
             |
             +-- SCAN (inline) -- WebSearch + WebFetch
             |
             +-- DECOMPOSE (inline) -- topic -> sub-questions
             |
             +-- DIVE (parallel subagents) -- 2-6 research agents
             |
             +-- VERIFY (parallel subagents) -- adversarial fact-checkers
             |
             +-- SYNTHESIZE (inline) -- merge + quality labels -> report
```

## Data flow

1. **SCAN** searches the web and local `docs/research/` for prior work. Produces `scan/result.json` with ranked sources.

2. **DECOMPOSE** breaks the topic into sub-questions with priority levels (P0/P1/P2). Each gets a deterministic `q_<hash>` ID. User approves the decomposition before proceeding.

3. **DIVE** dispatches parallel research agents (one per sub-question). Each agent follows `references/dive-prompt.md`, produces structured `output.json` + human-readable `output.md`. Agents run in background via the Agent tool.

4. **VERIFY** extracts atomic claims from DIVE outputs, assigns `c_<hash>` IDs, then dispatches adversarial verification agents. Verifiers receive `original_sources` per claim to detect press-release amplification. Each claim gets a verdict: verified / contested / rejected / uncertain.

5. **SYNTHESIZE** merges all outputs following `references/synthesize-guide.md`. Determines quality labels (`verification_status` using `verified_ratio`, `completion_status` from pipeline execution). Produces the final `synthesis.md` report.

## State management

All state lives in `~/.cache/delve/runs/<run_id>/`:

- `manifest.json` — run metadata (topic, depth, flags)
- `events.jsonl` — append-only event log (canonical source of truth)
- `state.json` — rebuildable index (current stage, per-stage status)
- `<stage>.done` — completion markers for fast resume detection
- `.lock/` + `lease.json` — concurrency control via atomic `mkdir`

The strict commit order for each stage: write artifact -> log event -> update state -> touch done marker.

## Trust boundaries

- Web content is treated as untrusted data, never as instructions
- Prompt injection heuristics are applied per `references/security-policy.md`
- Verification agents work independently from research agents (no shared context)
- `--providers claude` caps verification at `partially-verified` (same-model bias)
- No secrets, API keys, or PII are stored in run artifacts

## Resume

Runs survive interruption and system reboot. Resume checks `.done` markers to find the last completed stage, validates cache hashes for DIVE workers and VERIFY artifacts, and re-dispatches only what's needed. Changed prompt templates trigger downstream cascade invalidation.
