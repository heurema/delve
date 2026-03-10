# delve

Deep research orchestrator for Claude Code. Autonomous multi-agent research with stage-gated pipeline, claim-level verification, and resume support.

## Install

```bash
claude plugin add ~/personal/heurema/delve
```

## Usage

```
/delve <topic>                    Full research pipeline
/delve <topic> --quick            Fast scan + synthesize
/delve <topic> --depth deep       Maximum depth (6 agents)
/delve <topic> --providers claude  No external AI models
/delve resume [run_id]            Resume from checkpoint
/delve status                     List recent runs
```

## Pipeline

```
SCAN → DECOMPOSE → DIVE → VERIFY → SYNTHESIZE
 │         │         │        │         │
 │         │         │        │         └─ Merge + annotate → synthesis.md
 │         │         │        └─ Adversarial claim verification
 │         │         └─ Parallel research subagents
 │         └─ Topic decomposition + HITL approval
 └─ Web search + existing research check
```

## Depth Levels

| Depth | Agents | Verify | Time |
|-------|--------|--------|------|
| `--quick` | 0 | skip | ~60-90s |
| `shallow` | 2 | top 30% | ~3-5 min |
| `medium` | 3-4 | all factual | ~6-10 min |
| `deep` | 5-6 | all + cross | ~10-20 min |

## Output

Reports saved to `docs/research/YYYY-MM-DD-<topic>-<id>.md` with:
- Verified key findings
- Contested points with both sides
- Full source list
- Methodology and quality labels

## Quality Model

Two independent axes:
- **Verification**: verified / partially-verified / unverified
- **Completion**: complete / incomplete / synthesis_only / draft

## Resume

Runs checkpoint after each stage. Resume interrupted runs:

```
/delve resume              # pick from recent runs
/delve resume <run_id>     # resume specific run
```

## License

MIT
