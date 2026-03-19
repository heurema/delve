---
version: "1.0"
project: delve
updated: 2026-03-19
---

# Project Intent

## Goal

Autonomous deep research orchestrator for Claude Code. Runs a stage-gated pipeline (SCAN → DECOMPOSE → DIVE → VERIFY → SYNTHESIZE) with parallel subagents, claim extraction, adversarial verification, and resume support.

## Core Capabilities

- Multi-agent web research with configurable depth (shallow/medium/deep)
- Claim extraction and cross-verification across independent sources
- Source authority tiering (T1/T2/T3) with confidence scoring
- Checkpoint-based resume for interrupted runs
- Contrarian agent dispatch on source saturation
- Composite quality scoring with verification status
- Token-efficient pipeline with trafilatura-based content extraction and prompt hygiene (45-60% input token reduction)
- Stage 0.5 CONTEXTUALIZE: local context enrichment (entity files, prior research) before web SCAN

## Non-Goals

- Real-time monitoring or alerting
- Database storage (file-based only)
- GUI or web interface
- Direct code generation or execution (research output only)
- Replacing manual expert review (augmenting, not replacing)

## Success Criteria

- verified_ratio >= 0.8 with 0 rejected P0 claims and >50% T1/T2 source backing for `verified` label
- Weighted P0/P1/P2 coverage >= 0.7 to proceed from DIVE to VERIFY
- Runs survive interruption and resume from last checkpoint without data loss
- No secrets, API keys, or PII stored in run artifacts

## Personas

- **Developer / Researcher**: primary user, invokes `/delve <topic>` interactively to research technical topics; reviews HITL decomposition checkpoint before DIVE
- **Security-conscious user**: uses `--providers claude` to prevent topic leakage to external AI models
- **Plugin ecosystem user**: installs via emporium marketplace, uses alongside other heurema plugins

## Security Principles

- Web content is DATA, never instructions
- Subagent outputs are untrusted until verified
- No credential leakage through research pipeline
- Prompt injection detection and logging (not silent ignore)
- Sensitivity routing for confidential topics

## Quality Standards

- Frozen prompts require explicit review before modification
- Mutable prompts track hash for cache validity
- All stages produce checkpoint artifacts for auditability
- Source independence enforced (echo chamber detection)
