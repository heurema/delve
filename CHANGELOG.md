# Changelog

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
