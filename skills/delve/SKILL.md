---
name: delve
description: >
  Use when user says "/delve", "deep research", "research this topic",
  "investigate", "delve into", or asks for comprehensive multi-source
  research on any topic. Stage-gated pipeline with parallel subagents,
  claim-level verification, and resume support.
---

# Delve — Deep Research Orchestrator

## Parsing

Match the user's `/delve` invocation:

1. No arguments or just `/delve` → show [Help](#help)
2. First word is `resume` → [Resume Protocol](#resume-protocol)
3. First word is `status` → [Status Command](#status-command)
4. Otherwise → extract flags + topic

**Flags** (extract before treating remainder as topic):
- `--quick` — skip DIVE + VERIFY stages
- `--depth shallow|medium|deep` — agent intensity (default: `medium`)
- `--providers claude` — sensitivity routing, blocks external models
- `--output <path>` — custom output path for synthesis.md

**Conflicts:**
- `--quick` + `--depth` → ignore depth (quick always skips dive/verify)

## Constants

| Name | Value | Notes |
|------|-------|-------|
| CACHE_DIR | `~/.cache/delve/runs` | Per-run registry files |
| WORKER_TIMEOUT_MS | 120000 | Bash tool `timeout` parameter |
| COVERAGE_THRESHOLD | 0.7 | Min weighted coverage to proceed |
| CONTESTED_THRESHOLD | 0.3 | Above → mark as `draft` |
| P_WEIGHTS | P0=3, P1=2, P2=1 | For coverage calculation |

Depth → parallelism:

| Depth | Sub-questions | Max concurrent agents |
|-------|---------------|-----------------------|
| shallow | 2 | 2 |
| medium | 3-4 | 4 |
| deep | 5-6 | 6 |

## Run Initialization

Before any stage:

1. Generate run_id:
```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
```

2. Create run directory + subdirs:
```bash
RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/delve.XXXXXX")
chmod 700 "$RUN_DIR"
mkdir -p "$RUN_DIR"/{scan,decompose,dive,verify/verdicts,output}
mkdir -p ~/.cache/delve/runs
```

3. Write `manifest.json` (atomic: write to temp, mv):
```bash
TMP=$(mktemp "$RUN_DIR/.tmp.XXXXXX")
cat > "$TMP" << 'EOF'
<manifest JSON per checkpoint-schema.md>
EOF
mv "$TMP" "$RUN_DIR/manifest.json"
```

4. Acquire lock: `mkdir "$RUN_DIR/.lock"`. Write `lease.json` as sibling (NOT inside .lock/):
```json
// $RUN_DIR/lease.json (sibling of .lock/, not inside it)
{"pid": <$$>, "host": "<hostname>", "started_at": "<ISO>", "lease_id": "<run_id>"}
```

5. Initialize `state.json` (rebuildable index, updated after each stage):
```json
{
  "run_id": "<run_id>",
  "current_stage": "scan",
  "stages": {
    "scan": {"status": "pending"},
    "decompose": {"status": "pending"},
    "dive": {"status": "pending"},
    "verify": {"status": "pending"},
    "synthesize": {"status": "pending"}
  },
  "updated_at": "<ISO>"
}
```

6. Register run: write `~/.cache/delve/runs/<run_id>.json`

7. Append to `events.jsonl`:
```json
{"event": "run_started", "run_id": "<id>", "topic": "<topic>", "depth": "<depth>", "ts": "<ISO>"}
```

8. Announce:
```
Starting deep research: <topic>
Depth: <depth> | Run: <run_id>
```

Proceed to [Stage 1: SCAN](#stage-1-scan).

## Stage 1: SCAN

**Inline, ~20-30s. No subagents.**

### 1.1 Check existing research

Search for prior work on this topic:

```
Glob: docs/research/*<topic-keywords>*.md
Grep: <topic keywords> across docs/research/
```

For each match, read the frontmatter to check date and coverage.

### 1.2 Web search

Use WebSearch — 3-5 queries:
1. `<topic>` (verbatim)
2. `<topic> 2026 overview` (recency-biased)
3. `<topic> comparison alternatives` (breadth)
4-5. Topic-specific variations based on scan context

### 1.3 Fetch previews

Use WebFetch on the top-5 results by estimated relevance. Extract title, first 500 chars of content for snippet.

If WebFetch fails for a URL → mark `"fetched": false`, continue with others.

If WebSearch is unavailable → fallback to existing research only + warn user.

### 1.4 Write output

Write `scan/result.json` (atomic: temp + mv). Schema per `references/checkpoint-schema.md`.

### 1.5 Decision gate

| Gate | Condition | Action |
|------|-----------|--------|
| `no_evidence` | 0 web sources + 0 existing research | Warn user. Offer: abort or proceed with first-principles analysis |
| `reuse` | Comprehensive existing research < 30 days old | Skip to SYNTHESIZE, merge existing docs |
| `refresh` | Existing research > 30 days old | DIVE focuses on deltas and new sources |
| `extend` | Partial existing research (some aspects uncovered) | DIVE focuses on uncovered aspects |
| `full-run` | No prior research found | Full pipeline |

If `--quick` flag: after writing scan output → skip directly to [Stage 5: SYNTHESIZE](#stage-5-synthesize) with scan sources only.

If `reuse` gate: skip to [Stage 5: SYNTHESIZE](#stage-5-synthesize) using existing research files.

Log event: `{"event": "scan_complete", "sources_count": N, "existing_count": N, "decision_gate": "<gate>"}`.
Update `state.json`: `current_stage → "decompose"`, `stages.scan.status → "done"`, `stages.scan.completed_at`.
Touch `scan.done`.

**Note: every stage must follow this strict commit order:**
1. Write artifact (result.json, sub-tasks.json, etc.)
2. Log event to events.jsonl
3. Update state.json
4. Touch `<stage>.done` marker
