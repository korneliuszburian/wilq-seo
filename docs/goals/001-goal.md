# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-20 21:28 CEST.

This is the only active goal file. Keep it short and current. Do not append a
chronological work log here. When a task is done, move it to the short completed
foundation list or remove it from the active queue. Git history is the detailed
archive.

Progress hygiene rule: `docs/PROGRESS.md` is a compact recovery ledger, not a
full chronological dump. Keep current state, last 3-5 slices, active gaps and
next best actions there. Older detail belongs in `docs/progress/archive/`; the
first full archive is `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Recovery Contract

Every Codex session working on WILQ must read these files first:

1. `AGENTS.md` - operating rules, secrets policy, local paths and gotchas.
2. `docs/goals/001-goal.md` - current active goal and queue.
3. `docs/architecture/bdos-class-wilq-operating-system.md` - product bar.
4. `docs/infra/001.md` - original product scope.
5. `docs/architecture/codex-runtime.md` - skills, hooks, MCP and Codex evals.
6. `docs/audits/001-output.md` - fresh 2026-06-18 audit and next-slice critique.

Keep this file updated when connector readiness, live data status, blockers,
verification state or next tasks change.

## Product Bar

WILQ is an API-first marketing operating system for Ekologus, operated by a
Polish marketer through dashboard + Codex Desktop/CLI + WILQ skills.

WILQ is not:

- a connector dashboard,
- a prompt pack,
- a static report generator,
- a list of readiness cards,
- a place for invented marketing metrics.

The expected loop is:

1. Connector reads collect source facts.
2. WILQ normalizes facts into evidence IDs and metric facts.
3. Knowledge cards and expert rules map facts to diagnosis.
4. Opportunities and ActionObjects describe safe next moves.
5. Dashboard and Codex skills show the same evidence/action state.
6. Writes stay `dry_run -> preview -> confirm -> audit`.

Every marketer-facing response must be in Polish with Polish diacritics. Stable
API IDs, connector IDs, evidence IDs, enum values and endpoint paths remain in
their original form.

Skills are thin operator workflows over WILQ API. Do not put product decision
logic, dedupe rules, edge-case fixes or dashboard cleanup logic into skill
references. If a skill needs a smarter decision, implement the typed
API/schema/view-model first and make the skill consume that field.

## Delivery Expectation

Do not claim "better than BDOS" as done until the data/action contracts prove
it. A strong Ekologus demo can be delivered before the full product is complete:
dashboard decisions, WILQ API evidence, Polish Codex skills, ActionObject
safety, eval ledger and visible blocked claims. Ads now has a derived KPI read
contract for CTR/CPC/conversion rate/CPA/ROAS as calculations from campaign
facts, a read-only account currency contract, a read-only budget context
contract for campaign daily budgets versus 7-day cost, a read-only Google Ads
recommendations contract, a read-only Google Ads impression-share contract, a
read-only Google Ads change-history contract, a typed Ads business context
contract for profit margin, business goal, budget goal and target ROAS/CPA
inputs, a read-only recommendation impact
preview for recommendation types that expose impact metrics, a review-only
recommendation apply payload preview, a read-only 90-day search-term safety
contract and a review-only negative keyword payload preview plus read-only
keyword match context for negative keyword review, plus a read-only Keyword
Planner enrichment contract for custom segment review. Custom segments now
have a review-only payload preview from real search terms, but no
targeting/apply support. Campaign budgets now have review-only
`CampaignBudgetOperation` payload previews from budget facts, but no budget
apply support.
Full BDOS-class parity still requires optimizer contracts such as
configured business targets used in decision scoring, recorded human strategy
review outcome, pre/post change-impact windows, approved Keyword Planner
access/idea rows in live data, forecast or audience-size checks, custom segment
targeting/apply previews, budget apply safety, apply confirmation and mutation
audit paths, plus real Localo ranking/GBP/competitor/review read contracts.
Missing contracts must be shown as blockers, not hidden with prompt language.

Latest ActionObject impact sanity truth, runtime proof 2026-06-20 21:28 CEST:
WILQ now has `POST /api/actions/{action_id}/impact-check`, typed
`ActionImpactCheckRequest/ActionImpactCheckResult`, local audit events
`action_impact_check_blocked` and `action_impact_check_completed`, dashboard
panel `Impact sanity check` and Codex context-pack propagation through
`ActionObject.review_gate.last_impact_check_status/by/at/summary`. Impact check
before confirmation is blocked with `action_confirmation_required`; impact check
after `preview -> confirm` records `action_impact_check_completed`, removes
only `impact_sanity_check_required` and keeps real apply blockers. Runtime
proof on a temporary state DB: impact-before-confirm ->
`action_impact_check_blocked`, preview -> `action_preview_generated`, confirm
-> `action_apply_confirmed`, impact-after-confirm ->
`action_impact_check_completed`, context-pack latest audit event ->
`action_impact_check_completed`, `last_impact_check_status=checked`,
`apply_allowed=false`. This satisfies the local impact-sanity visibility/audit
step only. It does not execute vendor apply and does not prove real mutation
audit paths. Full `scripts/verify.sh` after this slice passed: backend
`135 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
dashboard build OK.

Latest ActionObject confirmation truth, runtime proof 2026-06-20 21:03 CEST:
WILQ now has a separate `POST /api/actions/{action_id}/confirm`, typed
`ActionConfirmRequest/ActionConfirmResult`, local audit events
`action_confirmation_blocked` and `action_apply_confirmed`, dashboard panel
`Jawne potwierdzenie preview` and Codex context-pack propagation through
`ActionObject.review_gate.last_confirmation_by/at/summary`. Confirmation before
dry-run preview is blocked with `dry_run_preview_required`; confirmation after
preview records `action_apply_confirmed`, removes only the satisfied
human-confirm blocker and keeps real apply blockers such as prepare-only mode or
`payload_apply_allowed_false`. Runtime proof on a temporary state DB:
confirm-before-preview -> `action_confirmation_blocked`, preview ->
`action_preview_generated`, confirm-after-preview -> `action_apply_confirmed`,
context-pack latest audit event -> `action_apply_confirmed`,
`last_confirmation_by=operator_runtime_proof`, `apply_allowed=false`. This
satisfies the local `preview -> confirm` visibility/audit step only. It does
not execute vendor apply, does not satisfy impact-sanity checks and does not
prove real mutation audit paths. Full `scripts/verify.sh` after this slice
passed: backend `133 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, dashboard build OK.

Latest ActionObject dry-run preview truth, runtime proof 2026-06-20 20:44 CEST:
WILQ now has `POST /api/actions/{action_id}/preview`, typed
`ActionPreviewRequest/ActionPreviewResult`, local audit event
`action_preview_generated` and dashboard panel `Dry-run preview`. Preview uses
existing ActionObject payload preview rows and returns `dry_run=true`,
`mutation_allowed=false`, `preview_items_total`, `omitted_items`, blockers and
`review_gate`. Daily context-pack includes the compact `latest_audit_event`
for active actions so Codex can see that preview was generated without loading
full audit history. Runtime proof on a temporary state DB: preview endpoint
returned `200`, ActionObject and `wilq-daily-command` context-pack both carried
`latest_audit_event.event_type=action_preview_generated` and
`apply_allowed=false`. This satisfies the local dry-run/preview visibility step
only. It does not execute vendor apply, does not confirm mutation and does not
satisfy remaining impact-sanity or real mutation-audit requirements. Full
`scripts/verify.sh` after this slice passed: backend `131 passed`, dashboard
unit `17 passed`, Playwright e2e `14 passed`, dashboard build OK.

Latest human review outcome truth, runtime proof 2026-06-20 20:28 CEST:
WILQ now has `POST /api/actions/{action_id}/review`, typed
`ActionReviewRequest/ActionReviewResult`, local audit events
`human_review_<outcome>` and `ActionObject.review_gate` fields
`last_review_outcome`, `last_reviewed_by`, `last_reviewed_at`,
`last_review_summary`. Dashboard cards and action detail show `Wynik review
człowieka`; daily context-pack preserves the same state for Codex skills.
Runtime proof on a temporary state DB: event type `human_review_needs_changes`,
ActionObject and `wilq-daily-command` context-pack both carried
`last_review_outcome=needs_changes`, `apply_allowed=false`, with no
`[REDACTED]`. This is local audit/review state only. It does not execute apply,
does not mutate vendors and does not satisfy remaining apply confirmation,
mutation audit or impact-sanity requirements. Full `scripts/verify.sh` after
this slice passed: backend `129 passed`, dashboard unit `17 passed`,
Playwright e2e `14 passed`, dashboard build OK.

Latest ActionObject review gate truth, live proof 2026-06-20 20:04 CEST:
`ActionObject.review_gate` is now a typed API/shared-schema/dashboard/Codex
context-pack contract. It exposes `required_checks`, `operator_checklist`,
`apply_blockers`, `confirmation_required` and `apply_allowed` for review-only
actions. Current live `/api/actions` and `POST /api/codex/context-pack
{"skill":"wilq-daily-command"}` show Merchant, content and Ads ActionObjects
with `status=pending_validation`, `apply_allowed=false`,
`confirmation_required=true` and explicit apply blockers. Redaction preserves
review-gate IDs; no `[REDACTED]` review checklist values should appear in
context-pack output. Scoped skill context-pack action metrics are compacted to
one exemplar row plus `metrics_total`, because detailed Ads facts live in the
typed diagnostics contracts and `wilq-ads-doctor` must stay under the 200 KB
budget. This is a visibility/safety contract only. It does not permit
write/apply mutations and does not satisfy the remaining apply confirmation or
audit-path requirements. Full `scripts/verify.sh` after this slice passed:
backend `127 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
dashboard build OK.

Latest Ads Keyword Planner truth, live proof 2026-06-20 19:30 CEST:
WILQ now has a conservative read-only Keyword Planner adapter using
Google Ads `generateKeywordIdeas`, typed `keyword_planner_read_contract`,
shared frontend schema, dashboard enrichment for custom segments and an Ads
Doctor smoke/eval guard. Current live `vendor_read`
`refresh_google_ads_0477a745f098` completed and collected normal Ads evidence,
but Keyword Planner returned `403 PERMISSION_DENIED` with
`authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`. Treat this as a Google Ads
developer-token approval/readiness blocker, not as missing `.env`, broken
OAuth or missing MCC/child customer setup. Current
`/api/ads/diagnostics.keyword_planner_read_contract.status=blocked`,
`missing_read_contracts=[keyword_planner_enrichment]`, `idea_rows=[]`; custom
segments remain review-only with
`missing_read_contracts=[keyword_planner_enrichment, forecast_or_audience_size]`.
Do not fabricate Keyword Planner ideas, audience size, forecast, targeting
applied, campaign performance, ROAS or conversion uplift. Latest strict eval:
`.local-lab/evals/codex-skill/20260620T173651Z/wilq-ads-doctor/result.json`.

Latest Ads business context truth, live proof 2026-06-20 17:34 CEST:
repo-local `.env` may contain non-secret Ads context such as profit margin,
Polish business goal and Polish budget goal, but `WILQ_ADS_TARGET_ROAS` and
`WILQ_ADS_TARGET_CPA_MICROS` are intentionally empty until a human confirms the
target. Do not preserve guessed CPA/ROAS targets as product truth. With empty
target values and the core non-secret context present, current
`/api/ads/diagnostics.business_context_read_contract` shows `status=ready`,
`missing_read_contracts=[target_roas_or_cpa]`, `target_roas=null`,
`target_cpa_micros=null` and `allowed_metrics=[profit_margin, business_goal,
human_budget_goal]`. The `ads_review_business_context` decision is also ready
with `braki=1`, `ustawione pola=3` and no
`act_configure_ads_business_context`; Command Center therefore keeps a single
ready Ads review card instead of a false business-context blocker. This still
does not unlock target verdicts, budget apply, recommendation apply,
wasted-budget verdicts, profitability verdicts or scaling recommendations;
those require confirmed targets plus the remaining optimizer contracts, human
review and audit paths.

Latest custom-segments context truth, live proof 2026-06-20 17:34 CEST:
`POST /api/codex/context-pack {"skill":"wilq-custom-segments"}` is now
workflow-specific: about 50 KB, `active_action_objects` and
`ads_diagnostics.action_ids` contain only
`act_prepare_custom_segments_from_search_terms`, `decision_queue` contains only
`ads_prepare_custom_segments_from_search_terms`, and `top_opportunities=[]`.
The dedicated `/ads-doctor/custom-segments` route renders the same review-only
contract, including real source terms, payload preview, missing
`keyword_planner_enrichment` and `forecast_or_audience_size`, and blocked
audience/apply/performance claims. Do not re-expand this skill context with
generic Ads decisions or opportunity cards.
Latest custom-segments triage follow-up, 2026-06-20 18:24 CEST:
`/api/ads/diagnostics.custom_segments_read_contract.candidates` now carries
typed `review_priority`, bounded `review_score`, Polish `review_reason` and
`human_review_gates`. Live proof after `scripts/local_stack.sh restart`: one
candidate, `Search terms: Kompendium PPWR`, with `review_priority=pilne`,
`review_score=75`, 6 source terms and blocked claims for audience size, ROAS,
targeting/apply and campaign performance. Decision
`ads_prepare_custom_segments_from_search_terms.metric_tiles` shows
`segmenty=1`, `pilne=1`, `wysokie=0`, `podgląd akcji=1`,
`źródłowe zapytania=6`. Scoped `wilq-custom-segments` context-pack is about
51 KB and keeps only `act_prepare_custom_segments_from_search_terms`,
`ads_prepare_custom_segments_from_search_terms`, the custom segment candidate
and no top opportunities. Strict eval now requires the review fields:
`.local-lab/evals/codex-skill/20260620T162316Z/wilq-custom-segments/result.json`
has `api_used=true`, `language=pl-PL`,
`act_prepare_custom_segments_from_search_terms` validated,
`operator_usefulness_score=5` and notes that audience size, ROAS, targeting
and campaign performance remain blocked. Full `scripts/verify.sh` passed after
this slice: backend `126 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, dashboard production build OK.

Latest Ads recommendation triage follow-up, 2026-06-20 18:48 CEST:
`/api/ads/diagnostics.recommendations_read_contract.recommendation_rows` now
carries typed `review_priority`, bounded `review_score`, Polish
`review_reason` and `human_review_gates`. Live proof after
`scripts/local_stack.sh restart`: 4 recommendation rows, `missing_read_contracts=[]`,
`act_prepare_google_ads_recommendation_review_queue` present, and decision
`ads_review_recommendations.metric_tiles` shows `rekomendacje=4`, `pilne=0`,
`wysokie=2`, `podgląd wpływu=2`, `podgląd akcji=4`. Row priorities:
`DISPLAY_EXPANSION_OPT_IN=normalne/23`,
`DYNAMIC_IMAGE_EXTENSION_OPT_IN=niski sygnał/10`,
`IMPROVE_PERFORMANCE_MAX_AD_STRENGTH=wysokie/57`,
`SEARCH_PARTNERS_OPT_IN=wysokie/53`. `/ads-doctor` renders the same priority,
score, reason and human review gates. Smoke script and strict Codex eval now
require these fields; latest eval artifact:
`.local-lab/evals/codex-skill/20260620T164726Z/wilq-ads-doctor/result.json`
with `api_used=true`, `language=pl-PL`, `operator_usefulness_score=5`. This is
still review-only; recommendation apply, automatic accepts, budget apply,
campaign mutation and performance uplift remain blocked.

Command Center is being held to the Polish marketer cockpit bar: stable API
fields such as `evidence_ids` remain unchanged, but marketer-facing labels must
say `Dowody`, `Przykładowe dowody`, `podgląd akcji`, `odczyt` and similar
Polish terms instead of raw English implementation wording. GA4 on Command
Center must use the same `Ga4DiagnosticsResponse.decision_queue` semantics as
`/ga4`, showing concrete review counts for `grupy ruchu`, `decyzje`, `pomiar`
and `jakość ruchu` while still blocking ROAS/revenue/conversion/tracking-fixed
claims until explicit contracts exist.

GA4 dedicated route and `wilq-ga4-analyst` context-pack must expose decision
metadata directly, not rely on frontend inference. Current live proof after
`scripts/local_stack.sh restart`: `/api/ga4/diagnostics.decision_queue` has
6 decisions with explicit `status`, `priority` and `metric_tiles`; 2 decisions
are `blocked` measurement issues for `(not set)` rows and 4 are `ready`
traffic-quality reviews. Metric tiles include `aktywni`, `sesje`, `zdarzenia`,
`odsłony` and `engagement`, e.g. `(not set)/(not set)` has `aktywni=179`,
`sesje=179`, `engagement=0%`; scoped `wilq-ga4-analyst` context-pack carries
the same fields with no GA4 redaction paths and no null
`status`/`priority`/`metric_tiles`. Full `scripts/verify.sh` passed after this
slice: backend `117 passed`, dashboard unit `14 passed`, Playwright e2e
`9 passed`, security, skill/API smokes and dashboard production build passed.

Ahrefs dedicated route and `wilq-ahrefs-gap-finder` context-pack must expose
authority evidence separately from true gap evidence. Current live proof after
`scripts/local_stack.sh restart`: `/api/ahrefs/diagnostics` has
`live_data_available=true`, `authority_fact_count=2`, `gap_fact_count=0`,
`blocker_count=1`, ready decision `ahrefs_review_authority_context` with
`DR=90`, `Ahrefs Rank=1450`, `fakty luk=0`, and blocked decision
`ahrefs_block_gap_claims_without_records` with missing read contracts:
`ahrefs_competitor_pages`, `ahrefs_content_gap_records`,
`ahrefs_backlink_gap_records`, `ahrefs_organic_keywords_by_url`,
`ahrefs_top_pages_by_competitor`. Scoped
`POST /api/codex/context-pack {"skill":"wilq-ahrefs-gap-finder"}` is
`32244 bytes`, includes `ahrefs_diagnostics`, omits `marketing_brief` and
`content_diagnostics`, and has `active_action_ids=[]`. This prevents the skill
from inheriting content ActionObjects when Ahrefs diagnostics has no actions.
Do not claim competitor/content/backlink gaps from DR/rank alone. Strict
non-interactive eval now enforces this: case `wilq-ahrefs-gap-finder` targets
`/ahrefs`, requires `blocked=true`, no non-null `action_id`, missing gap read
contracts and blocked claim terms. Latest eval artifact:
`.local-lab/evals/codex-skill/20260620T110348Z/wilq-ahrefs-gap-finder/result.json`;
result has `api_used=true`, `blocked=true`, Ahrefs evidence IDs,
`action_id=null` and `operator_usefulness_score=4`. Full `scripts/verify.sh`
passed after the diagnostics slice: backend `123 passed`, dashboard unit
`15 passed`, Playwright e2e `12 passed`, skill/API smokes and dashboard
production build passed.

Ads dedicated route and `wilq-ads-doctor` context-pack must expose decision
metadata directly, not rely on frontend inference. Current live proof after
`scripts/local_stack.sh restart`: `/api/ads/diagnostics.decision_queue` has
11 decisions with explicit `priority` and `metric_tiles`; `null_priority_count`
is `0` and `empty_tiles=[]`. Campaign review shows `kampanie=18`,
`kliknięcia=117`, `wyświetlenia=3075`, `koszt=161`, `konwersje=2`;
recommendations show `rekomendacje=4`, `podgląd wpływu=2`,
`podgląd akcji=4`; search terms show supported evidence-backed tiles
`zapytania=50`, `kliknięcia=7` and `koszt=41.8` when current evidence contains
`cost_micros`. Scoped `wilq-ads-doctor` context-pack carries the same fields
with no Ads redaction paths.

Ads recommendation review must separate missing read contracts from operator
review gates. Current live proof after `scripts/local_stack.sh restart`:
`/api/ads/diagnostics.recommendations_read_contract.missing_read_contracts=[]`
and the same decision in `decision_queue` has `operator_review_gates`:
`human_strategy_review`, `review_recommendation_type`, `review_impact_metrics`,
`review_change_history`, `review_business_goal`, `recommendation_apply_preview`,
`google_ads_rmf_compliance_review`, `human_confirm_before_apply`. Scoped
`wilq-ads-doctor` context-pack preserves these gates without `[REDACTED]`.
This does not unlock apply; it makes the human review gate explicit and
traceable.

Ads search-term and negative keyword review must apply the same rule:
human/operator validation gates are not missing read contracts. Current live
proof after `scripts/local_stack.sh restart` on 2026-06-20 15:52 CEST:
`/api/ads/diagnostics.search_terms_read_contract.missing_read_contracts=[]`
and `operator_review_gates=["negative_keyword_action_validation"]`; decision
`ads_review_search_terms` has the same gate and no missing read contracts.

Ads custom segment review must follow the same separation. Current live proof
after `scripts/local_stack.sh restart` on 2026-06-20 16:15 CEST:
`/api/ads/diagnostics.custom_segments_read_contract.status=ready`,
`missing_read_contracts=["keyword_planner_enrichment",
"forecast_or_audience_size"]` and
`operator_review_gates=["review_source_terms",
"reject_brand_or_low_intent_terms", "human_confirm_before_apply"]`; decision
`ads_prepare_custom_segments_from_search_terms` has the same separation with
`metric_tiles.segmenty=1`, `metric_tiles.źródłowe zapytania=6` and
`action_ids=["act_prepare_custom_segments_from_search_terms"]`. This remains
review-only source-term preparation; it does not unlock audience size,
conversion uplift, ROAS, targeting apply or campaign performance claims.
`search_term_safety_read_contract.missing_read_contracts=[]`,
`keyword_match_context_read_contract.missing_read_contracts=[]`, and the safety
decisions carry `operator_review_gates=["human_intent_review"]`. This still
does not unlock negative keyword apply; it only prevents the dashboard and
skills from mislabeling validation/human review as missing data. Full
`scripts/verify.sh` passed after the earlier safety slice:
backend `119 passed`, dashboard unit `14 passed`, Playwright e2e `11 passed`,
skill/API smokes, security checks and dashboard production build passed.
Latest negative keyword triage follow-up, 2026-06-20 18:03 CEST:
`/api/ads/diagnostics.negative_keywords_read_contract.candidates` now carries
typed `review_priority`, bounded `review_score`, Polish `review_reason` and
`human_review_gates`. Live proof after `scripts/local_stack.sh restart`: 6
candidates, top candidate
`asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a`
has `review_priority=pilne`, `review_score=84`; decision
`ads_review_negative_keyword_safety.metric_tiles` shows `kandydaci=6`,
`pilne=1`, `wysokie=1`, `podgląd akcji=6`, `kontekst słów=12`. The reason text
must keep saying that this is review ordering, not a wasted-budget verdict.
Dashboard `/ads-doctor` renders the same fields. This does not unlock negative
keyword apply, wasted-budget claims, CPA/ROAS verdicts or automatic exclusions.
Full `scripts/verify.sh` passed after this slice: backend `126 passed`,
dashboard unit `17 passed`, Playwright e2e `14 passed`, dashboard production
build OK.

Campaign-builder context-pack must stay workflow-specific. It must not pull
negative keyword or custom-segment ActionObjects unless the selected workflow
explicitly needs them. Current focused proof after the Ads review-gate slice:
`wilq-campaign-builder` context-pack is `191737 bytes` in a fresh API process
and `active_action_objects` contains only `act_prepare_ads_campaign_review_queue`
and `act_prepare_google_ads_recommendation_review_queue`. This keeps the
non-daily skill payload under the 200 KB budget and prevents Codex from mixing
campaign-building with separate negative/custom-segment workflows.

`wilq-ads-doctor` scoped context-pack must stay under the non-daily skill budget
without losing Ads decision state. Current live proof after
`scripts/local_stack.sh restart`: `POST /api/codex/context-pack` for
`wilq-ads-doctor` is `174292 bytes` over the wire, smoke-reported
`context_pack_bytes=183152`, keeps 11 Ads decisions, omits duplicate `sections`
and row payloads inside `decision_queue`, caps budget payload preview rows to 4,
keeps source evidence/action IDs, and preserves the full endpoint pointer:
`/api/ads/diagnostics`.

Demand Gen must stay honest until WILQ has Demand Gen-specific evidence and
ActionObjects. It must not present GA4 tracking review, negative keyword review
or custom segment review as Demand Gen actions. Current live proof after
`scripts/local_stack.sh restart`: dedicated endpoint
`GET /api/demand-gen/diagnostics`, dashboard route `/ads-doctor/demand-gen`
and scoped `wilq-demand-gen-operator` context-pack all expose the same blocked
readiness contract: `active_action_objects=[]`, `ads_diagnostics.action_ids=[]`,
`demand_gen_readiness.status=blocked`, `campaign_rows_evaluated=18`,
`campaign_channel_counts={PERFORMANCE_MAX: 8, SEARCH: 10}` and
`demand_gen_campaign_rows=[]`. `/ads-doctor/demand-gen` must not fall back to
generic registry sections such as `Evidence Registry` or `Connector Refresh Runs`.
`demand_gen_campaign_rows` is now an available read contract when campaign
channel facts exist; it must not be listed as missing in that state.
Remaining missing read contracts are
`demand_gen_asset_group_rows`, `demand_gen_creative_asset_rows`,
`demand_gen_landing_quality_by_campaign`, `demand_gen_migration_constraints`
and `demand_gen_action_object`. These IDs must not be redacted; they are
product contracts, not secrets. The `wilq-demand-gen-operator` smoke script
must fail if adjacent ActionObjects are again exposed as active Demand Gen
actions or if channel-bearing campaign rows are reported as missing. Focused
route proof passed: API contract tests for Demand Gen, dashboard unit route
test, Demand Gen Playwright route smoke, full `dashboard-api.spec.ts` with
`12 passed`, and live skill smoke.

Content on Command Center must use the same
`ContentDiagnosticsResponse.decision_queue` semantics as `/content-planner` and
`wilq-content-strategist`. Do not rebuild content first-screen copy from raw
tactical items. Current live proof after `scripts/local_stack.sh restart`:
`/api/content/diagnostics.decision_queue` has 4 decisions with
`null_status=[]`, `null_priority=[]`, `empty_tiles=[]`. Top decision:
`SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` with `status=ready`,
`priority=15`, `zapytania=7`, `WP=znaleziono`, `wyświetlenia=2902`,
`kliknięcia=123`, `CTR=4.24%`, `pozycja=1.5`. Scoped
`wilq-content-strategist` context-pack preserves those typed fields. Command
Center `daily_content_queue` consumes the same state and shows `query/page=10`,
`WP match=10`, `decyzje=4`, `wyświetlenia=7852`, `kliknięcia=138`, with no
`[REDACTED]` in content decision prose. Evidence IDs and ActionObject IDs must
stay in structured fields, not inside prose where redaction can mask useful
marketer context.

Merchant on Command Center must use the same
`MerchantDiagnosticsResponse.decision_queue` semantics as `/merchant` and
`wilq-merchant-feed-operator`. Do not rebuild Merchant first-screen copy from
raw metric facts. Current live proof after `scripts/local_stack.sh restart`:
`/api/merchant/diagnostics` shows `product_count=10900`, `issue_count=15`,
`issue_clusters=11`, `decision_count=8`; the top decision is
"Merchant: sprawdź brak potencjalnie wymaganego atrybutu / miara ceny
jednostkowej", `issue_count=892`,
`ev_refresh_refresh_google_merchant_center_a3ef2f66703f` and
`act_review_merchant_feed_issues`. Scoped `wilq-merchant-feed-operator`
context-pack carries the same decision with no redaction under
`merchant_diagnostics.decision_queue`. Command Center shows
`produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`, `decyzje=8`,
`blockery=0` and Polish marketer-facing labels. Latest follow-up: every
Merchant decision now exposes typed `priority` and numeric `metric_tiles`, so
`/merchant`, Command Center and `wilq-merchant-feed-operator` can rank the same
issue-level queue without frontend inference. Live proof after restart:
8 Merchant decisions, `null_priority=[]`, `empty_tiles=[]`, top decision
`priority=21`, `metric_tiles.zgłoszenia=892`.

Marketing Brief and Codex context-packs must use the same daily decision state
as Command Center. Do not rebuild `/api/marketing/brief` from stale raw metric
summaries when `CommandCenterResponse.daily_decisions` already contains typed
Merchant, Content, GA4 and Ads decisions. Current live proof after
`scripts/local_stack.sh restart`: `/api/marketing/brief.what_we_know` shows
`Przejrzyj kolejkę problemów Merchant Center`, `Przejrzyj kolejkę SEO z GSC i
WordPress`, `GA4: pomiar i jakość ruchu do kontroli`,
`Przejrzyj kolejki Ads do oceny bez apply` and `Ahrefs: domain_rating = 90`;
`what_blocks_us` contains the GA4 contract blocker; `recommended_focus` mirrors
ready daily decisions; scoped `wilq-daily-command` context-pack has the same
brief and Command Center decision titles with no `marketing_brief` redaction
paths. Stale strings such as `feed/product issues`, `active_products=12`,
`disapproved_products=3`, `active_users=20`, `sessions=30` and
`feed issue queue` must not return to the daily brief. Full `scripts/verify.sh`
passed after this slice: backend `117 passed`, dashboard unit `14 passed`,
Playwright e2e `9 passed`, security, skill/API smokes and dashboard production
build passed.

Latest daily context-pack follow-up, 2026-06-20 14:30 CEST:
`active_action_objects` in scoped `wilq-daily-command` context now inherit
`decision_id`, `decision_status`, `metric_tiles`, evidence IDs, blocked claims
and safe next step from `CommandCenterResponse.daily_decisions`. Redaction
preserves `decision_id`. Live proof after `scripts/local_stack.sh restart`:
Merchant action points to `decision_review_merchant_feed_issues` with
`produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`; GA4 action points to
`decision_review_ga4_landing_quality` with status `blocked`, `grupy ruchu=10`,
`pomiar=2`, `jakość ruchu=4`. Stale strings
`active_products=12`, `disapproved_products=3`, `active_users=20`,
`sessions=30`, `Connector .* ready`, `No performance metrics` and
`Run a read-only refresh` are absent from the live daily context-pack.

Latest Localo routing follow-up, 2026-06-20 14:30 CEST: Localo with real
aggregate facts is now `daily_localo_visibility_facts` and maps to
`plan_review_localo_visibility_facts`. Readiness/access-only Localo remains
`daily_localo_readiness` and must not be promoted as a ready primary operator
item. Current live Localo tiles: `miejsca=4`, `frazy=23`,
`widoczność=52.8261`, `recenzje=793`. `wilq-daily-command` smoke passed after
this change. Full `scripts/verify.sh` passed after this slice: backend
`124 passed`, dashboard unit `15 passed`, Playwright e2e `12 passed`,
dashboard production build OK.
Localo diagnostics and Command Center must select these facts by evidence ID
from the last successful Localo MCP aggregate read, not by a small newest-facts
limit, because later access probes can otherwise hide `localo_tracked_keyword_count`
and regress `frazy` to `0`. Live proof after `scripts/local_stack.sh restart`
on 2026-06-20 16:35 CEST: `/api/localo/diagnostics` uses
`refresh_localo_9e9ff67eadad`, reports `visibility_fact_count=17`,
`metric_tiles.frazy=23`, and Command Center
`decision_review_localo_visibility_facts.metric_tiles.frazy=23` with
`daily_localo_readiness` absent from the primary brief.

Opportunities must be decision-backed, not connector-registry-backed, when
daily decisions exist. `/api/opportunities`, `/opportunities` and full Codex
context-pack `top_opportunities` must show the same marketer decisions as
Command Center: Merchant feed review, Content refresh queue, GA4
measurement/traffic review and Ads review queue. Current live proof after
`scripts/local_stack.sh restart`: `/api/opportunities` returns 4 IDs:
`opp_decision_review_merchant_feed_issues`,
`opp_decision_prepare_content_refresh_queue`,
`opp_decision_review_ga4_landing_quality` and
`opp_decision_review_ads_campaign_metrics`; each carries `metric_tiles`,
evidence IDs, source connectors, ActionObject IDs and a Polish safe next step.
No `opp_connector_*` cards or `opportunities` redaction paths are present in
the live context-pack proof. Connector registry cards may remain as fallback
only when there are no daily decisions. Full `scripts/verify.sh` passed after
this slice: backend `117 passed`, dashboard unit `14 passed`, Playwright e2e
`9 passed`, security, skill/API smokes and dashboard production build passed.

Workflows must be operator contracts, not placeholder automation names. When
daily decisions exist, `/api/workflows` and `/workflows` must show core
workflow cards with `status`, `route`, `skill_id`, `metric_tiles`, source
connectors, evidence IDs, ActionObject IDs, blocked claims and a safe next
step. Planned workflows must explicitly list missing contracts and must not
imply automation or apply support. Current live proof after
`scripts/local_stack.sh restart`: `/api/workflows` returns 15 workflows:
4 `ready`, 4 `blocked`, 7 `planned`. Core workflows include `daily_command`,
`merchant_feed_review`, `gsc_content_doctor`, `ga4_data_analyst` and
`ads_daily_check`; `daily_command` has `decyzje=4`, `blockery=1`, `źródła=6`,
`akcje=7`; `ads_daily_check` has Ads review tiles and four review-only
ActionObjects. Old placeholder strings `Workflow definition runs against WILQ
API` and `Fetch WILQ API context` are absent. Full `scripts/verify.sh` passed
after this slice: backend `118 passed`, dashboard unit `14 passed`,
Playwright e2e `10 passed`, security, skill/API smokes and dashboard
production build passed.

Knowledge must connect source material to marketer decisions, not only list
cards and YAML playbooks. `/api/knowledge/operating-map` and `/knowledge` must
show how canonical knowledge cards, machine-readable playbooks and expert rules
bind to routes, skills, evidence IDs, ActionObject IDs, blocked claims and
missing contracts. Current live proof after `scripts/local_stack.sh restart`:
`/api/knowledge/operating-map` returns 11 bindings, 15 source cards, 14
playbooks and 31 expert rules. Core bindings include `knowledge_daily_command`,
`knowledge_merchant_feed_review`, `knowledge_gsc_content_doctor`,
`knowledge_ads_daily_check`, `knowledge_ga4_data_analyst` and
`knowledge_localo_visibility_review`; Ads binds
`card_google_ads_search_playbook`, `google_ads_search_playbook`,
`ads_search_terms_v1` and four review-only ActionObjects to `/ads-doctor` and
`wilq-ads-doctor`, while Localo stays blocked on `local_ranking_rows`,
`gbp_performance_rows` and `review_rows`.

## Research And Knowledge Contract

WILQ must be built from a source-backed marketing knowledge loop, not from loose
prompt intuition. The canonical source map is:

```txt
docs/research/wilq-marketing-source-map.md
```

Every serious Ads, SEO, Merchant, GA4, Ahrefs, Localo, WordPress or social
slice must follow this path:

1. Pick sources from the source map or add better current sources first.
2. Condense the source into a knowledge card, expert rule, schema contract or
   skill reference.
3. Bind the rule to required WILQ evidence fields and blocked claims.
4. Expose the result through the WILQ API before dashboard or skill polish.
5. Prove with dashboard/browser checks and `codex exec` that Polish prompts
   produce evidence-backed Polish outputs.

Research methods to preserve:

- ReAct-style loop: reason about the marketer task, call WILQ API/tooling, then
  answer from observed evidence.
- Self-RAG-style critique: retrieve only relevant evidence, check whether it is
  sufficient, then block unsupported recommendations.
- RAGAS/RAG-eval-style gates: context relevance, faithfulness to evidence,
  answer usefulness and no hallucinated metrics.
- Official platform docs first for APIs and constraints; practitioner sources
  only after the official contract is understood.
- BDOS-class product bar: diagnostics, safe actions, dry-run/preview/confirm,
  mutation/audit history, expert knowledge and multi-surface operation.

## Current Runtime Truth

Local dashboard:

```bash
http://127.0.0.1:5173/command-center
```

Local API:

```bash
http://127.0.0.1:8000/api/health
```

Current performance truth:

- `WILQ_DAILY_RUNTIME_CACHE_SECONDS` now defaults to `30`, while tests still
  disable runtime cache and connector refresh/action validation/action apply
  paths clear the cache.
- Dashboard TanStack Query now treats WILQ server state as a short operator
  snapshot: `staleTime=30000` and `refetchOnWindowFocus=false` by default.
- Live proof after local stack restart on 2026-06-20:
  `/api/dashboard/command-center` `27856 bytes`, cold `1.777s`, then `0.007s`,
  `0.009s`, `0.010s`, `0.007s` within the operator cache window. Daily Codex
  context-pack was `126449 bytes`, `0.382s`, then `0.237s`, `0.234s`.

Use `uv run ...` for Python/WILQ commands. Do not use global `python`.

Current connector truth:

- Connector summary live check 2026-06-19 14:53 Europe/Warsaw:
  `total=12`, `configured=9`, `missing_credentials=2`, `disabled=1`.
  The disabled connector is `google_sheets`, intentionally outside current
  Ekologus scope. The missing connectors are `linkedin` and `facebook`;
  they block publishing only, not evidence-backed drafting.
- `google_ads`: credentials are configured and live campaign-level
  `vendor_read` works after the 2026-06-18 OAuth + MCC/child-account fix.
  `596-895-8639 Agencja Proud Media` is the MCC/login customer. `Ekologus NOWY`
  is the child metrics customer. Do not call Ads an OAuth blocker unless a fresh
  read proves that. Google Ads now has live campaign rows, search-term rows,
  account currency evidence, a derived KPI read contract for
  CTR/CPC/conversion rate/CPA/ROAS, a
  read-only budget context contract, a read-only recommendations contract, a
  read-only impression-share contract, a read-only change-history contract, a
  read-only 90-day search-term safety contract, a prepare-only custom segment
  candidate contract with review-only payload preview and a prepare-only
  negative keyword safety review contract with review-only payload preview plus
  read-only keyword match context. Recommendations now also have a review-only
  apply payload preview ActionObject. Campaign budgets now also have
  review-only `CampaignBudgetOperation` payload previews exposed through
  `/api/ads/diagnostics`, `/api/actions/act_prepare_ads_campaign_review_queue`
  and dashboard `/ads-doctor`; every preview keeps `api_mutation_ready=false`,
  `apply_allowed=false` and `destructive=false`.
  Command Center now consumes those Ads diagnostics as a marketer decision,
  not as generic connector readiness. Live `/api/dashboard/command-center`
  proof after local stack restart: `daily_ads_status` title
  `Ads: kolejki budżetu, rekomendacji i zapytań`, status `ready`,
  priority `16`, metric tiles `kampanie=18`, `zapytania=50`,
  `podgląd budżetu=18`, `rekomendacje=4`, `wykluczenia=6`, `segmenty=1`,
  and ActionObjects `act_prepare_ads_campaign_review_queue`,
  `act_prepare_google_ads_recommendation_review_queue`,
  `act_prepare_custom_segments_from_search_terms` and
  `act_prepare_negative_keyword_review_queue`. The `wilq-daily-command`
  scoped context-pack carries the same Ads action-plan prompt.
  Command Center keeps API `blocked_claims` stable, but the dashboard now
  translates marketer-facing blocked claims in general decision/tactical/brief
  cards. Do not regress to visible raw labels such as `approval restored`,
  `lead uplift`, `profitability`, `wasted budget` or `search-term waste` on
  first-screen marketer surfaces.
  Latest live Ads proof: `refresh_google_ads_60956db2c42f` /
  `ev_refresh_refresh_google_ads_60956db2c42f` exposes
  `customer_currency_code=PLN`, 18 campaign rows, 50 30-day search-term rows,
  200 90-day search-term safety rows, 211 keyword match context rows, 4 active
  Google Ads recommendation rows, 2 recommendation rows with impact preview,
  4 recommendation apply payload preview rows, 18 campaign budget apply preview
  rows, 2 impression-share rows and
  `change_event_row_count=0` for the last 14 days.
  `/api/ads/diagnostics` reports
  `account_currency_read_contract.status=ready`,
  `account_currency_read_contract.currency_code=PLN`,
  `impression_share_read_contract.status=ready`,
  `change_history_read_contract.status=ready`,
  `recommendations_read_contract.status=ready`,
  `recommendations_read_contract.action_ids=["act_prepare_google_ads_recommendation_review_queue"]`,
  `recommendations_read_contract.missing_read_contracts=[]`,
  `recommendations_read_contract.operator_review_gates` includes
  `human_strategy_review` and `google_ads_rmf_compliance_review`,
  `search_term_safety_read_contract.status=ready`,
  `keyword_match_context_read_contract.status=ready`, decisions
  `ads_review_impression_share`, `ads_review_change_history` and
  `ads_review_search_term_safety`. CPA/ROAS are allowed only as calculations
  from campaign facts; budget context, recommendations, impression share,
  change history, 90-day search-term safety and keyword match context are
  allowed only as review/audit context. Dashboard `/ads-doctor` may format
  cost, CPC, CPA, budget and search-term costs in PLN, but profitability and
  margin verdicts remain blocked. Current `negative_keywords_read_contract`
  has 7 review-only
  candidates, 7 `negative_keyword_payload_preview` rows, no
  `90_day_safety_check` missing contract and no
  `negative_keyword_payload_preview` missing contract and no
  `keyword match context` missing contract. Negative keyword preview rows are
  exact-match review rows with `api_mutation_ready=false`,
  `apply_allowed=false` and `destructive=false`. Recommendation apply preview
  rows use `operation_type=ApplyRecommendationOperation`, but also keep
  `api_mutation_ready=false`, `apply_allowed=false` and `destructive=false`.
  Budget apply preview rows use `operation_type=CampaignBudgetOperation`, but
  also keep `api_mutation_ready=false`, `apply_allowed=false` and
  `destructive=false`.
  WILQ still blocks `negative keyword apply`, `recommendation apply`,
  `search-term waste`, CPA, ROAS and conversion-loss claims until human review,
  confirmation and future apply/audit contracts exist. Budget preview does not
  mean budget apply: WILQ still blocks budget scaling/apply until
  `human_budget_goal`, apply safety and mutation audit exist. Profitability,
  wasted-budget, audience size, campaign-performance, recommendation apply,
  change impact and performance-uplift claims still need explicit
  read/safety/apply contracts. Individual recommendation rows may still show
  `missing_metrics=["recommendation_impact"]` when Google Ads does not return
  impact metrics for that recommendation type; that is not an OAuth/API blocker.
  Full `scripts/verify.sh` passed for the Command Center Ads review-queues
  slice on 2026-06-20: backend API contracts `117 passed`, dashboard route
  tests `14 passed`, Playwright e2e `9 passed`, API smoke, skill structure
  smoke, skill API smoke, security checks and dashboard production build
  passed.
  Source-backed decision lineage now exists for Ads diagnostics: sections and
  decision queue items expose `knowledge_card_ids` and `expert_rule_ids`.
  Current proof chain for the budget slice is
  `google_ads_budget_review_playbook` ->
  `card_google_ads_budget_review_playbook` ->
  `ads_review_budget_context` with expert rules
  `ads_scaling_candidates_v1`, `ads_recommendations_v1` and
  `ads_principles_v1`. Dashboard `/ads-doctor` renders those trace IDs, and
  `wilq-ads-doctor` scoped context-pack preserves them for Codex. Fresh
  non-interactive `wilq-ads-doctor` eval passed for the newest 90-day safety
  slice:
  `.local-lab/evals/codex-skill/20260619T182309Z/wilq-ads-doctor/result.json`.
  Eval result includes `card_google_ads_budget_review_playbook`,
  `ads_scaling_candidates_v1`, `ads_recommendations_v1`,
  `ads_principles_v1`, `keyword_match_context_read_contract`,
  Google Ads evidence IDs and prepare-only
  `act_prepare_ads_campaign_review_queue` /
  `act_prepare_negative_keyword_review_queue` action candidates.
  Full `scripts/verify.sh` passed for this lineage/eval slice on 2026-06-19:
  backend API contracts `111 passed`, dashboard route tests `13 passed`,
  Playwright e2e `9 passed`, API smoke, skill structure smoke, skill API smoke,
  security checks and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk is `530.51 kB`, above the 500 KB warning threshold.
- `google_merchant_center`: live product/feed facts exist and support a review
  queue. Merchant diagnostics now distinguishes report occurrences from unique
  affected products: `/merchant` labels them as `Zgłoszenia`/`kontekst`, not
  `Affected`, and aggregate `product_count`/`issue_count` may fallback to latest
  refresh summary when issue-level metric facts are the only stored facts.
  Latest Merchant regression fix: live issue clusters can disappear when the
  Merchant metric fact read limit is too low, because newer aggregate facts push
  issue-level rows out of the window. The fix raises that limit and makes the
  Merchant skill smoke fail if live diagnostics has issues but no
  `issue_clusters`.
- `google_search_console`: query/page facts exist and support content decisions.
  Tactical/content reads now preserve complete latest metric groups per
  `(connector, evidence, dimensions)`, so query/page cards do not show false
  `impressions=0` when the same evidence group has real impressions. Latest
  GSC/content regression fix: newer aggregate GSC refresh rows can push older
  but still useful query/page facts outside a generic 300-row read window. The
  tactical/content selectors now preserve a larger GSC window for query/page
  evidence, and `wilq-gsc-content-doctor` smoke fails if query/page metric
  facts exist but `content_diagnostics.decision_queue` is empty. Latest content
  follow-up on 2026-06-20 makes `content_diagnostics.decision_queue` carry
  marketer-facing `summary`, `primary_query`, `total_clicks`,
  `total_impressions`, `aggregate_ctr` and `best_average_position`, sorted by
  real GSC demand instead of URL/id.
- `google_analytics_4`: landing/source/campaign facts exist and
  `/api/ga4/diagnostics.decision_queue` now feeds both dashboard `/ga4` and
  `wilq-ga4-analyst`. Current live decisions are traffic-quality review; ROAS,
  revenue, conversion-drop, attribution verdict and tracking-fixed claims stay
  blocked unless conversion/cost/read contracts exist. Command Center must keep
  GA4 as `blocked` while those interpretation contracts are missing, even when
  live GA4 behavior facts exist; `ready` would imply a complete marketer
  decision and causes confusion.
- `wordpress_ekologus` and `wordpress_sklep`: inventory context exists and must
  protect against duplicate content.
- `ahrefs`: aggregate authority/rank facts exist and `/api/ahrefs/diagnostics`
  now exposes them as authority context with a dedicated blocker for missing gap
  records. Deeper competitor/content/backlink workflows still need typed Ahrefs
  gap records before any gap claim is allowed.
- `localo`: MCP Server URL, OAuth Client ID/Organization ID, OAuth Client
  Secret/Create Token and local OAuth access token are configured. On
  2026-06-18, `refresh_localo_af3a75e8659e` completed a live API-triggered
  Localo MCP initialize with `mcp_initialize_status=200`, checked
  `LOCALO_ACCESS_TOKEN` and redacted the token value. No local ranking/GBP
  claim is allowed yet until WILQ API exposes Localo evidence beyond the
  OAuth/initialize probe.
- `linkedin` and `facebook`: publishing is permission-gated. Drafting can be
  prepare-only and evidence-backed; publishing cannot be claimed.
- `google_sheets`: disabled intentionally and not needed for current scope.

Known important local paths are documented in `AGENTS.md`; do not print secret
values.

## Completed Foundation

Do not rebuild these from scratch:

- Private repo, `.gitignore`, AGENTS rules, architecture docs and quality gates.
- WILQ API spine, typed schemas, connector registry, evidence registry,
  opportunities, expert rules, knowledge compiler and ActionObjects.
- Local `.env` credential runtime and redaction rules.
- SQLite local state, DuckDB metric store, Typer CLI and manual job scheduler.
- 12 repo-local WILQ skills under `.agents/skills`.
- Baseline non-interactive Codex eval harness and deterministic skill smokes.
- API-backed dashboard shell using typed frontend boundaries.
- Command Center, Merchant, Content Planner, GA4, Ads Doctor, Localo and Ahrefs route
  surfaces.
- Google Ads OAuth helper and successful live campaign metric read.
- Real-browser Playwright smoke in `scripts/verify.sh`.
- Merchant route/API clarification for feed problems: issue clusters show report
  occurrences and context, while product-level sample IDs/titles remain blocked
  until the Merchant read contract exposes them.
- Merchant route operator cleanup: `/merchant` now shows the feed review task,
  issue clusters, translated blocked claims, ActionObject validation and
  `Dowody i ograniczenia Merchant` instead of duplicate diagnostic sections or
  English technical copy.
- Content Planner route operator cleanup: `/content-planner` now renders
  typed content decisions from `content_diagnostics.decision_queue`, blocks GA4
  tracking gaps as non-content tasks, groups GSC/WordPress decisions per URL
  and avoids false zero metrics when evidence is missing. Latest proof after
  `scripts/local_stack.sh restart`: top decisions are
  `SEO: odśwież lub scal "bdo co to" (1 zapytanie)` z
  `4429 wyświetleń`, `4 kliknięcia`, CTR `0.09%`, oraz
  `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` z
  `2902 wyświetlenia`, `123 kliknięcia`, CTR `4.24%`; scoped
  `wilq-content-strategist` context-pack preserves the same decision fields,
  evidence IDs and `act_prepare_content_refresh_queue`.
- Command Center content bridge: `daily_content_queue`,
  `decision_prepare_content_refresh_queue` and scoped `wilq-daily-command`
  context-pack now consume `ContentDiagnosticsResponse.decision_queue` instead
  of raw tactical item summaries. The visible first-screen content decision is
  `Przejrzyj kolejkę SEO z GSC i WordPress`, with GSC aggregate counts and
  Polish no-claim summary. Action/evidence IDs stay available as structured
  fields.
- GA4 route operator cleanup: `/api/ga4/diagnostics` now exposes a typed
  `decision_queue` with `fix_measurement`, `review_landing_mapping` and
  `review_traffic_quality` decisions. Dashboard `/ga4` renders this as the
  primary marketer view, keeps evidence/action IDs, and no longer shows raw
  English diagnostic section titles such as `GA4: landing/source/campaign
  behavior`, `GA4: tracking/conversion readiness` or `Analytics Safety Gate`.
- Ads Doctor route operator cleanup: `/api/ads/diagnostics` now exposes a typed
  `decision_queue` with campaign review, search-term review, custom segment
  candidate review, budget context review and blocked write path decisions.
  Dashboard `/ads-doctor` renders those decisions first, keeps evidence/action
  traceability, translates status/blocked claims to Polish and no longer shows
  raw `Read contract Ads`, `Search terms read-only`,
  `Campaign activity read contract`, `Evidence`, `configured`, `READY`,
  `payload preview` or stale OAuth blocker copy when live Ads data exists.
- Localo route operator cleanup: `/api/localo/diagnostics` now exposes a typed
  access/readiness contract with missing Localo visibility contracts and blocked
  claims. Dashboard `/localo` renders `Status Localo / MCP access`,
  `Co marketer ma wiedzieć o Localo`, `Dowody i ograniczenia Localo` and a
  Localo/GBP safety gate instead of the generic tactical queue, `Metric facts`,
  `24 Taktyki` counters or stale `Dokończ Localo access` copy when MCP
  initialize already works.
- Ahrefs route operator cleanup: `/api/ahrefs/diagnostics` now exposes typed
  authority-context decisions and a blocker for missing competitor/content/
  backlink gap records. Dashboard `/ahrefs` renders `Status Ahrefs / dowody
  SEO`, `Co marketer ma wiedzieć o Ahrefs`, `Dowody i ograniczenia Ahrefs`
  and does not fall back to the generic registry surface.
- Metric store grouped batch reads for tactical/content surfaces: latest
  query/page groups keep clicks, impressions, CTR and position together instead
  of truncating by connector row count.

## Active Product Problems

These are the current reasons Goal 001 is not complete:

1. **Dashboard route audit must stay enforced, not restarted.**
   Command Center, `/actions`, `/opportunities` and `/merchant` have been
   cleaned up for the current stale Ads/Localo/readiness issues and technical
   wording. `/content-planner` has also been cleaned up around its typed
   content decision queue. `/ga4` has been cleaned up around its typed GA4
   decision queue. `/ads-doctor` has been cleaned up around its typed Ads
   decision queue. `/localo` has been cleaned up around
   `/api/localo/diagnostics`. `/ahrefs` has been cleaned up around
   `/api/ahrefs/diagnostics`. Remaining route work is now regression control:
   every touched route must preserve the decision-first hierarchy, Polish
   operator copy, Codex bridge, evidence IDs and blocked claims. Do not
   reintroduce generic registries, readiness-only cards, stale blocker copy or
   raw metric dumps as first-screen marketer insight.

2. **Command Center and supporting registries must stay separated.**
   Evidence IDs and ActionObjects are required, but the marketer needs a clear
   "what to do now and why" hierarchy. Raw connector/status/readiness cards and
   opportunity/action registries must not masquerade as marketing insight.

   Hard block: first-screen Command Center must not render readiness-only cards
   such as `connector_configured=true`, `Connector ... ready for ... refresh`,
   `No performance metrics have been collected`, or `Run a read-only refresh`.
   Those belong in lower diagnostic/settings surfaces unless converted into a
   real decision, blocker or action.

   Fresh audit correction: canonical `DailyDecision` is the primary Command
   Center model. `operator_brief`, `action_plan`, `marketing_brief`,
   diagnostics, `/api/actions` and `/api/opportunities` are supporting
   surfaces, not competing first-screen decision queues.

3. **Ads Doctor is useful for read-only review, but not yet a full optimizer.**
   Campaign-level activity, search-term facts, custom segment candidates and
   the latest negative keyword safety review queue now have explicit
   read/decision contracts. Budget context is also explicit and read-only:
   WILQ can compare campaign daily budget against 7-day cost, but cannot
   recommend scaling, pausing or applying budget changes. The negative keyword
   queue is prepare-only safety review, not a waste verdict or apply path.
   Recommendations, quality scoring, budget optimization decisions, impression
   share, keyword/match context, full 90-day safety history, Keyword Planner enrichment,
   forecast/audience-size contracts and apply previews still need explicit
   read/safety/ActionObject contracts before WILQ can claim BDOS-class Ads
   optimization value.

4. **Codex skill usefulness is not fully proven end-to-end.**
   Skills have contracts and smokes, and `wilq-daily-command` now has a
   strengthened usefulness guardrail plus a fresh non-interactive eval pass.
   `wilq-content-strategist`, `wilq-ads-doctor` and
   `wilq-custom-segments` also have strict usefulness passes after their
   matching API contracts. `wilq-ga4-analyst` has now been repaired against
   `/api/ga4/diagnostics.decision_queue` and passed a fresh strict
   non-interactive eval on 2026-06-19. `wilq-localo-operator` should consume
   `/api/localo/diagnostics` for access/readiness and must continue blocking
   ranking/GBP/competitor claims until actual Localo visibility facts exist.
   Goal 001 still needs the same strict usefulness pass across the remaining
   high-value skills and a clean plug-and-play Codex session proving Polish
   prompts -> WILQ API calls -> same evidence IDs as dashboard -> useful next
   actions.

5. **Knowledge condensation is not fully proven.**
   Playbooks and knowledge cards exist, but we must prove they influence skill
   outputs and content/Ads decisions instead of sitting beside the product.
   Goal 001 must show at least one source-backed chain:
   source -> knowledge card/rule -> API view model -> dashboard card ->
   non-interactive Codex skill output.

   Current progress moves this in the right direction for content and Ads:
   `content_diagnostics.decision_queue` is typed API state, not skill-reference
   logic. Ads diagnostics now has a first source-backed chain for budget
   review: `google_ads_budget_review_playbook` compiles to
   `card_google_ads_budget_review_playbook`, API decisions expose
   `knowledge_card_ids` and `expert_rule_ids`, `/ads-doctor` renders those
   trace IDs and `wilq-ads-doctor` context-pack preserves them. The remaining
   proof is a non-interactive Codex eval that verifies the skill uses that
   lineage in a Polish marketer answer. The follow-up daily context-pack slice
   also moved metric fact reads into batched/read-only API storage paths instead
   of skill-reference patches.

   This is the explicit home for the "best standards / practitioner sources /
   papers / doctoral-quality sources" layer. It is not a vague memory dump.
   The required shape is: source map -> knowledge card or expert rule ->
   typed WILQ evidence requirements -> blocked claims -> API view model ->
   dashboard + Codex skill proof. Do not close this problem by adding long
   prompt text to skills; close it by proving source-backed rules change
   concrete marketer decisions.

6. **Localo and social remain limited-evidence surfaces.**
   Localo access/readiness has a typed API surface in `/api/localo/diagnostics`.
   It proves MCP initialize/access state and names missing contracts, but local
   ranking/GBP/competitor/review insight remains blocked until a concrete Localo
   visibility read contract exists. Latest Localo follow-up: every
   `LocaloDecisionItem` now exposes typed `priority` and `metric_tiles`.
   Live proof after restart: 2 Localo decisions, `null_priority=[]`,
   `empty_tiles=[]`; access-ready decision shows `dostęp MCP=1`,
   `fakty Localo=0`, `braki kontraktu=5`, while the visibility blocker shows
   `blokady claimów=5`. Fresh `wilq-localo-operator` eval passed on
   2026-06-19 and proves the same semantic state: access is ready, local
   visibility insight is blocked. Social publishing remains permission-gated;
   drafting can be prepare-only and evidence-backed.

7. **Full verification after the latest changes passed.**
   `scripts/verify.sh` passed after the 2026-06-20 Ahrefs diagnostics slice:
   backend API contracts `123 passed`, dashboard route tests `15 passed`,
   Playwright e2e `12 passed`, security, skill/API smokes and dashboard
   production build passed. Keep this file current after every future slice.

8. **Ahrefs is authority-context-ready, not gap-analysis-ready.**
   `/api/ahrefs/diagnostics`, `/ahrefs` and scoped `wilq-ahrefs-gap-finder`
   context-pack now prove DR/rank authority facts and explicitly block
   competitor/content/backlink gap claims. Current live proof: DR=90,
   Ahrefs Rank=1450, `gap_fact_count=0`, `active_action_ids=[]`, and 5 missing
   gap read contracts. Next Ahrefs value work is to implement typed gap records,
   not to make the skill infer gaps from aggregate rank metrics. Strict eval
   coverage now exists for this guardrail:
   `.local-lab/evals/codex-skill/20260620T110348Z/wilq-ahrefs-gap-finder/result.json`.

## What WILQ Must Give The Marketer

For every meaningful screen or skill response, WILQ should answer:

- **Co widzę?** Real facts, source connector, freshness and evidence IDs.
- **Co to znaczy?** Diagnosis in Polish, with blocked claims named explicitly.
- **Co zrobić teraz?** One or more safe next actions, preferably ActionObjects.
- **Czego nie wolno twierdzić?** Missing evidence, unsupported metrics, blocked
  writes or permission gaps.
- **Jak sprawdzić?** Link/ID to evidence, action validation or dashboard route.

Examples of real value:

- Merchant: "10900 produktów, 15 typów problemów i 1887 zgłoszeń problemów
  feedu wymagają review; validate `act_review_merchant_feed_issues`; do not
  promise approval recovery."
- Content: "GSC + inventory WordPress suggests refresh/create/block decisions;
  do not promise ranking or lead uplift."
- GA4: "Landing/source/campaign traffic quality looks weak; review tracking and
  message match; do not claim ROAS/revenue."
- Ads: "Campaign and search-term metric facts exist, including conversion
  counts/value; review live activity and prepare safety review candidates, but
  keep profitability, wasted budget, budget scaling, negative keyword apply and
  recommendation/apply claims blocked until currency, margin, pacing,
  match-context, safety and ActionObject apply contracts exist."
- Localo: "MCP access działa (`mcp_initialize_status=200`), ale lokalna
  widoczność nie może być analizowana, dopóki WILQ API nie zbierze konkretnych
  Localo ranking/GBP/competitor facts poza initialize probe."

If a dashboard section only says "connector configured" without converting that
into a decision or blocker, it is not yet useful to the marketer.

## Plug-And-Play Acceptance Gate

Before Goal 001 can be closed, run a clean session that proves WILQ is useful
out of the box:

1. Start WILQ API and dashboard.
2. Open a fresh Codex session with repo skills available.
3. Use Polish marketer prompts:
   - `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
   - `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
   - `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
   - `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
   - `Czy Localo daje już ranking/GBP insight czy nadal blocker?`
4. For each prompt compare:
   - plain Codex without WILQ skill/API context,
   - Codex using the matching WILQ skill,
   - dashboard/API view for the same evidence.
5. Pass only if the skill response:
   - is in Polish,
   - calls WILQ API or honestly reports a blocker,
   - includes source connectors and evidence IDs,
   - does not invent metrics,
   - gives a next safe action,
   - matches dashboard/API evidence for the same claim.

This gate answers the real question: can Codex + WILQ API + WILQ skills do more
for the marketer than plain Codex/manual panel work?

## MCP Decision

Do not build a WILQ MCP server just because MCP exists.

Current position:

- WILQ REST API is canonical.
- Repo skills call REST/context-pack.
- MCP servers are adapters, not the product brain.
- Localo exposes external MCP/OAuth and remains an adapter source.

A WILQ MCP server is justified only if plug-and-play testing proves that Codex
tool ergonomics or reliability are materially worse through REST/skills than
through a thin MCP surface. If built, it must wrap WILQ API and must not bypass
evidence IDs, ActionObject validation, audit logging or redaction.

## Active Queue

This is the current executable goal. Work through it in order and update this
section whenever a step is completed, blocked or replaced by a better-proven
next step.

### Audit-Derived Goal Stack

Source of truth for this stack:

```txt
docs/audits/001-output.md
```

The audit confirms the architecture direction is right: FastAPI/WILQ API is the
brain, typed schemas and evidence IDs are the product contract, and dashboard
plus Codex skills must consume the same API state. The audit also confirms the
current weakness: WILQ still sometimes presents system readiness as marketer
insight and several skills pass because they block safely, not because they
produce high-value decisions.

Work in this order:

1. **Done: content decision queue and Content Planner route cleanup.**
   `content_diagnostics.decision_queue` must remain typed API state, not skill
   reference logic. It must support `refresh_or_merge`,
   `merge_create_after_inventory_check`, `inventory_check_before_create` and
   `block_as_tracking_not_content`, with evidence IDs, source connectors,
   ActionObject IDs and blocked claims. This was committed as
   `2e0b0dc feat(content): expose content decision queue`.
   Follow-up route cleanup on 2026-06-19 made `/content-planner` render this
   decision queue as the primary marketer view, grouped duplicated GSC queries
   per URL, blocked GA4 tracking gaps as non-content work and removed stale
   labels such as `Query/page`, `WP match`, `exact_url`, `payload preview` and
   false `impressions=0` / `ctr=0` for missing evidence. Follow-up on
   2026-06-20 added human-readable content decision summaries and GSC aggregates
   to the typed API/shared schema/dashboard/context-pack contract. Later the
   same day, Command Center and `wilq-daily-command` were bridged to this
   content diagnostics contract, so the first-screen Content card no longer
   uses the old raw `query/page + WP match` prose as the main insight. Full
   `scripts/verify.sh` passed for this bridge slice on 2026-06-20: backend
   `117 passed`, dashboard unit `14 passed`, Playwright e2e `9 passed`,
   security, skill/API smokes and dashboard production build passed.

2. **Active local slice: Command Center as canonical `DailyDecision`.**
   Introduce one first-screen decision model instead of competing
   `operator_brief`, `action_plan`, `marketing_brief`, diagnostics and action
   fragments. A `DailyDecision` must include:
   `co_widzimy`, `dlaczego_to_ma_znaczenie`, `bezpieczny_next_step`,
   `blocked_claims`, `evidence_ids`, `source_connectors`, `action_ids`,
   `skill_id`, `codex_prompt` and `route`.

   Current local status: `DailyDecision` schema and
   `/api/dashboard/command-center.daily_decisions` are implemented. Dashboard
   Command Center now renders one `Dzisiejsze decyzje marketera` board instead
   of duplicating the same intent as `Dzisiejszy panel operatora` plus
   `Plan działań marketera`. Full connector blocker cards were removed from
   `/command-center`; a compact `Źródła i ograniczenia` footer links to
   `/settings` for diagnostic credential/status details. `wilq-daily-command`
   smoke validates the field and its context-pack trace. Focused API/shared
   schema/dashboard checks and Playwright Command Center/demo proof pass after
   this cleanup. Full `scripts/verify.sh` passed on 2026-06-18 for the current
   checkout: backend API contracts 97 passed, dashboard route tests 12 passed,
   Playwright e2e 8 passed and dashboard production build passed.

   Follow-up completed on 2026-06-19: `/actions` starts from
   `ActionObjecty do przeglądu` and related evidence instead of generic
   registry dumps. `/api/actions` no longer resurrects
   `act_configure_google_ads_env` after a later Ads `status_probe` when a live
   Ads `vendor_read` exists. Browser proof with `agent-browser` found no stale
   Ads OAuth action and no generic registry dump on `/actions`. Focused
   Playwright e2e passed: `9 passed`.

   Follow-up completed on 2026-06-20: `/api/opportunities`, `/opportunities`
   and full Codex context-pack `top_opportunities` now consume daily marketer
   decisions instead of old connector-registry cards. Live proof after
   `scripts/local_stack.sh restart`: 4 decision-backed cards, all with
   `opp_decision_*` IDs, `metric_tiles`, evidence IDs, source connectors,
   ActionObject IDs and Polish next steps. The live proof contains no
   `opp_connector_*` opportunities and no redaction paths under
   `opportunities`. Full `scripts/verify.sh` passed after this slice.

   Follow-up completed on 2026-06-20: `/api/workflows` and `/workflows` now
   expose workflow contracts derived from daily decisions instead of 15 generic
   placeholders. Core workflows carry route, skill, metric tiles, source
   connectors, evidence IDs and ActionObject IDs; planned workflows show
   missing contracts such as `pre_post_change_impact`,
   `creative_asset_readiness`, `local_ranking_rows` and
   `social_publish_permission`. Full `scripts/verify.sh` passed after this
   slice with backend `118 passed`, dashboard unit `14 passed` and Playwright
   e2e `10 passed`.

   Follow-up completed on 2026-06-19: `/ga4` now consumes a typed
   `Ga4DecisionItem` queue from `/api/ga4/diagnostics.decision_queue` and shows
   marketer-facing decisions instead of raw `landing/source/campaign behavior`
   diagnostic sections. Browser proof found no stale phrases:
   `payload preview`, `read-only`, `Evidence`, `READY`, `configured`,
   `WP match`, `WP missing`, `landing/source/campaign`,
   `Analytics Safety Gate`, `Tracking readiness`, `conversion-like`,
   `tracking-gap checklist` or `metric_facts`. Full `scripts/verify.sh` passed
   after this slice with backend API contracts `98 passed`, dashboard route
   tests `13 passed`, Playwright e2e `9 passed` and dashboard production build
   passed.

   Follow-up completed on 2026-06-19: `/localo` now consumes
   `/api/localo/diagnostics` instead of the generic workflow/tactical surface.
   The route shows MCP access/readiness, missing visibility contracts and
   blocked Localo/GBP claims. It does not show `Local Visibility Focus`,
   `Taktyki z WILQ API`, `Metric facts`, `24 Taktyki` or stale
   `Dokończ Localo access` copy when access is already proven. Focused backend
   contract tests and dashboard route tests pass for this slice. Full
   `scripts/verify.sh` passed after this slice with backend API contracts
   `100 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
   and dashboard production build passed.

   Follow-up completed on 2026-06-20: Command Center Ads now consumes the same
   Ads diagnostics as `/ads-doctor` and exposes concrete review queues instead
   of generic `live metric facts` prose. `daily_ads_status` and
   `plan_review_ads_campaign_metrics` show budget, recommendation, search-term,
   negative keyword and custom segment review context with ActionObject IDs,
   blocked claims and a Polish Codex prompt. Live proof after
   `scripts/local_stack.sh restart`: `kampanie=18`, `zapytania=50`,
   `podgląd budżetu=18`, `rekomendacje=4`, `wykluczenia=6`, `segmenty=1`.
   Focused ruff, mypy and command-center API contract tests pass for this
   slice. Full `scripts/verify.sh` passed with backend API contracts
   `117 passed`, dashboard route tests `14 passed`, Playwright e2e `9 passed`,
   API smoke, skill structure smoke, skill API smoke, security checks and
   dashboard production build.

   Follow-up completed on 2026-06-20: Command Center marketer-facing blocked
   claims are now translated at the dashboard boundary. The API still exposes
   stable raw `blocked_claims`, but daily decisions, tactical cards and
   brief/action cards render Polish labels such as `ponowne zatwierdzenie
   produktu`, `wzrost leadów`, `opłacalność` and `zmarnowany budżet`. The Ads
   Codex prompt in `/api/dashboard/command-center` and scoped
   `/api/codex/context-pack` now blocks `opłacalność`, `zmarnowany budżet` and
   `wdrożenie zmian` in Polish instead of visible raw `profitability` /
   `wasted budget`. Focused backend/frontend checks and real-browser Command
   Center smoke passed for this slice.

   Follow-up completed on 2026-06-20: Ads search-term safety, keyword match
   context and negative keyword review now separate data availability from
   human intent review. `human_intent_review` moved out of
   `missing_read_contracts` and into `operator_review_gates` when the 90-day
   safety rows and keyword match context are present. Live proof after
   `scripts/local_stack.sh restart`: search-term safety and keyword context
   both have empty missing read contracts plus
   `operator_review_gates=["human_intent_review"]`; decisions
   `ads_review_search_term_safety` and `ads_review_negative_keyword_safety`
   carry the same gate. Full `scripts/verify.sh` passed with backend
   `119 passed`, dashboard unit `14 passed`, Playwright e2e `11 passed`,
   skill/API smokes, security checks and dashboard production build.

3. **Slice 2: performance budget and scoped runtime.**
   Command Center summary target: under 1s local and about 80-120 KB when
   feasible. Non-daily skill context-pack target: under 2s and under 200 KB.
   Full context-pack is a debug mode, not default runtime. Measure before and
   after; do not hide performance issues with random frontend memoization.

   Current status after the 2026-06-19 non-daily context-pack follow-up:
   all default skill context-packs are now below 200 KB. Full diagnostic detail
   remains in `full_context=true` and dedicated API endpoints. Live proof after
   `scripts/local_stack.sh restart`:
   - `wilq-campaign-builder`: `90711 bytes`, cold `1.867s`, warm `0.158s`,
     sources `google_ads`, `google_analytics_4`, `google_search_console`.
     It now uses `ads_diagnostics` plus lightweight `content_landing_context`
     instead of full `content_diagnostics`, and it no longer pulls Merchant,
     negative keyword or custom-segment ActionObjects by default. Latest fresh
     API-process proof after Ads review-gate scope cleanup: `191737 bytes`,
     active actions only `act_prepare_ads_campaign_review_queue` and
     `act_prepare_google_ads_recommendation_review_queue`.
   - `wilq-demand-gen-operator`: `100349 bytes`, cold `2.574s`, warm `0.156s`,
     sources `google_ads`, `google_analytics_4`; Ads and GA4 diagnostics build
     in parallel and Merchant stays omitted until a concrete Demand Gen/Merchant
     read contract exists. Latest fresh API-process proof after Demand Gen
     campaign-channel follow-up: `active_action_objects=[]`,
     `ads_diagnostics.action_ids=[]`, `demand_gen_readiness.status=blocked`,
     `campaign_rows_evaluated=18`,
     `campaign_channel_counts={PERFORMANCE_MAX: 8, SEARCH: 10}`,
     `demand_gen_campaign_rows=[]`; campaign rows are available, while asset,
     creative, landing-quality, migration and ActionObject contracts remain
     missing.
   - `wilq-content-strategist`: `91731 bytes`, cold `2.044s`, warm `0.166s`.
   - `wilq-ga4-analyst`: `28578 bytes`, cold `1.927s`, warm `0.147s`.
   - `wilq-merchant-feed-operator`: `24007 bytes`, cold `1.819s`, warm
     `0.153s`.
   - `wilq-ads-doctor`: `185126 bytes`, cold `1.392s`, warm `0.156s`.
     Latest live follow-up after Ads context-pack compaction:
     `174292 bytes` over the wire, smoke-reported `context_pack_bytes=183152`,
     duplicate `sections` and decision row payloads omitted, full Ads endpoint
     pointer preserved.
   - `wilq-custom-segments`: `187121 bytes`, cold `1.408s`, warm `0.194s`.
   - `wilq-daily-command`: `120504 bytes`, cold `1.918s`, warm `0.236s`.
   Focused ruff, mypy, context-pack API tests and live smoke scripts for
   `wilq-campaign-builder` and `wilq-demand-gen-operator` passed. Full
   `scripts/verify.sh` also passed after this slice: API smoke, skill smokes,
   dashboard route tests, Playwright e2e `9 passed` and dashboard production
   build. Slice 2 remains open only for deeper cold-path improvement,
   especially Demand Gen cold latency around `2.6s`, and future route-level
   lazy loading if browser proof shows it is still needed.

4. **Slice 3: Merchant issue-level triage.**
   Convert Merchant from `products/issues` summary into issue clusters by
   `issue_type`, `affected_attribute`, `country`, `reporting_context`, impact,
   sample products if available, evidence IDs and
   `act_review_merchant_feed_issues`. This is the strongest current demo win.

   Current status: typed `MerchantIssueCluster` exists in Python and
   shared frontend schemas. `/api/merchant/diagnostics` now returns
   `issue_clusters`, `act_review_merchant_feed_issues` carries the same cluster
   payload, and dashboard `/merchant` renders clusters as the primary review
   queue. Full `scripts/verify.sh` passed for this slice on 2026-06-18. The
   current Merchant API read contract still does not return sample product IDs
   or product titles; the UI must state that limit honestly.

   Latest Merchant follow-up after overnight context handoff: latest live check found a
   regression where `issue_count=15` but `issue_clusters=[]` because
   `MERCHANT_METRIC_FACT_LIMIT=240` was too low for the current DuckDB history.
   The fix raises the limit to `2000` and strengthens
   `wilq-merchant-feed-operator` smoke to fail on live issue data without
   clusters. Proof so far: `/api/merchant/diagnostics` on `:8015` returns
   `issue_cluster_count=11`; the Merchant smoke passes; non-interactive
   `wilq-merchant-feed-operator` eval passed at
   `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`
   with `operator_usefulness_score=5`, `act_review_merchant_feed_issues` and
   blocked feed/product mutation claims. Focused ruff/mypy/API tests passed.
   Full `scripts/verify.sh` passed after updating the stale Merchant demo e2e
   assertion: backend API contracts `102 passed`, dashboard route tests
   `13 passed`, Playwright e2e `9 passed`, skill API smoke passed and dashboard
   production build passed.

5. **Slice 4: Content/GSC/GA4/WordPress URL normalizer.**
   Normalize host, path, slash, sitemap, post/page type and GA4 landing path to
   full WordPress URL. The goal is reliable `refresh/merge/create/block`
   decisions and no duplicate content suggestions. GA4 `(not set)` remains a
   tracking issue, not a content task.

   Current local status: tactical queue now reads enough WordPress inventory
   rows from DuckDB to avoid false `missing` caused by large sitemap inventories.
   GSC full URLs and GA4 landing paths expose normalized path keys, match
   confidence and matched WordPress URL in typed API fields. Direct checkout
   proof shows BDO, Zielony Ład and remediacja GSC URLs as `found exact_url`,
   and GA4 landing paths as `found path_fallback`. Full `scripts/verify.sh`
   passed for this slice on 2026-06-18.

   Latest follow-up on 2026-06-19: content/tactical GSC selection now preserves
   older dimensioned query/page evidence even when newer aggregate GSC refreshes
   exist. Live proof on `:8016` after the fix:
   `query_page_count=10`, `matched_inventory_count=10`, `decision_count=4`
   with decisions for homepage, BDO, Zielony Ład and remediacja. Regression test
   `test_content_diagnostics_preserves_gsc_query_page_after_newer_aggregate_runs`
   seeds newer aggregate GSC runs and fails if the older query/page group is
   lost again.

6. **Slice 5: Ads Doctor read contracts.**
   Keep Ads as live campaign-level review until WILQ has explicit read
   contracts for search terms, conversions, campaign budget/spend/clicks,
   recommendations, change history, safety checks and blocked-claim matrix. Do
   not call it a money-leak optimizer until those facts exist.

   Current local status: `/api/ads/diagnostics.campaign_read_contract` is typed
   and live. It groups Google Ads metric facts into campaign rows with
   `campaign_id`, `campaign_name`, `clicks`, `impressions`, `cost_micros`,
   `conversions`, `conversion_value`, evidence IDs and blocked claims.

   Current local status: `/api/ads/diagnostics.search_terms_read_contract` is
   now typed too. Google Ads `vendor_read` queries `search_term_view` in read
   mode and stores `search_term_clicks`, `search_term_impressions`,
   `search_term_cost_micros`, `search_term_conversions` and
   `search_term_conversion_value` metric facts with campaign/ad group/search
   term dimensions. Live read `refresh_google_ads_c2f62ee2b43a` completed on
   2026-06-18 with 18 campaign rows, 50 search term rows, campaign
   `conversions=2.0`, campaign `conversion_value=2.0`, search-term
   `search_term_conversions=0.0` and
   `search_term_conversion_value=0.0`. This unlocks honest campaign/search-term
   review with conversion context, not automatic waste or negative keyword
   claims.

   Current local status: `/api/ads/diagnostics.decision_queue` is typed and
   dashboard `/ads-doctor` renders it as the primary marketer view:
   `ads_review_campaign_activity`, `ads_review_search_terms`,
   `ads_prepare_custom_segments_from_search_terms` and
   `ads_block_write_actions_without_actionobject`. Browser proof on 2026-06-19
   found no stale visible `Read contract Ads`, `Search terms read-only`,
   `Campaign activity read contract`, `Search terms read contract`,
   `Google Ads: campaign activity rows`, `Google Ads: search terms read-only rows`,
   `Evidence`, `configured`, `READY`, `payload preview`, `write/apply` or
   `WILQ ma read-only Google Ads evidence`.

   Current local status: `/api/ads/diagnostics.custom_segments_read_contract`
   is typed and ready when Google Ads search-term evidence exists. It exposes
   1 prepare-only candidate for campaign `Kompendium PPWR`, real
   `source_terms`, review-only `custom_segment_payload_preview`, evidence
   `ev_refresh_refresh_google_ads_eb8c239bc32b`, missing contracts
   `keyword_planner_enrichment` and `forecast_or_audience_size`, and
   ActionObject `act_prepare_custom_segments_from_search_terms`. The preview
   uses `member_type=KEYWORD`, `api_mutation_ready=false`,
   `apply_allowed=false` and `destructive=false`. Dashboard `/ads-doctor`
   renders these candidates; the skill `wilq-custom-segments` consumes the
   same contract.

   Fresh correction: Ads diagnostics now selects the latest Google Ads
   `vendor_read` as the evidence-bearing refresh. A later `status_probe` cannot
   downgrade live Ads state into stale OAuth blocker language. While live Ads
   data is available, `/api/marketing/brief`,
   `/api/ads/diagnostics.action_ids` and the scoped `wilq-ads-doctor`
   context-pack no longer promote `act_configure_google_ads_env`.

   Fresh skill proof: `wilq-ads-doctor` passed non-interactive Codex eval at
   `.local-lab/evals/codex-skill/20260618T191243Z/wilq-ads-doctor/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_connector_google_ads_status` and
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`, shows 18 campaign read-only
   rows and 50 search-term rows, and blocks CPA/ROAS profitability verdicts,
   search-term waste, wasted budget and negative keywords until missing
   interpretation/read/safety/ActionObject contracts exist.

   Fresh negative keyword safety proof: `wilq-ads-doctor` passed a new
   non-interactive Codex eval after `negative_keywords_read_contract` and
   `act_prepare_negative_keyword_review_queue` were added:
   `.local-lab/evals/codex-skill/20260619T065511Z/wilq-ads-doctor/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_connector_google_ads_status` and
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`, returns
   `negative_keywords_read_contract.status=ready`, `candidate_count=7`, one
   prepare-only ActionObject and blocked apply/waste/CPA/ROAS claims.

   Fresh manual usefulness proof: a 2026-06-19 `wilq-ads-doctor` run over live
   Ads evidence produced a useful Polish triage: 18 campaigns, 50 search-term
   rows, top campaign/search-term observations, and valid prepare-only
   ActionObjects `act_prepare_negative_keyword_review_queue` plus
   `act_prepare_custom_segments_from_search_terms`. This is recorded in
   `docs/evals/skill-eval-ledger.md`. It still blocks profitability, wasted
   budget, negative keyword apply, budget scaling and recommendation/apply
   claims until match context, full 90-day safety, payload preview, currency or
   margin interpretation, recommendations, change history and
   impression share exist.
   action candidate `act_prepare_negative_keyword_review_queue`, usefulness
   score 5 and no safety findings. It blocks `negative keyword apply`,
   search-term waste, wasted budget, CPA and ROAS without
   `90_day_safety_check`, payload preview and validated ActionObject.

   Fresh skill proof: `wilq-custom-segments` passed non-interactive Codex eval
   at
   `.local-lab/evals/codex-skill/20260619T035937Z/wilq-custom-segments/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`,
   `ev_connector_google_ads_status` and
   `ev_connector_google_search_console_status`, returns 1 recommendation and
   1 action candidate, validates
   `act_prepare_custom_segments_from_search_terms`, and blocks `audience size`,
   `ROAS`, `conversion uplift`, `targeting applied` and
   `campaign performance`.

   Latest follow-up: `/api/ads/diagnostics.negative_keywords_read_contract`,
   `keyword_match_context_read_contract` and
   `act_prepare_negative_keyword_review_queue` are implemented. The contract
   builds review-only candidates from `search_term_*` facts with activity and
   zero conversions/value in current evidence, attaches existing keyword/match
   type context from `ad_group_criterion`, and requires
   `apply_allowed=false`, `destructive=false`, evidence IDs, 90-day safety,
   payload preview and human intent review. It blocks `negative keyword apply`,
   `search-term waste`, `conversion loss`, CPA and ROAS.

   Latest local Ads budget context slice: Google Ads `campaign_budget` fields
   are stored as metric facts, `/api/ads/diagnostics` exposes
   `budget_pacing_read_contract.status=ready`, and `/ads-doctor` renders
   `Koszt 7 dni`, `7-dniowy budżet`, spend ratio and Google recommended-budget
   signal as read-only review context. This does not unlock budget scaling,
   campaign pause, wasted-budget or recommendation/apply claims.
   Full `scripts/verify.sh` passed for this slice on 2026-06-19: backend API
   contracts `108 passed`, dashboard route tests `13 passed`, Playwright e2e
   `9 passed`, API smoke, skill structure smoke, skill API smoke and dashboard
   production build passed. Known non-blocking warning: Vite main JS chunk
   `530.14 kB` exceeds the 500 KB warning threshold.

   Still missing for BDOS-class Ads value: change history,
   keyword/match context, full 90-day safety history, Keyword
   Planner enrichment, forecast/audience-size contract, custom segment payload
   preview, margin/currency interpretation, budget apply safety/confirmation
   and all Ads apply/audit paths. Full `scripts/verify.sh` passed after the custom
   segments slice on 2026-06-19: backend API contracts `100 passed`, dashboard
   route tests `13 passed`, Playwright e2e `9 passed` and dashboard production
   build passed. For the negative keyword safety slice, focused
   ruff/mypy/backend tests/dashboard tests/shared-schema typecheck passed, and
   full `scripts/verify.sh` passed with backend API contracts `102 passed`,
   dashboard route tests `13 passed`, Playwright e2e `9 passed`, skill API
   smoke passed and dashboard production build passed.

7. **Later P2/P3 data contracts.**
   Localo has access/readiness diagnostics, but still needs rankings, GBP
   visibility, competitors, reviews and local tasks before local SEO claims.
   Ahrefs needs competitor pages/backlink/content-gap records before gap claims.
   Custom Segments have real source terms, a prepare-only ActionObject and a
   review-only payload preview, but still need Keyword Planner enrichment,
   forecast/audience-size and targeting/apply contracts before any apply path.
   Campaign Builder needs campaign
   ActionObjects and payload preview contracts. Demand Gen needs
   creative/asset/landing-quality diagnostics. Social publishing stays explicit
   workflow only.

8. **Skill repair track: thin workflows after API contracts.**
   Skill repair is not done. It is also not the last cosmetic step. It runs
   immediately after the API/view-model contract for a workflow exists. The
   order is:
   - `wilq-daily-command` after canonical `DailyDecision`;
   - `wilq-merchant-feed-operator` after Merchant issue-level triage;
   - `wilq-content-strategist` and `wilq-gsc-content-doctor` after
     `content_diagnostics.decision_queue` and URL normalization. Fresh
     `wilq-gsc-content-doctor` eval passed on 2026-06-19 after the GSC
     query/page preservation fix:
     `.local-lab/evals/codex-skill/20260619T083631Z/wilq-gsc-content-doctor/result.json`;
   - done for `wilq-ga4-analyst` after GA4 decision queue repair; keep rerunning
     when conversion/cost/read contracts, tracking validation or richer
     landing/source/campaign classifiers are added;
   - done for `wilq-ads-doctor` after campaign table,
     search terms/conversions, budget context, recommendations, impression
     share and blocked-claim matrix; keep rerunning when change history, budget
     apply previews or negative keyword apply contracts are added. Fresh eval
     after impression-share context passed on 2026-06-19;
   - `wilq-localo-operator` after `/api/localo/diagnostics` for
     access/readiness and again after real ranking/GBP/competitor/review facts
     exist. Fresh access-ready blocker eval passed on 2026-06-19:
     `.local-lab/evals/codex-skill/20260619T072709Z/wilq-localo-operator/result.json`;
   - done for `wilq-custom-segments` after
     `ads_diagnostics.custom_segments_read_contract`,
     review-only `custom_segment_payload_preview` and
     `act_prepare_custom_segments_from_search_terms`; keep rerunning when
     Keyword Planner enrichment, forecast/audience-size or targeting/apply
     contracts are added;
   - done for `wilq-ahrefs-gap-finder` as an authority-only blocker workflow
     after `/api/ahrefs/diagnostics` and scoped context-pack were added. Fresh
     strict eval passed on 2026-06-20:
     `.local-lab/evals/codex-skill/20260620T110348Z/wilq-ahrefs-gap-finder/result.json`.
     Rerun after typed competitor/content/backlink gap records exist;
   - `wilq-campaign-builder`, `wilq-demand-gen-operator` and
     `wilq-social-publisher` only after their required read contracts or
     ActionObjects exist.

   Repair means:
   - `SKILL.md` has clean trigger intent, allowed endpoints, evidence
     requirements, blocked claims and output contract;
   - references contain durable domain guidance only, not product bug fixes,
     dedupe rules or dashboard cleanup patches;
   - deterministic smoke validates the API contract;
   - `scripts/codex_skill_eval.sh --skill <skill>` proves Polish output,
     WILQ API usage, evidence IDs, source connectors, ActionObject safety and
     a useful marketer decision for that workflow.

Stop doing, per audit:

- Do not treat `configured`, `ready for refresh`, or `connector_configured=true`
  as marketer insight.
- Do not promote LinkedIn/Facebook/social draft actions in daily flow unless
  the operator explicitly asks for social.
- Do not develop skills ahead of read contracts. Better prompts cannot replace
  missing API evidence.
- Do not load the full context-pack as default skill runtime.
- Do not put product decision repairs, dedupe rules or edge-case classifiers in
  skill references. Move them to typed API/schema/view-model contracts first.
- Do not call Ads Doctor a CPA/ROAS/search-term/wasted-budget optimizer until
  those read contracts exist.

Demo acceptance from the audit:

- First screen shows 3-5 marketer decisions, not system status.
- Every decision has evidence IDs, source connectors, blocked claims, route,
  ActionObject where applicable and a Polish Codex prompt for the matching
  skill.
- Dashboard and the matching skill return the same evidence/action IDs for the
  same marketer question.
- Skills are evaluated for usefulness, not only schema pass:
  Daily, Merchant, GA4, Content/GSC and Ads must each prove a concrete,
  evidence-backed Polish operator answer.

### 0. Preflight Truth

Goal: start from current runtime truth, not chat memory.

Tasks:

- Read `AGENTS.md`, this file, `docs/infra/001.md`,
  `docs/architecture/bdos-class-wilq-operating-system.md`,
  `docs/research/wilq-marketing-source-map.md` and
  `docs/goals/002-system-audit-and-usefulness-goal.md`.
- Check `git status --branch --short`.
- Use the canonical local runtime manager, not hand-rolled detached processes:
  - `scripts/local_stack.sh status`
  - `scripts/local_stack.sh start` if either service is not ready
  - `scripts/local_stack.sh restart` only when a managed WILQ process or stale
    port owner needs to be replaced
- Check API and dashboard routes:
  - `http://127.0.0.1:8000/api/health`
  - `http://127.0.0.1:5173/command-center`
- Measure command-center API latency and payload size.

Pass criteria:

- current blockers are written here,
- no old Ads OAuth blocker is treated as current unless fresh API evidence says
  so,
- no credential value or secret path content is printed.

### 1. Command Center Anti-Slop Cleanup

Goal: first-screen Command Center must be useful to a Polish marketer.

Active slice handoff:

```txt
docs/handoffs/dashboard-audit-active-slice.md
docs/handoffs/command-center-second-opinion-brief.md
```

Keep this file updated while auditing dashboard routes. It contains current
agent-browser proof paths, confirmed broken/outdated surfaces and the next
implementation queue. If context is lost, resume from that handoff before
editing more dashboard code.

Current product correction:

- Stop treating Command Center as a place to display every available metric.
- Command Center must become a decision cockpit for the Polish marketer.
- Each top-level item must explain:
  - `co widzę`,
  - `co to znaczy`,
  - `co zrobić teraz`,
  - `czego nie wolno twierdzić`,
  - `jak Codex może pomóc`.
- Raw metric facts, query/page rows, GA4 landing/source rows and Merchant issue
  rows belong in dedicated diagnostic routes unless condensed into one decision.
- Codex skills are the operating layer: from a Command Center decision, the
  marketer should be able to run a matching WILQ skill that calls WILQ API,
  returns Polish evidence-backed output, prepares safe briefs/drafts/action
  previews, and blocks unsupported claims.
- Skill trigger descriptions must be written for real marketer intent, not for
  internal connector names. Example prompts that must route naturally:
  `pokaż przestrzeń do polepszenia adsów w Ekologus`,
  `znajdź ostatnie kampanie i ich efekty`,
  `które treści odświeżyć najpierw`,
  `czy feed produktowy jest OK`,
  `sprawdź jakość ruchu z GA4`,
  `jak poprawić lokalną widoczność`.
- Command Center action cards must expose the Codex bridge explicitly:
  `skill_id`, Polish `codex_prompt`, `codex_context_endpoint`,
  `expected_codex_output`, evidence IDs, ActionObject IDs and blocked claims.
  Without this bridge, the dashboard is only a data UI and Codex is not an
  operating layer.
- Before broad UI changes continue, use the second-opinion brief to validate
  the information architecture and next slices.

Tasks:

- Audit `/command-center` top-to-bottom with browser proof after the page
  settles. Current proof:
  `.local-lab/proof/dashboard-audit/text/command-center-final-slice.txt`.
- Remove, rewrite or demote readiness-only cards:
  - `connector_configured=true`,
  - `Connector ... ready for ... refresh`,
  - `No performance metrics have been collected`,
  - `Run a read-only refresh`,
  - social/local/connector debug cards that do not create a decision.
- Keep evidence IDs, ActionObjects and blockers, but present them as decisions:
  `co widzę`, `co to znaczy`, `co zrobić teraz`, `czego nie wolno twierdzić`,
  `jak Codex może pomóc`.
- Fix duplicate React keys and any UI warnings observed in browser console.
- Keep dashboard labels in Polish with Polish diacritics.
- Preserve the 2026-06-18 cleanup: `Dzisiejszy panel operatora` is only a
  compact status/header; detailed decision cards live only in
  `Plan działań marketera`.
- Preserve the 2026-06-18 cleanup: Command Center must not show
  `Demo dla marketera`, visible `PRIORITY N`, GA4 `(not set)` tactical cards,
  Localo OAuth probe/debug metric facts, `Freshness: unknown - Credential
  presence only`, `connector_configured`, or `Run a read-only`.
- Preserve the 2026-06-18 Localo correction: Command Center and `/localo` must
  say "access działa, brak ranking/GBP facts", not "dokończ access", after a
  completed Localo MCP initialize proof.
- Preserve the 2026-06-18 brief dedupe: `/api/marketing/brief` and generated
  ActionObjects must show the latest metric fact per
  `(source_connector, metric_name, dimensions)` and must not repeat the same
  aggregate metrics from older refresh runs.
- Preserve the 2026-06-18 brief scope cleanup: `/api/marketing/brief` is a
  marketer decision brief, not a connector inventory. Optional social/missing
  credential items such as LinkedIn/Facebook and disabled Sheets must not show
  as global blockers in `what_blocks_us`; social draft ActionObjects may exist
  in `/api/actions`, but they must not be promoted into brief
  `safe_next_actions` until social becomes an active marketer workflow.
- Preserve the 2026-06-18 skill eval ledger: real skill prompt runs and their
  usefulness findings belong in `docs/evals/skill-eval-ledger.md`; latest
  runtime/progress/performance state belongs in `docs/PROGRESS.md`.
- Preserve the 2026-06-18 context-pack performance finding:
  `/api/codex/context-pack` measured about 9.15s and 940 KB for
  `wilq-content-strategist`, mostly because it embeds broad state including
  hundreds of evidence summaries and multiple diagnostics. The next runtime
  optimization should be skill-scoped context packs, not random frontend
  memoization.
- 2026-06-18 follow-up: `wilq-content-strategist` now receives a skill-scoped
  context-pack by default. Local proof after API restart: full pre-scope pack
  about 8.106s / 940864 bytes; scoped content pack about 2.679s / 154334 bytes.
  Smoke still passes with `content_live=True`, `query_page_count=10`,
  action IDs `act_review_ga4_tracking_quality` and
  `act_prepare_content_refresh_queue`.
- 2026-06-18 follow-up: deterministic smoke suite passed for 12/12 WILQ skills
  after scoped context-pack changes. Summary artifact:
  `.local-lab/evals/skill-smoke-summary-20260618T093210Z.jsonl`. This proves
  API contract health, not final `codex exec` usefulness; non-interactive
  Codex evals are still required.
- 2026-06-18 follow-up: first real non-interactive Codex eval passed for
  `wilq-content-strategist`:
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, evidence IDs,
  source connectors and `act_prepare_content_refresh_queue` as a safe candidate.
  Remaining quality gap: this eval is still too broad and must evolve to assert
  concrete content decisions (`refresh`, `merge/create-after-inventory-check`,
  `block`) rather than only schema-safe recommendations.
- 2026-06-18 follow-up: second real non-interactive Codex eval passed for
  `wilq-merchant-feed-operator`:
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  `google_merchant_center` evidence IDs, live Merchant facts
  (`product_count=10900`, `issue_count=15`) and
  `act_review_merchant_feed_issues` as the safe pending-validation review path.
  Remaining quality gap: future Merchant evals should assert issue-level
  clustering and explicit ActionObject validation proof.
- 2026-06-18 follow-up: third real non-interactive Codex eval passed for
  `wilq-ga4-analyst`:
  `.local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  `google_analytics_4` evidence IDs and
  `act_review_ga4_tracking_quality` as the safe pending-validation review path.
  It correctly blocks ROAS/revenue/conversion claims without stronger evidence.
  Remaining quality gap: future GA4 evals should assert ranked
  landing/source/campaign diagnostic items and explicit ActionObject validation
  proof.
- 2026-06-19 follow-up: `wilq-ga4-analyst` now consumes
  `/api/ga4/diagnostics.decision_queue` as the primary decision source. Fresh
  runtime proof after API restart showed `live_data_available=true`,
  `landing_group_count=10`, `decision_count=6` and
  `act_review_ga4_tracking_quality`. Fresh non-interactive Codex eval passed:
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, GA4 evidence IDs,
  `review_traffic_quality` decisions, pending validation for
  `act_review_ga4_tracking_quality`, and blocked ROAS/revenue/conversion/
  attribution/tracking-fixed claims. Remaining gap: no current evidence
  exercises `fix_measurement` or `review_landing_mapping`, and ActionObject
  validation is still pending.
- 2026-06-18 follow-up: fourth real non-interactive Codex eval passed for
  `wilq-gsc-content-doctor`:
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  GSC/WordPress evidence IDs, `content_diagnostics.live_data_available=true`,
  `query_page_count=10`, `matched_inventory_count=0` and
  `act_prepare_content_refresh_queue` as the safe pending-validation content
  queue path. Remaining quality gap: future GSC evals should assert concrete
  query/page candidates with `refresh`, `merge`, `create` or `block` decisions.
- 2026-06-18 follow-up: `wilq-daily-command` was hardened after Command Center
  and brief cleanup. Deterministic smoke now fails if daily context loses core
  ActionObjects or reintroduces social draft actions. Fresh non-interactive
  Codex eval passed:
  `.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, 14 evidence IDs, core
  ActionObject candidates only, no safety findings and
  `operator_usefulness_score=5`.
- 2026-06-18 active local slice: `content_diagnostics.decision_queue` moved
  content classification into typed WILQ API. Fresh eval passed at
  `.local-lab/evals/codex-skill/20260618T114810Z/wilq-content-strategist/result.json`.
  It uses API decisions `inventory_check_before_create`,
  `merge_create_after_inventory_check` and `block_as_tracking_not_content`.
  The follow-up route cleanup is documented in `docs/PROGRESS.md`; resume route
  audit on `/ga4`, `/ads-doctor` and `/localo`.
- Performance direction: follow TanStack/React guidance by avoiding client
  waterfalls and duplicated data models. Do not patch this with random
  `useMemo`; next performance slice should build a lightweight daily-decision
  view model or short-lived materialized cache for the first screen.

Pass criteria:

- `agent-browser` or Playwright proof shows no readiness slop on the first
  screen,
- marketer sees concrete daily decisions and tactical work, not connector
  inventory,
- dashboard unit/e2e tests assert the slop is absent.
- `/api/dashboard/command-center` remains materially faster than the previous
  6-7s baseline. Latest proof after parallel diagnostics:
  1.95-2.32s live-server response time.
- Latest proof after Localo + brief cleanup:
  - `http://127.0.0.1:8000/api/dashboard/command-center` returns
    `daily_localo_readiness.status=ready`, title
    `Localo: MCP access działa, brak jeszcze ranking/GBP facts`, and
    `plan_localo_access_ready_wait_for_visibility_facts`.
  - `http://127.0.0.1:8000/api/marketing/brief` has
    `duplicates_found=False` for item-local metric facts.
  - Latest live proof for `/api/marketing/brief` after restart:
    `what_we_know=6`, `what_blocks_us=0`, `safe_next_actions=3`,
    `recommended_focus=2`, duplicate item IDs `0`, duplicate metric facts `0`.
    Core brief actions are only:
    `act_review_merchant_feed_issues`,
    `act_review_ga4_tracking_quality`,
    `act_prepare_content_refresh_queue`.

### 2. Source-To-Product Condensation

Goal: prove that research sources shape WILQ behavior, not only docs.

Tasks:

- Done: Google Ads change-history read chain.
  - Product layer added:
    `/api/ads/diagnostics.change_history_read_contract`.
  - Live evidence:
    `refresh_google_ads_e7f371e9efac` /
    `ev_refresh_refresh_google_ads_e7f371e9efac`.
  - Live result: `change_event_row_count=0` for the last 14 days. This proves
    read access and blocker behavior, not change-impact.
  - API view model: `AdsChangeHistoryReadContract`, `AdsChangeHistoryRow` and
    decision `ads_review_change_history`.
  - Dashboard proof: `/ads-doctor` renders change-history read state and, when
    rows exist, sanitized event rows only.
  - Skill proof: `wilq-ads-doctor` smoke, scoped context-pack and
    non-interactive eval expose the same change-history contract.
  - Safety proof: change impact, performance uplift, budget scaling, budget
    apply and campaign mutation remain blocked.
  - Non-interactive Codex proof:
    `.local-lab/evals/codex-skill/20260619T162014Z/wilq-ads-doctor/result.json`
    has `language=pl-PL`, `api_used=true`, Google Ads evidence IDs and no
    safety findings.
  - Full proof: `scripts/verify.sh` passed with backend API contracts
    `111 passed`, dashboard route tests `13 passed`, Playwright e2e
    `9 passed`, API smoke, skill structure smoke, skill API smoke, security
    checks and dashboard production build passed. Non-blocking warning: Vite
    main JS chunk `540.14 kB`.
- Done: Google Ads impression-share read chain.
  - Product layer added:
    `/api/ads/diagnostics.impression_share_read_contract`.
  - Live evidence:
    `refresh_google_ads_baba7f993f1a` /
    `ev_refresh_refresh_google_ads_baba7f993f1a`.
  - API view model: `AdsImpressionShareReadContract`,
    `AdsImpressionShareRow` and decision `ads_review_impression_share`.
  - Dashboard proof: `/ads-doctor` renders campaign impression-share rows as
    read-only review input.
  - Skill proof: `wilq-ads-doctor` smoke, scoped context-pack and
    non-interactive eval expose the same impression-share contract.
  - Safety proof: budget scaling, budget apply, wasted budget, performance
    uplift and campaign mutation remain blocked.
  - Full proof: `scripts/verify.sh` passed with backend API contracts
    `111 passed`, dashboard route tests `13 passed`, Playwright e2e
    `9 passed`, API smoke, skill structure smoke, skill API smoke, security
    checks and dashboard production build passed. Non-blocking warning: Vite
    main JS chunk `536.68 kB`.
- Done: Google Ads recommendations read
  chain.
  - Product layer added:
    `/api/ads/diagnostics.recommendations_read_contract`.
  - Live evidence:
    `refresh_google_ads_138befce0a2c` /
    `ev_refresh_refresh_google_ads_138befce0a2c`.
  - API view model: `AdsRecommendationsReadContract`,
    `AdsRecommendationRow` and decision `ads_review_recommendations`.
  - Dashboard proof: `/ads-doctor` renders active recommendation types as
    read-only review input.
  - Skill proof: `wilq-ads-doctor` smoke and scoped context-pack expose the
    same recommendations contract.
  - Safety proof: apply, automatic accept, budget mutation and performance
    uplift claims remain blocked.
  - Full proof: `scripts/verify.sh` passed with backend API contracts
    `111 passed`, dashboard route tests `13 passed`, Playwright e2e
    `9 passed`, API smoke, skill structure smoke, skill API smoke, security
    checks and dashboard production build passed. Non-blocking warning: Vite
    main JS chunk `533.57 kB`.
  - Non-interactive Codex proof:
    `.local-lab/evals/codex-skill/20260619T153351Z/wilq-ads-doctor/result.json`
    includes `recommendations_read_contract`, `ads_review_recommendations`,
    `recommendation apply`, Google Ads evidence IDs and no safety findings.
- Done: Google Ads budget review chain.
  - Product layer added: `google_ads_budget_review_playbook`.
  - Compiled knowledge card:
    `card_google_ads_budget_review_playbook`.
  - Expert rules bound to API decisions:
    `ads_scaling_candidates_v1`, `ads_recommendations_v1`,
    `ads_principles_v1`.
  - API view model: `AdsDiagnosticSection` and `AdsDecisionItem` expose
    `knowledge_card_ids` and `expert_rule_ids`.
  - Dashboard proof: `/ads-doctor` renders those trace IDs only when present.
  - Skill context proof: `POST /api/codex/context-pack` for
    `wilq-ads-doctor` preserves the same decision lineage.
  - Safety proof: redaction allowlist preserves `knowledge_card_ids` and
    `expert_rule_ids`, while still redacting secret values.
- Done for this chain: non-interactive `wilq-ads-doctor` Codex eval passed at
  `.local-lab/evals/codex-skill/20260619T144600Z/wilq-ads-doctor/result.json`.
  It proves the Polish answer references the budget review knowledge/rule
  lineage, evidence IDs, prepare-only ActionObjects and blocked budget/apply
  claims.
- Next chains after Ads change history:
  - Ads pre/post change-impact window joined to campaign/search-term facts.
  - Ads Keyword Planner enrichment for search terms and custom segments.
  - GSC/content source-to-decision quality.
  - Localo visibility once ranking/GBP evidence exists.
- Use official docs first, then practitioner/academic sources only where they
  add operating value.

Pass criteria:

- one visible dashboard decision can be traced:
  source -> knowledge/rule -> API -> dashboard -> skill/eval,
- no rule exists only as prompt prose,
- blocked claims are explicit.

### 3. API And Skill Integration Proof

Goal: prove Codex + WILQ API + skills are better than plain Codex.

Tasks:

- Run real `codex exec` or Codex CLI/Desktop prompts against the local WILQ API.
- Use Polish prompts:
  - `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
  - `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
  - `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
  - `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
  - `Czy Localo daje już ranking/GBP insight czy nadal blocker?`
- Compare plain Codex answer vs WILQ-skill/API answer vs dashboard/API state.

Pass criteria:

- WILQ answer is in Polish,
- WILQ answer uses API or reports blocker,
- WILQ answer includes evidence IDs/source connectors,
- WILQ answer avoids invented metrics,
- WILQ answer gives a safe next action,
- WILQ answer matches dashboard/API for the same claim.

Current eval progress:

- `wilq-daily-command`: strengthened and re-evaluated at
  `.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json`.
  Strong daily pass: Merchant, Content and GA4 core action candidates only;
  Localo/social are not promoted without explicit evidence/workflow.
- `wilq-content-strategist`: passed non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  Safe, API-backed, but future eval must force concrete
  `refresh`/`merge`/`create`/`block` decisions.
- `wilq-merchant-feed-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  Strong Merchant pass with `product_count=10900`, `issue_count=15` and
  `act_review_merchant_feed_issues`.
- `wilq-ga4-analyst`: strict decision_queue pass at
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  The skill uses `/api/ga4/diagnostics.decision_queue`, returns
  `review_traffic_quality` decisions with GA4 evidence IDs, carries
  `act_review_ga4_tracking_quality` as pending validation, and blocks
  ROAS/revenue/conversion/attribution/tracking-fixed claims.
- `wilq-gsc-content-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  Safe GSC/content pass; future eval must force concrete query/page decisions.
- `wilq-ads-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json`.
  Important correction: Ads is currently live campaign review, not OAuth repair.
  The skill may use campaign and search-term evidence from `google_ads`, plus
  read-only derived KPI rows. It must still block profitability, wasted budget,
  negative keyword apply, budget scaling and recommendation/apply claims until
  WILQ exposes stronger interpretation, safety and apply contracts.
  Fresh strict source-backed lineage eval passed at
  `.local-lab/evals/codex-skill/20260619T144600Z/wilq-ads-doctor/result.json`
  and requires `card_google_ads_budget_review_playbook`,
  `ads_scaling_candidates_v1`, `ads_recommendations_v1` and
  `ads_principles_v1`.
- `wilq-localo-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T102743Z/wilq-localo-operator/result.json`.
  Important correction: Localo is currently access-ready, not missing
  `LOCALO_ACCESS_TOKEN`; however, the skill must still block ranking, GBP,
  competitor and local visibility uplift claims until WILQ exposes Localo facts
  beyond MCP initialize/access readiness.
- `wilq-daily-command`: passed at
  `.local-lab/evals/codex-skill/20260618T103758Z/wilq-daily-command/result.json`.
  This proves the top-level Polish daily loop across Command Center,
  MarketingBrief and context-pack: Merchant first, then Content/GA4/Ads/Localo
  with evidence IDs and safe next actions. Cleanup still needed:
  LinkedIn/Facebook draft ActionObjects can leak into daily action candidates
  from the wider `marketing_brief.action_ids`; daily primary actions should stay
  focused on core marketer decisions unless social is explicitly requested.
- `wilq-campaign-builder`: passed at
  `.local-lab/evals/codex-skill/20260618T104154Z/wilq-campaign-builder/result.json`.
  This is a safety/blocker pass, not campaign creation proof. It confirms
  Ads/GA4/GSC evidence access, then blocks campaign candidate and payload
  preview because WILQ lacks a campaign-specific ActionObject, keyword/asset
  evidence, budget facts and validated campaign payload contract.
- `wilq-custom-segments`: passed at
  `.local-lab/evals/codex-skill/20260618T104644Z/wilq-custom-segments/result.json`.
  This is an anti-hallucination pass. It blocks audience/custom segment
  candidates because WILQ currently has aggregate Ads/GSC facts, but not real
  source terms/search terms/query evidence with lineage.
- `wilq-demand-gen-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T105005Z/wilq-demand-gen-operator/result.json`.
  This is a guardrail pass with low usefulness (`operator_usefulness_score=3`).
  It correctly blocks Demand Gen recommendations because WILQ has aggregate
  Ads/GA4/Merchant readiness only, not asset, creative, landing-quality,
  migration diagnostics or a Demand Gen-specific ActionObject.
- `wilq-ahrefs-gap-finder`: passed at
  `.local-lab/evals/codex-skill/20260618T105335Z/wilq-ahrefs-gap-finder/result.json`.
  This is a guardrail pass with low usefulness (`operator_usefulness_score=3`).
  It correctly blocks backlink/competitor/content gap claims because WILQ has
  aggregate Ahrefs authority metrics plus GSC/WordPress context, but no concrete
  Ahrefs gap records.
- `wilq-social-publisher`: passed at
  `.local-lab/evals/codex-skill/20260618T105649Z/wilq-social-publisher/result.json`.
  This is a strong safety pass. It exposes LinkedIn/Facebook draft ActionObjects
  but blocks publishing and draft claims because social credentials and
  ActionObject validation are missing.

Current eval coverage: 12/12 WILQ skills have recorded non-interactive Codex
evals. GA4 has a fresh strict decision_queue rerun, Ads has multiple strengthened
read-contract reruns, and Ahrefs now has a strict blocker eval proving that
authority metrics cannot be promoted into gap recommendations:
`.local-lab/evals/codex-skill/20260620T110348Z/wilq-ahrefs-gap-finder/result.json`.
This proves API integration and guardrails, not Goal 001 completion. The next
product work must convert eval findings into fixes: Ahrefs gap records,
source-term/custom-segment evidence, campaign ActionObjects, Demand Gen
diagnostics and the final plug-and-play Codex acceptance session.

### 4. Performance Slice

Goal: Command Center must feel usable, not wait ~15 seconds for avoidable work.

Tasks:

- Measure:
  - `/api/dashboard/command-center`,
  - `/api/marketing/tactical-queue`,
  - `/api/metrics?limit=80`,
  - dashboard first meaningful render.
- Identify whether bottleneck is backend joins, payload size, duplicate frontend
  fetches, rendering volume or dev-server overhead.
- Prefer small fixes:
  - remove unused first-screen fetches,
  - lazy-load secondary panels,
  - truncate long evidence lists,
  - cache expensive view-model joins,
  - avoid broad refactors until measured.

Pass criteria:

- before/after timing is recorded here,
- first-screen work is reduced or a precise blocker remains,
- no performance fix removes required evidence/action traceability.

Current slice result:

- Implemented scoped default context-pack for
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`.
- Default daily context now includes `command_center`, `marketing_brief`, core
  daily ActionObjects, relevant connector status, relevant evidence summaries,
  knowledge cards, expert rules and expert capabilities.
- Default daily context no longer embeds `tactical_queue`, Ads/Merchant/Content
  or GA4 diagnostics. Full context remains available through
  `{"skill":"wilq-daily-command","full_context":true}`.
- Baseline from the old `:8000` runtime before this slice:
  - command-center: `5.937s`, `30521 bytes`;
  - marketing brief: `1.648s`, `46310 bytes`;
  - daily context-pack: `15.030s`, `996121 bytes`;
  - daily full context-pack: `11.734s`, `996121 bytes`.
- Fresh `:8011` runtime proof after this slice:
  - default daily context-pack: `2.888s`, `160053 bytes`;
  - repeated default daily context-pack: `2.985s`, `160053 bytes`;
  - repeated default daily context-pack: `2.959s`, `160053 bytes`;
  - full daily context-pack: `6.465s`, `998704 bytes`;
  - marketing brief: `0.541s`, `46072 bytes`;
  - command-center: `2.424s`, `30521 bytes`;
  - repeated command-center: `2.094s`, `30521 bytes`;
  - repeated command-center: `2.102s`, `30521 bytes`.
- Metric store read paths now use batch DuckDB reads and read-only DuckDB
  connections when the DB file already exists. This removes the conflicting
  lock failure observed when local profiling and the running `:8000` API read
  `.local-lab/state/wilq.duckdb` at the same time.
- Current follow-up adds a shared `DailyRuntime` for daily Codex context:
  `command_center`, `marketing_brief` and core daily ActionObjects are built
  from one connector/action/refresh snapshot and cached for a short TTL.
  `WILQ_DAILY_RUNTIME_CACHE_SECONDS` controls the TTL, default `30`; tests
  disable the cache. The cache is invalidated after connector refresh and
  action validation/apply paths.
- Fresh helper API proof on `:8011` after this follow-up:
  - default daily context: `3.047s` cold, then `0.467s`, `0.544s`, `0.470s`
    warm within TTL;
  - payload size stayed `160478 bytes`;
  - `/api/dashboard/command-center`: `2.034s`, `2.029s`, `2.396s`;
  - `/api/marketing/brief`: `0.618s`, `0.608s`, `0.588s`.
- Focused proof passed:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run pytest tests/test_api_contracts.py -q -k 'daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or command_center_exposes_polish_operator_brief or daily_context_pack_excludes_social_draft_action_objects or codex_context_pack_contains_no_metric_invention_instruction or codex_context_pack_includes_expert_rule_summaries'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8011
  ```
- Full proof passed:
  ```bash
  scripts/verify.sh
  ```

Completed follow-up on 2026-06-19, pushed as
`35d8be3 perf(api): share daily runtime endpoints`:

- Public dashboard endpoints are being moved onto the same `DailyRuntime`
  cache:
  - `GET /api/dashboard/command-center` ->
    `build_daily_runtime().command_center`;
  - `GET /api/marketing/brief` ->
    `build_daily_runtime().marketing_brief`.
- This is the next real bottleneck after scoping daily Codex context-pack:
  Command Center, Marketing Brief and Codex daily context should share one
  daily view-model in the API process instead of rebuilding overlapping daily
  state through separate endpoint paths.
- Changed files were:
  - `apps/api/wilq_api/main.py`,
  - `tests/test_api_contracts.py`,
  - `docs/CONTEXT.md`,
  - `docs/PROGRESS.md`,
  - `docs/goals/001-goal.md`.
- Added/updated tests:
  - `test_command_center_endpoint_uses_daily_runtime_cache`,
  - `test_marketing_brief_endpoint_uses_daily_runtime_cache`.
- Focused checks passed after adding both endpoint regression tests:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py tests/test_api_contracts.py
  uv run pytest tests/test_api_contracts.py -q -k 'command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or marketing_brief_aggregates_metric_facts_and_blockers'
  ```
- Result: ruff passed, mypy passed, pytest 5 selected tests passed.
- Broader route/API proof also passed:
  ```bash
  uv run pytest tests/test_api_contracts.py -q -k 'command_center or marketing_brief or daily_runtime or context_pack'
  pnpm --filter @wilq/dashboard typecheck
  pnpm --filter @wilq/dashboard test -- --run App.test.tsx
  ```
- Result: backend selected tests 17 passed, dashboard typecheck passed,
  dashboard route tests 13 passed.
- Full proof passed:
  ```bash
  scripts/verify.sh
  ```
- Result: backend API contracts 102 passed, dashboard route tests 13 passed,
  Playwright e2e 9 passed, skill API smoke passed and dashboard production
  build passed.
- Non-blocking warning: Vite reports the main JS chunk is above 500 KB. This is
  now a known future performance issue, not a blocker for this API runtime
  slice.

Remaining blocker:

- Payload size, DuckDB read stability and warm daily Codex context are much
  better, but cold runtime is not done. The remaining cost is inside Command
  Center diagnostics/tactical joins and should be reduced by the next product
  slices: Merchant issue-level triage, URL normalization and slimmer
  `DailyDecision` data. Do not hide this in skill references.

Completed 2026-06-19 follow-up, pushed as
`ad17223 perf(api): slim command center runtime`:

- `build_command_center_response()` and `build_command_center_brief()` now
  accept preloaded `tactical_queue` and `actions`, so DailyRuntime can build
  Command Center without refetching action/tactical state.
- Command Center no longer builds full Content Diagnostics, GA4 Diagnostics and
  Merchant Diagnostics just to render first-screen daily cards. Content and GA4
  summaries are derived from the already-built tactical queue; Merchant summary
  reads `google_merchant_center` metric facts directly and keeps full issue
  clustering on `/merchant`.
- Measured before this follow-up from local direct profiling:
  - `build_command_center_response()`: about `4.896s`;
  - `build_daily_runtime()`: about `6.600s`;
  - after removing Content/GA4 duplicate diagnostics:
    `build_command_center_response()` about `2.7-2.8s`;
  - after replacing Merchant Diagnostics in Command Center:
    `build_command_center_response()` about `1.685-2.073s`,
    `build_daily_runtime()` about `2.053-2.104s`.
- HTTP proof on fresh `:8016` after this follow-up:
  - cold `GET /api/dashboard/command-center`: `2.526s`, `26629 bytes`;
  - warm repeated Command Center within TTL: `0.011-0.012s`;
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`:
    `0.882-0.934s` while warm, `3.451s` after TTL expiry, `171000 bytes`.
- Full `scripts/verify.sh` passed after this follow-up:
  - backend API contracts: `103 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill API smoke and dashboard production build passed.
- This is useful progress, not final performance completion. The next
  bottleneck is the daily context-pack after cache expiry and any remaining
  route-level render cost in the dashboard. Keep evidence IDs, ActionObject IDs
  and blocked claims intact when optimizing.

Active 2026-06-19 follow-up:

- Daily Codex context-pack now reuses `DailyRuntime.refresh_runs` instead of
  calling `list_connector_refresh_runs()` again.
- Daily Codex context-pack now uses targeted `list_evidence_by_ids()` instead
  of scanning the full evidence registry. Metric-fact evidence can be fetched
  directly by evidence ID through DuckDB.
- Follow-up 2026-06-19 21:13 Europe/Warsaw reduces the shared daily cold path
  further without changing external API contracts:
  - `build_daily_runtime()` builds independent daily inputs in parallel;
  - Command Center passes preloaded ActionObjects into
    `build_ads_diagnostics(actions=...)` instead of reseeding action state;
  - Marketing Brief reads 200 latest metric groups per connector instead of
    500. Live checks confirmed this still preserves dimensional Merchant issue,
    GA4 landing/source, GSC query/page, WordPress and Ads facts.
- Follow-up 2026-06-19 21:32 Europe/Warsaw reduces default daily
  `wilq-daily-command` context-pack payload:
  - compacted active ActionObjects keep IDs, status, risk, evidence IDs,
    diagnosis/reason and full endpoint template, but drop heavy metrics/payload
    rows from the default packet;
  - embedded Command Center keeps `operator_brief`, `action_plan`,
    `daily_decisions` and primary counts, but omits duplicated
    `connector_health`;
  - embedded Marketing Brief caps item metric facts to 3 compact examples and
    top metric facts to 8 compact examples;
  - full data remains available via `full_context=true`,
    `/api/marketing/brief`, `/api/dashboard/command-center` and
    `/api/actions/{action_id}`;
  - Localo remains available in connector context, but is not required as a
    daily source connector until WILQ has Localo ranking/GBP evidence.
- Follow-up 2026-06-19 21:44 Europe/Warsaw resolves the current Vite main
  chunk warning by splitting dashboard vendor bundles:
  - no `chunkSizeWarningLimit` bypass was added;
  - Rollup manual chunks split React, TanStack, icons, schemas and misc vendor
    code;
  - current build chunks are app `142.44 kB`, `vendor-react` `192.70 kB`,
    `vendor-tanstack` `126.96 kB`, `vendor-schemas` `76.67 kB`,
    `vendor-icons` `7.91 kB`, `vendor-misc` `2.16 kB`.
- Focused proof passed:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/evidence/registry.py wilq/storage/metric_store.py wilq/briefing/daily_runtime.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/evidence/registry.py wilq/storage/metric_store.py wilq/briefing/daily_runtime.py
  uv run pytest tests/test_api_contracts.py -q -k 'codex_context_pack_embeds_marketing_brief_contract or list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_includes_compiled_knowledge_cards or daily_context_pack_excludes_social_draft_action_objects or command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
  ```
- HTTP proof on local `:8000` after this follow-up:
  - earlier daily context follow-up:
    `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` cold after
    TTL `2.548s`, warm `0.273s` and `0.324s`;
  - after the 21:13 follow-up and `scripts/local_stack.sh restart`:
    `GET /api/dashboard/command-center` after TTL `1.448s`, `1.466s`,
    `1.505s` at `27575 bytes`;
  - `GET /api/marketing/brief` after TTL `1.423s`, `1.503s`, `1.476s` at
    `71215 bytes`;
  - daily `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` after
    TTL `1.671s`, `1.764s`, `1.707s` at `235159 bytes`;
  - after the 21:32 context-pack payload compaction:
    default daily context-pack `120436 bytes`;
  - warm cache hits remain millisecond-level.
- Full `scripts/verify.sh` passed after this follow-up:
  - backend API contracts: `106 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- Full `scripts/verify.sh` passed after the 21:13 follow-up:
  - backend API contracts: `112 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- Non-interactive `wilq-daily-command` eval passed after the 21:32 payload
  compaction:
  `.local-lab/evals/codex-skill/20260619T193056Z/wilq-daily-command/result.json`.
  Result has `language=pl-PL`, `api_used=true`, 19 evidence IDs and source
  connectors for Merchant, GSC, WordPress, GA4, Ads and Ahrefs.
- Full `scripts/verify.sh` passed after the 21:32 payload compaction:
  - backend API contracts: `112 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- Focused dashboard proof passed after the 21:44 bundle split:
  - `pnpm --filter @wilq/dashboard typecheck`;
  - `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` -> `13 passed`;
  - `WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1` -> `8 passed`;
  - `pnpm --filter @wilq/dashboard build` -> no >500 KB chunk warning.
- Full `scripts/verify.sh` passed after the 21:44 bundle split:
  - API smoke passed;
  - skill structure smoke passed;
  - skill API smoke passed;
  - Playwright dashboard suite `9 passed`;
  - production dashboard build passed with no >500 KB chunk warning.
- This improves the known daily context-pack TTL spike and shared daily cold
  path, compacts daily context payload and removes the current dashboard chunk
  warning. Remaining future work: richer value contracts rather than hidden
  frontend-only memoization.
- Active Ads skill performance follow-up:
  - scoped `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now
    removes nested `*_metric_facts` from the skill packet, strips duplicated
    nested candidate payload previews, trims ActionObject row arrays while
    preserving totals in `context_pack_compaction`, and points to
    `/api/ads/diagnostics` plus `/api/actions/{action_id}` for full detail;
  - the API uses a short 5s skill context cache only as a compute shortcut for
    repeated identical skill calls. It is disabled in pytest and cleared after
    connector refresh, ActionObject validation and apply;
  - local proof on `:8000`: Ads context-pack `198513 bytes`, cold
    `1.281-1.620s`, warm `0.145-0.159s`, `search_term_rows_total=50`,
    `search_term_rows_included=8`,
    `search_term_safety_rows_included=8`,
    `keyword_match_context_rows_included=8`,
    `negative_keyword_candidates_included=4`, no `*_metric_facts` keys in
    scoped Ads diagnostics payload;
  - this satisfies the immediate non-daily Ads context-pack size target, but
    does not complete full performance work. Remaining: Command Center cold
    path, content/GA4 context packs, dashboard JS chunk and richer value
    contracts.
- Active Command Center GA4 correction:
  - live `/api/ga4/diagnostics` had GA4 dimensional facts, but Command Center
    could still show `landing groups=0` because it only counted GA4 tactical
    items;
  - Command Center now uses a lightweight GA4 `MetricFact` fallback for unique
    `landing_page` / `source_medium` / `campaign_name` groups;
  - GA4 remains `blocked`, because WILQ still lacks the interpretation
    contracts for ROAS/revenue/conversion drop/tracking fixed claims;
  - live proof on `:8000`: title
    `GA4: brak pełnego kontraktu interpretacji ruchu`, metric tiles
    `landing groups=10`, `low engagement=0`, `WP match=0`, `blockery=1`,
    evidence `ev_refresh_refresh_google_analytics_4_681b6bcefc85`, action
    `act_review_ga4_tracking_quality`;
  - daily Codex context-pack now returns the same GA4 decision as the
    dashboard.

Current hook-runtime fix:

- The Stop hook must never print plain text on stdout when Codex expects Stop
  hook JSON. The observed failure was:
  `Stop hook (failed): hook returned invalid stop hook JSON output`.
- `.codex/hooks/stop_log.py` now emits valid JSON with `continue=true` when it
  skips run logging because WILQ API is unreachable or because the configured
  API URL is unsupported. This keeps WILQ API unreachable as context, not as a
  hook failure.
- `.codex/hooks.json` must use `uv run python` from repo root, not global
  `python3`.
- Regression proof must cover unreachable local API and parse stdout as JSON.
- Full `scripts/verify.sh` passed after the hook fix:
  - backend API contracts: `105 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill smokes and dashboard production build passed.

### 5. Verification And Commit

Goal: finish with proof, not vibes.

Required focused checks after touched surfaces:

```bash
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run pytest tests/test_api_contracts.py -q
```

Required full gate:

```bash
scripts/verify.sh
```

Commit rules:

- Conventional Commits only.
- Do not commit `.env`, `.local-lab`, traces, screenshots, secrets or protected
  client data.
- Update this goal before commit with:
  - completed step,
  - proof commands,
  - remaining blockers,
  - next step.

## Immediate Next Tasks

1. **Preserve the cleaned marketer routes and move to value contracts.**
   Command Center, `/merchant`, `/content-planner`, `/ga4`, `/ads-doctor`,
   `/localo`, `/actions` and `/opportunities` have current decision-first
   cleanup proof. Do not restart those audits unless browser proof shows a
   regression. Next product work should add missing value contracts:
   typed Ahrefs gap records, deeper search-term/custom-segment evidence,
   remaining campaign optimization contracts and Demand Gen diagnostics. Ads
   target-aware KPI triage is started, but remains review-only. Campaign
   ActionObjects are now partially started via
   `act_prepare_ads_campaign_review_queue`; do not treat that as budget
   optimization or apply support.

2. **Keep supporting registries out of first-screen decision flow.**
   `/actions` is now ActionObject review, and `/opportunities` is now a
   supporting registry. Do not reintroduce them as duplicated Command Center
   decision queues unless a typed API model adds a new, useful marketer
   decision.

3. **Improve route usefulness, not just wording.**
   For every route cleanup, prefer typed API/view-model changes over copy-only
   patches. If a card has only connector readiness, convert it into a real
   decision, honest blocker, ActionObject validation path or remove it from the
   marketer route.

4. **Run focused verification after every route slice.**
   Minimum:
   ```bash
   uv run ruff check <touched-python-files>
   uv run mypy <touched-python-files>
   uv run pytest tests/test_api_contracts.py -q -k '<relevant-tests>'
   pnpm --filter @wilq/dashboard lint
   pnpm --filter @wilq/dashboard typecheck
   pnpm --filter @wilq/dashboard test -- --run App.test.tsx
   WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts
   ```

5. **Run full verification before commit.**
   Required:
   ```bash
   scripts/verify.sh
   ```

6. **Run stricter Codex/API proof for the next high-value gap.**
   Use `codex exec` or Codex Desktop/CLI against the local WILQ API. Plain
   static prompt evaluation is not enough. The proof must show API use, Polish
   output, evidence IDs, source connectors, blocked claims and safe next actions.
   GA4 now has a strict decision_queue rerun. Continue with Localo after real
   visibility facts, or Ahrefs/custom-segments/campaign-builder after their API
   read/action contracts exist.

7. **Commit semantically and push.**
   Use Conventional Commits only. Do not commit `.env`, `.local-lab`, test
   traces or secrets.

8. **Run plug-and-play Codex acceptance session.**
   Add only the final result and any active blockers back into this file.

## Latest Focused Verification

Passed after the 2026-06-19 Custom Segments review-only payload preview slice:

```bash
uv run ruff check wilq/schemas.py wilq/actions/google_ads/custom_segments.py wilq/briefing/ads_diagnostics.py apps/api/wilq_api/main.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/schemas.py wilq/actions/google_ads/custom_segments.py wilq/briefing/ads_diagnostics.py apps/api/wilq_api/main.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics or custom_segments or route_specific'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-custom-segments --api-base http://127.0.0.1:8000
```

Live `:8000` proof after `scripts/local_stack.sh restart`:

- `/api/ads/diagnostics.custom_segments_read_contract.status=ready`;
- `candidate_count=1`, `payload_preview_count=1`;
- remaining missing contracts:
  `keyword_planner_enrichment`, `forecast_or_audience_size`;
- `custom_segment_payload_preview` uses `member_type=KEYWORD`,
  `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`;
- `/api/actions/act_prepare_custom_segments_from_search_terms` exposes
  `preview_contract=custom_segment_payload_preview_v1` and validates;
- scoped `wilq-custom-segments` context-pack omits `content_diagnostics`, caps
  ActionObject metrics and measures about `186317 bytes`;
- non-interactive `wilq-custom-segments` eval passed:
  `.local-lab/evals/codex-skill/20260619T201200Z/wilq-custom-segments/result.json`
  with `operator_usefulness_score=5` and `safety_findings=[]`.
- full `scripts/verify.sh` passed after this slice:
  - backend API contracts `113 passed`;
  - dashboard route tests `13 passed`;
  - Playwright e2e `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed;
  - production build chunks remain below the 500 KB warning threshold.

Still blocked:

- custom segment targeting/apply;
- audience-size, conversion-uplift, ROAS, targeting-applied and
  campaign-performance claims;
- Keyword Planner enrichment, forecast/audience-size, human confirmation and
  Ads apply/audit contracts.

Passed after the 2026-06-19 Ads negative keyword payload preview slice:

```bash
uv run ruff check wilq/actions/google_ads/negative_keywords.py wilq/briefing/ads_diagnostics.py wilq/schemas.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/actions/google_ads/negative_keywords.py wilq/briefing/ads_diagnostics.py wilq/schemas.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics_exposes_live_campaign_metric_facts or google_ads_vendor_read_uses_oauth_and_search_stream or route_specific or ads_skill'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-ads-doctor --api-base http://127.0.0.1:8000
```

Live `:8000` proof after `scripts/local_stack.sh restart` and the 2026-06-19
keyword context slice:

- `/api/ads/diagnostics.keyword_match_context_read_contract.status=ready`
  with 211 context rows and `missing_read_contracts=["human_intent_review"]`.
- `/api/ads/diagnostics.negative_keywords_read_contract.payload_preview` has
  7 review-only preview rows and `missing_read_contracts=[]`.
- `/api/actions/act_prepare_negative_keyword_review_queue` exposes
  `preview_contract=negative_keyword_payload_preview_v1`,
  `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`.
- `wilq-ads-doctor` smoke passed with `context_row_count=211`,
  `candidate_count=7` and `payload_preview_count=7`.
- Non-interactive `wilq-ads-doctor` eval passed at
  `.local-lab/evals/codex-skill/20260619T182309Z/wilq-ads-doctor/result.json`.
- Full `scripts/verify.sh` passed: backend API contracts `111 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed`, API smoke,
  skill smokes and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk `549.44 kB` exceeds the 500 KB warning threshold.
- Still blocked: negative keyword apply, search-term waste, conversion loss,
  CPA and ROAS until human review, confirmation, apply/audit contracts and
  stronger intent validation exist.

Passed after the 2026-06-19 Ads campaign review ActionObject:

```bash
uv run ruff check wilq/actions/google_ads/campaign_review.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/actions/google_ads/campaign_review.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py -k "ads_diagnostics" tests/test_codex_skill_eval_cases.py::test_route_specific_codex_eval_cases_define_surface_markers -q
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
pnpm --filter @wilq/dashboard test -- --run
scripts/verify.sh
```

Live `:8000` proof after API restart:

- `/api/ads/diagnostics.action_ids` includes
  `act_prepare_ads_campaign_review_queue`.
- Campaign and derived KPI decisions attach only
  `act_prepare_ads_campaign_review_queue`.
- `/api/actions/act_prepare_ads_campaign_review_queue` exposes 8 live campaign
  candidates with evidence ID `ev_refresh_refresh_google_ads_c2f62ee2b43a`.
- Validation passed:
  `POST /api/actions/act_prepare_ads_campaign_review_queue/validate`
  returned `valid=true`.
- Full `scripts/verify.sh` passed: backend API contracts `108 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed`, API smoke,
  skill structure smoke, skill API smoke and dashboard production build passed.
  Known non-blocking warning: Vite main JS chunk `525.96 kB` exceeds the
  500 KB warning threshold.

Remaining Ads optimizer blockers:

- budget apply preview exists as review-only `CampaignBudgetOperation`, but
  human budget-goal, apply safety and mutation audit contracts are still
  missing,
- no recommendation apply support, human strategy-review or mutation audit path,
- no pre/post change-impact window contract,
- no profit-margin/business-goal interpretation contract,
- no campaign pause/budget apply audit path.

Passed after the 2026-06-19 Command Center GA4 metric-fact fallback:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or command_center_uses_ga4_metric_facts_without_ga4_tactical_items'
uv run pytest tests/test_api_contracts.py -q -k 'command_center'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
```

Result:

- Command Center no longer shows GA4 `landing groups=0` when dimensional GA4
  metric facts exist.
- Live `/api/dashboard/command-center` and
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` expose the
  same GA4 daily decision: `landing groups=10`, `blocked`, evidence
  `ev_refresh_refresh_google_analytics_4_681b6bcefc85`, action
  `act_review_ga4_tracking_quality`.
- Focused checks passed: API selected `2 passed`, Command Center API `6
  passed`, dashboard route tests `13 passed`, Playwright dashboard-api `8
  passed`.
- Full `scripts/verify.sh` passed after this slice:
  - backend API contracts: `108 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed;
  - non-blocking warning: Vite main chunk is `525.96 kB`, above the 500 KB
    warning threshold.

Passed after the 2026-06-19 Ads scoped context-pack compaction:

```bash
uv run ruff check apps/api/wilq_api/main.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py
uv run pytest tests/test_api_contracts.py -q -k 'codex_context_pack_scopes_ads_doctor_payload or codex_context_pack_scopes_content_strategist_payload or codex_context_pack_full_context_keeps_diagnostic_surfaces or list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan'
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Result:

- Scoped `wilq-ads-doctor` context-pack keeps Ads evidence/action traceability
  but removes nested metric-fact dumps from the Codex runtime packet.
- Runtime measurement on local `:8000` after keyword-context compaction:
  `198513 bytes`, cold `1.281-1.620s`, warm `0.145-0.159s`.
- The full Ads detail endpoint remains `/api/ads/diagnostics`; the cache must
  not be treated as source truth.
- Full `scripts/verify.sh` passed after this slice:
  - backend API contracts: `107 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed;
  - non-blocking warning: Vite main chunk is `525.96 kB`, above the 500 KB
    warning threshold.

Passed after the 2026-06-19 GA4 blocked-copy correction and manual
`wilq-ads-doctor` usefulness proof:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief'
pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-demo-proof.spec.ts --workers=1
scripts/verify.sh
```

Result:

- Live `/api/dashboard/command-center` now exposes
  `decision_review_ga4_landing_quality` as `blocked`, with title
  `GA4: brak danych do oceny ruchu` and copy that frames `/ga4` as a missing
  contract diagnostic, not a ready performance recommendation.
- Manual `wilq-ads-doctor` proof is recorded in
  `docs/evals/skill-eval-ledger.md`: 18 campaigns, 50 search-term rows,
  Google Ads evidence IDs, valid prepare-only ActionObjects and blocked
  waste/profitability/apply claims.
- Focused checks passed: ruff, mypy, selected backend contract test and
  targeted Playwright demo proof.
- Full gate passed: backend API contracts `106 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed`, API smoke, skill structure smoke,
  skill API smoke and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk remains above 500 KB.

Passed after the 2026-06-19 `wilq-ga4-analyst` decision_queue repair:

```bash
uv run ruff check wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ga4_diagnostics or route_specific'
uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-ga4-analyst --api-base http://127.0.0.1:8000
scripts/verify.sh
```

Result:

- API runtime proof: `live_data_available=true`, `landing_group_count=10`,
  `decision_count=6`.
- Deterministic smoke: passed with `act_review_ga4_tracking_quality`, GA4
  evidence IDs and supported decision types.
- Non-interactive Codex eval: passed at
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
- Narrow backend checks: ruff passed, mypy passed, focused pytest `3 passed`.
- Full gate: backend API contracts `100 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed` and dashboard production build passed.

Passed after the 2026-06-19 Ads derived KPI + conservative GA4 Command Center
status slice:

```bash
uv run ruff check wilq/schemas.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or ads_diagnostics_exposes_live_campaign_metric_facts'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
scripts/verify.sh
```

Result:

- Command Center GA4 remains `blocked` when live behavior facts exist but
  ROAS/revenue/conversion-drop/tracking-fixed interpretation contracts are
  missing.
- `/api/ads/diagnostics.derived_kpi_read_contract` exposes CTR/CPC/conversion
  rate/CPA/ROAS/value per conversion as calculated read-only KPI rows with
  evidence IDs and blocked profitability/waste/budget/apply claims.
- Live runtime proof on `:8000`: derived KPI status `ready`, `kpi_rows=18`,
  decision `ads_review_derived_kpis`.
- Full gate: backend API contracts `106 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed`, API smoke, skill structure smoke,
  skill API smoke and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk remains above 500 KB.

Passed after the 2026-06-19 `/ads-doctor` decision route cleanup:

```bash
uv run ruff check wilq/briefing/ads_diagnostics.py wilq/schemas.py tests/test_api_contracts.py
uv run mypy wilq/briefing/ads_diagnostics.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py -q -k 'ads_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
scripts/verify.sh
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/ads-doctor` has decisions for campaign review,
  search-term review and blocked write path, with no visible stale
  `Read contract Ads`, `Search terms read-only`, `Campaign activity read contract`,
  `Search terms read contract`, `Google Ads: campaign activity rows`,
  `Google Ads: search terms read-only rows`, `Evidence`, `configured`, `READY`,
  `payload preview`, `write/apply` or stale read-only evidence copy.
- Full `scripts/verify.sh`: passed with backend API contracts `98 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed` and dashboard
  production build passed.

Passed after the 2026-06-19 `/merchant` operator cleanup:

```bash
uv run ruff check wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/briefing/merchant_diagnostics.py
uv run pytest tests/test_api_contracts.py -q -k 'merchant_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
scripts/verify.sh
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/merchant` has no visible `payload preview`,
  `review queue`, `read-only`, `feed/product`, `configured`, `Evidence`,
  `Feed Safety Gate`, `ActionObject focus`, duplicate old Merchant diagnostic headings,
  `automatic feed edit`, `approval restored`, `sample product IDs` or `READY`.
- Full `scripts/verify.sh`: passed with backend API contracts `98 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed` and dashboard
  production build passed.

Passed after the 2026-06-19 `/actions` + `/opportunities` cleanup:

```bash
uv run ruff check wilq/opportunities/engine.py wilq/actions/service.py tests/test_api_contracts.py
uv run mypy wilq/opportunities/engine.py wilq/actions/service.py
uv run pytest tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts -q
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/actions` has no generic registry dump or stale Ads
  OAuth repair action; `/opportunities` has no old readiness/English blocker
  phrases.
- Full `scripts/verify.sh`: passed after this slice with backend API contracts
  `98 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
  and dashboard production build passed.

Already passed after the current stale-state cleanup started:

```bash
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run ruff check wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
uv run mypy wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts tests/test_api_contracts.py::test_google_ads_oauth_repair_action_is_explicit_and_redacted -q
```

Result:

- Dashboard typecheck: passed.
- Dashboard route tests: 12 passed.
- Backend ruff: passed.
- Backend mypy: passed.
- Focused backend API tests: 3 passed.
- Current-code sanity check: `daily_ads_status` is ready/live, Ads action plan
  is live review, Ads demo step is live campaign metrics, and active Ads repair
  action is filtered out when latest Ads refresh has live data.

Full `scripts/verify.sh` passed after the current cleanup:

```text
backend API contracts: 93 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Latest content decision queue verification:

- Focused ruff, mypy and API contract tests passed for
  `content_diagnostics.decision_queue`, redaction and skill smoke updates.
- Full `scripts/verify.sh` passed after adding clean-runtime core prepare
  ActionObjects and stabilizing `wilq-content-strategist` smoke.
- Clean runtime rule: core daily prepare ActionObjects may exist with connector
  evidence only, but content `decision_queue` must remain empty until real
  GSC/GA4/WordPress metric facts exist. Live runtime still requires concrete
  `inventory_check_before_create`, `merge_create_after_inventory_check` and
  `block_as_tracking_not_content` decisions.

Latest focused backend slice:

- Social draft ActionObjects remain available in `/api/actions` and explicit
  `wilq-social-publisher` context-pack.
- `GET /api/marketing/brief` top-level `action_ids` now contains only core
  daily actions:
  `act_review_merchant_feed_issues`,
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`.
- `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now exposes
  only those core daily `active_action_objects`.
- Proof:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py
  uv run pytest tests/test_api_contracts.py -q -k 'marketing_brief_exposes_metric_backed_prepare_actions or codex_context_pack_embeds_marketing_brief_contract or daily_context_pack_excludes_social_draft_action_objects or social_context_pack_keeps_explicit_social_draft_action_objects or command_center_exposes_polish_operator_brief'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
  ```

Latest Command Center cleanup:

- Localo is configured and access-ready, not an active OAuth/access blocker.
- Because WILQ still lacks concrete Localo ranking/GBP/competitor facts,
  access-ready Localo is no longer shown as a primary Command Center
  `operator_brief` card or action-plan item.
- Localo still appears as a primary Command Center card only when access is
  genuinely missing, because that is an actionable blocker.
- `/localo` and `wilq-localo-operator` remain the right surfaces for Localo
  access/readiness status until a real Localo visibility read contract exists.

Latest Marketing Brief cleanup:

- `GET /api/marketing/brief` now reads metric facts per connector instead of a
  single global DuckDB limit that was dominated by recent aggregate refreshes.
- Metric cards prefer dimensional business facts before aggregate facts, so the
  brief promotes useful GSC query/page, GA4 landing/source, Merchant issue and
  Ads campaign facts instead of stale-looking aggregates such as
  `active_products=12`, `sessions=30` or `clicks=3`.
- This does not change `/api/actions`; it only improves the evidence selected
  for the daily brief and Codex context.

Latest Command Center Codex bridge cleanup:

- Daily decision cards now visibly expose `Jak Codex może pomóc`, the matching
  `skill_id`, `codex_prompt`, `codex_context_endpoint` and
  `expected_codex_output`.
- The first-screen source footer uses Polish operator wording:
  `Źródła`, `Aktywne`, `Do naprawy`, `Otwórz ustawienia`.
- Focused proof passed:
  ```bash
  pnpm --filter @wilq/dashboard lint
  pnpm --filter @wilq/dashboard typecheck
  pnpm --filter @wilq/dashboard test -- --run App.test.tsx
  WILQ_E2E_API_PORT=<dynamic> WILQ_E2E_DASHBOARD_PORT=<dynamic> CI= pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
  ```

Latest Command Center metric-decision cleanup:

- `DailyDecision` now exposes `metric_tiles` and Command Center renders them
  directly on the first-screen decision cards.
- Runtime proof after API restart:
  - Merchant decision: `produkty=10900`, `typy problemów=15`,
    `zgłoszenia=1887`, `decyzje=8`, `blockery=0`;
  - Content decision: `query/page=10`, `WP match=10`, `decyzje=4`,
    `wyświetlenia=7852`, `kliknięcia=138`;
  - GA4 decision: `grupy ruchu=10`, `decyzje=6`, `pomiar=2`,
    `jakość ruchu=4`, `braki kontraktu=1`;
  - Ads decision: `kampanie=18`, `search terms=50`, `rekomendacje=4`,
    `podgląd budżetu=18`.
- GA4 no longer claims `0 landing/source groups` when tactical queue already
  has landing/source/campaign groups; diagnostics falls back to tactical group
  count when section metric facts are empty.
- Merchant issue cluster IDs include reporting context and resolution, so issue
  clusters do not collide across `all_contexts`, `FREE_LISTINGS` and
  `SHOPPING_ADS`.
- `agent-browser` proof was run with local runtime dir:
  `XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime`.

Latest Ads/Localo stale-state cleanup:

- Live Ads diagnostics no longer overload `blocked_handoff` for "next step"
  messaging. `blocked_handoff` is now only for real access blockers; live Ads
  keeps write/apply limits in `ads_action_safety`, campaign/search-term read
  contracts and blocked claims.
- `wilq-ads-doctor` smoke now accepts both legal API states: live diagnostics
  with no OAuth handoff, or blocked diagnostics with a blocked handoff and
  ActionObject IDs.
- `/localo` no longer renders generic global tactical queue stats when there
  are no Localo tactical items. It keeps Localo access/readiness and blocks
  ranking/GBP/local-visibility claims until a real Localo read contract exists.
- Focused proof passed:
  - `uv run ruff check wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
  - `uv run mypy wilq/briefing/ads_diagnostics.py`
  - `uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q`
  - `pnpm --filter @wilq/dashboard lint`
  - `pnpm --filter @wilq/dashboard typecheck`
  - `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
  - `WILQ_E2E_API_PORT=8875 WILQ_E2E_DASHBOARD_PORT=5373 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts` -> `8 passed`
  - `scripts/verify.sh` -> backend API contracts `98 passed`, dashboard route
    tests `12 passed`, Playwright e2e `8 passed`, dashboard production build
    passed.

Important product note:

- The Codex bridge is necessary but not sufficient. It only connects a dashboard
  decision to a WILQ skill. It is not yet the marketer value by itself.
- The next useful slice must audit the primary dashboard routes
  `/ga4`, `/ads-doctor` and `/localo`, then
  replace technical inventory with real metric-backed decisions.
- Every route should preserve evidence/action traceability while making the
  marketer-facing hierarchy obvious: real metric, diagnosis, safe next action,
  blocked claims and matching Codex skill/prompt.

Latest Localo aggregate value facts slice:

- Done: Localo is no longer only an OAuth/MCP access proof. The Localo connector
  now performs read-only MCP GraphQL `query` calls after initialize and stores
  only aggregate facts. It must not store raw Localo place names, addresses,
  keywords, categories or Localo IDs.
- Live proof: `uv run wilq connectors refresh localo --mode vendor_read
  --reason "Goal 001 Localo aggregate value facts proof"` completed as
  `refresh_localo_9e9ff67eadad` with evidence
  `ev_refresh_refresh_localo_9e9ff67eadad`.
- Live aggregate facts: `localo_active_place_count=4`,
  `localo_tracked_keyword_count=23`,
  `localo_avg_visibility_current=52.8261`,
  `localo_avg_latest_grid_position=3.2105`,
  `localo_reviews_count=793`, `localo_review_reply_rate=0.809584`.
- `/api/localo/diagnostics` now reports `live_data_available=true`,
  `visibility_fact_count=17`, `allowed_evidence=[place_inventory,
  local_rankings, reviews]`, and missing contracts
  `[gbp_visibility, competitor_visibility, local_tasks]`.
- Command Center now promotes Localo only when real facts exist or access is
  genuinely blocked. Current live Localo card tiles:
  `miejsca=4`, `frazy=23`, `widoczność=52.8261`, `recenzje=793`.
- `wilq-localo-operator` context-pack receives the same diagnostics. Redaction
  now preserves long metric names such as
  `localo_latest_grid_position_count`; secret-like values remain redacted.
- Still blocked by design: do not claim `GBP performance`,
  `competitor visibility`, `local task completed`, `GBP write` or
  `local visibility uplift` until separate read/action contracts exist.
- Full proof passed: ruff/mypy on changed backend modules, selected
  Localo/redaction API tests, dashboard route unit tests, live Localo
  vendor_read, live context-pack redaction check and `scripts/verify.sh`.
  Final verify result: backend API contracts `122 passed`, dashboard unit tests
  `14 passed`, Playwright e2e `11 passed`, skill/API smokes and production
  build passed.
