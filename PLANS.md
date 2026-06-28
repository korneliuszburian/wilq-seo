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
- No UI string translators, `replaceAll` masking helpers or hardcoded cleanup
  dictionaries.
- No deprecated active fields, compatibility aliases or stale
  target/dev/migration semantics when direct migration is feasible.
- Primary marketer language uses `Centrum pracy`, `Treści`, `Google Ads`,
  `blokady` and WILQ-described evidence instead of working names and raw IDs.
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
- UI translators, string patchers and compatibility aliases are removed where
  direct migration is feasible.
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

Make Centrum pracy API-owned and decision-first.

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
- 2026-06-27..2026-06-28: Active cleanup moved many marketer-facing labels from
  React helpers into typed API/domain/shared-schema fields across Centrum
  pracy, Ads, Merchant, GA4, Localo, Ahrefs, Knowledge, tactical queue, metric
  chips and action previews. Detailed proof is in git commits and
  `.local-lab/proof/`; `docs/PROGRESS.md` keeps only current state and latest
  accepted proof.
- 2026-06-28: Current remaining cleanup work is label fallback hardening,
  remaining content/ads payload-derived panels, context-pack copy and recovery-doc
  pruning. Do not start deferred product layers until `PLAN.md` completion is
  green or explicitly deferred.
- 2026-06-28: Unknown Knowledge, Localo, GA4, Demand Gen, opportunity-domain
  and Merchant tactical labels now fall back to neutral Polish operator labels.
  The remaining raw fallback scan is limited to non-marketer connector
  normalization and title fallback paths.
- 2026-06-28: Treści expandable plan/draft panel now renders
  API-owned action preview cards instead of constructing marketer-facing cards
  from content/WordPress payload arrays.
- 2026-06-28: Treści selected-decision first screen now renders
  API-owned `marketer_decision` fields instead of parsing content action
  payload previews.
- 2026-06-28: Knowledge cards now render confidence as a neutral Polish label
  instead of using confidence text as a visual status state.
- 2026-06-28: Knowledge first-screen decision and card summaries now use
  API/domain source, action, evidence, knowledge and lineage labels instead of
  route-local count assembly.
- 2026-06-28: Knowledge playbook cards now use API/domain
  `required_evidence_summary_label` and `mapped_action_type_summary_label`
  instead of route-local Polish count formatting. Live API proof confirmed the
  fields on `/api/knowledge/playbooks`; browser proof lives at
  `.local-lab/proof/knowledge-playbook-labels-clean.txt`.
- 2026-06-28: Szanse cards now render API/domain evidence, source, action and
  knowledge summary labels instead of route-local count assembly.
- 2026-06-28: Google Ads search-term, negative-keyword and change-history
  surfaces now use API/schema display labels for campaign, ad group, change
  event and changed resource context instead of visible raw IDs. Live API proof
  confirmed label fields on `/api/ads/diagnostics?view=summary`; browser proof
  lives at `.local-lab/proof/ads-display-labels-clean.txt`.
- 2026-06-28: Treści expanded decision and Ahrefs review cards now use API
  labels or neutral Polish operator fallbacks instead of visible raw enum/status
  keys. Browser proof lives at
  `.local-lab/proof/content-enum-labels-clean.txt`.
- 2026-06-28: Demand Gen now uses API/domain `action_summary_label` and
  campaign-channel labels instead of route-local action count formatting or raw
  channel fallbacks. Live API proof confirmed
  `/api/demand-gen/diagnostics`; browser proof lives at
  `.local-lab/proof/demand-gen-summary-labels-clean.txt`.
- 2026-06-28: Workflow cards now use API/domain
  `missing_contract_labels` for expanded missing-data details instead of raw
  workflow contract keys.
- 2026-06-28: Workflow cards and run summaries now use API/domain source,
  evidence, action, missing-data and blocked-claim summary labels. Fresh
  `/workflows` loads no longer wait on hidden related-action data.
- 2026-06-28: Recovery docs were condensed again. `docs/PROGRESS.md` and
  `docs/goals/001-goal.md` now keep current state, active findings and latest
  proof instead of append-only implementation history.

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
  route-local label helpers are debt. If an old action payload preview contract
  still needs a route-local reader, record a dated blocker with the affected
  action kind and removal condition instead of treating it as compatibility.
- Content action preview labels are product semantics too. If a preview is
  visible to the marketer, the backend/action contract must provide its label;
  React must not translate source type, mode, operation, draft status or
  publication readiness enums.
- Centrum pracy labels are part of the canonical daily view-model. If the first
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
- Treści diagnostic labels follow the same rule as action preview
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
- Unknown enum fallback is a shared product surface. Even if a normal dataset
  only emits known values, fallback paths must be neutral Polish copy because
  vendor contracts drift and tests should prove the drift does not leak raw
  keys to the marketer.
- A dashboard panel that needs action preview semantics should render
  `ActionObject.preview_cards`; reading action payload arrays is temporary debt
  only when a domain-specific selected-decision view-model does not yet exist.
- A dashboard's selected-decision first screen should use a domain view-model
  such as `marketer_decision`; action preview cards are for expandable action
  details, not for reconstructing the primary decision.
- Recovery docs can become product noise if they preserve every finished slice.
  Keep detailed history in git commits and proof artifacts, and keep recovery
  files short enough to restart from.

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
- Active Treści decision, gate, WordPress match, preflight and Ahrefs
  candidate labels are API-owned. Do not reintroduce React dictionaries for
  those labels; migrate remaining action-preview label helpers only through
  typed API/action source fields.
- Active Centrum pracy daily-decision labels are API-owned. Do not reintroduce
  route-local dictionaries for decision copy, source labels, metric labels,
  blocked promises, CTA labels or skill labels.
- Action detail first-screen preview cards must come from typed
  `ActionObject.preview_cards`. Raw action payload inspection is allowed only
  inside technical detail or as a short-lived blocker for unmigrated action
  kinds; do not preserve old payload fallbacks once a typed card exists.
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
- Unknown vendor/domain values in API-owned labels must use neutral Polish
  operator copy. Do not fall back to raw enum/source values in visible labels.
- Treści plan/draft cards are action preview semantics. They must stay
  on `ActionObject.preview_cards`; do not restore route-local content/WordPress
  payload card renderers.
- Treści selected-decision copy, metrics, source facts and H1/H2/FAQ/CTA
  snapshot belong to `marketer_decision`; do not restore
  `action.payload.content_brief_preview` parsing in the route.

## Outcomes & Retrospective

- Current outcome: the active cleanup is materially reducing dashboard/API
  Polglish and raw technical leakage, but it is not complete.
- Latest accepted proof: Merchant, Treści and Ahrefs no longer show
  targeted `ID` proof-count/product-ID wording in browser text/snapshot proof,
  and the focused API/dashboard checks plus language guard passed.
- Latest content cleanup proof: Treści diagnostics now expose
  API-owned status, blocked-claim and metric labels; focused API/dashboard
  tests, typecheck, language guard, live API proof and `agent-browser read` for
  `/content-planner` passed.
- Remaining risk: docs, dashboard routes and skill/context-pack fixtures can
  drift back into append-only history or raw vendor terminology unless every
  repeated issue becomes a focused guardrail.
- Next improvement: keep `docs/PROGRESS.md` and `docs/goals/001-goal.md`
  concise; move detailed history to git/proof artifacts and keep only active
  gaps plus the next executable slice in recovery docs.
- Latest fallback cleanup proof: focused API fallback tests, marketer language
  guard and `git diff --check` passed for Knowledge, Localo, GA4, Demand Gen,
  opportunity domain and Merchant tactical fallback labels.
- Latest Treści proof: focused route test, dashboard typecheck,
  marketer language guard and browser text proof passed after moving the
  expandable plan/draft panel to API-owned preview cards.
- Latest Treści proof: focused API test, route test, dashboard
  typecheck, marketer language guard and browser text proof passed after moving
  the selected-decision snapshot to API-owned `marketer_decision`.
- Latest Knowledge proof: focused Knowledge/StatusBadge tests, dashboard
  typecheck, marketer language guard and browser text proof passed after
  separating confidence copy from status badge state.
- Latest Workflow proof: focused API/shared-schema/dashboard tests, dashboard
  typecheck, marketer language guard and browser proof passed after moving
  missing-data details to API/domain labels.
- Latest Workflow proof: focused API/shared-schema/dashboard tests, dashboard
  route test, dashboard typecheck, marketer language guard and browser proof
  passed after moving process summaries to API/domain labels and fixing the
  hidden-actions loading state.
- Latest blocked-claim fallback proof: focused API fallback tests, marketer
  language guard and helper proof passed after central labels stopped exposing
  unknown raw technical claim values.
- Latest Knowledge proof: focused route test, dashboard typecheck, marketer
  language guard and browser proof passed after Knowledge details stopped
  showing raw connector IDs and fixed Polish count forms.
- Latest Knowledge proof: focused API/shared-schema/dashboard tests, dashboard
  typecheck, marketer language guard and browser proof passed after moving
  first-screen decision and card summaries to API/domain labels.
- Latest Szanse proof: focused API/shared-schema/dashboard tests, dashboard
  typecheck, marketer language guard and browser proof passed after moving
  evidence, source, action and knowledge summaries to API/domain labels.
- Latest Knowledge proof: focused API/shared-schema/dashboard tests, dashboard
  typecheck, marketer language guard, live API proof and browser proof passed
  after moving knowledge blocked-claim summaries to API/domain labels.
- Latest GA4 proof: focused API/shared-schema/dashboard tests, dashboard
  typecheck, marketer language guard, live API proof and browser proof passed
  after moving GA4 evidence/action summaries to API/domain labels.
