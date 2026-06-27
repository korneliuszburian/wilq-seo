# PLANS.md - WILQ Long-Range ExecPlan

This is the long-range living ExecPlan for WILQ.

Current cleanup and `/goal` live in `PLAN.md`. This file describes the durable
product path after the active cleanup is green.

## How To Use This File

- Read `PLAN.md` first.
- Do not implement broad product layers until the current cleanup goal is
  complete.
- Keep this file self-contained and short enough to be useful after context
  loss.
- Update Progress, Surprises & Discoveries, Decision Log and Outcomes &
  Retrospective after meaningful milestones.
- Maintain the mandatory long-running-task sections:
  `Progress`, `Surprises & Discoveries`, `Decision Log` and
  `Outcomes & Retrospective`.
- Prune obsolete assumptions instead of layering new plans over old plans.
- Every milestone must end with focused verification or an explicit blocker.
- Every milestone must be written as: goal, work, result, proof.
- Every stopping point must update `Progress` with what is done, what remains
  and the exact next action.

## OpenAI Planning Standards

This plan follows these official patterns:

- ExecPlans / `PLANS.md`:
  `https://developers.openai.com/cookbook/articles/codex_exec_plans`
- Goals:
  `https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex`
- Codex prompting:
  `https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide`

Long-running task requirements:

- The task must be restartable from repo files, not chat memory.
- The plan must show user-visible outcome, implementation scope,
  verification surface and blocker policy before coding starts.
- A milestone is not complete until its named proof passes.
- A partially completed milestone must be split into completed and remaining
  work in `Progress`.
- Unexpected behavior, product corrections, wrong assumptions and test
  discoveries go into `Surprises & Discoveries` with evidence.
- Any route change, architecture pivot or scope decision goes into
  `Decision Log` with the reason.
- After a milestone, `Outcomes & Retrospective` records what changed, what proof
  exists, what remains risky and what should improve the next slice.

Goal requirements:

- A `/goal` must define:
  - outcome,
  - verification surface,
  - constraints,
  - boundaries,
  - iteration policy,
  - blocked stop condition.
- A goal must be narrow enough to audit and broad enough to let Codex choose the
  next valid action.
- Completion cannot be based on belief, screenshots alone, shape-only smoke or
  "looks done". It must match the verification surface.

Prompt requirements:

- Say what to read first.
- Say what to search.
- Say which commands/tools to use.
- Say what not to touch.
- Say what counts as proof.
- Say what to do if blocked.
- Replace vague wording with observable behavior and checks before
  implementation.
- Require updates to recovery docs after each meaningful slice.

Milestone template:

```txt
Objective:
What user-visible or system-visible state must become true.

Inspect first:
Files, endpoints, tests, docs and runtime surfaces to read before editing.

Tasks:
Concrete code/docs/test/browser work.

Acceptance:
The exact behavior that must be true.

Verification:
Commands, browser proof, evals or artifacts that prove acceptance.

Blocked stop condition:
Missing input/contract/credential/runtime state that stops the slice and the
exact next input needed.
```

## Product Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- WILQ Core must become reusable through workspace/profile contracts.
- Multi-client SaaS, agency admin, billing, tenant UI and workspace switcher are
  out of scope until Ekologus works deeply.

## Product Thesis

WILQ is not a chatbot, prompt pack, static report, SEO-slop generator, blind
autopublisher or one-client hardcode.

WILQ is an API-first Marketing Operating System:

- WILQ API is the brain.
- Dashboard is the marketer cockpit.
- Codex skills are operator workflows over API contracts.
- Connectors provide evidence, not product logic.
- Actions are safe operating units with validation, preview, confirmation,
  audit and blocked-claim handling.
- Knowledge is condensed into cards/rules/validators/evals, not long prompt
  dumps.
- Measurement closes the loop before success/failure claims.

## Permanent Invariants

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- Brak sprawdzenia przez człowieka -> brak WordPress draft handoff.
- No audit -> no zapis zmian.
- No measurement window -> no success/failure claim.
- Existing content is preserve-first.
- Dev/staging/design URLs are optional context only, never default source of
  truth, final canonical or blocker.
- Skills consume API; they do not invent product logic.
- Dashboard renders typed view-models; it does not rewrite business meaning.
- No UI string translators or hardcoded cleanup dictionaries.
- Client-specific service, claim, tone and conversion rules live in workspace
  layers, not reusable core.

## Target Product Graph

```txt
ClientWorkspace
-> Connector Registry
-> Evidence / Metric Facts
-> Knowledge Cards / Expert Rules
-> Domain Diagnostics
-> Marketing Priority Engine
-> Condensed Dashboard Cockpit
-> Action Validation
-> Human Review
-> Safe Draft/Write Handoff
-> Measurement Outcome
-> Knowledge Feedback
```

## Milestone 1 - Finish Current Cleanup

Objective:

Complete `PLAN.md`.

Required outcome:

- Active docs agree on corrected product model.
- Active API/content/action/skill contracts are free of stale dev/migration
  semantics.
- Marketer-facing surfaces use clean Polish operating language.
- UI translators and string patchers are removed.
- Focused tests, skill smoke, browser proof and `git diff --check` pass.

Stop condition:

- If any stale active field remains, do not start new product layers.

## Milestone 2 - ClientWorkspace-Ready Core

Objective:

Make Ekologus depth-first while extracting reusable boundaries.

Build typed contracts:

- `ClientWorkspace`
- `SiteProfile`
- `BrandProfile`
- `ServiceMap`
- `ClaimPolicy`
- `ConnectorProfile`
- `MeasurementProfile`
- `KnowledgeNamespace`

Tasks:

- Move Ekologus offer, service, claim, tone and CTA rules into workspace/profile
  data.
- Preserve current Ekologus behavior.
- Add tests proving workspace data is loaded from one place.
- Do not add multi-client UI.

Acceptance:

- Core modules no longer depend on global Ekologus-only vocabulary.
- A future workspace can be added as data/config plus connector setup, not by
  copying prompt text.

## Milestone 3 - ContentPreflight

Objective:

Before writing, WILQ must decide whether writing is allowed.

Result states:

- preserve
- refresh
- merge
- create
- block

Inputs:

- source public URL
- final canonical URL
- optional preview URL
- WordPress inventory
- GSC query/page facts
- GA4 measurement blockers
- Ahrefs review rows
- service map
- claim policy

Acceptance:

- No content draft request can bypass preflight.
- Existing content defaults to preserve unless evidence supports refresh or
  merge.
- Create is blocked when duplicate/canonical/cannibalization risk is unresolved.

## Milestone 4 - Content Inventory v2

Objective:

WILQ must know what content actually exists.

Inventory record:

- URL
- canonical URL
- post/page ID
- content type
- status
- title
- meta title and description
- H1/H2
- FAQ
- CTA
- internal links
- schema types
- modified date
- extracted main content
- source connector
- evidence IDs
- topic/service/funnel tags

Acceptance:

- Preserve/refresh/merge/create decisions use structured inventory, not only URL
  presence.
- Missing inventory facts become blockers, not guesses.

## Milestone 5 - Duplicate, Canonical And Cannibalization

Objective:

Prevent unsafe content creation.

Start deterministic:

- exact URL/path match
- slug match
- title/H1 similarity
- query overlap
- service/topic overlap
- canonical conflict
- same CTA/funnel/service overlap

Acceptance:

- WILQ explains why a topic should be preserved/refreshed/merged instead of
  created.
- No draft bypasses duplicate/canonical checks.

## Milestone 6 - ContentSalesBrief

Objective:

Turn content work into sales-aware, evidence-backed briefs.

Brief must include:

- content mode
- reader and buyer problem
- buyer trigger
- service mapping
- funnel stage
- objections
- proof required
- H1/title/meta/H2/FAQ/CTA direction
- internal link direction
- source facts
- missing evidence
- forbidden claims
- legal/factual review notes
- publication blockers

Acceptance:

- Draft generation can only use a typed sales brief.
- Brief explains why the content should exist commercially.

## Milestone 7 - Claim Ledger

Objective:

Track every risky claim before draft or publication.

Claim statuses:

- approved
- needs_source
- needs_expert_review
- forbidden
- stale

Claim types:

- service claim
- legal requirement claim
- risk claim
- guarantee claim
- performance claim
- SEO claim
- business outcome claim

Acceptance:

- Unsupported ranking, lead, revenue, compliance or guarantee claims are
  blocked.
- Draft artifacts cannot contain untracked risky claims.

## Milestone 8 - Human Review

Objective:

Human review is a required transition before draft handoff.

Review fields:

- reviewed_by
- factual accuracy
- brand voice
- sales value
- helpfulness
- duplicate risk
- legal safety
- CTA quality
- internal link quality
- decision
- notes

Acceptance:

- No draft is publish-ready without a completed human check.
- Review feedback becomes reusable knowledge.

## Milestone 9 - Structured Draft Generation

Objective:

Generate typed drafts or typed refusals.

Requirements:

- preflight passed
- sales brief exists
- claim ledger exists
- sprawdzenie przez człowieka path exists
- draft validates against schema

Acceptance:

- No loose prose generation path is considered product behavior.
- Messy user prompts cannot bypass gates.

## Milestone 10 - WordPress Draft Handoff

Objective:

Create safe draft-only WordPress handoff.

Requirements:

- validated preflight
- approved sales brief
- claim ledger
- sprawdzenie przez człowieka
- preview
- confirmation
- audit
- `post_status=draft`

Acceptance:

- WILQ can prepare a WordPress draft safely.
- WILQ never autopublishes by default.

## Milestone 11 - Measurement Loop

Objective:

Measure results after publication windows.

Measure:

- GSC impressions, clicks, CTR, position
- GA4 engaged sessions and key events when mapped
- source/medium quality
- Ads/search-term landing overlap when relevant

Acceptance:

- No success/failure claim before measurement window.
- Outcomes feed future decisions and knowledge cards.

## Milestone 12 - Marketing Priority Engine

Objective:

Make Command Center API-owned and decision-first.

Tasks:

- Rank decisions by evidence strength, freshness, business priority,
  blocker risk and actionability.
- Move canonical decision copy and CTA into API view-models.
- Keep connector readiness visible only when it blocks action.

Acceptance:

- Dashboard does not duplicate or invent decision copy.
- Wilku starts from one clear daily queue.

## Milestone 13 - Knowledge Compiler v2

Objective:

Condense sources and decisions into durable knowledge.

Cards:

- source card
- service card
- content card
- query cluster card
- claim card
- review feedback card
- outcome card
- duplicate/canonical card

Acceptance:

- Knowledge has lineage, freshness, confidence and owner.
- Stale knowledge lowers confidence or blocks claims.

## Milestone 14 - Dashboard For Marketer

Objective:

Make WILQ usable without developer narration.

Every route first screen must show:

- primary decision
- why it matters
- safe next step
- blocker
- evidence/source summary
- later measurement

Acceptance:

- Browser audit and marketer UAT show that Wilku knows what to do next.
- Raw technical detail is available but not default.

## Milestone 15 - Safe Execution Expansion

Objective:

Enable writes only when contracts are mature.

Requirements:

- typed payload
- preview
- confirmation
- audit
- failure handling
- secret redaction
- safety limits

Acceptance:

- Every write is traceable and reversible or has an explicit failure story.
- High-risk/destructive writes stay blocked until separately supported.

## Final Completion Definition

WILQ is complete for this long-range goal when:

- Ekologus works deeply as a real marketer cockpit.
- Core architecture is workspace-ready.
- Content preflight, inventory, sales brief, claim ledger, sprawdzenie przez człowieka, draft
  handoff and measurement loop are implemented.
- Ads, Merchant, GA4, Localo and Social follow the same evidence/review/audit
  pattern.
- Skills, hooks and evals enforce the same contracts.
- Dashboard is condensed and marketer-readable.
- Real marketer UAT or explicit owner deferral is recorded.
- Final verification passes or exact blockers are recorded.

## Progress

- 2026-06-25: Replaced old long-range plan with clean product path.
- 2026-06-25: Current cleanup goal lives in `PLAN.md`.
- 2026-06-25: Active cleanup proof is recorded in `docs/PROGRESS.md`: active
  runtime dev/migration scan passed, Content Planner and Demand Gen browser
  snapshots are clean for forbidden visible terms, and focused
  API/dashboard/skill checks passed. Cleanup is not complete for the whole
  cockpit: Command Center, Ads, Merchant, GA4 and Localo backend copy still
  needs source-level marketer-language cleanup before Milestone 2 starts.
- 2026-06-27: Action review-gate and preview validation labels are now sourced
  from WILQ API/domain output instead of route-local cleanup. `DetailPanels`
  prefers API label arrays for preview requirements and missing-data rows, and
  API tests fail if action label arrays fall back to generic technical wording.
- 2026-06-27: Action preview, confirmation and impact-check result blockers now
  carry API-owned `blocker_labels`; dashboard result panels render those labels
  instead of route-local blocker-key translations.
- 2026-06-27: Action detail no longer uses route-local fallback labels for
  preview requirements, missing-data rows or "after confirmation" rows.
  Unknown technical keys are not converted into generic marketer copy; active
  API sources must provide explicit Polish label arrays. Live API/browser proof
  for Ads target guardrails found no generic fallback labels.
- 2026-06-27: The last active `marketingLabels.ts` consumer was removed and
  the file was deleted. Action detail now reads API-owned payload label fields
  for blocked claims, Localo allowed reads, Ads target options and WordPress
  post status; route-local Ads/blocked-claim label translation is not allowed
  to return.
- 2026-06-27: Ads Doctor start-here copy, effect-check plan copy and business
  context status copy moved from React helpers into Ads API/shared-schema
  presentation fields.
- 2026-06-27: Localo blocked-claim source values, skill evals, smoke tests and
  knowledge rules now use Polish operating language. Old active values such as
  `GBP performance`, `GBP write`, `write path`, `competitor visibility` and
  `local visibility uplift` are now language-guarded instead of translated in
  React.
- 2026-06-27: Legacy content-review audit events are normalized at the action
  service boundary, so old dev-preview review terms stored in local state no
  longer leak through `/api/actions`.
- 2026-06-27: Removed the unused action gate label dictionary from
  `ActionObjectPanels`; action panels now rely on API-owned label arrays instead
  of route-local raw-key translation. A stale dashboard expectation for raw
  Merchant vendor text was inverted into a guard against showing that text.
- 2026-06-27: Merchant skill context-pack accepts the current runtime request
  shape without falling back to full context. The API must validate supported
  request fields explicitly and keep default skill contexts scoped and
  condensed.
- 2026-06-27: Social Publisher source evidence now uses `source_inputs` and
  `missing_publish_access` in the active API/skill contract. The old
  `candidate_inputs` field and social "permissions" wording were removed from
  active context, smoke tests and eval cases. Social source inputs carry
  condensed `context_summary` values instead of raw vendor dimensions.
- 2026-06-27: Content Planner active decision labels, content gate labels,
  WordPress match labels, preflight labels and Ahrefs candidate labels now come
  from WILQ API/domain output. The content route consumes those fields instead
  of owning React-side label helper maps for active content decisions. Proof is
  stored under `.local-lab/proof/20260627-content-api-labels/`.
- 2026-06-27: Command Center daily decisions now use WILQ API/shared-schema
  label fields for decision state, priority, route, CTA, source connectors,
  evidence summary, action summary, skill label and blocked promises. The route
  no longer owns local business-copy helper maps for those fields. Proof:
  `.local-lab/proof/20260627-command-center-api-labels/`.
- 2026-06-27: Command Center daily decisions now use WILQ API/shared-schema
  freshness labels. The route no longer falls back to raw freshness enum
  states.
- 2026-06-27: Marketing brief blockers now exclude successful vendor reads and
  non-marketing runtime adapters. Completed GSC/GA4/Merchant reads stay in
  evidence/metric sections; `what_blocks_us` now contains only real decision
  blockers such as GA4 claim readiness and Ads business context. Proof:
  `.local-lab/proof/20260627-marketing-brief-blockers/`.
- 2026-06-27: Ahrefs status, priority and blocked-promise labels now come from
  WILQ API/shared-schema fields. The `/ahrefs` route no longer owns Ahrefs
  label helpers and no longer renders raw metric-fact values as first-screen
  marketer copy. Proof:
  `.local-lab/proof/20260627-ahrefs-api-status-labels/`.
- 2026-06-27: Ads Doctor primary connector/status/decision labels now come
  from WILQ API/shared-schema fields. The route no longer owns helper copy for
  primary Ads titles, summaries, rationale, next step or top status labels, and
  source summaries no longer expose `koszt_micros=`, `wartość_konwersji=`,
  `search-term rows` or `wiersze_bez_konwersji` on the marketer surface. Proof:
  `.local-lab/proof/20260627-ads-api-decision-labels/`.
- 2026-06-27: Browser proof for Merchant, Content Planner and Ahrefs found
  remaining visible `ID` proof counts and product-ID wording. The producing
  API/domain/dashboard sources now render plain Polish proof summaries and the
  proof scan under `.local-lab/proof/20260627-label-cleanup-browser/` is clean
  for the targeted stale terms.
- 2026-06-27: Ads secondary proof rows, registry/action evidence counts and
  action impact-check results now use API-owned source/evidence/action labels
  instead of route-local counts or raw connector IDs in normal UI.
- 2026-06-27: Read-only parallel audit found one remaining active runtime
  compatibility path for old content-review audit terms in
  `wilq/actions/service.py` and stale 2026-06-25 handoff/audit docs that should
  be marked superseded or rewritten before the next product goal.
- 2026-06-27: Old content-review audit events based on dev-site mapping are now
  dropped from active action output instead of being rewritten at response time.
  The remaining cleanup is historical handoff/audit docs that still read like
  current dev-site migration guidance.
- 2026-06-27: Content action preview labels for brief source, brief mode,
  WordPress draft operation, WordPress post status, draft generation status,
  publication readiness and blocked claims moved into the content action API
  payload. The Content route now renders those fields directly and the removed
  local helper functions are guarded against returning.
- 2026-06-27: Merchant action detail previews now use API-owned typed
  `preview_cards`. The detail route prefers those cards before raw payload
  fallback, and Merchant feed issue cards show Polish problem/sample summaries
  without raw SKU/product IDs.
- 2026-06-27: Google Ads recommendation action details now use API-owned typed
  `preview_cards` without raw recommendation enums or raw campaign/budget IDs
  in primary card text.
- 2026-06-27: Localo metric labels now live in one domain label source used by
  Localo diagnostics and marketing brief. `MetricFactChips` no longer owns a
  metric-name dictionary; it renders API `metric_label` and exposes missing
  labels instead of guessing them.
- 2026-06-27: `MetricFact` now carries API-owned dimension key/value labels.
  `MetricFactChips` no longer owns dimension dictionaries and renders
  `dimension_labels` plus `dimension_value_labels` directly.
- 2026-06-27: Merchant diagnostic metric facts now receive API/domain
  metric and dimension labels. The Merchant route no longer owns a local
  metric-label dictionary for its evidence/limitations metric tiles.
- 2026-06-27: GA4 diagnostic metric facts now receive API/domain metric and
  dimension labels. The GA4 route no longer owns a local metric-label
  dictionary for its proof metric tiles.
- 2026-06-27: GA4 tracking-quality action previews now receive API/domain
  operation and missing-dimension labels. The GA4 route no longer owns those
  preview translators.
- 2026-06-27: Merchant action preview payloads now receive API/domain
  preview-contract labels. The Merchant route no longer owns that dictionary.
- 2026-06-27: Merchant issue clusters and issue decisions now receive
  API/domain reporting-context labels. The Merchant route no longer owns a
  reporting-context fallback.

## Discoveries

- Stale dev/staging assumptions can create large fake product work. Treat them
  as cleanup blockers, not backlog.
- Marketer-facing copy must be clean at source, not patched in React.
- Generic labels such as "warunek techniczny do sprawdzenia" are not useful
  enough for active action surfaces when the raw source key is known. Add a
  source label and a guardrail instead of preserving the fallback.
- Action result endpoints need the same label discipline as action detail
  payloads. If a result returns raw blocker keys for audit, it must also return
  marketer-facing labels for dashboard rendering.
- Test fixtures can drift from real action payload keys. When browser/API proof
  finds a real key that fixtures missed, align the fixture with the production
  key instead of adding a React-side translation.
- Knowledge/playbook text can reintroduce old operator language even when API
  payloads are clean. Treat active knowledge sources as product sources and
  clean them with the same guardrails.
- Persisted local-state records can reintroduce old product semantics even
  after current action payloads are clean. Treat API-visible history as part of
  the active contract and normalize or migrate it at the service boundary.
- Dead route-local dictionaries are still product risk even when unused. Remove
  them when API-owned labels already exist, and turn stale raw-string fixtures
  into guards instead of preserving them.
- Request shape drift is product risk. The API must define supported request
  fields explicitly and must not silently return full cross-system context when
  a skill-scoped request is intended.
- Skill context size is a product surface. A skill-default context must contain
  condensed decisions and labels, not full payloads or raw vendor enums that
  force Codex to parse implementation detail.
- Source evidence for a skill can leak technical vendor values even when the
  primary action cards look clean. Context-pack proof must scan nested
  skill-specific brief and tactical queue surfaces, not only the direct action
  payload.
- Content decision labels are product semantics, not presentation cleanup.
  Existing API-owned labels should be consumed directly by the route; active
  route-local label helpers are debt unless they are only rendering old action
  payload preview contracts waiting for their own cleanup slice.
- Content action preview labels are product semantics too. If a preview is
  visible to the marketer, the backend/action contract must provide its label;
  React must not translate source type, mode, operation, draft status or
  publication readiness enums.
- Command Center labels are part of the canonical daily view-model. If the first
  screen needs better wording, fix the command-center API/domain source and
  schema, not React-side dictionaries.
- Daily context-pack size is sensitive to live evidence count. The current
  default caps embedded evidence summaries at 32 and keeps full evidence IDs in
  decisions/briefs for drilldown; treat future size growth as a context
  condensation task, not a reason to hide useful labels from the dashboard.
- Completed connector refreshes are not blockers. If a successful read appears
  under `what_blocks_us`, fix marketing-brief source logic instead of changing
  dashboard copy.
- Browser text proof catches marketer-visible jargon that unit tests can miss.
- A response-time sanitizer for obsolete product semantics is still product
  debt even if the current API output looks clean. Prefer one explicit storage
  migration/drop policy plus a regression guard over keeping compatibility code
  in the active runtime path.
  Keep proof scans as part of every route cleanup slice and promote repeated
  findings into API/domain labels or language guards.
- Content Planner diagnostic labels follow the same rule as action preview
  labels: connector status, refresh status, section blockers and metric names
  are API/domain semantics. React may format numbers, but it must not own the
  meaning of those fields.
- Browser proof caught a Polish pluralization issue in Merchant preview card
  copy. Keep browser text proof in every marketer-route cleanup slice because
  API/unit checks do not catch all readability failures.
- Showing "Metryka bez etykiety" in the dashboard is useful as a failure
  signal. Do not hide missing API labels with React dictionaries; fix the
  producing domain contract and add a test.
- Dimension labels follow the same rule as metric labels. If a dimension key or
  value is visible to a marketer, the API contract must carry the label; React
  may only display it.
- Merchant raw enums such as `SHOPPING_ADS`, `MERCHANT_ACTION` and
  `NOT_IMPACTED` may remain internal/test input values, but marketer-facing
  payloads must expose Polish label fields and route tests must guard against
  rendering the raw enum.

## Decision Log

- WILQ is the system; Wilku is the human operator persona.
- Ekologus remains first depth-first workspace.
- No compatibility strategy for stale dev/migration contracts.
- No UI translators or hardcoded cleanup helpers.
- Full condensation is product behavior, not a presentation layer only.
- Historical audit data may keep storage lineage, but API-visible action output
  must not expose obsolete dev-preview or review-language fields.
- Route-local action gate translations are not a compatibility layer. The WILQ
  API/domain contract must provide marketer-facing labels for active action
  gates and blockers.
- Default skill contexts are operator contracts. Full raw context stays behind
  explicit `full_context: true`; default skill calls must remain condensed and
  free of unnecessary raw vendor values.
- Merchant labels belong in one domain label source. Tactical queue and
  Merchant diagnostics must share those labels instead of carrying separate
  local maps or exposing vendor enum strings.
- `source_inputs` is the active social draft source-evidence contract. Do not
  restore `candidate_inputs` or publish-permissions wording as compatibility
  aliases.
- Active Content Planner decision, gate, WordPress match, preflight and Ahrefs
  candidate labels are API-owned. Do not reintroduce React dictionaries for
  those labels; migrate remaining action-preview label helpers only through
  typed API/action source fields.
- Active Command Center daily-decision labels are API-owned. Do not reintroduce
  route-local dictionaries for decision copy, source labels, metric labels,
  blocked promises, CTA labels or skill labels.
- Action detail first-screen preview cards must come from typed
  `ActionObject.preview_cards`. Raw action payload inspection is allowed only
  as a temporary fallback for unmigrated action kinds or inside technical
  detail.
- Metric chip names must come from `MetricFact.metric_label`. Dimension
  key/value labels must come from `MetricFact.dimension_labels` and
  `MetricFact.dimension_value_labels`; do not add new dashboard dictionaries
  for metric semantics.
- Merchant metric labels belong in `merchant_labels.py` and the Merchant API
  view-model, not in `MerchantDiagnosticSurface`.
- GA4 metric labels belong in the GA4 diagnostics API/domain view-model, not
  in `Ga4DiagnosticSurface`.
- GA4 action preview operation and missing-dimension labels belong in the GA4
  action payload contract, not in `Ga4DiagnosticSurface`.
- Merchant preview-contract labels belong in the Merchant action payload
  contract, not in `MerchantDiagnosticSurface`.
- Marketer-visible proof counts should describe "dowody źródłowe", not `ID`.
  Technical identifiers stay in schemas/audit/drilldown, not in the primary
  decision surface.
- If a marketer route needs a semantic dictionary to explain a status, blocker,
  metric, source or action, treat it as a missing API/schema/view-model field.
  Do not add or preserve route-local translators as cleanup strategy.

## Outcomes & Retrospective

- Current outcome: the active cleanup is materially reducing dashboard/API
  Polglish and raw technical leakage, but it is not complete.
- Latest accepted proof: Merchant, Content Planner and Ahrefs no longer show
  targeted `ID` proof-count/product-ID wording in browser text/snapshot proof,
  and the focused API/dashboard checks plus language guard passed.
- Latest content cleanup proof: Content Planner diagnostics now expose
  API-owned status, blocked-claim and metric labels; focused API/dashboard
  tests, typecheck, language guard, live API proof and `agent-browser read` for
  `/content-planner` passed.
- Remaining risk: docs, dashboard routes and skill/context-pack fixtures can
  drift back into append-only history or raw vendor terminology unless every
  repeated issue becomes a focused guardrail.
- Next improvement: keep `docs/PROGRESS.md` and `docs/goals/001-goal.md`
  concise; move detailed history to git/proof artifacts and keep only active
  gaps plus the next executable slice in recovery docs.
