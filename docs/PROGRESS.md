# WILQ Progress Ledger

This is the short recovery ledger. It is not a changelog and must not become an
append-only transcript.

Full current plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-29

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Marketer-facing UI and skill output must use Polish operating language.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators or string replacement helpers.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.

## Latest Verified State

- Tactical queue, Merchant fallback issue cards and workflow brief cards now
  render metadata as labelled Polish chips instead of slash-combined fragments
  such as `obszar / zadanie / priorytet` or `rodzaj / priorytet`. Focused
  dashboard tests guard against those source patterns returning; live browser
  proof after stack restart confirmed `/social-publisher` and `/merchant` did
  not expose the guarded stale fragments.
- Merchant issue decisions now use source labels such as
  `Merchant: problem z atrybutem: link produktu - błąd strony produktu`
  instead of slash-combined raw issue/attribute wording. Merchant action
  preview cards use the same clean issue/attribute order, and the expandable
  action intro copy in Merchant, Treści, Google Ads and GA4 no longer creates
  broken singular grammar from `1 akcja do sprawdzenia`. Focused API tests,
  dashboard route tests, both language guards and browser proof for
  `/merchant`, `/content-planner`, `/ads-doctor` and `/ga4` passed.
- Centrum pracy, powiązane action-plan summaries, tactical queue GSC/content
  diagnoses and Ads/content diagnostic summaries no longer use report-style
  equality metric copy, slash shorthand for GSC query/page counts or English
  query labels. The producing API/domain sources now emit natural Polish metric
  phrases with basic plural handling. Focused API tests, dashboard tests, live
  `/api/dashboard/command-center`, browser proof and both language guards passed.
- Google Ads campaign triage no longer summarizes priority counts with
  report-style equality copy. The Ads diagnostics API now emits natural Polish
  priority phrases such as pilne kampanie and campaigns with a high review
  signal. Focused Ads API tests, live `/api/ads/diagnostics?view=summary` and
  the marketer language guard passed.
- Merchant attribute matching no longer uses underscore-to-space
  normalization. It now uses canonical comparison keys, while marketer labels
  stay in explicit label fields. Dashboard fixtures and API tests no longer
  preserve old report-style metric phrasing as positive expected copy.
- Knowledge operating map no longer marks the daily plan as unusable only
  because it contains blocked decisions. `Plan dnia WILQ` now reports
  `gotowe z blokadami`: the process is usable for the marketer, while blocked
  decisions remain visible as a boundary and risk signal. Live
  `/api/knowledge/operating-map` and `/knowledge` browser proof confirmed the
  corrected status.
- Treści top metric tiles now come from the API-owned
  `operator_summary.metric_tiles` instead of route-local labels. The visible
  `/content-planner` screen shows `Zapytania i adresy z GSC`,
  `Treści znalezione w WordPress` and `Luki Ahrefs powiązane z WordPress`;
  live API and browser proof returned zero hits for the old slash/arrow
  shortcuts, English overlap wording and visible raw inventory wording. The
  marketer language guard now blocks those stale content metric shortcuts.
- Active skill contracts, Ads/Merchant/Localo operator copy and the marketing
  brief no longer use `akcje sprawdzone w WILQ` / `akcji sprawdzonej w WILQ`
  wording. They now describe actions as `akcje do sprawdzenia w WILQ` and keep
  system control separate from human review. `scripts/marketer_language_guard.py`
  now blocks the stale phrasing and duplicated `do sprawdzenia do sprawdzenia`
  copy. Live API and browser scans over Ads, Merchant, Localo and Procesy
  returned zero hits for the guarded stale terms.
- `/actions` no longer labels validated-but-still-reviewable actions as
  `sprawdzone w WILQ`. The action API now distinguishes contract validation
  from human review with `kontrola WILQ poprawna`, while the action status
  remains `gotowa do sprawdzenia`. Live API and browser proof for `/actions`
  returned zero hits for the misleading old label in action validation and
  review-gate copy.
- Action reason copy no longer mixes Polish with the raw English word
  `evidence`. The negative-keyword review reason now says `bieżące dowody`,
  and `/api/actions` plus `/actions` browser proof returned zero hits for the
  guarded route slugs and stale English action-reason terms.
- Full action and Centrum pracy API responses no longer expose generic metric
  dimension placeholders such as `wymiar`, `wymiar do sprawdzenia`,
  `wartość wymiaru do sprawdzenia` or `wartość do sprawdzenia`. Shared metric
  schemas now label common Google Ads, Ahrefs, content inventory and WordPress
  dimensions at the API/source level, with technical IDs described as available
  only in technical detail.
- Action recommended reasons no longer expose route slugs such as `/merchant`,
  `/content-planner`, `/ads-doctor`, `/ga4`, `/localo` or
  `/social-publisher` in operator-facing copy. The cleanup happened in the API
  action source, with a regression test guarding the route-slug leak.
- `PLANS.md` now expands the long-range BDOS benchmark watchlist with a
  unified safe-change flow, stronger PMax asset/search-theme/readiness tracks,
  GTM measurement-safety copy boundaries, GA4 source hygiene, lead-quality loop
  and Google automation readiness checks. These remain future capability
  tracks, not active Goal 001 scope.
- Daily context-pack connector status now carries API-owned Polish
  `status_label`, freshness labels and operator-safe summaries. It no longer
  exposes empty freshness labels or summaries like `status configured` to
  Codex skills.
- Daily context-pack metric facts now carry Polish `metric_label` plus
  labelled metric dimensions from `dimension_labels` and
  `dimension_value_labels`. Compact skill context no longer exposes raw metric
  keys such as `issue_product_count` or raw vendor dimension enums such as
  `MERCHANT_ACTION`, `FREE_LISTINGS` and `competitor_page`.
- Marketer-useful metric dimension values now stay useful in compact skill
  context: GA4 source/campaign/landing-page values and GSC query values no
  longer collapse to generic placeholder copy when they are safe to show.
- Compact Codex skill context no longer exposes raw active-action payload
  bodies, payload key lists, payload-preview key names or raw blocker keys such
  as `payload_apply_allowed_false`. Skill contexts now use typed preview cards,
  Polish blocker labels and `/api/actions/{action_id}` for drilldown.
- Compact Codex skill context now also removes raw Ahrefs read-contract keys,
  raw Ahrefs metric-label dictionary keys, raw Merchant preview-card IDs and
  raw Merchant issue-type values. Live scans for daily, content, Merchant, Ads,
  GA4, Localo and Ahrefs context packs returned zero hits for the guarded
  technical terms.
- `scripts/context_pack_language_guard.py` now makes that live context-pack
  stale-language scan repeatable. `scripts/verify.sh` runs it against the
  temporary skill API before skill smokes, and `scripts/pre_demo_gate.sh` runs
  it against the managed local API before dashboard/skill demo checks.
- Active Codex skill interface names, prompts and response contracts now use
  Polish operator wording instead of old English working names, raw proof-ID
  wording, blocker jargon or mixed query/page wording.
  `scripts/marketer_language_guard.py` now guards that class of phrases in
  active skill/docs/test contracts.
- `docs/CONTEXT.md` current-boundary rules now use Polish WILQ operating
  language instead of old English formulas. `scripts/marketer_language_guard.py`
  guards that recovery file together with the active plan files.
- Goal completion owner-defer proof now uses one canonical Polish JSON shape
  from the UAT handoff. Stale alias fields such as `defer_uat`, `date`,
  `owner`, `safe_to_show` and `blocked_claims` are rejected instead of silently
  normalized.
- Filled marketer UAT result input now also uses one canonical Polish JSON
  shape. Stale English packet fields and `pass`/`fail`/`yes` route/result
  values are rejected instead of normalized, while the human markdown report
  renders Polish route and readiness labels.
- Live UAT packet markdown now renders a readable Polish session card instead
  of raw JSON blocks. The machine JSON remains available through `--format json`
  for recording/completion checks, but the marketer handoff no longer leads
  with technical field names.
- Latest live UAT packet was regenerated on 2026-06-29T05:18:19Z in
  `.local-lab/proof/marketer-uat-packet-20260629T051819Z.{md,json}`.
  The markdown packet has no guarded hits for old route names, stale content
  URL terms or technical action-model jargon. `/api/connectors` was reachable
  at the same slice: 12 connectors total, 9 configured, 2 missing-credential
  optional social connectors and Google Sheets disabled by scope.
- Skill smoke guardrails now validate the Polish WILQ instruction for metrics
  and source evidence instead of stale English proof wording. Content skill
  smoke accepts condensed context-pack preview cards for WordPress draft handoff
  while full payload contracts stay verified through API tests. Merchant
  Playwright proof now checks the current technical label `Klucz dowodu w WILQ`
  after opening evidence details.
- Action review-gate helpers no longer use old migration-oriented function
  names. Historical raw audit fragments are still sanitized before reaching
  normal operator copy, but the active code path now names that behavior as raw
  content review audit cleanup instead of content migration review.
- Action panel technical drawer code no longer uses the old
  `ActionPayloadPreviewToggle` component name or `payload={action.payload}`
  prop. The drawer remains visible as `dane techniczne akcji`, and
  `ActionPanels.test.tsx` guards against reintroducing the old
  payload-preview component naming.
- Action Detail preview-card renderer is now named around change preview, not
  payload preview. `ActionDetailRoute.test.tsx` guards against restoring the
  old `ActionPayloadPreviewSummary` function name while the normal panel keeps
  rendering typowane karty podglądu akcji.
- Dashboard action panels now live in `ActionPanels.tsx` and export
  `ActionFocus` / `ActionIdFocus`. The UI layer no longer names this shared
  action surface after the technical `ActionObject` model, while the API type
  remains unchanged at the contract boundary.
- GA4 expandable action panel no longer masks a missing API action label with
  the route-local fallback `liczba akcji do sprawdzenia`. If the API label is
  missing, the dashboard now shows the explicit failure signal
  `brak etykiety akcji z WILQ`, and `App.test.tsx` guards that behavior.
- Shared dashboard status badges no longer fall back to raw status values when
  an API label is missing. The visible UI shows `brak etykiety z WILQ` so
  missing view-model copy is caught as a source-of-truth defect instead of
  leaking enum text to the marketer.
- Action review panels now use the API-owned review-gate status label instead
  of a route-local fallback. Operator-facing audit history also strips raw
  audit identifiers and old preview-audit reference copy from summaries, while
  technical audit IDs remain available only through API/audit detail.
- Demand Gen landing-quality cards no longer join landing page and traffic
  source with slash copy. They render API-owned `landing_page_label` and
  `source_medium_label` as separate labelled lines, with a dashboard test
  guarding against returning to `/oferta/ / google / cpc` copy.
- Compact Codex skill context no longer exposes generic metric-dimension
  placeholders like `wymiar` or `wartość wymiaru do sprawdzenia`. Metrics now
  keep only dimensions with useful API-owned labels; live context-pack guard
  covers daily, content strategist and Ahrefs packs for this regression.
- Ads skill context active actions now compact action metrics through the same
  metric context helper, so `wilq-ads-doctor` no longer receives raw
  `dimension_value_labels` or generic placeholder dimension values in active
  action objects.
- `PLANS.md` now includes a long-range BDOS benchmark watchlist for GTM
  measurement safety, Google Ads API v24.2/PMax tracks, GA4 source hygiene,
  lead-quality loops and bidding/campaign-change readiness. These are future
  capability tracks, not active Goal 001 scope.
- Connector status now uses the latest successful `vendor_read` when available.
  On 2026-06-29T04:15Z, GSC, GA4 and Merchant refreshed live with
  `vendor_data_collected=true`, and on 2026-06-29T00:20-00:43Z Google Ads,
  Ahrefs, Localo,
  WordPress ekologus.pl and WordPress sklep.ekologus.pl were refreshed live and
  `/api/connectors` reported all configured first-party/source connectors as
  fresh. Merchant refresh retries transient `ReadTimeout` responses. LinkedIn
  and Facebook remain missing-credential optional social connectors; Google
  Sheets remains disabled by current scope. Google Ads Keyword Planner remains
  blocked by developer-token approval, not by missing OAuth credentials.
- Action validation errors for Ads, GA4 and Localo now use source-owned Polish
  operator copy instead of English/technical `payload`, `requires`,
  `apply_allowed` or mutation-readiness wording. Focused tests guard this
  against regression.
- Primary navigation and touched route headings use marketer-readable Polish:
  `Centrum pracy`, `Merchant`, `Treści`, `Google Ads`, `GA4`, `Procesy`,
  `Szanse`, `Akcje`, `Baza wiedzy`.
- Touched Ads, Merchant, GA4, Localo, Ahrefs, Knowledge, tactical queue,
  Procesy and action-detail surfaces render API/domain/shared-schema labels
  instead of route-local label dictionaries.
- Action-detail normal preview uses typed API preview cards. Raw action payloads
  stay behind technical detail.
- Action-detail review gates use API/domain blocker summary labels in normal
  panels. Full blocker lists stay in technical detail.
- Action-detail effect checks use plain before/after comparison wording from
  API/domain labels, including historical stored summaries.
- Impact-check label handling no longer rewrites old window wording with
  string replacement; historical summaries are normalized through typed
  prefix labels.
- Raw historical audit details are sanitized by a generic raw-contract guard.
  Legacy raw review events remain visible only as neutral history and do not
  unlock review gates.
- Content, Merchant, Ads and Localo normal route copy avoids technical-evidence
  wording such as `dowody techniczne`, `techniczne warunki akcji` and
  `techniczne potwierdzenie`. Technical detail drawers remain allowed.
- Codex skill eval cases no longer require working route names or English
  evidence wording as operator-visible output, and the eval harness now fails
  operator-facing JSON values that reintroduce old route names or technical
  jargon.
- Daily and content-strategist context-pack tests now scan string values for
  old working route names, stale content URL terms and technical jargon so
  compacted prompt context cannot quietly reintroduce the cleaned language.
- Active actions with operator preview payloads are guarded to expose typed
  preview cards, preventing fallback rows assembled from raw preview shape.
- Expanded DOM/browser audit across core marketer routes and action details has
  no visible hits for old route names, stale content URL terms or technical
  action-model jargon outside technical drawers. Fresh `agent-browser` proof on
  2026-06-29 covered `command-center`, `merchant`, `content-planner`,
  `ads-doctor`, `ga4`, `localo`, `ahrefs`, `knowledge`, `actions` and
  `workflows`.
- Playwright marketer demo proof passed again on 2026-06-29T04:23Z for the
  path from Centrum pracy through Merchant, Treści, GA4, Google Ads and Localo;
  screenshots live under
  `.local-lab/proof/dashboard-demo/2026-06-29T04-23-01-046Z/`.
- Content active semantics use public/final URL wording. Active content
  diagnostics/actions no longer expose dev-site placement semantics as product
  logic.
- Treści selected-decision and plan/draft panels render API-owned
  view-models instead of parsing raw action payload previews.
- Treści loading/error action fallback uses the API-owned action summary label
  instead of assembling action-count copy from action IDs.
- Treści preflight, summary, decision, proof and action panels use API/domain
  evidence and action summary labels instead of route-local count formatting.
- Tactical queue API now uses Polish `Treści i GSC` / `Treści` labels instead
  of old mixed content labels, and Ahrefs blocked-claim copy now uses Polish
  wording for missing GSC and WordPress checks.
- `/actions` first-screen priority cards now describe the safe operating step
  instead of pointing at technical details. Raw action data remains behind the
  explicit technical toggle; proof:
  `.local-lab/proof/actions-technical-drawer-20260629.txt`.
- Ads live-data diagnostics and evidence detail now use Polish proof wording
  instead of `ID dowodu`; connector-status evidence summaries no longer expose
  angielskie opisy pól dostępu. Dowód w przeglądarce:
  `.local-lab/proof/evidence-detail-no-id-wording-20260629.txt` and
  `.local-lab/proof/evidence-detail-expanded-no-id-wording-20260629.txt`.
- Codex context-pack product rules and strict instruction now use Polish WILQ
  operating language instead of old English rule wording. Live context-pack
  guard covers daily, content, Merchant, Ads, GA4, Localo and Ahrefs skills.
- Active plan/recovery docs now use Polish WILQ operating rules instead of old
  English rule formulas; `scripts/marketer_language_guard.py` guards those
  active plan files.
- Merchant, Ads, GA4, Demand Gen, Localo and social touched preview surfaces use
  API-owned preview cards or display labels instead of raw payload shape.
- Localo top metric tiles use API/domain missing-data summary labels instead
  of route-local count formatting.
- GA4 overview, decision and proof panels use API/domain evidence and action
  summary labels instead of route-local count formatting.
- Google Ads first-screen, condensed decision, proof and action panels use
  API/domain evidence and action summary labels instead of route-local count
  formatting.
- Google Ads and GA4 diagnostics expose top-level API-owned
  `source_connector_labels`, and the touched proof panels render those labels
  instead of assembling source labels from nested sections or decisions.
- Google Ads start-here, business-context, strategy-readiness and campaign
  triage panels use API/domain action summary labels instead of route-local
  action count formatting.
- Google Ads optimizer-readiness and strategy review panels use API/domain
  source-contract, policy and required-validation summary labels instead of
  route-local count formatting.
- Google Ads strategy review panel uses API/domain missing-data summary labels
  instead of route-local count formatting.
- Action priority cards, action registry cards and connector refresh run cards
  use API/domain evidence summary labels instead of route-local evidence count
  formatting.
- WordPress handoff action review gates use operator-safe check keys and labels;
  normal `/actions` proof no longer exposes technical checklist jargon.
- Merchant overview, operator summary, decision, proof and action panels use
  API/domain evidence and action summary labels instead of route-local count
  formatting.
- Merchant product-file summaries, product-sample next steps and visible blocked-claim
  labels use API/domain Polish wording. Live `/merchant` proof no longer shows
  raw Merchant metric keys, vendor endpoint names, action IDs, generic
  Merchant fallback labels or old product-file jargon in normal copy; the
  language guard now covers Merchant terms in active API, dashboard, skill,
  knowledge, workflow and plan sources.
- Ahrefs decision and gap-contract panels use API/domain evidence and action
  summary labels instead of route-local count formatting.
- Ahrefs gap-contract metric tiles use API/domain missing-data and
  blocked-claim summary labels instead of route-local count formatting.
- Custom Segments candidate, forecast and proof panels use API/domain evidence
  and action summary labels instead of route-local count formatting.
- Custom Segments validation tiles use API/domain missing-data and
  required-check summary labels instead of route-local count formatting.
- Demand Gen uses API/domain evidence, action and campaign-channel labels
  instead of route-local count formatting or raw channel fallbacks.
- Google Ads search-term, negative-keyword and change-history surfaces use
  API/schema display labels for campaign, ad group, change event and changed
  resource context instead of visible raw IDs.
- Google Ads campaign triage, search-term, n-gram, 90-day safety and keyword
  context rows use API/domain evidence summary labels instead of route-local
  evidence count formatting.
- Google Ads campaign, KPI, budget, impression-share and change-history tables
  use API/domain row summary labels for human review gates, blocked claims and
  changed fields instead of route-local label joins.
- Google Ads shared-budget panel no longer exposes raw budget identifiers in
  normal marketer copy. Budget IDs remain technical row keys only; visible copy
  uses budget name fallback and campaign-count wording.
- Google Ads full-review optimizer, strategy-readiness, change-impact,
  campaign-triage and recommendation panels use API/domain summary labels for
  missing data, required checks and blocked claims instead of rendering long
  review/blocker arrays. Change-impact copy uses plain before/after comparison
  wording instead of old technical result-window wording.
- Connector settings cards use API/domain credential summary labels instead of
  route-local credential/source count formatting.
- Merchant issue-cluster cards and decision summaries use API/domain reported
  issue summary labels instead of route-local issue count formatting or broken
  Polish count forms.
- Treści expanded decision and Ahrefs review cards use API labels or neutral
  Polish operator fallbacks instead of visible raw enum/status keys.
- Knowledge details use API-owned source labels and Polish count forms instead
  of raw connector IDs.
- Knowledge seed cards use Polish marketer-facing summaries instead of English
  wording about evidence identifiers.
- Dashboard API smoke and demo proof no longer require stale proof language such
  as raw Merchant issue keys, raw proof IDs in normal demo flow, `audience size`,
  `launchu`, `DR`, `brak facts` or `competitor_page`.
- Dashboard API smoke now includes a shared runtime visible-copy guard over
  `main`, so core routes fail if old working route names, registry headings,
  stale URL/mapping terms, raw `payload` wording or vendor fallback keys return
  to the visible marketer surface.
- The old `Goal 002` draft is archived under `docs/goals/archive/`, and the
  marketer language guard now fails if another first-level `docs/goals/*.md`
  file appears beside the canonical `001-goal.md`.
- Knowledge first-screen decision and card summaries use API/domain source,
  action, evidence, knowledge and lineage summary labels instead of route-local
  count assembly.
- Knowledge playbook cards use API/domain evidence and action-type summary
  labels instead of route-local Polish count formatting.
- Knowledge decision cards use API/domain blocked-claim summary labels instead
  of joining blocked-claim arrays or falling back to raw counts in React.
- Knowledge decision-impact panels use API/domain missing-data,
  blocked-decision and blocked-claim summary labels. First-screen
  blocked-claim copy is condensed to count summaries, while full claim lists
  stay in details.
- Procesy cards and run summaries use API/domain source, evidence, action,
  missing-data and blocked-claim summary labels. Fresh `/workflows` loads no
  longer wait on hidden related-action data.
- Procesy expanded details use API/domain missing-data detail labels and
  condensed blocked-claim summaries instead of route-local label joins.
- Szanse cards use API/domain evidence, source, action and knowledge summary
  labels instead of route-local count assembly or raw identifiers.
- Shared `StatusBadge` does not own a product-language dictionary; touched
  surfaces pass raw state values plus API/domain visible labels.
- Unknown visible label fallbacks collapse to neutral Polish operator labels
  instead of exposing raw enum keys, snake_case or English values.
- Connector refresh runs hydrate Polish status labels at the shared schema
  boundary, including historical runs returned by the API.
- Full local verification passed after the current cleanup slice:
  `rtk scripts/verify.sh` completed backend tests, shared-schema tests,
  dashboard tests, API smoke, skill smokes, Playwright route smoke and
  dashboard build. Treat this as cleanup-gate proof, not final MOS completion.
- Live UAT packet export is ready for Wilku/marketer review and now uses
  Polish operator keys in the visible WILQ snapshot instead of raw
  `decision_type`, `status`, URL-field or route-check keys. The packet still
  does not prove UAT happened; it is the input for a 15-minute human session.
- Durable UAT handoff: `docs/handoffs/2026-06-29-marketer-uat-ready.md`.
  Next completion step is a filled real UAT result or an explicit owner defer
  note; do not replace that with more technical proof.
- Goal 001 completion proof is guarded by
  `scripts/goal_001_completion_check.py`. Running it without `--uat-result` or
  `--owner-defer` must return `blocked_missing_uat_proof`; that is the honest
  current state until UAT/defer evidence exists.
- Live context-pack language guard now also blocks `ActionObject`, `dry-run`,
  raw URL-field names and related blockers in compact skill context values.
  The content action compact context no longer sends the raw
  `content_url_review_contract` or source facts that name `source_public_url`.
- Fresh first-party Google reads are healthy after the latest stack restart:
  GSC, GA4 and Merchant are `configured`, have no missing credentials and have
  fresh `last_success_at` values from 2026-06-29T02:30Z. LinkedIn and Facebook
  remain optional missing-credential social connectors; Google Sheets remains
  disabled by current scope.
- Connector status objects now hydrate Polish `status_label` values at the
  shared backend schema boundary, so `/api/connectors` no longer returns empty
  visible status labels.
- Treści diagnostics now expose `live_data_status_label` from the API and the
  route renders that field instead of owning local live-data wording.
- Metric facts now hydrate Polish `metric_label` values at the shared backend
  schema boundary, and live contract smoke fails if a metric fact exposes an
  empty or raw snake_case metric label.
- Google Ads campaign rows now hydrate Polish campaign status and channel labels
  at the shared schema boundary, and live contract smoke rejects empty or raw
  visible `*_label` fields across checked API payloads.
- Current proof artifacts live in `.local-lab/proof/`; detailed history lives
  in git commits.

## Active Findings

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and
   `docs/goals/001-goal.md` short and aligned. History belongs in git and proof
   artifacts.
2. Continue raw fallback cleanup in active API/helper modules. Any new visible
   raw fallback must be fixed at typed API/schema/view-model source.
3. Continue typed contract/vendor-enum label registries outside the already
   cleaned Ads campaign status/channel path so unknown read contracts and vendor
   enums do not fall back to raw snake_case or English values in marketer-facing
   copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
5. Dashboard still needs focused cleanup for any newly found payload-derived
   panels. Compact skill context active actions are now guarded against raw
   payload leakage.
6. Merchant attribute-key matching now uses canonical comparison keys instead
   of underscore-to-space label normalization. Do not reintroduce generic
   underscore humanization as a compatibility layer.
7. Continue checking compacted context-packs after dashboard/API cleanup. Daily
   and content-strategist context packs have focused tests, and
   `scripts/context_pack_language_guard.py` now guards live compact skill
   contexts across the core skill set in both `verify.sh` and the pre-demo
   gate.
8. Continue focused browser audits when touched routes change. The latest
   expanded audit of core routes and action details is clean; any future long
   blocker/review list must be condensed at API/domain source, not trimmed in
   React.
9. Real marketer UAT is still required for a usefulness claim unless the owner
   explicitly defers it. Current handoff:
   `docs/handoffs/2026-06-29-marketer-uat-ready.md`.
   Guard:
   `rtk uv run python scripts/goal_001_completion_check.py --format markdown`.

## Latest Accepted Proof

Most recent verified local slice:

- Compact content action context cleanup: content strategist and GA4 skill
  context packs no longer expose raw URL review contract values such as
  `source_public_url`, `final_canonical_url` or
  `confirm_final_canonical_url` as string values. The full action detail
  remains available through `/api/actions/{action_id}`.
  Verification:
  - `rtk uv run pytest tests/test_context_pack_language_guard.py tests/test_api_contracts.py::test_codex_context_pack_scopes_content_strategist_payload tests/test_api_contracts.py::test_codex_context_pack_embeds_marketing_brief_contract -q`
  - `rtk scripts/local_stack.sh restart`
  - `rtk uv run python scripts/context_pack_language_guard.py --api-base http://127.0.0.1:8000`
  - `rtk uv run python scripts/marketer_language_guard.py`

Previous verified local slice:

- Completion guard for UAT/defer: `scripts/goal_001_completion_check.py`
  validates either a filled real UAT result or an explicit owner defer note.
  Without those inputs it returns `blocked_missing_uat_proof`, preventing a
  technical cleanup pass from being mistaken for a human usefulness proof.
  Verification:
  - `rtk uv run pytest tests/test_goal_001_completion_check.py tests/test_marketer_uat_result.py -q`
  - `rtk uv run python scripts/goal_001_completion_check.py --format markdown || true`

Previous verified local slice:

- UAT packet cleanup: `scripts/export_marketer_uat_packet.py` now exports
  marketer-readable Polish snapshot fields, and
  `scripts/record_marketer_uat_result.py` accepts the matching Polish filled
  result format. Fresh proof:
  `.local-lab/proof/marketer-uat-packet-20260629.md`,
  `.local-lab/proof/marketer-uat-packet-20260629.json`, and current
  `agent-browser` reads for Centrum pracy, Merchant and Treści. This remains
  preparation for real UAT, not UAT completion.
  Verification:
  - `rtk uv run pytest tests/test_marketer_uat_packet.py tests/test_marketer_uat_result.py -q`
  - `rtk uv run python scripts/marketer_language_guard.py`
  - packet/proof scan for old UAT keys and stale route/content terms
  - `rtk git diff --check`

Previous verified local slice:

- Broad cleanup verification: `rtk scripts/verify.sh` passed after action
  context condensation, typed preview-card cleanup and live Google connector
  proof. Live `/api/connectors` confirms GSC, GA4 and Merchant are configured
  and fresh with no missing credential names; `/api/content/diagnostics`,
  `/api/ga4/diagnostics` and `/api/merchant/diagnostics` all report
  `live_data_available=true`.

Previous verified local slice:

- Compact skill action-context cleanup: active actions in daily, content,
  Merchant, Ads, GA4 and Localo context packs now omit raw action payloads,
  payload key lists, raw payload-preview field names and raw apply-blocker keys.
  Full action detail remains available through `/api/actions/{action_id}` and
  typed preview cards.
  Verification:
  - `rtk uv run python scripts/context_pack_language_guard.py --api-base http://127.0.0.1:8000`
  - `rtk uv run pytest tests/test_api_contracts.py::test_daily_context_pack_uses_daily_decisions_for_action_summaries tests/test_api_contracts.py::test_daily_context_pack_preserves_action_review_gates tests/test_api_contracts.py::test_codex_context_pack_scopes_merchant_payload_preview -q`
  - `rtk uv run pytest tests/test_api_contracts.py::test_codex_context_pack_scopes_content_strategist_payload tests/test_api_contracts.py::test_ads_doctor_context_pack_uses_summary_diagnostics -q`
  - `rtk scripts/local_stack.sh restart`
  - live `POST /api/codex/context-pack` active-action scan for daily, content,
    Merchant, Ads, GA4 and Localo skills
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk git diff --check`

Previous verified local slice:

- Metric dimension usefulness cleanup: shared `MetricFact.dimension_value_labels`
  now preserves marketer-useful free-text values for queries, pages, landing
  pages, campaigns, sources and country while still translating known vendor
  enums. Live context-pack proof showed no guarded raw vendor terms and useful
  GA4/GSC dimension values in top metric facts.
  Verification:
  - `rtk uv run pytest tests/test_connector_status_labels.py tests/test_metric_store_and_cli.py -q`
  - `rtk uv run pytest tests/test_api_contracts.py::test_compact_metric_fact_context_uses_dimension_labels tests/test_api_contracts.py::test_codex_context_pack_embeds_marketing_brief_contract -q`
  - `rtk scripts/local_stack.sh restart`
  - live `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` metric usefulness scan
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk git diff --check`

Previous verified local slice:

- Daily context-pack metric-dimension cleanup: compact marketing brief metric
  facts now use `MetricFact.metric_label`, `dimension_labels` and
  `dimension_value_labels`, and known Ahrefs cross-surface metrics hydrate a
  Polish label before reaching Codex skills. Live `POST /api/codex/context-pack`
  proof showed 8 top metric facts and 0 raw metric/vendor-dimension failures
  for the guarded terms.
  Verification:
  - `rtk uv run pytest tests/test_api_contracts.py::test_compact_metric_fact_context_uses_dimension_labels tests/test_api_contracts.py::test_codex_context_pack_embeds_marketing_brief_contract tests/test_api_contracts.py::test_daily_context_pack_uses_daily_decisions_for_action_summaries tests/test_api_contracts.py::test_codex_context_pack_scopes_merchant_payload_preview -q`
  - `rtk uv run pytest tests/test_connector_status_labels.py tests/test_metric_store_and_cli.py -q`
  - `rtk scripts/local_stack.sh restart`
  - live `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` metric-dimension scan
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk git diff --check`

Previous verified local slice:

- Daily context-pack connector-status cleanup: compact connector status now
  exposes Polish `status_label`, freshness labels, last successful read time
  and operator-safe summaries. Live `POST /api/codex/context-pack` proof showed
  8 connector statuses and 0 raw/empty label failures after stack restart.
  Verification:
  - `rtk uv run pytest tests/test_api_contracts.py::test_codex_context_pack_embeds_marketing_brief_contract -q`
  - live `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` label scan
  - `rtk scripts/local_stack.sh restart`

Previous verified local slice:

- Connector freshness cleanup: live GSC, GA4 and Merchant vendor reads
  completed with external calls and `vendor_data_collected=true`; connector
  status now reuses the latest successful vendor read instead of showing
  credential-presence-only freshness after a successful refresh.
  Verification:
  - `rtk uv run wilq connectors refresh google_search_console --mode vendor_read --reason "Goal 001 live GSC data proof after access check"`
  - `rtk uv run wilq connectors refresh google_analytics_4 --mode vendor_read --reason "Goal 001 live GA4 data proof after access check"`
  - `rtk uv run wilq connectors refresh google_merchant_center --mode vendor_read --reason "Goal 001 live Merchant data proof after access check"`
  - `rtk uv run pytest tests/test_connector_status_labels.py -q`
  - `rtk uv run pytest tests/test_api_contracts.py::test_google_first_party_status_accepts_authorized_user_credentials tests/test_api_contracts.py::test_connector_status_does_not_expose_secret_values -q`
  - live `/api/connectors`, `/api/content/diagnostics`, `/api/ga4/diagnostics`
    and `/api/merchant/diagnostics` proof after `rtk scripts/local_stack.sh restart`

Previous verified local slice:

- Ads/GA4 source-label cleanup: `/api/ads/diagnostics?view=summary` and
  `/api/ga4/diagnostics` now expose top-level API-owned
  `source_connector_labels`, and the touched proof panels render those labels
  directly. The unused dashboard `connectorLabelsFromStatuses` helper was
  removed instead of kept as stale translator code.
  Verification:
  - `rtk uv run pytest tests/test_api_contracts.py::test_ads_diagnostics_summary_view_compacts_heavy_payload tests/test_api_contracts.py::test_ga4_diagnostics_exposes_landing_quality_contract -q`
  - `rtk pnpm --dir apps/dashboard typecheck`
  - `rtk pnpm --dir apps/dashboard test -- OpportunitiesRoute --runInBand`
  - live API proof after `rtk scripts/local_stack.sh restart`
  - `agent-browser` DOM proof for `/ads-doctor` and `/ga4`

Previous verified local slice:

- Content source-label cleanup: connector refresh runs now expose
  API-owned `connector_label`, content diagnostics/preflight decision objects
  expose `source_connector_labels`, and Treści no longer maps
  connector IDs in React.
  Verification:
  - `rtk uv run pytest tests/test_api_contracts.py::test_operator_label_fallbacks_do_not_expose_raw_connector_ids tests/test_api_contracts.py::test_content_diagnostics_blocks_until_vendor_read_when_no_content_evidence tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue -q`
  - `rtk pnpm --dir apps/dashboard typecheck`
  - `rtk pnpm --dir apps/dashboard test src/routes/ContentDiagnosticSurface.test.ts src/routes/App.test.tsx --pool forks --poolOptions.forks.singleFork`
  - `rtk uv run python scripts/live_contract_smoke.py --api-base http://127.0.0.1:8000`
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `agent-browser` text proof for `/content-planner`
  - `rtk git diff --check`

Previous verified local slice:

- Ads enum-label cleanup: Google Ads campaign rows hydrate Polish campaign
  status/channel labels, live API scans across core endpoints found no empty or
  raw visible `*_label` fields, and `live_contract_smoke.py` now guards visible
  operator labels.
  Verification:
  - `rtk uv run pytest tests/test_connector_status_labels.py tests/test_live_contract_smoke.py tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts -q`
  - `rtk uv run python scripts/live_contract_smoke.py --api-base http://127.0.0.1:8000`
  - `rtk uv run python scripts/marketer_language_guard.py`
  - live `*_label` scan across core API endpoints
  - `rtk git diff --check`

Previous verified local slice:

- Metric label cleanup: `MetricFact` hydrates Polish metric labels, live API
  scans across core diagnostics/actions/opportunities found no empty or raw
  metric labels, and `live_contract_smoke.py` now guards this contract.

Previous verified local slice:

- Connector/content live-data label cleanup: `ConnectorStatus` hydrates Polish
  status labels, `/api/connectors` has no empty status labels, and Treści shows
  API-owned `live_data_status_label` for GSC and WordPress readiness.
  Verification:
  - `rtk uv run pytest tests/test_connector_status_labels.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue -q`
  - `rtk pnpm --dir apps/dashboard typecheck`
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1`
  - live `/api/connectors` and `/api/content/diagnostics` proof after stack restart
  - `agent-browser snapshot` for `/content-planner`
  - `rtk git diff --check`

Previous verified local slice:

- Recovery goal-file cleanup: the old `Goal 002` draft moved to
  `docs/goals/archive/`, and `scripts/marketer_language_guard.py` now enforces
  that `docs/goals/001-goal.md` is the only active first-level goal file.
  Verification:
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk git diff --check`

Previous verified local slice:

- Dashboard proof contract cleanup: API-backed e2e smoke and demo proof now
  assert current marketer-readable route copy and reject stale proof wording
  such as raw Merchant issue keys, raw proof IDs in the normal demo flow,
  `audience size`, `launchu`, `DR`, `brak facts` and `competitor_page`.
- A shared runtime visible-copy guard now scans each core route's visible
  `main` text for stale route names, registry headings, stale URL/mapping
  terms, raw `payload` wording and vendor fallback keys.
- Current verification for this dashboard proof slice:
  - `rtk pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1`
  - `rtk pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-demo-proof.spec.ts --workers=1`
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk git diff --check`

## Older Proof History

Older verified slices are intentionally omitted from this recovery ledger. Use git history and `.local-lab/proof/` when older evidence is needed.
