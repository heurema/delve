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
6. **Propagate source tiers** — For each claim, carry over the `source_tier` from the originating dive output's claim. When deduplicating claims from multiple dive outputs with different tiers:
   - Preserve all source URLs and their tiers
   - `original_source_tiers[i]` corresponds to `original_sources[i]` (same length, index-aligned)
   - Sort highest tier first (T1 > T2 > T3) when ordering the arrays
   - If the same claim has `source_tier: "T1"` in one dive output and `source_tier: "T3"` in another, the deduplicated claim gets `original_sources: ["url_T1", "url_T3"]` and `original_source_tiers: ["T1", "T3"]`
7. **Do NOT generate IDs** — The orchestrator will assign `c_<hash>` IDs after receiving your output. Use sequential placeholder keys (`claim_1`, `claim_2`, ...) in your output.

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
      "original_source_tiers": ["T2"],
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
- Maximum {{MAX_CLAIMS}} claims per run (prioritize high-priority claims if more exist)
- Every claim must be traceable to at least one source URL or document
- Do NOT invent claims — only extract what the research agents actually found
