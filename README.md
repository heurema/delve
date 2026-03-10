# Delve

<div align="center">

**Autonomous deep research with claim-level verification**

[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-5b21b6?style=flat-square)](https://skill7.dev/plugins/delve)
[![Version](https://img.shields.io/badge/version-0.2.0-5b21b6?style=flat-square)](https://github.com/heurema/delve)
[![License MIT](https://img.shields.io/badge/license-MIT-5b21b6?style=flat-square)](LICENSE)

```bash
claude plugin marketplace add heurema/emporium
claude plugin install delve@emporium
```

</div>

## What it does

Research tasks need more than a single web search. Delve runs a stage-gated pipeline that scans for sources, decomposes the topic into sub-questions, dispatches parallel research subagents, then verifies every claim through adversarial fact-checking before producing a synthesis report. Each stage checkpoints to disk so interrupted runs resume from where they left off.

## Install

<!-- INSTALL:START — auto-synced from emporium/INSTALL_REFERENCE.md -->
```bash
claude plugin marketplace add heurema/emporium
claude plugin install delve@emporium
```
<!-- INSTALL:END -->

<details>
<summary>Manual install from source</summary>

```bash
git clone https://github.com/heurema/delve
cd delve
claude plugin install .
```

</details>

## Quick start

```bash
# Full research pipeline (default: medium depth, 3-4 agents)
/delve "WebSocket vs SSE for real-time updates"

# Fast scan + synthesize (skip dive & verify)
/delve "OAuth 2.1 changes" --quick

# Maximum depth with 6 parallel agents
/delve "Rust async runtimes" --depth deep
```

## Commands

| Command | Description |
|---------|-------------|
| `/delve <topic>` | Full research pipeline |
| `/delve <topic> --quick` | Scan + synthesize only |
| `/delve <topic> --depth <level>` | `shallow` (2) / `medium` (4) / `deep` (6) agents |
| `/delve <topic> --providers claude` | Single-model mode, no external AI |
| `/delve <topic> --output <path>` | Custom output location |
| `/delve resume [run_id]` | Resume interrupted run |
| `/delve status` | List recent runs |

## Pipeline

```
SCAN -> DECOMPOSE -> DIVE -> VERIFY -> SYNTHESIZE
 |          |          |        |          |
 |          |          |        |          +- Merge + annotate -> synthesis.md
 |          |          |        +- Adversarial claim verification
 |          |          +- Parallel research subagents
 |          +- Topic decomposition + HITL approval
 +- Web search + existing research check
```

## Depth levels

| Depth | Agents | Verify | Time |
|-------|--------|--------|------|
| `--quick` | 0 | skip | ~60-90s |
| `shallow` | 2 | top 30% | ~3-5 min |
| `medium` | 3-4 | all factual | ~6-10 min |
| `deep` | 5-6 | all + cross | ~10-20 min |

## Quality model

Two independent axes:
- **Verification**: verified / partially-verified / unverified
- **Completion**: complete / incomplete / synthesis_only / draft

Reports include a methodology section with exact quality labels, claim counts, and source attribution.

## Resume

Runs checkpoint after each stage to `~/.cache/delve/runs/`. Resume interrupted runs:

```
/delve resume              # pick from recent runs
/delve resume <run_id>     # resume specific run
```

## Requirements

- Claude Code with skill support
- WebSearch and WebFetch tools available (for SCAN and DIVE stages)
- Git repository context (for saving reports to `docs/research/`)

## Privacy

Delve uses Claude Code subagents and built-in WebSearch/WebFetch tools. Your research topic and web content are processed through Claude's standard API under your existing authentication. No data is sent to additional endpoints beyond what Claude Code normally uses. When `--providers claude` is active, no external AI models are invoked and the topic is redacted in local event logs.

## Feedback

If the verifier returns incorrect verdicts, the pipeline stalls, or resume doesn't work — file it from Claude Code with [Reporter](https://github.com/heurema/reporter):

```bash
claude plugin install reporter@emporium
```

Then: `/report bug` or `/report feature` or `/report question`

## See also

- [skill7.dev/plugins/delve](https://skill7.dev/plugins/delve) — plugin page and changelog
- [github.com/heurema/emporium](https://github.com/heurema/emporium) — plugin registry
- [docs/how-it-works.md](docs/how-it-works.md) — architecture, data flow, verification model
- [docs/reference.md](docs/reference.md) — all commands, options, output format, troubleshooting

## License

[MIT](LICENSE)
