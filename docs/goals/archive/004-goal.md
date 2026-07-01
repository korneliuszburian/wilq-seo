# Goal 004 - Content Operations Layer

Status: active.

Beads epic: `wilq-seo-2qq`.

## Objective

Turn the verified Goal 003 Content Quality Workbench into a daily Ekologus
content operating loop.

Wilku must be able to run a real content work session through WILQ:

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
-> later outcome interpretation
```

This is not an MVP track. The target is the final-grade architecture delivered
in small verified slices. Temporary incompleteness is acceptable only when the
slice moves the final operating loop closer without weakening gates, preserving
stale aliases or moving product logic out of WILQ API.

## Current Baseline

Goal 003 is complete and fully verified. The current repo proves:

- API-owned multi-item content queue.
- Per-`work_item_id` workflow state for review, audit, generated output and
  quality review.
- Gated OpenAI SDK Structured Outputs runtime.
- Deterministic `ContentQualityReview`.
- Evidence-bound revision plan.
- Polish `/content-workflow` dashboard surface.
- WordPress draft-only/dry-run boundary.
- Adversarial content workflow tests.
- Full repo-level `rtk scripts/verify.sh` passes.

Goal 004 begins from this baseline. It must not re-litigate Goal 003 or weaken
the safety model to move faster.

## Non-Negotiable Rules

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- WILQ API owns product logic.
- Dashboard renders API-owned view models.
- Codex is repo/dev/eval/orchestration and operator workflow, not the
  production writer.
- Production generation uses WILQ API plus OpenAI SDK Structured Outputs plus
  strict schemas.
- No evidence ID means no recommendation.
- No source connector means no recommendation.
- No preflight means no writing.
- No Sales Brief means no draft.
- No claim gate means no draft.
- No human review means no WordPress draft.
- No audit means no write/apply.
- No measurement window means no success/failure claim.
- `ekologus.pl` is the canonical public content home.
- `ekologus.dev.proudsite.pl` is preview/design/staging context only and never
  canonical SEO evidence.
- Existing content is preserve-first.
- WordPress remains draft-only/review-gated. No automatic publish.
- No broad RAG/vector DB before typed knowledge cards, rules, validators and
  evals are solid.
- No deprecated aliases or compatibility junk when direct migration is
  feasible.
- No fake SEO score. Quality is blockers, evidence coverage, claim safety,
  usefulness, service fit, CTA fit and measurement readiness.

## In Scope

Goal 004 includes these production-grade layers:

1. Content workflow contract freeze.
2. `ContentOpportunityEnrichment` per `work_item_id`.
3. Typed Ekologus knowledge cards.
4. Operations-grade Sales Brief from enrichment and knowledge.
5. Claim-gated draft variants through Structured Outputs.
6. Bounded revision application with version/diff and quality rerun.
7. WordPress draft-only adapter boundary.
8. Measurement outcome interpreter.
9. `wilq-content-operator` Codex skill over WILQ API.
10. Wilku UAT harness for real content work sessions.
11. Anti-slop execution guard for every slice.

## Out Of Scope

Goal 004 must not build:

- automatic WordPress publish,
- destructive updates of existing `ekologus.pl` content,
- mass article generation,
- direct Codex-authored production content,
- direct Codex/OpenAI calls bypassing WILQ API,
- direct WordPress client calls from skills,
- broad RAG/vector memory as the product brain,
- multi-client SaaS or agency admin,
- Ads/Merchant/Localo write automation,
- social publishing,
- success/failure claims before measurement readiness.

## Completion Definition

Goal 004 is complete only when current repo evidence proves all of this:

1. At least five Ekologus content work items are available as a real operating
   queue with typed actionable or blocked states.
2. Every selected work item can receive API-owned opportunity enrichment with
   evidence/source connectors or explicit blockers.
3. Typed Ekologus knowledge cards exist for services, buyer problems, triggers,
   CTA patterns, claims and evidence requirements.
4. The operations-grade Sales Brief consumes enrichment and knowledge cards and
   blocks drafts when service fit, claim policy, evidence or measurement context
   is missing.
5. Draft variants are generated only through WILQ API plus SDK Structured
   Outputs after all gates and always keep `publish_ready=false`.
6. Quality review blocks bad variants before human review.
7. Revision application is bounded, versioned, diffed, evidence-bound and forces
   quality review again.
8. Human review and audit remain mandatory before WordPress handoff.
9. WordPress handoff is draft-only, dry-run by default and structurally unable
   to publish or destructively update content.
10. Measurement outcome interpretation refuses early claims and classifies later
    outcomes conservatively.
11. `wilq-content-operator` skill uses only WILQ API and passes adversarial
    evals for unsafe shortcuts.
12. Wilku UAT is completed or explicitly owner-deferred with the remaining risk
    stated.
13. Full `rtk scripts/verify.sh` passes at completion.

## Verification Surface

Use focused verification after every slice and full verification before broad
completion claims.

Required proof surface:

- Python domain tests under `tests/content`.
- API contract tests for new endpoints.
- Shared schema tests for new typed contracts.
- Dashboard route/component tests for `/content-workflow`.
- Playwright dashboard proof for the work session path.
- Skill smoke and adversarial evals for `wilq-content-operator`.
- `rtk uv run python scripts/audit_complexity.py --changed --allow-frozen`.
- `rtk pnpm fallow:audit`.
- `rtk git diff --check`.
- Full `rtk scripts/verify.sh` before completion.

## Beads Operational Graph

Use Beads as the authoritative development task graph. Current Goal 004 epic:

- `wilq-seo-2qq` - Goal 004: Content Operations Layer.

Initial slices:

- `wilq-seo-xlw` - recovery and plan alignment.
- `wilq-seo-6kd` - freeze content workflow contract.
- `wilq-seo-a3t` - production content opportunity enrichment.
- `wilq-seo-dtj` - Ekologus typed knowledge cards.
- `wilq-seo-8xc` - operations-grade Sales Brief from enrichment and knowledge.
- `wilq-seo-ao0` - draft variants through structured outputs.
- `wilq-seo-a09` - bounded revision application.
- `wilq-seo-03a` - WordPress draft-only adapter boundary.
- `wilq-seo-prk` - measurement outcome interpreter.
- `wilq-seo-wr4` - WILQ content operator skill and UAT harness.
- `wilq-seo-akt` - anti-slop execution guard.

Do not duplicate these as markdown task tracking. This section is an index for
recovery only; operational status lives in Beads.

## Execution Order

### 1. Recovery and plan alignment

Inspect first: `AGENTS.md`, `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md`,
`docs/goals/archive/003-goal.md`, Beads.

Build: this goal file, active `PLANS.md` transition, progress ledger update and
Beads graph.

Do not build: product behavior.

Proof: `bd ready --json`, `git diff --check`, commit and push.

### 2. Freeze the content workflow contract

Inspect first:

- `apps/api/wilq_api/routers/content_workflow.py`
- `wilq/content/workflow/api.py`
- `wilq/content/workflow/models.py`
- `wilq/content/workflow/store.py`
- `packages/shared-schemas/src/contentWorkflow.ts`
- `apps/dashboard/src/routes/ContentWorkflowSurface.tsx`

Build: contract inventory and drift tests across Python API, shared schemas and
dashboard helper contracts.

Do not build: enrichment, variants or new UI behavior.

Proof: focused contract tests, shared schema tests, dashboard tests and
changed-code audit.

### 3. Add ContentOpportunityEnrichment

Inspect first: content queue, diagnostics, GSC/GA4/Ahrefs/Ads/Merchant/Localo
evidence surfaces and WordPress inventory.

Build: typed enrichment per `work_item_id` with intent, service fit, buyer
problem, buyer trigger, CTA hypothesis, measurement baseline, source facts and
blockers.

Do not build: broad RAG, fake opportunity score or prompt-only keyword research.

Proof: API tests for evidence/source/service-fit blockers and successful
enrichment.

### 4. Add Ekologus knowledge cards and operations-grade Sales Brief

Inspect first: `wilq/knowledge`, current sales brief, claim ledger, content
draft package and Ekologus source docs.

Build: typed cards plus an operations-grade Sales Brief that consumes enrichment
and knowledge.

Do not build: prose dumps or knowledge hidden only in prompts.

Proof: tests prove missing service card, claim policy or evidence blocks drafts.

### 5. Add draft variants and bounded revision application

Inspect first: structured generation, draft package, quality review and revision
plan modules.

Build: typed variants and revision application with version/diff and mandatory
quality-review rerun.

Do not build: mass generation, free regeneration or publish-ready drafts.

Proof: fake SDK tests, API tests, adversarial tests and no WordPress write.

### 6. Harden WordPress draft-only and measurement outcome

Inspect first: handoff, WordPress execution and measurement window modules.

Build: optional draft-only adapter boundary and conservative outcome
interpreter.

Do not build: publish, destructive update or causal success theater.

Proof: tests prove dry-run default, publish impossible, early outcome blocked
and later interpretation source-bound.

### 7. Add WILQ content operator skill and UAT harness

Inspect first: existing WILQ content skills, skill eval harness, hooks and
`/content-workflow`.

Build: `wilq-content-operator` skill that orchestrates WILQ API only, plus UAT
packet for three to five real content work items.

Do not build: direct writer skill, direct OpenAI calls, direct WordPress calls or
auto-approval.

Proof: skill smoke, adversarial evals, Playwright/UAT proof and full verify.

## Stop Conditions

Stop and record a blocker if:

- generation can happen without evidence/source/preflight/brief/claim gate,
- React starts deciding workflow state,
- Codex writes production drafts directly,
- WordPress publish or destructive update becomes reachable,
- measurement claims can happen before outcome readiness,
- dev preview URL becomes canonical evidence,
- stale aliases are retained without an explicit short migration,
- broad RAG becomes the first answer instead of typed cards and validators,
- changed files grow frozen monoliths with new feature behavior.
