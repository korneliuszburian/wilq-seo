# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-28

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

This goal does not finish the full WILQ Marketing Operating System. It makes
the current review cockpit coherent, condensed and usable enough that Wilku can
inspect it without reading technical internals.

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
- No React/UI translator functions, `replaceAll` helpers or route-local
  dictionaries for product semantics.
- No compatibility aliases or deprecated active fields when a direct migration
  is feasible.
- Remove stale target/dev/migration semantics from active contracts.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.
- Raw IDs may appear in technical panels, audit detail and trace views only.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Current Cleanup Language

The canonical cleanup vocabulary is defined in `PLAN.md`. This goal file should
not repeat stale working names except when describing an explicit guardrail.
Dashboard paths may keep existing technical route slugs during this goal, but
primary navigation, headings, summaries, skill output and recovery docs should
use cleaned Polish operator language.

## Current State

- Cleanup has already moved many Ads, Merchant, GA4, Localo, Ahrefs,
  Knowledge, Brief Workflow, tactical queue and Action Detail labels from
  dashboard helpers into API/domain/shared-schema fields.
- Touched marketer surfaces now avoid raw evidence/action/connector IDs,
  endpoint names, raw enum keys, old dev-site mapping wording and English
  validation copy in normal UI.
- Action Detail normal preview renders typed API preview cards only. Raw action
  payloads remain available only behind the collapsed technical detail panel.
- Demand Gen diagnostics expose typed API preview cards; the route no longer
  builds its primary preview from raw `payload_preview` shape.
- Generic status routes, Demand Gen, Merchant, GA4, Ads, Content and custom
  segment first-screen labels have been tightened to marketer-readable Polish.
- Legacy raw audit summaries are no longer cleaned by string replacement
  helpers; raw historical summaries collapse to a neutral audit note.
- Ahrefs/content public contracts now use public URL wording; active
  diagnostics, source facts, tactical queue and WordPress draft handoff no
  longer expose stale target-field semantics.
- Knowledge operating map now carries API-owned labels for source connectors,
  evidence summaries, missing data and blocked claims, so the Knowledge route
  does not show playbook refusal rules or raw connector IDs on the first screen.
- Knowledge playbooks now expose Polish source rules and output contracts.
- UAT packet/result scripts now use marketer-facing Polish route names and
  markdown labels.
- Ahrefs visible copy now uses `dowody`, `SEO i treści`, `linki zwrotne`,
  `widok Treści` and `organiczne słowa dla URL`; live Ahrefs API/browser proof
  shows no `Ahrefs evidence`, `SEO/content`, `backlinków` or `per URL` residue.
- Custom Segments candidates now expose API-owned preview cards and rejection
  reason labels. The dashboard route no longer derives the visible segment card
  from `candidate.payload_preview`.
- GA4 full review now renders API-owned action preview cards and no longer
  parses `action.payload.payload_preview` for the review card.
- Ads negative keyword candidates now expose API-owned preview cards. The
  dashboard route no longer derives the visible negative-keyword card from
  `candidate.payload_preview`.
- Ads recommendation rows now expose API-owned preview cards. The dashboard
  route no longer derives the visible recommendation card from
  `row.payload_preview`.
- Ads budget rows now expose API-owned preview cards. The dashboard route no
  longer derives the visible budget card from `row.payload_preview`.
- Merchant product samples and product performance rows now expose API-owned
  display labels. The dashboard route no longer shows raw product sample IDs,
  raw Ads product status enums or raw Ads cost micros in those panels.
- Merchant decision and price-impact previews now expose API-owned preview
  cards. The dashboard route no longer parses raw `payload_preview` for those
  marketer-facing cards.
- Content URL semantics now use public/final wording in active gates. Active
  content diagnostics/actions no longer expose dev-site placement semantics.
- Social source inputs no longer use a hardcoded dev-preview host filter.
  Content objects must expose a public/final/canonical URL before they can drive
  that workflow.
- Content primary URL labels no longer fall back to `preview_url`.
- Shared `StatusBadge` no longer owns a product-language dictionary. Registry,
  workflow, Opportunities, tactical queue, marketing brief, Custom Segments,
  Demand Gen, Merchant and Content badges use API/domain `*_label` fields.
- Opportunity, workflow run, marketing brief, tactical queue, Merchant issue
  cluster, Custom Segments read contracts and Demand Gen readiness contracts now
  expose the missing status/risk labels through typed API/shared schemas.
- Demand Gen campaign mode review no longer exposes active
  `transition_candidate` / `demand_gen_transition_*` contracts. API, shared
  schemas, dashboard, skill smoke and playbook/rule IDs now use
  `demand_gen_campaign_mode_review`, `review_required`, `review_status_label`
  and marketer-facing labels such as `kontrola trybu kampanii`.
- Marketing brief items expose API-owned `kind_label`, and Brief Workflow cards
  render that label instead of raw brief kind enums.
- Tactical queue items expose API-owned `dimension_value_labels`, and touched
  tactical/Merchant/metric chips no longer fall back to raw dimension values in
  marketer-facing context.
- Content source facts use Polish operator labels instead of raw GSC
  key-value strings, and the Content status heading uses `Stan danych treści`.
- Tactical queue GSC diagnoses use Polish metric labels instead of raw
  `clicks=` / `impressions=` key-value strings.
- Active WILQ skill contracts now use Polish operator wording for dowody,
  źródła danych, blokady and technical trace IDs instead of pushing
  English/Polish mixed terms into primary skill answers.
- Opportunity fallback copy and Content vendor-read blockers now use Polish
  source-data wording instead of credential/vendor/query-page/playbook jargon.
- Seeded content refresh action copy now uses Polish source-data wording instead
  of `URL/query evidence`, `GSC query/page` or WordPress inventory jargon.
- Dashboard e2e proof now checks current marketer labels such as `Centrum
  pracy`, `Treści` and `Google Ads`, and no longer expects raw Ads evidence IDs
  in the primary Ads proof panel.
- Google Ads OAuth repair and blocked Merchant feed diagnostics now use Polish
  operator wording instead of raw OAuth/credential/vendor-read jargon.
- Ads n-gram and custom-segment action/context copy now uses Polish operator
  wording instead of `N-gram review`, `search-term evidence`, `negative keyword
  queue` or English `forecast` wording.
- Dashboard proof sections now use action-oriented `Dowody i warunki ...`
  wording, and touched routes/tests no longer expose low-value proof/audit
  jargon in primary marketer copy.
- Connector label fallbacks now use safe Polish operator labels instead of raw
  connector IDs in shared helpers, command center, marketing brief, GA4/Localo
  diagnostics and context-pack refresh-run summaries. Refresh-run summaries now
  expose `connector_label` and `status_label`.
- Route labels now use safe operator-label helpers in Centrum pracy and the
  workflow registry. Unknown routes no longer fall back to raw route paths or
  generic fallback copy.
- Ads diagnostics label fallbacks now use closed Polish labels for unknown
  vendor enums, changed fields, missing read contracts, metrics and review
  gates. Ads budget/recommendation preview cards no longer embed raw campaign or
  budget IDs in their marketer-facing card IDs.
- Ads blocked-claim source labels were cleaned from old verdict wording toward
  direct labels such as `opłacalność` and `zmarnowany budżet`.
- Shared Python schema fallbacks for marketing risk, tactical domains,
  tactical dimensions, metric dimension values and Ads/Demand Gen read statuses
  now use safe Polish fallback labels instead of raw enum values.
- Ads recommendation and change-history helper fallbacks now use safe Polish
  labels for unknown recommendation types, missing recommendation metrics,
  change resource types and change operation types.
- Ahrefs, GA4, Localo and Merchant diagnostic label helpers now use neutral
  Polish fallback labels for unknown statuses, read contracts and risks instead
  of exposing raw enum values or `status: ...` strings.
- Workflow registry and workflow-run labels now use neutral Polish fallback
  labels for unknown process statuses and risks instead of exposing raw values.
- GA4 tracking-quality actions, Ads campaign triage and Opportunities now use
  neutral Polish fallback labels for unknown operation types, dimensions,
  validation gates, channels and risks.
- Content draft handoff, post-publication measurement and tactical WordPress
  match summaries now use `stan ...` wording instead of `status:` prefixes in
  marketer-facing summaries.
- Dashboard StatusBadge usage now passes raw state values with API labels for
  Knowledge, Action, GA4 and Merchant status/risk/validation badges instead of
  using the visible label as the visual state.
- Tactical queue cards show evidence/action summaries first and keep linked
  trace IDs inside `Szczegóły techniczne`.
- Workflow cards use `Brakujące dane` and `Granice wniosków`; focused tests no
  longer preserve raw `queued` or old verdict wording as visible workflow copy.
- Google Sheets compact route copy now uses safe export/testing language
  instead of export contract/UAT jargon.
- Metric chips now use `zmiana:` and `Etykieta: wartość` formatting instead of
  `delta:` and key=value display.
- Action preview API results now expose typed/redacted `preview_items` and
  `preview_cards`. Marketer-facing preview surfaces must use those view-models;
  raw action payload previews stay in payload/audit/technical detail only.
- Centrum pracy daily-decision badges now render API-owned labels instead of raw
  decision-state enum text. API titles use `Google Ads` and `Treści` wording,
  and old drilldown wording was removed from the active action plan copy.
- Browser proof after the status-label slice covered touched marketer routes;
  visible badges used Polish labels from the API rather than raw status/risk
  enum values.
- Recovery docs are being kept short because append-only progress logs made the
  active goal harder to resume.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and this file short and
   aligned.
2. Remove remaining scattered raw fallback paths in knowledge, Content, GA4,
   Localo, Merchant and Ads helper modules by adding typed
   API/schema/view-model labels.
3. Remove remaining status/risk label-as-value calls in dashboard surfaces when
   the caller can pass both visual state and API label.
4. Add typed contract/vendor-enum label registries outside the already-cleaned
   Ads diagnostics helper path so unknown read contracts and vendor enums do not
   fall back to raw snake_case or English values in marketer-facing copy.
5. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
6. Dashboard still needs focused cleanup for Knowledge first-screen summaries,
   workflow/registry counters and remaining content/ads payload-derived panels.
7. The remaining active `replace("_", " ")` scan hits are Merchant attribute-key
   normalizers used for equality matching, not visible operator labels.
8. The remaining dashboard StatusBadge label-as-value scan hits are source and
   domain tags, not status/risk/validation state badges.

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

- Active docs agree on the corrected product model and cleaned language.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Deprecated active fields and compatibility aliases are removed where direct
  migration is feasible.
- Focused API/dashboard/skill checks pass for all touched slices.
- Browser proof verifies touched marketer routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.

The final WILQ Marketing Operating System remains a later goal. It still
requires ContentPreflight, sales brief, claim ledger, sprawdzenie przez
człowieka, WordPress draft handoff, measurement loop, workspace profiles,
knowledge lifecycle and safe execution gates.
