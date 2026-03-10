# Claim Extraction Prompt

You are decomposing research outputs into atomic, verifiable claims for independent verification.

## Input

You will receive multiple `output.json` files from research agents, each containing claims, citations, and a summary.

## Process

1. **Extract claims** — From each output.json, extract every factual statement. Break compound claims into atomic ones (one verifiable fact per claim).
2. **Classify** — Assign each claim a type:
   - `factual` — verifiable statement about the world (e.g., "Python 3.12 added inline comprehensions")
   - `quantitative` — involves specific numbers, percentages, or measurements (e.g., "throughput increased 40%")
   - `methodology` — describes how something works or should be done (e.g., "use connection pooling for database access")
   - `opinion` — subjective assessment, even if from an expert (e.g., "Rust is the best choice for this use case")
   - `time-sensitive` — claim whose truth depends on when it was made (e.g., "X is the latest version")
3. **Deduplicate** — If the same claim appears in multiple outputs from different sub-questions, keep ONE instance but record all source_questions.
4. **Source independence check** — If multiple claims trace to the same original URL or source document, note this. Three articles quoting the same press release = one source, not three.
5. **Assign priority** — `high` for claims central to the research topic, `medium` for supporting claims, `low` for peripheral claims.
6. **Do NOT generate IDs** — The orchestrator will assign `c_<hash>` IDs after receiving your output. Use sequential placeholder keys (`claim_1`, `claim_2`, ...) in your output.

## Output

Return a JSON object with claims keyed by sequential placeholders. The orchestrator will replace keys with `c_<hash>` IDs computed via `printf '%s' "$(echo "<text>" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')" | shasum -a 256 | cut -c1-6`.

```json
{
  "claims": {
    "claim_1": {
      "text": "exact claim text",
      "type": "factual",
      "source_questions": ["q_abc123", "q_def456"],
      "original_sources": ["https://example.com/article"],
      "priority": "high"
    }
  },
  "total": 15,
  "by_type": {
    "factual": 8,
    "quantitative": 3,
    "methodology": 2,
    "opinion": 1,
    "time-sensitive": 1
  }
}
```

## Rules

- Skip tautologies, hedged statements ("might", "could potentially"), and vague generalizations
- Skip opinions unless they are from a named expert and attributed
- Maximum 30 claims per run (prioritize high-priority claims if more exist)
- Every claim must be traceable to at least one source URL or document
- Do NOT invent claims — only extract what the research agents actually found
