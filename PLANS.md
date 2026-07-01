# PLANS.md - Goal 005 Knowledge Depth And UAT Closure

This is the active long-running ExecPlan for the current WILQ product layer.
It must stay restartable without chat history.

Current cleanup truth remains in `PLAN.md`, `docs/CONTEXT.md`,
`docs/PROGRESS.md`, `docs/goals/001-goal.md`,
`docs/goals/archive/004-goal.md`, `docs/goals/005-goal.md` and Beads.

## How To Use This File

- Read `AGENTS.md`, `PLAN.md`, `docs/CONTEXT.md`,
  `docs/PROGRESS.md` and `docs/goals/005-goal.md` first.
- Run `bd prime` and `bd ready --json` before choosing work.
- Use Beads for operational task tracking. Do not copy the Beads issue list
  into markdown TODOs.
- Update this file only when the active product plan, proof, decision or
  blocker changes.
- Keep `Progress`, `Surprises & Discoveries`, `Decision Log` and
  `Outcomes & Retrospective` current.

## Latest Completed Goal

Goal 004: Content Operations Layer.

Status: completed on 2026-07-01. Beads epic `wilq-seo-2qq`.

Goal 004 proved the safe mechanics of content operations:

```text
queue candidate
-> opportunity enrichment
-> typed Ekologus knowledge cards
-> operations-grade Sales Brief
-> claim-gated draft variants
-> deterministic quality review
-> bounded revision application
-> human review
-> audit
-> WordPress draft-only handoff
-> measurement window
-> conservative outcome interpretation
```

Broad proof passed with `rtk scripts/verify.sh`: 509 Python tests, 107
dashboard/shared tests and 14 Playwright E2E/demo checks.

Important limitation: Goal 004 closed the architecture and test proof, not
daily usefulness for Wilku. The UAT harness exists, but the first real content
operations session with Wilku is still not a product proof unless completed or
explicitly owner-deferred with residual risk.

## Active Goal

Goal 005: Ekologus Knowledge Depth & UAT Closure.

Status: active. Beads epic `wilq-seo-1oa`.

Objective:

Validate that WILQ's safe content operations loop is useful with real Ekologus
knowledge, not only mechanically complete. Goal 005 must deepen typed knowledge
cards, expose a read-only Service Profile/review path, run or explicitly defer
the first real Wilku UAT, and audit Sales Brief v2 signal quality.

This is not a new writing-flow goal. Do not add autopublishing, social
publishing, broad RAG/vector DB, multi-client SaaS, workspace admin, outcome
claims before measurement, or direct Codex/OpenAI/WordPress bypasses.

## Product Thesis

WILQ's hardest anti-slop problem after Goal 004 is no longer "can the system
block unsafe writing?". It can. The harder question is whether the typed
knowledge and evidence signals are deep enough that Wilku gets a useful
Ekologus-specific brief instead of formally correct generic SEO copy.

The next product step is therefore:

```text
knowledge-card depth audit
-> Service Profile read/review surface
-> Sales Brief signal-quality audit
-> first real Wilku UAT
-> precise follow-up blockers or implementation slices
```

## Non-Negotiable Rules

- WILQ API owns product logic.
- Dashboard renders API-owned view models.
- Codex skills consume WILQ API; they do not invent product behavior.
- No evidence ID means no recommendation.
- No source connector means no recommendation.
- Weak, stale or thin evidence must become an explicit low-confidence/blocker
  state, not a polished generic brief.
- Typed knowledge cards do not replace live evidence.
- Knowledge-card updates must be reviewed/gated. Initial Service Profile work
  is read-only plus flag/review request, not ungated self-service writes.
- No broad RAG/vector DB before typed cards, source lineage, freshness,
  validators and evals are strong.
- No fake SEO score or magic content score.
- No publish-ready draft claim.
- WordPress remains draft-only/review-gated. No automatic publish.
- Measurement outcome remains conservative and cannot claim success before the
  observation window has usable data.

## Current Discovery

Current `wilq/content/knowledge/cards.py` contains three seeded cards:

- `ekologus_service_environmental_compliance`
- `ekologus_cta_consultation_without_guarantee`
- `ekologus_evidence_live_connector_requirement`

That is enough for Goal 004 contract proof. It is not yet enough to claim deep
Ekologus knowledge coverage across real services, buyer problems, triggers,
CTA patterns, claim policies and evidence requirements.

## In Scope

Goal 005 includes:

1. Knowledge-card depth audit against real Ekologus services, buyer problems,
   buyer triggers, CTA patterns, claim constraints and evidence requirements.
2. Read-only Ekologus Service Profile/review design so Wilku can inspect card
   status, source lineage, freshness and missing coverage without editing code.
3. First real Wilku content UAT, or explicit owner defer with residual risk.
4. Sales Brief v2 signal-quality audit across current queue candidates,
   connector freshness/density and enrichment usefulness.
5. Evidence-based draft variant selection guard design: no fake score, no new
   generation flow, just API-owned comparison by evidence coverage, service
   fit, buyer problem, CTA fit, duplicate risk and quality findings.
6. Focused blockers/tests for missing required knowledge or weak signals.

## Out Of Scope

Goal 005 must not build:

- automatic WordPress publishing,
- destructive updates of existing `ekologus.pl` content,
- mass article generation,
- direct Codex-authored production content,
- direct Codex/OpenAI calls bypassing WILQ API,
- direct WordPress client calls from skills,
- broad RAG/vector memory,
- multi-client SaaS or agency admin,
- Ads/Merchant/Localo write automation,
- social publishing,
- public success/failure claims before measurement readiness.

## Completion Definition

Goal 005 is complete only when repo evidence proves all of this:

1. Knowledge-card coverage is audited against real Ekologus services, buyer
   problems, triggers, CTA patterns, claim constraints and evidence
   requirements.
2. The audit states whether current cards are production-depth, thin, stale or
   placeholder-like, with exact gaps and source lineage.
3. Missing required card states are represented as typed blockers and covered by
   focused tests or a documented blocker.
4. A read-only Service Profile/review design or implementation exists for
   Wilku-facing inspection of cards, freshness, source lineage and gaps.
5. Knowledge-card write/update behavior remains blocked unless a future
   human-review/audit path is explicitly implemented.
6. Sales Brief v2 signal quality is assessed for current queue candidates:
   sufficient, thin, stale or blocked, with connector/domain cause stated.
7. Draft variant selection has an evidence-based comparison plan or
   implementation and does not introduce a fake SEO/content score.
8. One real Wilku UAT session is completed in 45 minutes or less, or the owner
   explicitly defers it with residual risk and exact next UAT input required.
9. UAT proof captures confusion points, off-brand/generic SEO findings,
   source-trace questions, selected work item and exact follow-ups.
10. `docs/PROGRESS.md`, `PLANS.md`, `docs/goals/005-goal.md` and Beads agree.
11. Focused verification passes for changed areas, and full
    `rtk scripts/verify.sh` passes before completion claims.

## Verification Surface

Use focused verification after every slice and full verification before
completion.

Minimum proof surface:

- Knowledge-card domain tests under `tests/content`.
- API contract tests for Service Profile/review endpoints if implemented.
- Dashboard route/component tests if a Service Profile surface is implemented.
- `wilq-content-operator` smoke/eval if the skill consumes new Service Profile
  or UAT fields.
- `rtk git diff --check` for docs-only slices.
- `rtk uv run pytest tests/content -q` for content domain changes.
- Relevant dashboard tests/typecheck for UI changes.
- `rtk scripts/verify.sh` before completion.

## Beads Operational Graph

Use Beads as the authoritative development task graph. Active Goal 005 epic:

- `wilq-seo-1oa` - Goal 005: Ekologus Knowledge Depth & UAT Closure.

Initial slices:

- `wilq-seo-9do` - Goal 005 recovery and plan alignment.
- `wilq-seo-3lk` - audit Ekologus knowledge-card depth.
- `wilq-seo-94k` - design read-only Ekologus Service Profile review surface.
- `wilq-seo-jst` - run first real Wilku content UAT or record explicit defer.
- `wilq-seo-n8r` - audit Sales Brief v2 signal quality.
- `wilq-seo-87i` - define evidence-based draft variant selection guard.

This section is a recovery index only. Operational status lives in Beads.

## Execution Order

### 1. Recovery and plan alignment

Inspect first: `AGENTS.md`, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md`,
`docs/PROGRESS.md`, `docs/goals/archive/004-goal.md`, current knowledge-card
code and Beads.

Build: this active plan, `docs/goals/005-goal.md`, progress/context alignment
and Beads graph.

Do not build: product behavior.

Proof: `bd ready --json`, `git diff --check`, commit and push.

### 2. Knowledge-card depth audit

Inspect first:

- `wilq/content/knowledge/cards.py`
- `wilq/content/briefs/sales.py`
- `wilq/content/enrichment/opportunity.py`
- `tests/content/test_content_knowledge_cards.py`
- current Ekologus source docs and live queue/enrichment when API is reachable.

Build: a coverage audit and exact implementation blockers for missing or thin
cards.

Do not build: broad RAG or prompt-only knowledge.

Proof: focused tests or explicit blocker if production-depth cards cannot be
created without owner/source input.

### 3. Service Profile review path

Inspect first: content knowledge cards, knowledge API router, dashboard knowledge
surfaces and shared schemas.

Build: read-only Service Profile/review design or implementation. It should let
Wilku inspect current service knowledge, source lineage, freshness, claim
constraints and missing coverage. Flagging/review requests are allowed only if
they are explicitly gated.

Do not build: direct knowledge-card editing.

Proof: API/dashboard tests if implemented; otherwise a concrete design with
blocked write-path rules.

### 4. Sales Brief v2 signal-quality audit

Inspect first: queue candidates, enrichment source facts, GSC/GA4/Ahrefs/
WordPress connector freshness and Sales Brief v2 output.

Build: an audit that classifies signals as sufficient, thin, stale or blocked
and names connector/domain causes.

Do not build: fake opportunity scores.

Proof: domain/API tests or a documented blocker for weak source data.

### 5. Wilku UAT

Inspect first: UAT harness, `/content-workflow`, current content queue and
operator skill output.

Build: a real UAT packet and session proof, or explicit owner defer with
residual risk.

Do not build: a prettier demo that hides missing depth.

Proof: participant/date/scope, selected work item, completion time, confusion
points, off-brand/generic SEO findings, source-trace questions and follow-ups.

## Stop Conditions

Stop and record a blocker if:

- current knowledge cards are mostly seed/placeholder coverage and no trusted
  Ekologus source exists to deepen them,
- Wilku cannot complete one content session within 45 minutes without developer
  intervention,
- draft variants sound like generic SEO despite passing formal gates,
- WordPress draft-only handoff requires debugging during normal UAT,
- Wilku asks "skąd to wzięło?" and the UI cannot show a concrete source fact,
- a proposed endpoint lets Wilku update knowledge cards without human
  review/audit,
- live Structured Outputs is enabled without a separate adapter-boundary audit.

## Progress

- 2026-07-01: Goal 005 Beads epic `wilq-seo-1oa` created. Initial recovery,
  knowledge audit, Service Profile, UAT, Sales Brief signal-quality and variant
  selection slices created.
- 2026-07-01: Current knowledge implementation inspected. It has three seeded
  cards, so Goal 005 starts from "contract proof exists, depth unverified".

## Surprises & Discoveries

- The current cards are useful as guardrails but too broad for deep Ekologus
  operations: one service card covers BDO/odpady/Zielony Lad together.
- UAT harness proof is not the same as Wilku UAT. Treat it as preparation, not
  validation.

## Decision Log

- Goal 005 focuses on usefulness validation and knowledge depth, not another
  writing pipeline.
- Service Profile starts read-only plus review/flag semantics. Direct
  self-service knowledge writes are out of scope until a review/audit path
  exists.
- Variant selection must be evidence-based dimensions/blockers, not a fake
  score.

## Outcomes & Retrospective

Not completed. Goal 005 is active.
