# Synthesis Guide

## Purpose

Merge research outputs from multiple dive agents and annotate with verification verdicts to produce a coherent, honest research report.

## Inputs

- `dive/q_*/output.json` — structured research per sub-question
- `dive/q_*/output.md` — human-readable research per sub-question
- `verify/verdicts/c_*.json` — per-claim verification verdicts (if verify ran)
- `verify/summary.json` — aggregate verification stats (if verify ran)
- `scan/result.json` — original source list

## Synthesis Rules

### Claim handling by verdict

| Verdict | Treatment in report |
|---------|-------------------|
| `verified` | Include in Key Findings. State as fact. |
| `contested` | Include in Contested Points. Present BOTH sides with evidence. Never pick a side without stating why. |
| `rejected` | Exclude from Key Findings. If the rejection is itself informative, mention in Contested Points with the correction. |
| `uncertain` | Include only if central to the topic. Mark explicitly as unverified. |
| No verdict (verify skipped) | Include but note "unverified" in methodology section. |

### Source independence

- Track which original sources support each finding
- If 3 articles all cite the same press release → count as 1 source, not 3
- Note when a finding relies on a single source vs. multiple independent confirmations
- Prefer findings backed by independent sources
- Annotate each source in the Sources section with its tier: `[1] [T1] Title — URL`
- In Key Findings, prioritize findings backed by T1 sources
- Add tier distribution to Methodology section: `Source quality: X T1, Y T2, Z T3`

### Confidence resolution

If a claim was `low` confidence in DIVE (T3-only) but VERIFY found T1/T2 evidence and marked it `verified`, treat it as verified. The VERIFY verdict overrides DIVE confidence for synthesis purposes.

The synthesizer trusts the `stale` flag from DIVE citations as-is — it does NOT recompute staleness.

### Quality over quantity

- Lead with the most important and well-supported findings
- Do not pad the report with low-confidence or tangential information
- If research found contradictions, say so — an honest "we don't know" is better than false certainty
- Gaps in research are findings too — include them

## Output Structure

### synthesis.md

```markdown
---
topic: <topic>
run_id: <run_id>
date: <YYYY-MM-DD>
depth: <shallow | medium | deep>
verification: <verified | partially-verified | unverified>
completion: <complete | incomplete | synthesis_only | draft | cancelled | no_evidence>
sources: <count>
claims_verified: <count>
claims_contested: <count>
composite_score: <float 0-1 — weighted quality score: (verified_ratio*3 + source_independence_ratio*2 + p0_coverage*2)/7>
---

# <Topic> — Deep Research

## Key Findings

<Numbered findings, organized by theme. Each backed by verified claims.
Include inline source references [1], [2].>

## Contested Points

<For each contested claim: state the claim, present supporting evidence,
present contradicting evidence, note which sources are more authoritative.>

## Gaps & Open Questions

<What the research could not determine. What would need further investigation.>

## Sources

<Numbered list with tier annotation. Format: [N] [T1] Title — URL (accessed YYYY-MM-DD)
Mark sources as: primary / secondary / aggregator.>

## Methodology

- **Pipeline:** SCAN → DECOMPOSE → DIVE → VERIFY → SYNTHESIZE
- **Depth:** <depth>, **Agents:** <count>
- **Duration:** <total time>
- **Quality:** <verification_status> / <completion_status>
- **Claims:** <verified>/<total> verified, <contested> contested, <rejected> rejected
- **Source quality:** X T1, Y T2, Z T3
```

### Determining quality labels

**verification_status:**

| Status | Conditions (ALL must be true) |
|--------|-------------------------------|
| `verified` | >=80% claims verified AND 0 rejected P0 claims AND >50% of verified claims backed by at least one T1 or T2 source AND full pipeline ran |
| `partially-verified` | 50-79% verified, OR verify degraded, OR `--providers claude`, OR <=50% of verified claims have T1/T2 backing |
| `unverified` | <50% verified, verify skipped, or verify failed |

**`--quick` mode:** `--quick` skips DIVE and VERIFY. No tier annotations exist. `verification_status` is always `unverified`. Tier conditions only apply when the full pipeline ran.

**completion_status:**
- `complete`: all stages ran, all P0 sub-questions covered
- `incomplete`: DIVE had partial success (<100% workers completed)
- `synthesis_only`: no new research conducted, synthesized from existing docs
- `draft`: contested_ratio > 30%
- `cancelled`: user interrupted
- `no_evidence`: 0 sources found, first-principles only

### Draft threshold

If contested_ratio > 0.3 (30%), mark completion as `draft` and add a warning at the top of the report:

```markdown
> **Draft Report** — Over 30% of claims are contested. This report should be treated
> as preliminary and may require additional research or expert review.
```
