# Changelog

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
