# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-27

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

The goal is not to finish the full WILQ Marketing Operating System. The goal is
to make the current review cockpit coherent, condensed and usable enough that
Wilku can inspect it without reading technical internals.

## Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = public canonical content home.
- Dev preview hosts = optional design/staging context only when explicitly
  configured for a workflow.

## Product Rules

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- Brak sprawdzenia przez człowieka -> brak WordPress draft handoff.
- No audit -> no zapis zmian.
- No measurement window -> no success/failure claim.
- No business logic in prompts or skill references.
- No React/UI translator functions for product semantics.
- No hardcoded label replacement.
- No compatibility aliases or deprecated active fields when a direct migration
  is feasible.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Current State

- Core route path remains:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Current cleanup has already moved many Command Center, Content, Ads, GA4,
  Merchant, Localo, Ahrefs and Action Detail labels from dashboard helpers into
  API/domain/shared-schema labels.
- Recent committed cleanup slices:
  - `c5ea815 fix(dashboard): source ads and knowledge labels from api`
  - `66a0a4d fix(dashboard): source tactical labels from api`
  - `443dad4 fix(actions): drop obsolete content review audits`
  - `d2f78a6 fix(actions): label impact check result sources`
  - `6497044 fix(ads): source negative keyword labels from api`
  - `df4c750 fix(ads): clean recommendation and keyword context copy`
  - `5a805aa fix(merchant): condense source and evidence labels`
  - `d783636 fix(ga4): clean measurement labels`
  - `0a7414e fix(localo): clean access proof labels`
  - `6e93975 fix(dashboard): hide raw trace ids in detail panels`
  - `e6001a5 fix(dashboard): source proof labels from api`
  - `f74c770 fix(demand-gen): expose clean proof labels`
  - `be6205b fix(brief): use clean action wording`
  - `709a4cc fix(dashboard): remove id jargon from proof copy`
  - `551108f fix(ads): source secondary proof labels from api`
  - `f853404 fix(dashboard): clean registry evidence counts`
- The Ads recommendation/keyword-context cleanup removes raw
  recommendation enum summaries, mixed English/Polish recommendation-review
  wording, raw keyword match/status rendering and fixed English shorthand
  labels.
- The Merchant cleanup adds API-owned source connector labels
  and evidence summaries, then uses them in Merchant panels instead of raw
  connector IDs, evidence IDs and read-contract/debug labels.
- The GA4 cleanup is committed. It adds API-owned source connector labels,
  evidence summaries and safe reporting-dimension labels, then uses them in GA4
  panels instead of raw `(not set)`, `tracking-gap`, connector IDs, evidence IDs
  and `ID` evidence counts.
- The Demand Gen cleanup is committed. It adds API-owned source labels and
  evidence summaries, then uses them instead of raw source IDs and `ID` proof
  counts.
- The latest proof-copy cleanup is committed. Merchant, Content Planner and
  Ahrefs no longer show `ID` proof counts or "przykładowe ID produktów" in
  normal route proof copy; Marketing Brief and action validation no longer
  expose `akcji WILQ`, `ID dowodu` or English validation messages.
- Ads Doctor secondary proof rows now use API-owned evidence, source and action
  summaries instead of route-local counts or `Akcje WILQ` labels.
- Actions, Opportunities, Registry and Knowledge panels no longer render
  `Dowody: X ID` as normal route copy in the touched paths.
- Action impact-check results now return API-owned source labels and evidence
  summaries, and the dashboard no longer renders raw source connector IDs in
  that result panel.
- Old content-review audit events based on dev-site mapping are now dropped
  from active action output instead of being rewritten at response time.
- Stale 2026-06-24/25 handoff and audit docs that still mentioned dev-site
  migration now carry superseded notes.
- Current active slice: final stale-term scan and recovery alignment for
  Goal 001.
- Tactical Queue, Brief Workflow, Merchant tactical snippets, Ads Doctor and
  Knowledge panels now consume API/shared-schema labels for the touched
  priority/source/evidence/action/blocker/dimension/status/display label paths.
- Action detail previews no longer import `marketingLabels.ts`; the old
  route-local Ads/blocked-claim translator file has been deleted. The touched
  action preview labels now come from API-owned payload label fields.
- Ads Doctor no longer owns start-here summary, effect-check summary or
  business-context status wording in React. Those fields are now sourced from
  Ads API/shared-schema contracts.
- Content Planner no longer owns route/local helpers for content brief source,
  content brief mode, WordPress draft operation, WordPress post status, draft
  generation status or publication readiness. Content action preview payloads
  now carry those labels from the backend.
- Content Planner no longer owns connector status, refresh status, section
  blocked-claim, section title or metric-name translators. Content diagnostics
  now return typed API labels for those fields, and the dashboard renders them
  directly.
- Merchant action detail previews now expose typed API preview cards and the
  detail route renders them before raw payload fallback. Merchant feed issue
  cards show Polish problem/sample summaries instead of raw SKU/product IDs.
- Localo metric facts now share a domain label source across diagnostics and
  marketing brief, and `MetricFactChips` reads `metric_label` instead of a
  React-side metric-name dictionary.
- Metric fact dimensions now carry API-owned `dimension_labels` and
  `dimension_value_labels`; `MetricFactChips` no longer owns dimension
  key/value dictionaries.
- Merchant diagnostics now label Merchant metric facts and Merchant metric
  dimensions at the API/domain layer; the Merchant route no longer owns a
  local metric-label dictionary for evidence/limitations metric tiles.
- GA4 diagnostics now label GA4 metric facts and GA4 metric dimensions at the
  API/domain layer; the GA4 route no longer owns a local metric-label
  dictionary for proof metric tiles.
- GA4 tracking-quality action previews now carry API-owned operation and
  missing-dimension labels; the GA4 route no longer owns those translators.
- Merchant action preview payloads now carry API-owned preview-contract labels;
  the Merchant route no longer owns that dictionary.
- Merchant issue clusters and issue decisions now carry and render API-owned
  reporting-context labels; the Merchant route no longer owns a local
  reporting-context fallback.
- Command Center daily decisions now carry and render API-owned freshness
  labels; the route no longer falls back to raw freshness enum states.
- Google Ads recommendation action details now render API-owned preview cards
  without raw recommendation enums or raw Google Ads IDs in primary card copy.
- Google Ads budget action details now render API-owned preview cards without
  raw operation names or raw Google Ads IDs in primary card copy.
- Google Ads negative-keyword action details now render API-owned preview cards
  without raw match type, level or Google Ads IDs in primary card copy.
- Google Ads custom-segment action details now render API-owned preview cards
  without raw member type, old English internal segment name or Google Ads IDs
  in primary card copy.
- Demand Gen action details now render API-owned preview cards without raw
  Google Ads channel enum keys in primary card copy.
- Keyword Planner access blocker action details now render API-owned preview
  cards without raw Google Ads API error strings in primary card copy.
- Social draft action details now render API-owned preview cards without raw
  source connector IDs or metric keys in primary card copy, and the old
  `source_inputs` payload fallback was removed from Action Detail.
- WordPress draft handoff action details now render API-owned preview cards
  without raw candidate IDs, preview-contract names or operation names in
  primary card copy.
- Content refresh action details now render API-owned preview cards for content
  brief review and WordPress draft payload review. The primary card copy uses
  public/final URL semantics and no longer depends on raw content payload
  contracts, `target_site`, `target_url` or mapping-review wording.
- Google Ads search-term n-gram action details now render API-owned preview
  cards without raw `SearchTermNgramReview`, preview-contract names or
  n-gram-to-negative-keyword contract keys in primary card copy. Live browser
  proof passed, but this route remains slow enough to need a separate
  performance slice.
- Google Ads target-guardrail and strategy-review action details now render
  API-owned preview cards without raw action types, validation keys or `.env`
  field names in primary card copy.
- Touched Ads, Merchant, GA4 and tactical queue paths now hide raw
  evidence/action link IDs behind numbered links and use marketer-readable
  loading/error copy instead of endpoint or route names.
- Ads Doctor dead route-local status/risk label helpers were removed and are
  guarded by route source tests.
- Recovery docs are being condensed because long append-only progress logs made
  the active goal harder to resume.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and `docs/CONTEXT.md` must stay
   short and aligned. History belongs in git and proof artifacts, not active
   recovery docs.
2. `DetailPanels.tsx` now has typed action-detail preview view-model paths for
   Merchant feed issues, Google Ads budget reviews, Google Ads recommendation
   reviews, Google Ads negative-keyword reviews, Google Ads custom-segment
   reviews, Demand Gen readiness reviews, Keyword Planner access blocker
   reviews, social draft inputs, WordPress draft handoff reviews and content
   refresh reviews plus Google Ads search-term n-gram reviews and GA4
   tracking-quality reviews plus Localo visibility reviews, but remaining
   action kinds still infer active preview cards from raw payload shape.
   Migrate those action kinds one by one; raw payload may remain only in
   collapsed technical detail.
3. Demand Gen, registry/workflow, action detail and knowledge routes still have
   scattered raw fallback paths. Fix them by adding typed API/schema/view-model
   labels; do not add route-local replacement dictionaries.
4. Repeated metric/dimension naming in dashboard components should become
   API-owned labels. Metric names in `MetricFactChips` now use `metric_label`;
   dimension key/value labels now use `dimension_labels` and
   `dimension_value_labels`. Keep removing route-local metric dictionaries as
   they are found; Merchant and GA4 diagnostic metric tiles are now migrated.
   Merchant preview-contract and reporting-context labels are now migrated.
   Pure numeric formatting can stay in UI.

## Execution Policy

- Use `rtk` before every shell command.
- Inspect existing implementation before editing.
- Prefer small verified slices and conventional commits.
- Use subagents for parallel read-only audits or disjoint write scopes.
- Do not let multiple workers edit the same files without explicit ownership.
- After each slice:
  - run focused tests,
  - capture browser/API proof when a marketer route changes,
  - update only current recovery facts,
  - commit and push a coherent green slice.

## Verification

Focused checks:

- Docs-only: `rtk git diff --check`.
- API/schema/action: focused `rtk uv run pytest ...`.
- Dashboard: touched route test plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skill changes: deterministic smoke and targeted eval.
- Marketer copy: `rtk uv run python scripts/marketer_language_guard.py`.
- Browser: `agent-browser` snapshot for touched marketer routes.

Broad checks:

- `rtk scripts/verify.sh` before cross-surface completion claims.

## Completion Definition

Goal 001 is complete when:

- Active docs agree on the corrected product model.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Focused API/dashboard/skill checks pass for all touched slices.
- Browser proof verifies touched marketer routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.

The final WILQ Marketing Operating System remains a later goal. It still
requires ContentPreflight, sales brief, claim ledger, sprawdzenie przez
człowieka, WordPress draft handoff, measurement loop, workspace profiles,
knowledge lifecycle and safe execution gates.
