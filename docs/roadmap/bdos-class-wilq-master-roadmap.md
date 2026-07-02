# BDOS-Class WILQ Master Roadmap

Date: 2026-07-01

This document answers the operator question: what do we already have, what is
still missing compared with a "better BDOS.ai", and how the abandoned
`ekologus-ai` work should feed WILQ without turning WILQ into a static artifact
factory.

## What We Are Building

WILQ is a Marketing Operating System for Ekologus. The product brain is the WILQ
API. Dashboard, Codex skills, hooks, expert rules, workflows and future write
actions must all consume the same typed contracts, evidence IDs, source
connectors, knowledge cards and audit trail.

The BDOS-class bar is not "copy BDOS". The bar is:

- diagnostics based on connector evidence, not memory,
- recommendations with source connectors and evidence IDs,
- safe typed actions with preview, validation, confirmation and audit,
- content operations that prove source traceability and claim safety,
- Polish operator surfaces that explain decision, reason, blocker and next safe
  step,
- no invented metrics, no autopublish, no write action outside an ActionObject.

## Current State

Approximate product completion against the long-term BDOS-class ambition:
`35-45%`.

That number is intentionally conservative. The repo has a serious API-first
core, many typed surfaces and tests, but it is not yet a finished marketing OS
because real UAT, production-depth knowledge review, stronger optimizer logic,
post-publication measurement proof and write execution are not done.

### Already Real

- WILQ API is the canonical product boundary.
- Dashboard and Codex skills are designed to consume API context, not invent
  their own product behavior.
- Content workflow has typed endpoints for queue, selected snapshot, enrichment,
  preflight, Sales Brief, draft package, structured draft generation/preview,
  quality review, revision, human review, WordPress draft handoff/execution,
  measurement window and measurement outcome.
- ActionObject system exists with validation, review, preview, confirmation,
  impact checks, apply path and audit events.
- Diagnostics surfaces exist for daily command center, Ads, Merchant, GA4, GSC,
  Ahrefs, Localo, content, opportunities, evidence, metrics, jobs, connectors,
  expert rules, knowledge and workflows.
- WILQ skills exist for daily command, ads, campaign building, custom segments,
  demand gen, GA4, GSC content, Ahrefs, Merchant, Localo, content operations,
  content strategy and social publishing.
- Skill eval and smoke harnesses exist and enforce Polish output, API use,
  evidence/source connector guardrails and safe ActionObject behavior.
- Ekologus source-fact registry exists for public source facts and first
  redacted `ekologus-ai` internal facts.
- Content knowledge cards now carry source fact IDs, source connectors, lifecycle
  status and production-depth readiness guardrails.
- First Wilku-facing handoff artifacts exist for Eko-Opieka/Eko Kalendarz and
  Audyt zgodności review.

### Mechanically Present, Not Yet Proven

- Content workflow can prepare structured decisions, but real Wilku UAT is still
  missing or owner-deferred.
- Knowledge cards are source-backed but mostly `review_required`, not
  `approved_current`.
- Public source facts support analysis and UAT, but do not by themselves unlock
  production-depth drafts.
- Measurement outcome exists as a workflow stage, but content success claims
  still need stronger provenance to metric facts, connector refreshes and
  observation windows.
- WordPress path is draft/handoff oriented; this is not autopublish.
- Ads/Merchant/GA4/GSC/Ahrefs/Localo surfaces exist, but many are still
  diagnosis/review surfaces rather than full optimizer workflows.

### Explicitly Missing

- Real Wilku UAT on 3-5 content candidates with time-to-brief, confusion points,
  source-trace questions and generic/off-brand findings.
- Human approval lifecycle that can promote source facts/cards from
  `review_required` to `approved_current`.
- Production-depth Ekologus service knowledge across service fit, buyer
  problems, CTAs, forbidden claims, claim policies and evidence requirements.
- A proper claim ledger/generation gate that blocks every draft claim not tied to
  approved source facts/evidence.
- Variant selection guard based on evidence coverage, service fit, CTA fit,
  duplicate/canonical risk and quality review findings.
- Sales Brief v2 signal-quality audit over actual connector freshness/density.
- Measurement provenance hardening: no `measured_success` without metric fact
  IDs, connector IDs, matching work item/window and observation readiness.
- Full BDOS-grade Ads workflows: search-term waste/n-gram, keyword research,
  negative keyword action flow, budget/bidding triage, change history, mutation
  logs and account-folder style context.
- Full Merchant workflows: feed issue triage, price/product evidence, product
  buckets and safe Shopping/PMax recommendations.
- Full reporting layer: daily/monthly review with change history, blockers,
  source freshness, actions and observed outcomes.
- Social Inventory and anti-duplication: historical LinkedIn/Facebook posts,
  topic/claim/CTA/channel metadata, duplicate-risk checks and brand-voice
  evidence before claiming a new social direction is not repeating prior
  content.
- Write execution beyond safe supported ActionObject types.
- Multi-client abstraction. Ekologus should work deeply first.

## How WILQ Should Actually Work

Target content loop:

1. Candidate enters queue from GSC/GA4/Ahrefs/WordPress/manual signal.
2. WILQ pulls connector metrics and source facts.
3. WILQ checks inventory, canonical and duplicate risk.
4. WILQ matches approved and review-required knowledge cards.
5. Preflight decides whether the work item is blocked, review-only or draftable.
6. Sales Brief names the service fit, buyer problem, CTA, evidence and blockers.
7. Claim Ledger names allowed, weak, forbidden and human-review claims.
8. Draft Package/Structured Draft uses only allowed claims.
9. Quality Review blocks unsupported, risky, generic or off-brand output.
10. Human Review decides what can be used.
11. WordPress path stays draft-only unless a future write action model supports
    more.
12. Measurement window observes GSC/GA4/WordPress signals.
13. Outcome interpretation creates learning proposals, not automatic knowledge
    rewrites.

## How `ekologus-ai` Fits

`ekologus-ai` is not a second product brain. It is the abandoned first attempt at
an Ekologus content brain. WILQ should reuse its reviewed lessons in three ways:

- import reviewed source concepts as redacted/review-required source facts,
- port schema/gate patterns into WILQ API where they close real gaps,
- use its materials to create normal handoff artifacts, drafts, conclusions and
  review questions for Wilku.

Do not build a separate "special package for Wilku" layer. If Wilku needs an
artifact, generate a normal handoff, brief, review packet or draft package from
the existing WILQ content workflow.

## Roadmap

### Next Slice: Product Clarity And Reuse Audit

- Finish `ekologus-ai` reuse audit.
- Map `ekologus_brain` contracts to WILQ content workflow gaps.
- Keep only reusable patterns, not the old CLI/product shell.

### Goal 005: Knowledge Depth And UAT Closure

- Promote source-fact registry from proof to reviewed working layer.
- Add more Ekologus service source facts from public/reviewed sources.
- Keep all private/internal facts redacted and review-required.
- Run or explicitly defer Wilku UAT.
- Audit Sales Brief v2 signal quality.

### Goal 006 Candidate: Claim Ledger And Generation Gate

- Port the useful `ekologus-ai` evidence pack/source claim marker/generation gate
  pattern into WILQ API.
- Block draft claims that are not in the ledger.
- Add tests for forbidden legal/offer/product/penalty claims.

### Goal 007 Candidate: Measurement Provenance

- Tie measurement outcomes to metric facts, connector refresh/job lineage,
  work item ID, baseline period and observation period.
- Create learning proposals instead of automatic knowledge edits.

### Goal 008 Candidate: BDOS-Grade Ads Loop

- Harden Ads diagnostics into action-ready workflows.
- Add Google Ads Developer Assistant style guardrails: API version awareness,
  schema/resource inspection, GAQL validation, linted generated helper code,
  read-only execution proof and diagnostic artifacts before operator-facing
  Ads recommendations.
- Add negative keyword/search-term waste review, preview and safe confirmation.
- Add change-history/audit reporting.

### Goal 009 Candidate: Reporting And Daily Operating Rhythm

- Turn command center into a daily/monthly operating cockpit.
- Show what changed, why it matters, what is blocked, what can safely be done
  today and what was learned after publication/action.

### Goal 010 Candidate: Social Inventory And Reuse Guard

- Build read-only inventory for historical LinkedIn/Facebook posts.
- Store sanitized metadata: channel, date, topic, service, claim, CTA, format,
  source link/post ID and optional observed aggregate outcomes.
- Add duplicate-risk and reuse checks before generating social draft
  directions: same topic too soon, same claim/CTA repeated, or allowed reuse
  only with a different angle.
- Use history as brand-voice and cadence evidence, not as automatic factual
  approval for service/legal/product claims.
- Keep publishing blocked until LinkedIn/Facebook credentials, review actions
  and audit paths are implemented.

## Practical Percentages

- API/schemas/core safety foundation: `60-70%`.
- Content workflow mechanics: `60-70%`.
- Ekologus-specific reviewed knowledge depth: `20-30%`.
- Real operator usefulness proof: `10-20%`.
- Ads/Merchant/GA4/GSC/Ahrefs/Localo BDOS-grade optimizer depth: `25-35%`.
- Safe write execution and mutation audit maturity: `20-30%`.
- Reporting/learning loop: `20-30%`.
- Overall BDOS-class WILQ: `35-45%`.

The biggest gap is not "more UI". The biggest gap is reviewed source knowledge,
claim-level generation safety, real Wilku UAT and measurement/provenance proof.
