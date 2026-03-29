# Checkpoint Schema Reference

Version: 1.0

## lease.json

Sibling of `.lock/` directory (NOT inside it). Written at lock acquisition, read on resume.

```json
{
  "pid": "integer — process ID of the orchestrator",
  "host": "string — hostname",
  "started_at": "ISO 8601 timestamp",
  "lease_id": "string — same as run_id"
}
```

## manifest.json

Frozen at run start. Never modified after creation.

```json
{
  "run_id": "string — YYYYMMDDTHHMMSSZ-PID",
  "topic": "string — original research topic",
  "depth": "shallow | medium | deep",
  "quick": "boolean",
  "providers": "all | claude",
  "output_path": "string — custom or default output path",
  "schema_version": "1.0",
  "created_at": "ISO 8601 timestamp",
  "original_request": "string — full user input verbatim"
}
```

## events.jsonl

Append-only. CANONICAL source of truth. One JSON object per line.

Common fields: `event`, `ts` (ISO 8601), `run_id`.

Events:
- `run_started` — `{topic, depth, providers}`
- `scan_complete` — `{sources_count, existing_count, decision_gate}`
- `decompose_complete` — `{total, active, skipped}`
- `worker_dispatched` — `{task_id, question, priority}`
- `worker_complete` — `{task_id, status, duration_ms, claims_count}`
- `worker_timeout` — `{task_id, timeout_ms}`
- `worker_error` — `{task_id, error}`
- `worker_retry` — `{task_id, attempt}`
- `dive_complete` — `{completed, failed, coverage}`
- `claim_extraction_complete` — `{total_claims, by_type, prompt_hashes}`
- `verify_complete` — `{verified, contested, rejected, uncertain}`
- `overlap_analysis_complete` — `{avg_overlap_ratio, pair_count}` — emitted after Stage 3.5 source overlap detection
- `source_saturation_detected` — `{overlap_ratio, pairs_affected}` — emitted when avg_overlap_ratio > 0.6 (warning only)
- `synthesize_complete` — `{verification_status, completion_status, composite_score, output_path, prompt_hashes}`
- `run_complete` — `{duration_ms, status}`
- `run_aborted` — `{reason, stage}`
- `run_cancelled` — `{stage}`
- `resume_started` — `{from_stage, rerun_tasks[]}`

## state.json

REBUILDABLE from events.jsonl + .done markers. Updated after each stage.

```json
{
  "run_id": "string",
  "current_stage": "scan | decompose | dive | verify | synthesize | complete | aborted",
  "stages": {
    "scan": {"status": "done | pending", "completed_at": "ISO"},
    "decompose": {"status": "done | pending", "completed_at": "ISO"},
    "dive": {"status": "done | partial | pending", "completed": 3, "total": 4},
    "verify": {"status": "done | skipped | pending", "completed_at": "ISO"},
    "synthesize": {"status": "done | pending", "completed_at": "ISO"}
  },
  "updated_at": "ISO"
}
```

## scan/result.json

```json
{
  "sources": [
    {
      "url": "string",
      "title": "string",
      "snippet": "string — first 500 chars of fetched content",
      "relevance": "float 0-1",
      "fetched": "boolean — whether WebFetch succeeded"
    }
  ],
  "existing_research": [
    {"path": "string", "date": "YYYY-MM-DD", "coverage": "full | partial"}
  ],
  "decision_gate": "full-run | extend | refresh | reuse | no_evidence",
  "gate_rationale": "string"
}
```

## decompose/sub-tasks.json

```json
{
  "tasks": {
    "q_<6hex>": {
      "question": "string",
      "priority": "P0 | P1 | P2",
      "depends_on": ["q_<6hex>"],
      "estimated_sources": "integer",
      "rationale": "string",
      "skip": "boolean",
      "skip_reason": "string | null"
    }
  },
  "total": "integer",
  "active": "integer",
  "skipped": "integer"
}
```

Hash: first 6 hex chars of SHA-256 of question text (lowercase).

## dive/q_\<hash\>/output.json

```json
{
  "question": "string — the sub-question",
  "claims": [
    {
      "text": "string — one verifiable factual statement",
      "source": "string — URL or doc path",
      "source_tier": "T1 | T2 | T3",
      "confidence": "high | medium | low"
    }
  ],
  "citations": [
    {
      "url": "string",
      "title": "string",
      "accessed": "ISO date",
      "source_tier": "T1 | T2 | T3",
      "stale": "boolean — true if source appears >12 months old (agent-assessed from content)"
    }
  ],
  "confidence": "high | medium | low — overall assessment",
  "gaps": ["string — areas needing further research"],
  "summary": "string — 2-3 sentence summary"
}
```

## dive/q_\<hash\>/status.json

```json
{
  "status": "completed | timeout | error | pending | retrying",
  "model": "string — agent type used",
  "attempt_id": "integer — starts at 1",
  "started_at": "ISO",
  "completed_at": "ISO | null",
  "duration_ms": "integer | null",
  "input_hash": "string — SHA-256 of prompt sent",
  "prompt_hash": "string — SHA-256 of dive-prompt.md content",
  "depth_ratio": "float | null — crawl_calls / total_calls, written on completion",
  "error": "string | null"
}
```

## verify/claims.json

```json
{
  "claims": {
    "c_<6hex>": {
      "text": "string — atomic claim",
      "type": "factual | opinion | methodology | quantitative | time-sensitive",
      "source_questions": ["q_<hash>"],
      "original_sources": ["string — URL or path"],
      "original_source_tiers": ["T1 | T2 | T3 — parallel array, [i] corresponds to original_sources[i]"],
      "priority": "high | medium | low"
    }
  },
  "total": "integer",
  "by_type": {"factual": 0, "quantitative": 0, "methodology": 0, "opinion": 0, "time-sensitive": 0}
}
```

Hash: first 6 hex chars of SHA-256 of claim text (lowercase).

## verify/verdicts/c_\<hash\>.json

```json
{
  "claim_id": "c_<6hex>",
  "claim": "string",
  "verdict": "verified | contested | rejected | uncertain",
  "evidence": "string — supporting or contradicting evidence",
  "sources": ["string — verification source URLs"],
  "source_tiers": ["T1 | T2 | T3 — parallel array, [i] corresponds to sources[i]"],
  "notes": "string | null"
}
```

## verify/summary.json

```json
{
  "total": "integer",
  "verified": "integer",
  "contested": "integer",
  "rejected": "integer",
  "uncertain": "integer",
  "coverage": "float 0-1 — fraction of claims that received any verdict",
  "verified_ratio": "float 0-1 — fraction with verdict=verified",
  "contested_ratio": "float 0-1"
}
```

## output/synthesis.json

```json
{
  "run_id": "string",
  "topic": "string",
  "depth": "string",
  "verification_status": "verified | partially-verified | unverified",
  "completion_status": "complete | incomplete | synthesis_only | draft | cancelled | no_evidence",
  "sources_count": "integer",
  "claims": {
    "total": "integer",
    "verified": "integer",
    "contested": "integer",
    "rejected": "integer"
  },
  "timing": {
    "total_ms": "integer",
    "scan_ms": "integer",
    "decompose_ms": "integer",
    "dive_ms": "integer",
    "verify_ms": "integer",
    "synthesize_ms": "integer"
  },
  "agents_used": "integer",
  "output_path": "string",
  "created_at": "ISO"
}
```

## Run Registry Entry

`~/.cache/delve/runs/<run_id>.json`:

```json
{
  "run_id": "string",
  "topic": "string",
  "depth": "string",
  "status": "running | completed | aborted | cancelled",
  "run_dir": "string — absolute path to tmpdir",
  "created_at": "ISO",
  "completed_at": "ISO | null",
  "output": "string | null — path to synthesis.md"
}
```
