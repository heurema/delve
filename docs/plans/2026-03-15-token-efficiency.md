# Token Efficiency Optimization — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce delve's token consumption by 45-60% (65K -> 25-36K) without degrading research quality.

**Architecture:** Three sequential steps: (A) prompt hygiene — drop duplicate data, compress rules, cap output; (B) Python extraction script + VERIFY payload slimming; (C) prompt reordering for cache hits. All changes are to markdown prompt files + one Python script. No runtime infrastructure changes.

**Tech Stack:** Markdown (SKILL.md, reference prompts), Python 3.11+ (trafilatura via PEP 723 + uv)

**Spec:** `docs/specs/2026-03-15-token-efficiency-design.md`

---

## Chunk 1: Step 1 — Prompt Hygiene

### Task 1: Drop output.md from SYNTHESIZE inputs

**Files:**
- Modify: `skills/delve/references/synthesize-guide.md:9-12`
- Modify: `skills/delve/SKILL.md:624-625`

- [ ] **Step 1: Edit synthesize-guide.md — remove output.md from Inputs**

In `skills/delve/references/synthesize-guide.md`, replace lines 9-12:

```
- `dive/q_*/output.json` — structured research per sub-question
- `dive/q_*/output.md` — human-readable research per sub-question
- `verify/verdicts/c_*.json` — per-claim verification verdicts (if verify ran)
- `verify/summary.json` — aggregate verification stats (if verify ran)
```

with:

```
- `dive/q_*/output.json` — structured research per sub-question
- `verify/verdicts/c_*.json` — per-claim verification verdicts (if verify ran)
- `verify/summary.json` — aggregate verification stats (if verify ran)
```

- [ ] **Step 2: Edit SKILL.md 5.1 — remove output.md from input collection**

In `skills/delve/SKILL.md`, replace line 625:

```
- `dive/q_*/output.json` and `output.md` (from completed workers)
```

with:

```
- `dive/q_*/output.json` (from completed workers)
```

- [ ] **Step 3: Verify no other references to output.md in downstream stages**

Run: `grep -n 'output\.md' skills/delve/SKILL.md | grep -v 'Write.*output\.md\|dive/q_.*output\.md.*output\.json'`

Expected: only DIVE stage references (3.3 write) and contrarian section remain. No references in stages 4 or 5.

- [ ] **Step 4: Commit**

```bash
git add skills/delve/references/synthesize-guide.md skills/delve/SKILL.md
git commit -m "feat: drop output.md from SYNTHESIZE and claim extraction inputs"
```

---

### Task 2: Create compact source-authority-rules

**Files:**
- Create: `skills/delve/references/source-authority-rules-compact.md`
- Modify: `skills/delve/SKILL.md:540` (4.1 claim extraction)
- Modify: `skills/delve/SKILL.md:633` (5.1 SYNTHESIZE)

- [ ] **Step 1: Create source-authority-rules-compact.md**

Write `skills/delve/references/source-authority-rules-compact.md`:

```markdown
# Source Tiers (compact)

T1 (highest): official docs, specs, RFCs, peer-reviewed papers, .gov/.edu
T2 (standard): major news, Wikipedia, established tech pubs, 1k+ star repos
T3 (low): blogs, forums, social media, Medium, press releases

Rules: default T3, upgrade only on match. No transitive trust. Press releases always T3.
T3-only claims -> confidence: low. Multiple T3 citing same source = 1 confirmation.
```

- [ ] **Step 2: Edit SKILL.md 4.1 — use compact rules for claim extraction**

In `skills/delve/SKILL.md`, replace line 540:

```
Read `references/source-authority-rules.md` for tier classification context.
```

with:

```
Read `references/source-authority-rules-compact.md` for tier classification context.
```

- [ ] **Step 3: Edit SKILL.md 5.1 — use compact rules for SYNTHESIZE**

In `skills/delve/SKILL.md`, replace line 633:

```
Read `references/source-authority-rules.md` for tier definitions.
```

with:

```
Read `references/source-authority-rules-compact.md` for tier definitions.
```

- [ ] **Step 4: Verify VERIFY (4.3) still uses full rules**

Run: `grep -n 'source-authority-rules' skills/delve/SKILL.md`

Expected: line 309 and 575 still reference `source-authority-rules.md` (full version for DIVE and VERIFY). Lines 540 and 633 now reference `source-authority-rules-compact.md`.

- [ ] **Step 5: Commit**

```bash
git add skills/delve/references/source-authority-rules-compact.md skills/delve/SKILL.md
git commit -m "feat: compact source-authority-rules for claim extraction and SYNTHESIZE"
```

---

### Task 3: Update Prompt Mutability and Resume Protocol

**Files:**
- Modify: `skills/delve/SKILL.md:56-64` (Prompt Mutability)
- Modify: `skills/delve/SKILL.md:782-788` (Resume Protocol cache validity)
- Modify: `skills/delve/references/checkpoint-schema.md:52,56` (event types)

- [ ] **Step 1: Add compact rules to Prompt Mutability section**

In `skills/delve/SKILL.md`, after line 61 (`- source-authority-rules.md ...`), add:

```
- `source-authority-rules-compact.md` — compact tier summary for claim extraction and SYNTHESIZE; changes alter tier context
```

- [ ] **Step 2: Add compact rules to Resume Protocol hash checks**

In `skills/delve/SKILL.md`, replace lines 782-784:

```
**VERIFY artifacts:** If `claim-extraction-prompt.md` or `verify-prompt.md` changed since last run:
- Compare SHA-256 of current prompt file vs hash stored in events.jsonl `claim_extraction_complete` event
- Mismatch → delete `verify/claims.json` + all `verify/verdicts/c_*.json` + `verify.done`, re-run VERIFY from scratch
```

with:

```
**VERIFY artifacts:** If `claim-extraction-prompt.md`, `verify-prompt.md`, or `source-authority-rules-compact.md` changed since last run:
- Compare SHA-256 of current prompt files vs hashes stored in events.jsonl `claim_extraction_complete` event's `prompt_hashes` field
- Mismatch → delete `verify/claims.json` + all `verify/verdicts/c_*.json` + `verify.done`, re-run VERIFY from scratch
```

Replace lines 786-788:

```
**SYNTHESIZE artifacts:** If `synthesize-guide.md` or `security-policy.md` changed since last run:
- Compare SHA-256 of current prompt file vs hash stored in events.jsonl `synthesize_complete` event
- Mismatch → delete `output/synthesis.md` + `output/synthesis.json` + `synthesize.done`, re-run SYNTHESIZE
```

with:

```
**SYNTHESIZE artifacts:** If `synthesize-guide.md`, `security-policy.md`, or `source-authority-rules-compact.md` changed since last run:
- Compare SHA-256 of current prompt files vs hashes stored in events.jsonl `synthesize_complete` event's `prompt_hashes` field
- Mismatch → delete `output/synthesis.md` + `output/synthesis.json` + `synthesize.done`, re-run SYNTHESIZE
```

- [ ] **Step 3: Add prompt_hashes to checkpoint event types**

In `skills/delve/references/checkpoint-schema.md`, replace line 52:

```
- `claim_extraction_complete` — `{total_claims, by_type}`
```

with:

```
- `claim_extraction_complete` — `{total_claims, by_type, prompt_hashes}`
```

Replace line 56:

```
- `synthesize_complete` — `{verification_status, completion_status, composite_score, output_path}`
```

with:

```
- `synthesize_complete` — `{verification_status, completion_status, composite_score, output_path, prompt_hashes}`
```

- [ ] **Step 4: Update SKILL.md event emission lines to include prompt_hashes**

In `skills/delve/SKILL.md`, find the claim extraction log event (around line 557):

```
Log event: `{"event": "claim_extraction_complete", "total_claims": N, "by_type": {...}}`.
```

Replace with:

```
Log event: `{"event": "claim_extraction_complete", "total_claims": N, "by_type": {...}, "prompt_hashes": {"claim-extraction-prompt.md": "<SHA-256>", "source-authority-rules-compact.md": "<SHA-256>"}}`.
```

Find the synthesize log event (in Stage 5.4):

```
{"event": "synthesize_complete", "verification_status": "...", "completion_status": "...", "composite_score": <float 0-1>, "output_path": "..."}
```

Replace with:

```
{"event": "synthesize_complete", "verification_status": "...", "completion_status": "...", "composite_score": <float 0-1>, "output_path": "...", "prompt_hashes": {"synthesize-guide.md": "<SHA-256>", "security-policy.md": "<SHA-256>", "source-authority-rules-compact.md": "<SHA-256>"}}
```

- [ ] **Step 5: Commit**

```bash
git add skills/delve/SKILL.md skills/delve/references/checkpoint-schema.md
git commit -m "feat: add source-authority-rules-compact to prompt mutability and resume hash chain"
```

---

### Task 4: Hard cap on DIVE output

**Files:**
- Modify: `skills/delve/references/dive-prompt.md:96-101`

- [ ] **Step 1: Add Output Limits section to dive-prompt.md**

In `skills/delve/references/dive-prompt.md`, before the `## Security Rules` section (line 84), insert:

```markdown
## Output Limits

- Maximum 8 claims per sub-question
- Maximum 5 citations per sub-question
- Summary: 2-3 sentences (not a full report)
- Focus claims on directly answering the sub-question, not peripheral findings
- If you found more claims than the limit, add `"claims_omitted": N` to your output.json (where N is the count of omitted claims)

```

- [ ] **Step 2: Verify placement**

Run: `grep -n 'Output Limits\|Security Rules\|claims_omitted' skills/delve/references/dive-prompt.md`

Expected: `Output Limits` appears before `Security Rules`. `claims_omitted` appears in the limits section.

- [ ] **Step 3: Commit**

```bash
git add skills/delve/references/dive-prompt.md
git commit -m "feat: hard cap DIVE output — max 8 claims, 5 citations, overflow signal"
```

---

## Chunk 2: Step 2 — Content Extraction Script

### Task 5: Create fetch_clean.py

**Files:**
- Create: `scripts/fetch_clean.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create scripts directory**

```bash
mkdir -p scripts
```

- [ ] **Step 2: Write fetch_clean.py**

Write `scripts/fetch_clean.py` with exact content from spec (section 2.1):

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["trafilatura"]
# ///
"""Fetch URL and extract clean article text via trafilatura."""

import json
import signal
import sys

from trafilatura import bare_extraction, fetch_url
from trafilatura.settings import use_config

# Hard timeout: 15s total (fetch + extract). Prevents hung network stalls.
signal.signal(signal.SIGALRM, lambda *_: sys.exit(124))
signal.alarm(15)


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_clean.py <url> [max_chars]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    config = use_config()
    config.set("DEFAULT", "DOWNLOAD_TIMEOUT", "10")

    html = fetch_url(url, config=config)
    if not html:
        json.dump({"url": url, "status": "fetch_failed", "text": ""}, sys.stdout)
        sys.exit(0)

    doc = bare_extraction(
        html,
        url=url,
        favor_precision=True,
        include_comments=False,
        include_links=False,
        include_tables=True,
        deduplicate=True,
        fast=True,
    )

    if not doc or not doc.text or len(doc.text) < 100:
        json.dump({"url": url, "status": "extraction_failed", "text": ""}, sys.stdout)
        sys.exit(0)

    text = doc.text
    total_chars = len(text)
    if total_chars > max_chars:
        text = text[:max_chars]
        truncated = True
    else:
        truncated = False

    json.dump({
        "url": url,
        "status": "ok",
        "title": doc.title or "",
        "date": doc.date or "",
        "text": text,
        "total_chars": total_chars,
        "truncated": truncated,
    }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/fetch_clean.py
```

- [ ] **Step 4: Test the script**

```bash
uv run scripts/fetch_clean.py "https://docs.python.org/3/library/asyncio.html" 2000
```

Expected: valid JSON with `"status": "ok"`, non-empty `"title"`, `"text"` field with clean article text, `"total_chars"` > 0.

- [ ] **Step 5: Test failure mode — bad URL**

```bash
uv run scripts/fetch_clean.py "https://thisdomaindoesnotexist12345.com" 2000
```

Expected: JSON with `"status": "fetch_failed"`.

- [ ] **Step 6: Add to .gitignore**

Append to `.gitignore`:

```
scripts/__pycache__/
```

- [ ] **Step 7: Commit**

```bash
git add scripts/fetch_clean.py .gitignore
git commit -m "feat: add fetch_clean.py — trafilatura-based content extraction"
```

---

### Task 6: Update dive-prompt.md to use fetch_clean.py

**Files:**
- Modify: `skills/delve/references/dive-prompt.md:9`
- Modify: `skills/delve/SKILL.md:305-313` (3.1 prompt building)

- [ ] **Step 1: Replace WebFetch step in dive-prompt.md**

In `skills/delve/references/dive-prompt.md`, replace line 9:

```
3. **Fetch and analyze** — Use WebFetch on the most promising results. Extract specific facts, data points, and claims.
```

with:

```
3. **Fetch and analyze** — For each promising URL, extract clean content using Bash:
   ```
   uv run PLUGIN_ROOT/scripts/fetch_clean.py "URL" 3000
   ```
   This returns JSON with `status`, `title`, `date`, `text`, `total_chars`, `truncated` fields.
   - If the command outputs valid JSON with `"status": "ok"`: use `text` for analysis, `title` for citation, `date` to compute `stale`
   - If `"status"` is `"fetch_failed"` or `"extraction_failed"`: fall back to WebFetch for that URL
   - If the command fails entirely (non-zero exit, no JSON output, or `uv` not found): fall back to WebFetch for that URL
   - The script strips HTML boilerplate (navigation, ads, footers) and returns only article content
```

- [ ] **Step 2: Update SKILL.md 3.1 prompt building with PLUGIN_ROOT resolution**

In `skills/delve/SKILL.md`, replace lines 311-313:

```
For each non-skipped sub-question from sub-tasks.json:
1. Build the full prompt: dive-prompt.md content + sub-question details + relevant sources from scan/result.json
2. Write frozen prompt to `dive/q_<hash>/prompt.md` (for resume auditability)
```

with:

```
For each non-skipped sub-question from sub-tasks.json:
1. Read dive-prompt.md content
2. Replace `PLUGIN_ROOT` with the resolved absolute path of the plugin root (`${CLAUDE_PLUGIN_ROOT}`)
3. Append source-authority-rules.md content (full version for DIVE agents)
4. Add sub-question details + relevant sources from scan/result.json
5. Write frozen prompt to `dive/q_<hash>/prompt.md` (for resume auditability — required for input_hash/prompt_hash cache validity)
```

- [ ] **Step 3: Commit**

```bash
git add skills/delve/references/dive-prompt.md skills/delve/SKILL.md
git commit -m "feat: integrate fetch_clean.py into DIVE prompt with WebFetch fallback"
```

---

### Task 7: Slim VERIFY claim payload

**Note:** Task 6 added ~2 lines to SKILL.md 3.1, shifting subsequent line numbers. Use text-matching (Edit tool old_string), not line numbers, for all SKILL.md edits below.

**Files:**
- Modify: `skills/delve/references/verify-prompt.md:20,40-53`
- Modify: `skills/delve/SKILL.md` (4.3 dispatch, ~line 587 pre-Task-6 — use text match)

- [ ] **Step 1: Update verify-prompt.md step 4 — origin_domains**

In `skills/delve/references/verify-prompt.md`, replace the step 4 text (line 20):

```
4. **Check source independence** — Each claim includes an `original_sources` list showing where DIVE agents found it. Your verification sources MUST be independent from these. If all supporting evidence you find traces back to the same root URLs as `original_sources`, return `uncertain` not `verified`. Same press release chain doesn't count as independent confirmation.
```

with:

```
4. **Check source independence** — Each claim includes `origin_domains` showing which root domains DIVE agents used. Your verification sources MUST come from different root domains. If all supporting evidence traces to the same domains, return `uncertain` not `verified`. Same press release chain doesn't count as independent confirmation.
```

- [ ] **Step 2: Update verify-prompt.md output schema — remove original_sources**

In `skills/delve/references/verify-prompt.md`, replace lines 41-52 (the JSON schema):

```json
[
  {
    "claim_id": "c_<hash>",
    "claim": "the claim text",
    "original_sources": ["URLs from DIVE — provided for independence check"],
    "verdict": "verified | contested | rejected | uncertain",
    "evidence": "specific evidence supporting your verdict — quote sources, cite data points",
    "sources": ["URLs you consulted for verification"],
    "source_tiers": ["T1 | T2 | T3 — parallel array, source_tiers[i] corresponds to sources[i]"],
    "notes": "additional context, caveats, or the correction if rejected"
  }
]
```

with:

```json
[
  {
    "claim_id": "c_<hash>",
    "claim": "the claim text",
    "verdict": "verified | contested | rejected | uncertain",
    "evidence": "specific evidence supporting your verdict — quote sources, cite data points",
    "sources": ["URLs you consulted for verification"],
    "source_tiers": ["T1 | T2 | T3 — parallel array, source_tiers[i] corresponds to sources[i]"],
    "notes": "additional context, caveats, or the correction if rejected"
  }
]
```

Keep line 55 (invariant) unchanged.

- [ ] **Step 3: Update SKILL.md 4.3 — add URL-to-domain transform**

In `skills/delve/SKILL.md`, find and replace the text (use text match, not line number — shifted by Task 6):

```
  prompt: <verify-prompt.md + batch of claims as JSON array, each claim including its `original_sources` and `original_source_tiers` lists>
```

with:

```
  prompt: <verify-prompt.md + batch of claims as JSON array, each claim including `origin_domains` (root domains extracted from `original_sources` by orchestrator: scheme + netloc → domain only, deduplicated)>
```

- [ ] **Step 4: Commit**

```bash
git add skills/delve/references/verify-prompt.md skills/delve/SKILL.md
git commit -m "feat: slim VERIFY payload — replace original_sources with origin_domains"
```

---

### Task 8: Update README privacy section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update privacy section in README**

Find the privacy paragraph in `README.md` (currently around line 113) and replace:

```
Delve uses Claude Code subagents and built-in WebSearch/WebFetch tools. Your research topic and web content are processed through Claude's standard API under your existing authentication. No data is sent to additional endpoints beyond what Claude Code normally uses.
```

with:

```
Delve uses Claude Code subagents and built-in WebSearch/WebFetch tools. Your research topic and web content are processed through Claude's standard API under your existing authentication. DIVE agents use an optional Python script (`scripts/fetch_clean.py`) to extract clean article text via the trafilatura library — this makes direct HTTP requests from your machine to fetch web pages, separate from Claude Code's WebFetch. If the script is unavailable (no `uv` installed) or fails, agents fall back to WebFetch automatically. When `--providers claude` is active, no external AI models are invoked and the topic is redacted in local event logs.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update privacy section — disclose direct HTTP via trafilatura"
```

---

## Chunk 3: Step 3 — Prompt Caching Layout

### Task 9: Explicit prompt assembly order

**Note:** Line numbers below are pre-Task-6 references. Use text-matching for edits. Task 6 shifted SKILL.md lines by ~2.

**Files:**
- Modify: `skills/delve/SKILL.md` (3.1 — already updated in Task 6, verify only)
- Modify: `skills/delve/SKILL.md` (4.3 VERIFY — use text match)

- [ ] **Step 1: Verify DIVE prompt order (3.1) is already correct**

After Task 6, SKILL.md 3.1 should already have the order:
1. dive-prompt.md
2. PLUGIN_ROOT replacement
3. source-authority-rules.md (shared prefix)
4. sub-question details (unique)
5. sources (unique)

Run: `grep -A 6 'Read dive-prompt.md content' skills/delve/SKILL.md | head -7`

Expected: steps 1-5 with shared content (dive-prompt + rules) before unique content (sub-question + sources).

- [ ] **Step 2: Make VERIFY prompt order explicit in 4.3**

In `skills/delve/SKILL.md`, find and replace (use text match, not line numbers):

```
### 4.3 Verification (parallel subagents)

Read `references/verify-prompt.md`.

Read `references/source-authority-rules.md` once. Append its content to each verify prompt before dispatch.
```

with:

```
### 4.3 Verification (parallel subagents)

Read `references/verify-prompt.md` once.

Read `references/source-authority-rules.md` once.

For each batch, build the full prompt in this order (shared prefix first for cache efficiency):
1. verify-prompt.md content
2. source-authority-rules.md content
3. Claim batch (unique per batch)
```

- [ ] **Step 3: Commit**

```bash
git add skills/delve/SKILL.md
git commit -m "feat: explicit prompt assembly order for cache-friendly shared prefixes"
```

---

### Task 10: Version bump and CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Update CHANGELOG.md**

Prepend to CHANGELOG.md:

```markdown
## [0.7.0] - 2026-03-15

### Added
- `scripts/fetch_clean.py` — PEP 723 trafilatura-based content extraction with 15s timeout, title/date metadata, WebFetch fallback
- `references/source-authority-rules-compact.md` — 80-token compact tier rules for claim extraction and SYNTHESIZE (FROZEN)
- Output Limits in dive-prompt.md: max 8 claims, 5 citations per sub-question with `claims_omitted` overflow signal
- `prompt_hashes` field in `claim_extraction_complete` and `synthesize_complete` checkpoint events
- Explicit prompt assembly order in SKILL.md 3.1 and 4.3 for cache-friendly shared prefixes

### Changed
- SYNTHESIZE no longer receives `output.md` — uses `output.json` only (FROZEN: synthesize-guide.md updated)
- Claim extraction (4.1) and SYNTHESIZE (5.1) use compact source-authority-rules; VERIFY (4.3) keeps full rules
- VERIFY batch payload uses `origin_domains` instead of `original_sources` + `original_source_tiers` (FROZEN: verify-prompt.md updated)
- DIVE agents use fetch_clean.py for content extraction with 3-tier fallback to WebFetch
- SKILL.md 3.1 prompt building includes PLUGIN_ROOT resolution
- Resume Protocol hash-check chain includes `source-authority-rules-compact.md`
- README privacy section updated: discloses direct HTTP via trafilatura

### Token Impact
- Target: 45-60% reduction (65K → 25-36K input tokens per medium-depth run)
- Step 1 (prompt hygiene): ~15-22K savings
- Step 2 (content extraction + VERIFY slim): ~10-15K savings
- Step 3 (cache layout): ~2-4K savings
```

- [ ] **Step 2: Bump version in plugin.json**

In `.claude-plugin/plugin.json`, change `"version": "0.6.0"` to `"version": "0.7.0"`.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md .claude-plugin/plugin.json
git commit -m "chore: bump to v0.7.0, changelog for token efficiency optimization"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `uv run scripts/fetch_clean.py "https://docs.python.org/3/library/asyncio.html" 2000` returns valid JSON with `status: "ok"`, non-empty `title`, `date` field present
- [ ] `grep -c 'output\.md' skills/delve/references/synthesize-guide.md` returns `0`
- [ ] `grep 'source-authority-rules-compact' skills/delve/SKILL.md` shows lines in 4.1 and 5.1
- [ ] `grep 'source-authority-rules\.md' skills/delve/SKILL.md` shows lines in 3.1, 4.3 (full rules for DIVE and VERIFY)
- [ ] `grep 'origin_domains' skills/delve/references/verify-prompt.md` shows the updated step 4
- [ ] `grep 'original_sources' skills/delve/references/verify-prompt.md` returns 0 matches
- [ ] `grep 'claims_omitted' skills/delve/references/dive-prompt.md` shows the overflow signal
- [ ] `grep 'PLUGIN_ROOT' skills/delve/SKILL.md` shows the resolution step in 3.1
- [ ] `grep 'prompt_hashes' skills/delve/references/checkpoint-schema.md` shows updated event types
- [ ] `grep 'prompt_hashes' skills/delve/SKILL.md` shows updated event emission lines in 4.1 and 5.4
- [ ] `git log --oneline -10` shows ~8 atomic commits
