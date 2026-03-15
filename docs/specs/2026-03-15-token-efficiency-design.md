# Token Efficiency Optimization — Design Spec

## Problem

A medium-depth delve run consumes ~60-65K input tokens. The largest token sinks are:
1. Raw WebFetch content (70-95% HTML boilerplate) passed through DIVE agents
2. `source-authority-rules.md` (665 tokens) duplicated into 10-12 subagent prompts
3. Claim extraction receives all dive outputs monolithically (~20-30K tokens)
4. SYNTHESIZE receives duplicate data (output.json + output.md)
5. VERIFY receives bloated claim objects with full source arrays

**Target:** reduce to ~25-30K tokens (50-60% reduction) without degrading research quality.

## Research Inputs

- **trafilatura** (`~/contrib/trafilatura/`): Python library for web content extraction. Removes boilerplate HTML (navigation, ads, footers), returns clean article text. Benchmarked: 24.5K raw HTML -> 1.8K clean text (93% reduction). CLI: `uvx trafilatura -u URL --precision --no-comments --deduplicate --fast`.
- **rtk** (`~/contrib/rtk/`): Rust CLI for terminal output compression. Key patterns: tee+hint (save full content to file, pass summary to LLM), JSON schema extraction, normalized deduplication, overflow hints.
- **Codex review** (GPT-5.4): confirmed B-level approach, flagged risks in per-worker claim extraction (global dedupe loss), suggested hard caps in DIVE output and synthesis_input.json intermediate.

## Approach

**B+ strategy** — moderate optimizations + cherry-picked safe elements from aggressive tier.

Rolled out in 3 sequential steps:
- **Step 1 (A):** prompt-only changes, zero risk
- **Step 2 (B):** Python script + prompt changes, low risk with fallback
- **Step 3 (partial-C):** structural prompt changes for caching, low risk

## Step 1: Prompt Hygiene (A)

### 1.1 Drop output.md from downstream stages

**Files changed:** `SKILL.md` (5.1), `synthesize-guide.md` (FROZEN)

DIVE agents continue to produce output.md (written to disk for human debugging). But downstream stages no longer receive it as input:

- **Claim extraction** (SKILL.md 4.1): already uses only output.json per `claim-extraction-prompt.md` line 7. Verify that SKILL.md 4.1 text says "Collect all `dive/q_*/output.json` files" (line 542) — no output.md reference. No change needed.
- **SYNTHESIZE** (SKILL.md 5.1 + synthesize-guide.md): remove `dive/q_*/output.md` from both SKILL.md 5.1 input collection logic and synthesize-guide.md Inputs list. Synthesizer works from output.json (structured claims + citations + summary) + verdict files.

**synthesize-guide.md change (FROZEN — triggers cache invalidation):**
```
## Inputs

- `dive/q_*/output.json` — structured research per sub-question
- `verify/verdicts/c_*.json` — per-claim verification verdicts (if verify ran)
- `verify/summary.json` — aggregate verification stats (if verify ran)
- `scan/result.json` — original source list
```

**Cache invalidation:** synthesize-guide.md is FROZEN. Changing it invalidates SYNTHESIZE stage in cached runs. SKILL.md's resume protocol already checks SHA-256 of synthesize-guide.md (Resume Protocol → Cache validity section). Existing cached runs will re-run SYNTHESIZE automatically on resume — this is safe because SYNTHESIZE is the final stage with no downstream dependencies.

**Estimated saving:** ~10-15K tokens per run (output.md duplicated output.json content in verbose form).

### 1.2 Compress source-authority-rules.md

**File changed:** `source-authority-rules.md`

Current: 665 tokens with verbose prose, examples, edge cases.

New approach: two versions based on consumer needs.

**Full version (for DIVE agents):** Keep current file as-is. DIVE agents need the full ruleset to correctly classify sources they discover. ~665 tokens, but only sent to DIVE agents (4-5 copies max).

**Compact version (for VERIFY, claim extraction, SYNTHESIZE):** These stages already receive pre-classified `source_tier` values from DIVE. They need only the tier ordering and key rules, not the full domain lists.

Create `references/source-authority-rules-compact.md`:
```markdown
# Source Tiers (compact)

T1 (highest): official docs, specs, RFCs, peer-reviewed papers, .gov/.edu
T2 (standard): major news, Wikipedia, established tech pubs, 1k+ star repos
T3 (low): blogs, forums, social media, Medium, press releases

Rules: default T3, upgrade only on match. No transitive trust. Press releases always T3.
T3-only claims -> confidence: low. Multiple T3 citing same source = 1 confirmation.
```

~80 tokens instead of 665. SKILL.md updated: sections 4.1 (claim extraction) and 4.3 (VERIFY dispatch) changed from `Read references/source-authority-rules.md` to `Read references/source-authority-rules-compact.md`. SYNTHESIZE (5.1) also uses compact version.

**Cache invalidation:** `source-authority-rules-compact.md` is a new file, not currently tracked in the resume protocol's hash-check chain. Add it to SKILL.md's Resume Protocol: VERIFY cache validity must also hash `source-authority-rules-compact.md` alongside `claim-extraction-prompt.md` and `verify-prompt.md`. SYNTHESIZE cache validity must hash it alongside `synthesize-guide.md` and `security-policy.md`.

**Estimated saving:** ~5K tokens (saved on 6-7 VERIFY+inline copies: (665-80) * 7 = ~4K).

### 1.3 Hard cap on DIVE output

**File changed:** `dive-prompt.md`

Add output constraints to the dive-prompt.md output contract:

```markdown
## Output Limits

- Maximum 8 claims per sub-question
- Maximum 5 citations per sub-question
- Summary: 2-3 sentences (not a full report)
- Focus claims on directly answering the sub-question, not peripheral findings
```

This reduces DIVE output size, which cascades to smaller inputs for claim extraction and SYNTHESIZE.

**Estimated saving:** ~5-8K tokens across all downstream stages.

**Note on savings estimates:** Steps 1.1 and 1.3 have partially overlapping savings — smaller DIVE output (1.3) means smaller output.md too (1.1). The estimates are approximate upper bounds, not strictly additive. Combined Step 1 saving is ~15-22K tokens realistically.

### Step 1 total estimated saving: ~15-22K tokens (~25-35%)

---

## Step 2: Content Extraction Script (B)

### 2.1 Create `scripts/fetch_clean.py`

**New file:** `scripts/fetch_clean.py`

PEP 723 inline metadata script — self-contained, no venv needed:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["trafilatura"]
# ///
"""Fetch URL and extract clean article text via trafilatura."""

import json
import sys

from trafilatura import fetch_url, extract

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_clean.py <url> [max_chars]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    html = fetch_url(url)
    if not html:
        json.dump({"url": url, "status": "fetch_failed", "text": ""}, sys.stdout)
        sys.exit(0)

    text = extract(
        html,
        output_format="txt",
        favor_precision=True,
        include_comments=False,
        include_links=False,
        include_tables=True,
        deduplicate=True,
        fast=True,
    )

    if not text or len(text) < 100:
        json.dump({"url": url, "status": "extraction_failed", "text": ""}, sys.stdout)
        sys.exit(0)

    total_chars = len(text)
    if total_chars > max_chars:
        text = text[:max_chars]
        truncated = True
    else:
        truncated = False

    json.dump({
        "url": url,
        "status": "ok",
        "text": text,
        "total_chars": total_chars,
        "truncated": truncated,
    }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
```

**Output contract:** JSON to stdout with fields `url`, `status` (ok|fetch_failed|extraction_failed), `text`, `total_chars`, `truncated`.

**Dependencies:** `trafilatura` only. Managed by uv via PEP 723 — first run caches to `~/.cache/uv/`, subsequent runs instant.

### 2.2 Modify dive-prompt.md to use script

**File changed:** `dive-prompt.md`

Replace step 3 "Fetch and analyze":

```markdown
3. **Fetch and analyze** — For each promising URL, extract clean content using Bash:
   ```
   uv run PLUGIN_ROOT/scripts/fetch_clean.py "URL" 3000
   ```
   This returns JSON with `status`, `text`, `total_chars`, `truncated` fields.
   - If the command outputs valid JSON with `"status": "ok"`: use the extracted `text` for analysis
   - If `"status"` is `"fetch_failed"` or `"extraction_failed"`: fall back to WebFetch for that URL
   - If the command fails entirely (non-zero exit, no JSON output, or `uv` not found): fall back to WebFetch for that URL
   - The script strips HTML boilerplate (navigation, ads, footers) and returns only article content
```

**Fallback robustness:** The dive-prompt must handle three failure modes: (a) script returns error JSON (graceful), (b) script crashes / uv not installed (no JSON on stdout — shebang fails before Python runs), (c) script times out. In all cases the agent falls back to WebFetch. The prompt explicitly lists "no JSON output" as a fallback trigger.

**PLUGIN_ROOT resolution:** The orchestrator (SKILL.md) resolves `${CLAUDE_PLUGIN_ROOT}` at dispatch time and injects the absolute path into the dive prompt. Update SKILL.md 3.1 prompt-building steps (replacing existing steps, preserving resume auditability):

```
For each sub-question, build the full prompt:
1. Read dive-prompt.md content
2. Replace `PLUGIN_ROOT` with the resolved absolute path of the plugin root
3. Append source-authority-rules.md content (full version for DIVE agents)
4. Add sub-question details + relevant sources from scan/result.json
5. Write frozen prompt to `dive/q_<hash>/prompt.md` (preserved from current protocol — required for resume cache validity via input_hash/prompt_hash)
```

### 2.3 Slim VERIFY claim payload

**Files changed:** `SKILL.md` (4.3), `verify-prompt.md` (FROZEN)

**Data flow:** claim-extraction-prompt.md (FROZEN, NOT modified) continues to produce `original_sources` and `original_source_tiers` arrays as before. The **orchestrator** (SKILL.md 4.3) performs URL-to-domain reduction when building VERIFY batch payloads:

```
claim-extraction output (unchanged):
  original_sources: ["https://arxiv.org/abs/1234", "https://blog.example.com/post"]
  original_source_tiers: ["T1", "T3"]

orchestrator transforms to VERIFY batch payload:
  origin_domains: ["arxiv.org", "example.com"]
```

The transformation logic is added to SKILL.md 4.3: "For each claim in the batch, extract root domains from `original_sources` (scheme + netloc → domain only, deduplicated) and pass as `origin_domains` array."

Current claim object sent to VERIFY batches:
```json
{
  "claim_id": "c_abc123",
  "claim": "text",
  "original_sources": ["url1", "url2", "url3"],
  "original_source_tiers": ["T1", "T3", "T2"]
}
```

Optimized VERIFY batch payload (produced by orchestrator, not claim extractor):
```json
{
  "claim_id": "c_abc123",
  "claim": "text",
  "origin_domains": ["arxiv.org", "example.com"]
}
```

**Rationale:** VERIFY agents need `original_sources` only for independence check. Root domains are sufficient — the verifier checks domain independence, not URL-path uniqueness.

**verify-prompt.md changes (FROZEN — triggers cache invalidation):**

Update step 4 (currently line 20):
```markdown
4. **Check source independence** — Each claim includes `origin_domains` showing which
   root domains DIVE agents used. Your verification sources MUST come from different
   root domains. If all supporting evidence traces to the same domains, return
   `uncertain` not `verified`.
```

Update output schema (currently lines 40-53) — remove `original_sources` field, keep all other fields unchanged:
```json
[
  {
    "claim_id": "c_<hash>",
    "claim": "the claim text",
    "verdict": "verified | contested | rejected | uncertain",
    "evidence": "specific evidence supporting your verdict",
    "sources": ["URLs you consulted for verification"],
    "source_tiers": ["T1 | T2 | T3 — parallel array, source_tiers[i] corresponds to sources[i]"],
    "notes": "additional context, caveats, or the correction if rejected"
  }
]
```

Preserve the existing invariant (currently line 55): `**Invariant:** source_tiers and sources MUST have the same length.` — this line is NOT removed.

**Cache invalidation:** verify-prompt.md is FROZEN. Changing it invalidates all VERIFY artifacts in cached runs. SKILL.md resume protocol already hashes verify-prompt.md for VERIFY cache validity. Existing runs will re-run VERIFY on resume.

**Estimated saving:** ~3-5K tokens across VERIFY batches.

### Step 2 total estimated saving: ~10-15K tokens additional (on top of Step 1)

---

## Step 3: Prompt Caching Layout (partial-C)

### 3.1 Reorder prompt structure for cache hits

**Files changed:** `SKILL.md` (3.1, 4.3)

Claude's prompt caching works on shared prefixes. The current SKILL.md 3.1 says: "Read `references/source-authority-rules.md` once. Append its content to each dive prompt before dispatch." and then "Build the full prompt: dive-prompt.md content + sub-question details + relevant sources from scan/result.json". The exact insertion point of source-authority-rules.md relative to sub-question details is ambiguous. To guarantee cache-friendly ordering, we make it explicit:

New structure (explicit in SKILL.md 3.1):
```
[dive-prompt.md] + [source-authority-rules.md] + [sub-question (unique)] + [sources (unique)]
```

Shared prefix comes first. All DIVE agents share the same prefix → prompt cache hit after the first agent.

Same for VERIFY agents:
```
[verify-prompt.md] + [source-authority-rules-compact.md] + [claim batch (unique)]
```

**Estimated saving:** ~2-4K tokens (cache hits on shared prefix for agents 2-5).

### Step 3 total: ~2-4K tokens additional

---

## Total Estimated Impact

| Step | Saving | Cumulative | New baseline |
|------|--------|------------|-------------|
| Baseline | — | — | ~60-65K |
| Step 1 (A) | ~15-22K | ~15-22K | ~40-48K |
| Step 2 (B) | ~10-15K | ~25-37K | ~25-38K |
| Step 3 (C) | ~2-4K | ~27-41K | ~22-36K |

**Conservative estimate:** 45% reduction (65K -> 36K).
**Optimistic estimate:** 60% reduction (65K -> 25K).

Note: estimates are approximate and partially overlapping. Actual savings require token telemetry (see Deferred).

## Files Changed Summary

### Step 1
| File | Change | FROZEN? |
|------|--------|---------|
| `skills/delve/SKILL.md` | Update 5.1 to not collect output.md; update 4.1 and 4.3 to read `source-authority-rules-compact.md` instead of full rules; add compact file to Resume Protocol hash-check chain for VERIFY and SYNTHESIZE; add `source-authority-rules-compact.md` to Prompt Mutability section as FROZEN | No |
| `skills/delve/references/synthesize-guide.md` | Remove `dive/q_*/output.md` from Inputs list | **FROZEN** — invalidates SYNTHESIZE cache |
| `skills/delve/references/source-authority-rules-compact.md` | **New file** — 80-token compact tier rules for non-DIVE stages | New (add to Resume Protocol hash chain) |
| `skills/delve/references/dive-prompt.md` | Add Output Limits section (max 8 claims, 5 citations) | MUTABLE |

### Step 2
| File | Change | FROZEN? |
|------|--------|---------|
| `scripts/fetch_clean.py` | **New file** — PEP 723 trafilatura extraction script. Prerequisite: `mkdir scripts/` | New |
| `skills/delve/references/dive-prompt.md` | Replace WebFetch with fetch_clean.py + 3-tier fallback | MUTABLE |
| `skills/delve/SKILL.md` | Add PLUGIN_ROOT resolution in 3.1; add URL-to-domain transform in 4.3 for VERIFY batch payload | No |
| `skills/delve/references/verify-prompt.md` | Replace `original_sources` with `origin_domains` in step 4 and output schema | **FROZEN** — invalidates VERIFY cache |
| `.gitignore` (delve repo) | Add `scripts/__pycache__/` | N/A |

### Step 3
| File | Change | FROZEN? |
|------|--------|---------|
| `skills/delve/SKILL.md` | Make prompt assembly order explicit in 3.1 and 4.3 (shared prefix first, unique content last) | No |

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| trafilatura fails on JS-heavy/paywalled sites | Fallback to WebFetch in dive-prompt.md |
| uv not installed | Shebang fails before Python runs — no JSON on stdout. dive-prompt.md fallback handles "no JSON output" explicitly → WebFetch |
| Hard caps in DIVE lose important claims | 8 claims per sub-question is generous for focused questions. P0 retry already covers critical gaps |
| Slim VERIFY payload loses independence check fidelity | Root domains are sufficient — verifier checks domain independence, not URL-path uniqueness |
| output.md removal degrades SYNTHESIZE quality | output.json contains all claims, citations, summary, confidence. output.md added no unique data |
| Prompt reordering changes agent behavior | Reordering is content-preserving — same text, different position. Agents should behave identically |

## Deferred (future iterations, after telemetry)

- **URL-level cache** for trafilatura extractions (`normalized_url + extractor_version` key)
- **2-pass claim extraction**: per-worker local extract → global reducer (dedupe + union source_questions)
- **synthesis_input.json**: compact intermediate file before SYNTHESIZE (verified findings + contested + gaps + citation map)
- **Token telemetry**: log actual token counts per stage to events.jsonl for data-driven optimization

## Acceptance Criteria

1. ~~Medium-depth run consumes <= 35K input tokens~~ **Deferred** — requires token telemetry (not yet implemented). Manual spot-check: compare output.json sizes before/after optimization on the same topic
2. Research quality unchanged: same verification_status and completion_status on identical topics (manual comparison on 2-3 test topics)
3. `scripts/fetch_clean.py` works on macOS/Linux with `uv >= 0.4`. Test: `uv run scripts/fetch_clean.py "https://docs.python.org/3/library/asyncio.html" 2000` returns valid JSON with `status: "ok"`
4. Fallback to WebFetch works when: (a) script returns `extraction_failed`, (b) `uv` not installed (no JSON output), (c) URL is JS-heavy/paywalled
5. Resume protocol unbroken: FROZEN prompt changes (synthesize-guide.md, verify-prompt.md) trigger automatic re-run of their stages via SHA-256 hash mismatch. New file `source-authority-rules-compact.md` added to hash-check chain
6. All FROZEN prompt modifications version-bumped in CHANGELOG. `source-authority-rules-compact.md` added to Prompt Mutability section as FROZEN
