# Source Authority Rules

## Purpose

Classification rules for source credibility. The orchestrator reads this file and appends it to agent prompts (DIVE, VERIFY) at dispatch time. For inline stages (claim extraction, synthesize), the orchestrator reads it directly.

## Tier Definitions

| Tier | Trust Level | Domains / Signals |
|------|-------------|-------------------|
| T1 | Highest | arxiv.org, .gov, .edu, ACM DL (dl.acm.org), IEEE (ieeexplore.ieee.org), Nature (nature.com), Springer (springer.com, link.springer.com), Science (science.org), RFC (rfc-editor.org), W3C specs (w3.org), IETF (ietf.org, datatracker.ietf.org), official docs (docs.*, developer.*), official GitHub repos of the project being researched |
| T2 | Standard | Major news (Reuters, AP, BBC, NYT, Bloomberg, TechCrunch), Wikipedia, established tech publications (InfoQ, Ars Technica, The Register, Hacker News front page links), GitHub repos with 1k+ stars, conference proceedings (NIPS, ICML, ACL, EMNLP, etc.), vendor docs from established companies |
| T3 | Low | Personal blogs, forums (Reddit, StackOverflow answers), social media, Medium posts without institutional affiliation, SEO-optimized aggregator sites, press release wire services (PRNewswire, BusinessWire, GlobeNewsWire) |

## Classification Rules

1. **Default is T3.** Upgrade only when domain matches T1 or T2 criteria.
2. **No transitive trust.** A T3 source quoting a T1 source does NOT become T2. Cite the original T1 source directly.
3. **Press releases are always T3** even if they originate from a T1 institution. Find the underlying paper/report instead.
4. **GitHub repos:**
   - T1 if it's the official repo of the project being researched
   - T2 if >1k stars and relevant to the topic
   - T3 otherwise
5. **Recency (DIVE agents only):** If a source appears to be >12 months old (determine from publication date, "last updated" text, or explicit year references in the content — NOT from the `accessed` date), set `"stale": true` in the citation object. Do NOT auto-downgrade the tier. The `stale` boolean is informational for the synthesizer.
6. **VERIFY agents** do NOT set `stale` — their `sources` field is a plain URL array. Staleness is assessed only during DIVE.

## Confidence Override

If a claim is supported only by T3 sources, set confidence to `low` regardless of source count. This takes precedence over agreement-based confidence:
- T3-only + multiple agreement = still `low`
- T3-only + single source = `low`

## Echo Chamber Detection

Multiple T3 sources all citing the same original source count as ONE T3 confirmation, not multiple. Identify the root source and cite it directly.
