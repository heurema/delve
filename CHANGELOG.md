# Changelog

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

## [0.6.0] - 2026-03-14

### Added
- Tier 2 entity matching: reads bank/entities/*.md for project stack, key_projects, conventions
- Sub-project matching for ~/personal/ (skill7→heurema, forgequant→forgequant entities)
- Contrarian agent dispatch: when source overlap > 0.6, dispatches additional DIVE agent with blacklisted URLs, forced alternative viewpoint, and query reformulation
- `contrarian_complete` event (separate from dive_complete)
- Initial status.json for contrarian worker (pending state before dispatch)
- Resume protocol handles contrarian pending/error/timeout states
- Cache validity for contrarian includes worker output dependency (not just prompt hash)

### Changed
- context_pack.project now includes stack and entity_file fields
- query_enriched appends project + stack hint
- tier_used reflects highest tier that produced data (1/2/3)
- Assumption display shows stack: `Context: <project> (<stack>) | prior research: <N> file(s)`
- contextualize_complete event includes stack field

## [0.5.0] - 2026-03-14

### Added
- Stage 0.5: CONTEXTUALIZE — tiered local context enrichment before SCAN
- Tier 1: cwd→project mapping (fjx, itools, personal, contrib, vicc) + git branch detection
- Tier 3: docs/research/*.md frontmatter scan for prior work (from project root, not cwd)
- context_pack output (context.json) with query_original, query_enriched, project, git_branch, prior_research, assumptions, confidence
- Assumption display UX: one-line summary when confident, disambiguation prompt when ambiguous
- New flags: `--no-context` (skip Stage 0.5 entirely), `--broad` (skip project scoping)

### Changed
- Stage 1.1 uses context_pack.prior_research instead of re-scanning docs/research/
- Tier 2 (entity matching for project.stack) explicitly deferred to Phase 2

## [0.4.0] - 2026-03-14

### Added
- Composite quality score: weighted metric (verified_ratio×3 + source_independence×2 + p0_coverage×2) / 7, logged to events.jsonl and synthesis.md frontmatter
- Prompt Mutability section: FROZEN (verify-prompt, claim-extraction, synthesize-guide, security-policy, source-authority-rules) vs MUTABLE (dive-prompt)
- Stage 3.5: source overlap detection via Jaccard similarity across DIVE agent citations
- `source_saturation_detected` warning event when avg overlap > 0.6
- Cache invalidation for FROZEN prompt changes (synthesize-guide, security-policy)
- `overlap_analysis_complete` and `source_saturation_detected` event types in checkpoint schema

### Changed
- Root domain extraction uses scheme+netloc only (was scheme+netloc+path) for both overlap detection and source independence
- `p0_coverage` lookup uses `verify/claims.json` for source_questions mapping (was incorrectly referencing verdict files)
- `p0_coverage` defaults to 0 when `decompose/sub-tasks.json` missing (--quick, reuse modes) or when total_p0=0
- Single-worker runs log `overlap_analysis_complete` with zeroed fields instead of silently skipping

## [0.3.0] - 2026-03-11

### Added
- 3-tier source credibility scoring (T1/T2/T3) across all pipeline stages
- New `references/source-authority-rules.md` — shared tier classification rules
- `source_tier` field in dive output claims and citations
- `stale` boolean in dive citations for sources >12 months old
- `source_tiers` parallel array in verify verdicts
- `original_source_tiers` in claim extraction output
- Tier annotations in synthesis report sources: `[N] [T1] Title — URL`
- Tier distribution in synthesis methodology section

### Changed
- `verification_status: verified` now requires >50% of verified claims backed by T1/T2 sources
- T3-only claims forced to `low` confidence in DIVE
- T3-only evidence cannot produce `verified` verdict in VERIFY (→ `uncertain`)
- Synthesize quality labels table replaces prose definitions

## [0.2.0] - 2026-03-10

### Changed
- RUN_DIR moved from tmpdir to persistent `~/.cache/delve/runs/<run_id>/` — runs survive reboot
- Claim extraction limit now depth-dependent: shallow=20, medium=35, deep=60 (was hardcoded 30)
- Verifiers receive `original_sources` per claim — prevents press-release amplification false positives

### Fixed
- Resume after reboot no longer fails with "Run directory was cleaned up"
- Deep mode no longer silently truncates claims from P0 sub-questions

## [0.1.0] - 2026-03-10

### Added
- Initial release
- 5-stage pipeline: SCAN → DECOMPOSE → DIVE → VERIFY → SYNTHESIZE
- Parallel research subagents with configurable depth
- Claim-level verification with adversarial prompts
- Resume support from checkpoints
- Sensitivity routing (--providers claude)
- Quick mode (--quick) for scan+synthesize only
