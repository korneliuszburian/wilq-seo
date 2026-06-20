# WILQ Context Index

Ten plik jest indeksem recovery po utracie kontekstu. Nie zastępuje goalu ani
AGENTS.md; wskazuje, gdzie leży aktualna prawda operacyjna.

## Start Here

1. `AGENTS.md` - stałe reguły pracy, sekrety, lokalne ścieżki i gotchas.
2. `docs/goals/001-goal.md` - jedyny aktywny goal i kolejka następnych zadań.
3. `docs/PROGRESS.md` - krótki aktualny stan slice'ów, testów i decyzji.
4. `docs/evals/skill-eval-ledger.md` - przebiegi ręcznych i non-interactive testów skillów.
5. `docs/research/wilq-marketing-source-map.md` - źródła marketingowe i techniczne.
6. `docs/architecture/bdos-class-wilq-operating-system.md` - poprzeczka produktowa.
7. `docs/architecture/codex-runtime.md` - Codex skills, hooks, evals i runtime.
8. `docs/audits/001-output.md` - świeży audyt 2026-06-18: co zatrzymać, co
   zacząć i pięć następnych slice'ów dla marketera.
9. `docs/progress/archive/2026-06-19-progress-ledger.md` - pełny progress
   ledger sprzed kompaktowania, używany tylko gdy potrzebna jest starsza
   historia.

## Current Critical Direction

Audit `docs/audits/001-output.md` is now folded into
`docs/goals/001-goal.md`. The current order is:

0. Progress ledger maintenance rule, 2026-06-19 22:51 Europe/Warsaw:
   `docs/PROGRESS.md` is now a short recovery ledger, not the full historical
   changelog. Keep current state, last 3-5 slices, active gaps and next best
   actions there. Move older detail to `docs/progress/archive/`; the first full
   archive is `docs/progress/archive/2026-06-19-progress-ledger.md`.

0. Ads business context truth, 2026-06-20 10:12 Europe/Warsaw:
   `/api/ads/diagnostics` now exposes `business_context_read_contract` and
   decision `ads_review_business_context`. Live state is intentionally blocked
   until repo-local non-secret targets exist:
   `WILQ_ADS_PROFIT_MARGIN`, `WILQ_ADS_BUSINESS_GOAL`,
   `WILQ_ADS_BUDGET_GOAL` and `WILQ_ADS_TARGET_ROAS` or
   `WILQ_ADS_TARGET_CPA_MICROS`. This is API product state, not skill prompt
   logic. Current proof after stack restart: blocker_count=2,
   `ads_review_business_context.priority=22`, context-pack bytes for
   `wilq-ads-doctor` = 186844.

0. Ads recommendation apply-preview truth, 2026-06-20 00:20 Europe/Warsaw:
   Google Ads recommendation review now has a typed review-only apply payload
   preview in `/api/ads/diagnostics`, `/api/actions`,
   dashboard `/ads-doctor` and scoped `wilq-ads-doctor` context-pack. Live
   proof `refresh_google_ads_60956db2c42f` /
   `ev_refresh_refresh_google_ads_60956db2c42f` returned 4 active
   recommendations, 2 impact-preview rows and 4 apply payload preview rows.
   `/api/ads/diagnostics.recommendations_read_contract.status=ready`,
   `missing_read_contracts=["human_strategy_review"]`, and
   `action_ids=["act_prepare_google_ads_recommendation_review_queue"]`.
   The ActionObject payload uses
   `preview_contract="recommendation_apply_preview_v1"` and
   `operation_type=ApplyRecommendationOperation`, but keeps
   `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`.
   Do not call this apply support; it is a review queue and safety preview.
   Full `scripts/verify.sh` passed after this slice: backend `115 passed`,
   dashboard unit `13 passed`, Playwright e2e `9 passed`, security checks,
   skill/API smokes and dashboard production build passed. The security gate
   also required `uv.lock` update `msgpack 1.2.0 -> 1.2.1`.

0. Ads account-currency truth, 2026-06-19 23:12 Europe/Warsaw:
   Google Ads campaign read now includes `customer.currency_code` and persists
   a read-only `account_currency_code` fact. Live proof
   `refresh_google_ads_26cb4673eee2` /
   `ev_refresh_refresh_google_ads_26cb4673eee2` returned
   `customer_currency_code=PLN`, 18 campaign rows, 50 30-day search-term rows,
   200 90-day safety rows, 211 keyword context rows and 4 active
   recommendations. `/api/ads/diagnostics.account_currency_read_contract` is
   `ready` with `currency_code=PLN`, and derived KPI missing contracts no
   longer include `account_currency`. Dashboard `/ads-doctor` formats Ads costs
   in PLN across campaign, KPI, budget, search-term and negative-keyword review
   surfaces. Full `scripts/verify.sh` passed: backend API contracts
   `115 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
   and dashboard production build passed. This is still not profitability
   proof: profit margin, business goal, recommendation apply support and human
   confirmation remain blocked.

0. Ads recommendation impact truth, 2026-06-19 23:44 Europe/Warsaw:
   Google Ads recommendation read now includes `recommendation.impact` and
   persists read-only `recommendation_impact_{base|potential}_*` metric facts.
   Live proof `refresh_google_ads_978ef3a667f6` /
   `ev_refresh_refresh_google_ads_978ef3a667f6` returned 4 active
   recommendations and `recommendation_impact_row_count=2` with
   `recommendation_impact_metric_count=8`.
   `/api/ads/diagnostics.recommendations_read_contract.status=ready`; missing
   contracts after the newer apply-preview slice are now only
   `human_strategy_review`.
   The scoped `wilq-ads-doctor` context-pack exposes the same impact rows:
   `IMPROVE_PERFORMANCE_MAX_AD_STRENGTH` has `delta_cost_micros=4377640`, and
   `SEARCH_PARTNERS_OPT_IN` has zero click/impression/cost deltas in current
   evidence. Some recommendation types legitimately return no impact metrics;
   treat that as per-row `missing_metrics=["recommendation_impact"]`, not a
   global API blocker. This is still review-only: recommendation apply,
   automatic accept, budget apply, campaign mutation and performance-uplift
   claims remain blocked. Full `scripts/verify.sh` passed after this slice:
   backend API contracts `115 passed`, dashboard route tests `13 passed`,
   Playwright e2e `9 passed`, skill/API smokes and dashboard production build
   passed.

0. Local runtime stability rule, 2026-06-19 15:12 Europe/Warsaw: use
   `scripts/local_stack.sh start|stop|restart|status|logs` for the normal local
   WILQ API/dashboard stack. It owns `.local-lab/runtime/{api,dashboard}.pid`
   and logs, reports unmanaged port owners, and keeps canonical URLs
   `http://127.0.0.1:8000/api/health` and
   `http://127.0.0.1:5173/command-center`. Do not hand-roll `nohup`, `setsid`,
   detached `uvicorn`, detached Vite or ad hoc `kill` loops for these ports.
0. Source-to-product lineage rule, 2026-06-19 16:47 Europe/Warsaw: do not fix
   Ads/marketing reasoning by stuffing more edge cases into skill references.
   Current Ads budget review proof lives in typed product state:
   `google_ads_budget_review_playbook` ->
   `card_google_ads_budget_review_playbook` ->
   `/api/ads/diagnostics.ads_review_budget_context` with
   `knowledge_card_ids` and `expert_rule_ids` ->
   dashboard `/ads-doctor` trace lines ->
   `wilq-ads-doctor` scoped context-pack. Redaction must preserve
   `knowledge_card_ids` and `expert_rule_ids`, just like evidence/action IDs.
   Non-interactive proof passed at
   `.local-lab/evals/codex-skill/20260619T144600Z/wilq-ads-doctor/result.json`.
   The first strengthened eval failed because the smoke output did not expose
   lineage IDs; the fix was to make the deterministic smoke script emit the
   typed API lineage, not to make the skill invent it.
0. Runtime truth gotcha, 2026-06-19 16:47 Europe/Warsaw: if live API output
   contradicts source/tests, restart with `scripts/local_stack.sh restart`
   before debugging product logic. The Ads lineage proof initially looked broken
   because the managed API child was stale; after restart,
   `/api/ads/diagnostics` and the scoped context-pack exposed the expected
   `knowledge_card_ids` and `expert_rule_ids`.
0. DailyRuntime performance truth, 2026-06-19 21:13 Europe/Warsaw: the current
   cold-path fix is shared backend work, not frontend memoization. Profiling
   showed repeated wide DuckDB metric fact materialization and duplicate Ads
   action seeding. `build_daily_runtime()` now parallelizes independent daily
   inputs; Command Center passes preloaded ActionObjects into
   `build_ads_diagnostics(actions=...)`; Marketing Brief reads 200 latest metric
   groups per connector, which preserves live dimensional Merchant, GA4, GSC,
   WordPress and Ads facts. Current proof after restart:
   `/api/dashboard/command-center` after TTL is about `1.45-1.51s`,
   `/api/marketing/brief` after TTL is about `1.42-1.50s`, and daily
   `wilq-daily-command` context-pack after TTL is about `1.67-1.76s`. Remaining
   gaps are dashboard JS chunk size and daily context-pack payload size.
0. Daily context-pack payload truth, 2026-06-19 21:32 Europe/Warsaw: default
   `wilq-daily-command` context-pack is intentionally compact. It keeps
   `operator_brief`, `action_plan`, `daily_decisions`, evidence IDs, source
   connectors and core ActionObject IDs, but compacts Marketing Brief metric
   facts, compacts active ActionObjects and omits Command Center
   `connector_health`; full detail stays in `full_context=true` and the API
   endpoints. Current proof: default daily context-pack is `120436 bytes`
   instead of the previous `235159 bytes`, and non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260619T193056Z/wilq-daily-command/result.json`.
   Localo is not a required daily source connector while WILQ lacks Localo
   ranking/GBP evidence.
0. Dashboard bundle truth, 2026-06-19 21:44 Europe/Warsaw: the main Vite JS
   chunk warning was fixed by Rollup manual chunks, not by raising
   `chunkSizeWarningLimit`. Current production build chunks are below 500 KB:
   app `142.44 kB`, `vendor-react` `192.70 kB`, `vendor-tanstack`
   `126.96 kB`, `vendor-schemas` `76.67 kB`, `vendor-icons` `7.91 kB`,
   `vendor-misc` `2.16 kB`. Preserve this split unless a better measured
   lazy-route split replaces it.
0. Non-daily context-pack scope truth, 2026-06-19 22:45 Europe/Warsaw:
   default skill packs must carry decision context, evidence IDs, ActionObject
   IDs and enough examples for the matching workflow, not whole diagnostic
   registries. Current live proof after restart: `wilq-campaign-builder`
   `90711 bytes` with `ads_diagnostics` plus lightweight
   `content_landing_context`; `wilq-demand-gen-operator` `100349 bytes` with
   Ads + GA4 only; `wilq-content-strategist` `91731 bytes`;
   `wilq-ga4-analyst` `28578 bytes`; `wilq-merchant-feed-operator`
   `24007 bytes`; `wilq-ads-doctor` `185126 bytes`;
   `wilq-custom-segments` `187121 bytes`; `wilq-daily-command`
   `120504 bytes`. Full diagnostics remain available through `full_context=true`
   and dedicated API endpoints. Remaining performance gap: Demand Gen cold
   request is about `2.6s`, while warm cache hits are about `0.15s`. Full
   `scripts/verify.sh` passed after this slice with API smoke, skill smokes,
   dashboard route tests, Playwright e2e `9 passed` and dashboard production
   build.
0. Custom segments payload-preview truth, 2026-06-19 22:08 Europe/Warsaw:
   custom segments now have a typed review-only payload preview in
   `/api/ads/diagnostics`, `/api/actions/act_prepare_custom_segments_from_search_terms`
   and `/ads-doctor`. This is not apply support. Keep
   `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false` until
   Keyword Planner enrichment, forecast/audience-size, human confirmation and
   Ads apply/audit contracts exist. Default `wilq-custom-segments`
   context-pack is scoped to Ads diagnostics, omits `content_diagnostics` and
   measures about `186317 bytes`. Latest eval artifact:
   `.local-lab/evals/codex-skill/20260619T201200Z/wilq-custom-segments/result.json`.
0. Ads recommendations truth, 2026-06-19 17:22 Europe/Warsaw: Google Ads
   recommendation review is now a typed read-only contract, not a prompt TODO.
   Live proof `refresh_google_ads_138befce0a2c` /
   `ev_refresh_refresh_google_ads_138befce0a2c` returned 4 active
   recommendations: `DISPLAY_EXPANSION_OPT_IN`,
   `DYNAMIC_IMAGE_EXTENSION_OPT_IN`,
   `IMPROVE_PERFORMANCE_MAX_AD_STRENGTH`, `SEARCH_PARTNERS_OPT_IN`.
   `/api/ads/diagnostics.recommendations_read_contract.status=ready`, decision
   queue includes `ads_review_recommendations`, and scoped
   `wilq-ads-doctor` context-pack exposes the same contract. Historical note:
   at this point impact preview was still missing; see the newer 2026-06-19
   23:44 entry above for the current impact-read truth. Do not call
   recommendations apply-ready until human review and recommendation apply
   preview exist.
0. Ads impression-share truth, 2026-06-19 17:55 Europe/Warsaw: Google Ads
   impression share is now a typed read-only contract, not a missing Ads
   optimizer blocker. Live proof `refresh_google_ads_baba7f993f1a` /
   `ev_refresh_refresh_google_ads_baba7f993f1a` returned
   `impression_share_row_count=2`. `/api/ads/diagnostics` exposes
   `impression_share_read_contract.status=ready` and decision
   `ads_review_impression_share`; scoped `wilq-ads-doctor` context-pack exposes
   the same contract. Current live rows: `Kompendium PPWR` has search IS
   `0.2322`, budget-lost IS `0.5924`, rank-lost IS `0.1754`; `(2026) Ekologus
   Ogólna` has search IS `0.1819`, budget-lost IS `0.0075`, rank-lost IS
   `0.8106`. Do not call this budget scaling or wasted-budget proof: change
   history, human budget goal and budget apply preview remain missing.
0. Ads change-history truth, 2026-06-19 18:19 Europe/Warsaw: Google Ads
   change history is now a typed read-only contract. Live proof
   `refresh_google_ads_e7f371e9efac` /
   `ev_refresh_refresh_google_ads_e7f371e9efac` returned
   `change_event_row_count=0`; `/api/ads/diagnostics` exposes
   `change_history_read_contract.status=ready`, decision
   `ads_review_change_history`, and section `ads_change_history`. This means
   WILQ successfully queried `change_event` for the last 14 days and found no
   events. It is not change-impact proof. Keep `change impact`,
   `performance uplift`, `budget scaling`, `budget apply` and
   `campaign mutation` blocked until pre/post performance windows, human review
   and apply preview exist. Non-interactive `wilq-ads-doctor` eval passed at
   `.local-lab/evals/codex-skill/20260619T162014Z/wilq-ads-doctor/result.json`.
0. Ads 90-day search-term safety truth, 2026-06-19 18:57 Europe/Warsaw:
   Google Ads negative keyword review now has a typed 90-day safety read.
   Live proof `refresh_google_ads_5a0c672b5000` /
   `ev_refresh_refresh_google_ads_5a0c672b5000` returned 50 30-day
   search-term rows and 200 90-day `search_term_90d_*` rows.
   `/api/ads/diagnostics.search_term_safety_read_contract.status=ready`, the
   decision queue includes `ads_review_search_term_safety`, and
   `negative_keywords_read_contract` has 7 review-only candidates without
   `90_day_safety_check` as a missing contract. Do not call this apply-ready:
   `negative keyword apply`, `search-term waste`, CPA, ROAS and
   conversion-loss claims remain blocked until keyword match context, payload
   preview, ActionObject validation and human review exist. Gotcha: Ads
   diagnostics and action generation must use a large enough Google Ads metric
   fact window, otherwise 200 safety rows can push 30-day search-term facts out
   of view. Non-interactive `wilq-ads-doctor` eval passed at
   `.local-lab/evals/codex-skill/20260619T165729Z/wilq-ads-doctor/result.json`.
0. Ads keyword match context truth, 2026-06-19 20:17 Europe/Warsaw:
   Google Ads negative keyword review now has typed read-only context for
   existing account keywords and match types. Live proof
   `refresh_google_ads_eb8c239bc32b` /
   `ev_refresh_refresh_google_ads_eb8c239bc32b` returned 211
   `keyword_match_context` rows from `ad_group_criterion`. `/api/ads/diagnostics`
   exposes `keyword_match_context_read_contract.status=ready` with only
   `human_intent_review` missing. `negative_keywords_read_contract` now has 7
   candidates, 7 payload preview rows and `missing_read_contracts=[]`. This is
   still not apply-ready: negative keyword apply, search-term waste,
   conversion loss, CPA and ROAS stay blocked until human review/confirmation
   and future apply/audit contracts exist. Non-interactive
   `wilq-ads-doctor` eval passed at
   `.local-lab/evals/codex-skill/20260619T182309Z/wilq-ads-doctor/result.json`
   after the eval case was tightened to require
   `keyword_match_context_read_contract` and forbid stale `bez match context`
   wording.
0. Recovery truth, 2026-06-19 14:53 Europe/Warsaw: connector summary is
   `total=12`, `configured=9`, `missing_credentials=2`, `disabled=1`.
   `google_sheets` is intentionally disabled for this Ekologus scope.
   `linkedin` and `facebook` are missing credential surfaces; they block
   publishing, not prepare-only evidence-backed drafting. The knowledge layer
   is explicitly in the active goal, but it is not fully proven: future slices
   must connect source-backed marketing standards/papers/practitioner sources
   to knowledge cards or expert rules, then to typed WILQ API view-models,
   dashboard decisions and non-interactive Codex skill outputs.
0. Overnight recovery truth, 2026-06-19 09:37 Europe/Warsaw: after
   `3a7d4ab test(skills): prove localo access-ready blocker`, the next Merchant
   slice fixed issue-cluster preservation. `MERCHANT_METRIC_FACT_LIMIT` was too
   low and live issue-level facts were truncated out of
   `/api/merchant/diagnostics`. Fresh proof on temporary API `:8015` showed
   `issue_cluster_count=11`, and non-interactive eval passed:
   `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`.
   Final proof for this Merchant fix: `scripts/verify.sh` passed with backend
   API contracts `102 passed`, dashboard route tests `13 passed`, Playwright
   e2e `9 passed`, skill API smoke passed and dashboard build passed.
   Temporary API/e2e ports were cleaned up after verification.
1. Command Center first-screen cleanup is implemented and verified: one
   `Dzisiejsze decyzje marketera` board, no duplicated `Plan działań marketera`
   and no full connector blocker cards on `/command-center`.
2. Ads campaign/search-term/budget/recommendation/impression-share read contracts are
   implemented with conversion counts/value, read-only budget context and
   read-only recommendation/impression-share review. Latest local work adds
   `impression_share_read_contract.status=ready`, 2 impression-share rows from
   `refresh_google_ads_baba7f993f1a`, and decision
   `ads_review_impression_share`. This is still not budget/waste/apply.
   Continue with change history, keyword/match context, full 90-day safety,
   human budget goals, recommendation apply support/audit and
   value/account-currency semantics before any money-leak/CPA/ROAS/budget
   scaling/negative-keyword apply claims. Full `scripts/verify.sh` passed for
   this slice with backend `108 passed`, dashboard unit `13 passed`,
   Playwright e2e `9 passed`, skill smokes and dashboard production build.
3. Repair each skill only after the matching API/read contract exists.

Recently completed and pushed foundations:

- `2e0b0dc feat(content): expose content decision queue`
- `39511ac feat(command-center): add daily decision model`
- `8cfdf83 perf(codex): scope daily command context pack`
- `de09cab perf(api): batch metric fact reads`
- `ad17223 perf(api): slim command center runtime`

Current performance slice truth:

- `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now defaults
  to `context_scope.mode=daily`.
- Default daily context excludes full tactical queue and diagnostics. Use
  `{"skill":"wilq-daily-command","full_context":true}` for debug/full mode.
- Latest fresh `:8011` proof after the local patch:
  - daily context-pack: about `2.9s`, `160053 bytes`;
  - full daily context-pack: about `6.5s`, `998704 bytes`;
  - marketing brief: about `0.5s`, `46072 bytes`;
  - command-center: about `2.1-2.4s`, `30521 bytes`.
- Current follow-up adds a shared `DailyRuntime` view-model for
  daily Codex context. It builds `command_center`, `marketing_brief` and core
  actions from one connector/action/refresh snapshot and caches that runtime
  for a short operator TTL. The default TTL is now 30 seconds and is still
  invalidated after connector refresh and action validation/apply paths. Fresh
  helper API proof on `:8011`: cold daily context
  `3.047s`, then warm cached daily context `0.467s`, `0.544s`, `0.470s`, same
  payload size `160478 bytes`.
- This is improved from the old full context-pack (`~996 KB`, `~15s`) but not
  done. Batch DuckDB reads and read-only metric-store connections fixed a
  conflicting-lock runtime risk. Remaining cold-run bottleneck: diagnostics
  inside Command Center, especially the tactical/diagnostic joins used before
  Merchant issue-level triage and URL normalization are fully shaped.
- 2026-06-19 follow-up pushed as `ad17223`: Command Center first-screen cards now reuse
  preloaded `tactical_queue`/`actions`; Content/GA4 cards no longer build full
  diagnostics; Merchant card reads `google_merchant_center` metric facts
  directly instead of full Merchant Diagnostics. Direct cold proof improved to
  `build_command_center_response() ~=1.7-2.1s` and
  `build_daily_runtime() ~=2.1s`; HTTP proof on fresh `:8016` showed cold
  Command Center `2.526s` and warm TTL `0.011-0.012s`. Daily context-pack can
  still spike after TTL (`3.451s` observed), so this is not final performance
  completion.
- Active 2026-06-19 follow-up after `ad17223`: daily context-pack now reuses
  `DailyRuntime.refresh_runs` and targeted `list_evidence_by_ids()` instead of
  scanning the full evidence registry. Local `:8000` proof: daily context-pack
  after TTL `2.548s`, warm `0.273-0.324s`, size `171000 bytes`; Command Center
  after TTL `2.009s`, warm `0.008s`, size `26629 bytes`. This improves the
  context-pack TTL spike, but full performance is not done.
- Active 2026-06-19 Ads skill follow-up after keyword context: scoped
  `wilq-ads-doctor` context-pack now removes `*_metric_facts`, keeps full
  detail available at `/api/ads/diagnostics`, limits embedded Ads sample rows
  for skill runtime, strips duplicated nested candidate `payload_preview`,
  trims ActionObject payload row arrays while preserving totals, limits scoped
  connector refresh runs to 3, and uses a short 5s API-side context cache. The
  cache is only a compute shortcut; it is cleared after connector refresh,
  ActionObject validation and apply. Local `:8000` proof: Ads context-pack
  `198513 bytes`, cold `1.281-1.620s`, warm `0.145-0.159s`; full totals remain
  in `context_pack_compaction` with embedded samples
  `search_term_rows_included=8`, `search_term_safety_rows_included=8`,
  `keyword_match_context_rows_included=8` and
  `negative_keyword_candidates_included=4`. Non-interactive
  `wilq-ads-doctor` eval passed at
  `.local-lab/evals/codex-skill/20260619T184940Z/wilq-ads-doctor/result.json`.
  Remaining performance gaps: Command Center cold path is still about `2.2s`,
  daily context-pack is about `237939 bytes`, and dashboard JS chunk is still
  above Vite's 500 KB warning.
- Active 2026-06-19 Command Center GA4 fallback: `/api/ga4/diagnostics`
  had live GA4 dimensional facts (`landing_group_count=10`), but Command
  Center could show `landing groups=0` because it only counted GA4 tactical
  queue items. Command Center now reads a lightweight GA4 metric-fact fallback
  directly and keeps GA4 as `blocked` for missing interpretation contracts.
  Live `:8000` proof after restart: GA4 daily decision title
  `GA4: brak pełnego kontraktu interpretacji ruchu`, metric tiles
  `landing groups=10`, `low engagement=0`, `WP match=0`, `blockery=1`,
  evidence `ev_refresh_refresh_google_analytics_4_681b6bcefc85`, action
  `act_review_ga4_tracking_quality`. Targeted Playwright dashboard-api spec
  passed `8 passed` on `:8000/:5173`.
- Active 2026-06-19 Ads campaign review ActionObject:
  `act_prepare_ads_campaign_review_queue` is implemented with payload type
  `campaign_change_review`. It is generated from live `google_ads` campaign
  metric facts, exposes up to 8 campaign candidates, includes budget context
  when available, and now also has read-only recommendations and
  impression-share contracts. It still requires change history, value/currency
  review, budget/apply preview and human confirmation before any apply path. It
  keeps `apply_allowed=false` plus `destructive=false`. Live `:8000` proof
  after restart: Ads diagnostics includes the new action ID, campaign and
  derived KPI decisions attach only this campaign action, and validation
  returns `valid=true`. This closes the first campaign ActionObject gap, not
  the full Ads optimizer. Full `scripts/verify.sh` passed for this slice with
  backend API contracts `108 passed`, dashboard route tests `13 passed`,
  Playwright e2e `9 passed` and dashboard production build passed.

Current Ads negative-keyword safety truth:

- `negative_keyword_payload_preview` and `keyword_match_context` are now
  implemented as review-only contracts, not apply contracts. Live
  `/api/ads/diagnostics` shows
  `negative_keywords_read_contract.payload_preview` with 7 items and
  `missing_read_contracts=[]`; the keyword context contract is ready with 211
  rows and only `human_intent_review` missing.
- `act_prepare_negative_keyword_review_queue.payload` includes
  `preview_contract=negative_keyword_payload_preview_v1`,
  `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false` and
  exact-match preview rows with evidence IDs.
- Do not describe these rows as ready negative keywords. They are a review
  preview for the marketer. Still blocked: negative keyword apply,
  search-term waste, conversion loss, CPA and ROAS until human review,
  confirmation, apply/audit contracts and stronger intent validation exist.
  Full `scripts/verify.sh` passed after the newest keyword-context slice with
  backend API contracts `111 passed`, dashboard route tests `13 passed`,
  Playwright e2e `9 passed`, API smoke, skill smokes and dashboard production
  build passed. Non-blocking warning: Vite main JS chunk `549.44 kB` exceeds
  the 500 KB warning threshold.

Current hook-runtime truth:

- If WILQ API is unreachable, SessionStart may report that as context. It is
  not a product blocker by itself.
- Stop hook must not print plain text on stdout. `.codex/hooks/stop_log.py`
  emits valid JSON with `continue=true` for unreachable API or unsupported API
  URL skip paths.
- `.codex/hooks.json` must use `uv run python` from repo root for hooks; do not
  reintroduce global `python3`.

Current Merchant slice truth:

- `MerchantIssueCluster` is implemented in Python and shared frontend schemas.
- `/api/merchant/diagnostics` returns `issue_clusters` grouped by issue type,
  affected attribute, country, reporting context, severity and resolution.
- `act_review_merchant_feed_issues` includes issue clusters in its payload.
- Dashboard `/merchant` renders issue clusters as the primary review queue.
- Full `scripts/verify.sh` passed for this slice on 2026-06-18.
- Current Merchant read contract still exposes aggregate issue dimensions and
  counts only; no sample product IDs/titles yet.
- Active WIP on 2026-06-19: if live Merchant diagnostics reports
  `issue_count > 0`, the smoke script must require `issue_clusters`. This guards
  against a regression where DuckDB metric fact row limits hide issue-level
  rows while aggregate Merchant facts remain visible.
- Fresh Merchant skill proof: `wilq-merchant-feed-operator` passed
  non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`.
  It reports `product_count=10900`, `issue_count=15`,
  `issue_cluster_count=11`, recommends `act_review_merchant_feed_issues`, and
  blocks automatic feed edit/product mutation claims.
- Dashboard demo proof now asserts the Merchant issue-cluster view
  (`Zgłoszenia` plus issue types such as
  `missing_potentially_required_attribute` / `availability_updated`) instead of
  the old stale `Merchant: status produktów PL` copy.

Current content URL normalization truth:

- Tactical queue reads enough WordPress inventory rows from DuckDB to keep large
  sitemap inventories in the WordPress index.
- GSC full URLs and GA4 landing paths are normalized to stable path keys.
- `ContentDecisionItem` now exposes `normalized_page_path`,
  `wordpress_match_confidence` and `wordpress_content_url`.
- Context-pack redaction preserves these public URL/path fields while still
  redacting token-like secret values.
- Direct checkout proof shows BDO, Zielony Ład and remediacja GSC URLs as
  `found exact_url`; GA4 landing paths resolve with `path_fallback`.
- Full `scripts/verify.sh` passed for this slice on 2026-06-18.

Current Command Center cleanup truth:

- `/command-center` renders `daily_decisions` as the single marketer decision
  board.
- The old summary/plan duplication is removed from the first screen.
- Full connector blocker/status cards are no longer rendered on
  `/command-center`; the compact `Źródła i ograniczenia` footer links to
  `/settings`.
- Focused frontend/backend checks and full `scripts/verify.sh` passed on
  2026-06-18 after the cleanup.

Current Ads Doctor contract truth:

- `/api/ads/diagnostics.campaign_read_contract` is typed and rendered on
  `/ads-doctor`.
- It groups live Google Ads metric facts into campaign rows with campaign ID,
  campaign name, clicks, impressions, cost micros, conversions, conversion
  value, evidence IDs and blocked claims.
- It explicitly limits allowed metrics to `clicks`, `impressions`,
  `cost_micros`, `conversions` and `conversion_value`.
- `/api/ads/diagnostics.search_terms_read_contract` is typed and rendered on
  `/ads-doctor`.
- Google Ads `vendor_read` now queries `search_term_view` read-only and stores
  `search_term_clicks`, `search_term_impressions` and
  `search_term_cost_micros`, `search_term_conversions` and
  `search_term_conversion_value` with campaign, ad group, search term and
  status dimensions.
- Search terms rows are for read-only review. Latest work adds
  `/api/ads/diagnostics.negative_keywords_read_contract` and
  `act_prepare_negative_keyword_review_queue` for prepare-only safety review of
  zero-conversion search terms with activity. Do not claim search-term waste,
  CPA, ROAS, conversion loss or negative keyword apply until keyword/match
  context, full 90-day safety, derived KPI semantics and validated preview/apply
  contracts exist.
- Live proof on 2026-06-18:
  `refresh_google_ads_c2f62ee2b43a` completed with 18 campaign rows, 50 search
  term rows, `conversions=2.0`, `conversion_value=2.0`,
  `search_term_conversions=0.0` and
  `search_term_conversion_value=0.0`.
- Still missing read contracts: recommendations, change history, impression
  share, keyword/match context, full 90-day safety history, payload previews for
  apply paths, human budget goals and explicit profitability/account-currency
  interpretation.

Do not repair product logic inside skill references. If a skill needs a better
decision, add the typed WILQ API/schema/view-model field first and make the
skill consume it.

## Current Runtime

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:5173/command-center`
- API health: `curl -sf http://127.0.0.1:8000/api/health`
- Final gate: `scripts/verify.sh`

## Latest Localo Skill Proof

- `wilq-localo-operator` passed non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260619T072709Z/wilq-localo-operator/result.json`.
- Localo access is ready: `localo_access_status=access_ready`,
  `localo_refresh_status=completed`, `mcp_initialize_status=200`.
- The skill correctly blocks ranking, GBP, competitor and local visibility
  uplift claims because WILQ has no Localo visibility facts beyond MCP/OAuth
  access probe.
- There is no Localo write/apply path yet: `action_ids=[]`.

## Skill Eval Harness

Istniejący harness non-interactive:

```bash
scripts/codex_skill_eval.sh --all --api-base http://127.0.0.1:8000
scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000
```

Ważne pliki:

- `scripts/codex_skill_eval.sh`
- `docs/evals/cases/wilq-skill-eval-cases.json`
- `docs/evals/schemas/wilq-skill-eval-result.schema.json`
- `.agents/skills/*/scripts/smoke_*`

Harness sprawdza schema, język PL, API usage, evidence/source connectors i
ActionObject safety. Nie zastępuje ręcznej oceny użyteczności odpowiedzi dla
marketera; tę ocenę zapisujemy w `docs/evals/skill-eval-ledger.md`.

## Skill Eval Pipeline

Cel: udowodnić, że WILQ skill realnie pomaga polskiemu marketerowi, a nie tylko
zwraca poprawny JSON. Każdy skill musi przejść przez ten sam pipeline.

### 1. Preflight

Sprawdź aktualną prawdę runtime:

```bash
curl -sf http://127.0.0.1:8000/api/health
git status --short
```

Nie zaczynaj od pamięci rozmowy. Jeśli API nie działa, najpierw napraw runtime
albo zapisz blocker w `docs/PROGRESS.md`.

### 2. Ręczny prompt marketera

Użyj realistycznego polskiego promptu, takiego jak marketer faktycznie zada:

```text
Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh, merge,
create albo block dla Ekologus na podstawie GSC, WordPress, GA4 i Ahrefs
evidence. Nie obiecuj leadów, revenue ani wzrostów pozycji.
```

Oczekiwany przebieg:

- skill czyta swój `SKILL.md`,
- skill czyta wymagane `references/`,
- skill pobiera WILQ API evidence,
- skill cytuje source connector IDs i evidence IDs,
- skill wskazuje ActionObject IDs, jeśli API je udostępnia,
- skill blokuje unsupported claims,
- odpowiedź jest po polsku z polskimi znakami.

Manualny wynik zapisuj w `docs/evals/skill-eval-ledger.md`, nawet jeśli potem
non-interactive eval przejdzie. Manualny przebieg jest często bogatszy i pokazuje
realną użyteczność dla marketera.

### 3. Deterministic smoke

Uruchom smoke script skilla:

```bash
uv run python .agents/skills/<skill>/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Dla `wilq-daily-command` użyj:

```bash
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
```

Smoke potwierdza kontrakt API/skilla, ale sam nie dowodzi jakości odpowiedzi.

### 4. Non-interactive Codex eval

Uruchom `codex exec` przez harness:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000
```

Używaj `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1`, gdy globalna konfiguracja
Codexa/MCP może powodować poboczne błędy transportu. Eval ma mierzyć WILQ
skill/API, nie przypadkowe globalne narzędzia.

Wyniki zapisują się w:

```text
.local-lab/evals/codex-skill/<timestamp>/<skill>/
  prompt.md
  result.json
  trace.jsonl
  stderr.log
```

Nie commituj `.local-lab`.

### 5. Interpretacja pass/fail

`passed` oznacza tylko, że wynik spełnił obecne warunki harnessa:

- `language=pl-PL`,
- polskie znaki,
- `api_used=true`,
- zgodność ze schemą,
- source connectors,
- evidence IDs,
- ActionObject safety,
- brak oczywistych unsafe claims.

To nie zawsze oznacza, że skill dał świetną decyzję marketingową. Po każdym
passie zapisz ocenę jakości:

- Czy odpowiedź jest konkretna, czy ogólna?
- Czy daje kolejkę decyzji, czy tylko opisuje zasady?
- Czy używa tych samych evidence IDs co dashboard/API?
- Czy wskazuje najmniejszy bezpieczny następny krok?
- Czy blokuje metryki, których WILQ nie ma?
- Czy marketer może od razu coś zrobić?

Jeśli pass jest zbyt ogólny, nie traktuj go jako koniec pracy. Dopisz gap do
`docs/evals/skill-eval-ledger.md` i wzmocnij case/harness tak, żeby wymagał
konkretnych decyzji.

### 6. Aktualizacja dokumentów

Po każdym istotnym przebiegu zaktualizuj:

- `docs/evals/skill-eval-ledger.md` - prompt, endpointy, wynik, evidence IDs,
  ActionObject IDs, jakość odpowiedzi i product gaps.
- `docs/PROGRESS.md` - krótki aktualny stan i ścieżka artefaktu.
- `docs/goals/001-goal.md` - tylko jeśli zmienia się aktywny goal, blocker,
  acceptance gate albo następny krok.

### Aktualny znany wynik referencyjny

Pierwszy pełny przebieg:

```text
skill: wilq-content-strategist
manual prompt: completed and useful
non-interactive eval: passed
artifact: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json
```

Wynik zawierał:

- `pl-PL`,
- polskie znaki,
- `api_used=true`,
- evidence IDs,
- source connectors,
- `act_prepare_content_refresh_queue`.

Najważniejszy wniosek: obecny harness dobrze łapie kontrakt, API usage i brak
halucynacji, ale za słabo mierzy "czy skill dał świetną kolejkę decyzji".
Manualny przebieg był bogatszy, bo wyciągnął konkretne decyzje: BDO refresh,
Zielony Ład merge/create-after-inventory-check, homepage low-priority refresh i
GA4 `(not set)` jako block. Następny poziom evali musi tego wymagać wprost.

### Następna kolejność skillów

Najpierw testuj skille, które mają realne ActionObjects i największą wartość
dla demo:

1. `wilq-merchant-feed-operator` - `act_review_merchant_feed_issues`.
2. `wilq-ga4-analyst` - `act_review_ga4_tracking_quality`.
3. `wilq-gsc-content-doctor` - `act_prepare_content_refresh_queue`.
4. `wilq-ads-doctor` - live campaign evidence; search terms/CPA/ROAS nadal
   wymagają osobnych read contracts.
5. `wilq-localo-operator` - access działa, ale local ranking/GBP facts są nadal
   blocked.

Po nich wróć do skillów bez aktualnego ActionObject i oceń, czy powinny dostać
nowe API/action contracts, czy pozostać blocker/readiness workflows.

## Current Product Direction

Command Center ma być "co marketer robi dziś", nie connector inventory.
Codex skills mają być operacyjną warstwą nad WILQ API: najpierw API evidence,
potem diagnoza, blokady claimów i bezpieczny następny krok po polsku.

## Current Critical Direction - 2026-06-18 13:55

Najważniejszy świeży audyt:

```txt
docs/audits/001-output.md
```

Wniosek audytu: architektura idzie w dobrym kierunku, ale WILQ jest nadal
`safe operating shell`, nie pełny BDOS-class OS. Największy problem to nie
liczba skillów, tylko brak jednego canonical operator view modelu i brak części
read/action contracts. API ma być mózgiem; skills mają być cienkimi workflow po
API.

Twarda zasada zapisana w `AGENTS.md`: nie wolno łatać logiki produktu,
deduplikacji, klasyfikacji decyzji, rankingów ani edge-case fixes w skill
references. Jeśli skill potrzebuje mądrzejszej decyzji, najpierw implementujemy
typed WILQ API/schema/view-model, a skill tylko konsumuje pole API.

## Recently Completed - Shared Daily Runtime Endpoints

This slice is done and pushed as `35d8be3 perf(api): share daily runtime endpoints`.
Do not resume it as active work unless a new performance regression is found.

What changed:

- `GET /api/dashboard/command-center` returns
  `build_daily_runtime().command_center`.
- `GET /api/marketing/brief` returns
  `build_daily_runtime().marketing_brief`.
- `connector_refresh()` clears `clear_daily_runtime_cache()` after refresh.
- Endpoint regression tests cover both daily-runtime-backed routes.

Full proof before commit:

```bash
scripts/verify.sh
```

Result:

- backend API contracts: `102 passed`;
- dashboard route tests: `13 passed`;
- Playwright e2e: `9 passed`;
- skill API smoke: passed;
- dashboard production build: passed;
- non-blocking warning: Vite main chunk is above 500 KB.

## Latest Slice - Ads Negative Keyword Safety Review

Ads safety slice is implemented and verified locally. Nie zaczynaj od zera i
nie cofaj poprzednich route/performance cleanupów.

Commit: `c68a9fd feat(ads): add negative keyword safety review`.

Cel slice'a:

- Dodać Ads negative keyword safety review jako prepare-only contract.
- Użyć realnych Google Ads search-term metric facts, ale nie claimować waste.
- Wystawić ten sam stan przez API, dashboard, shared schema, ActionObject i
  `wilq-ads-doctor` smoke/eval contract.
- Zablokować `negative keyword apply`, `search-term waste`, CPA, ROAS,
  conversion loss i automatyczne zmiany bez walidacji.

Main files:

- `wilq/actions/google_ads/negative_keywords.py`
- `wilq/actions/payloads.py`
- `wilq/actions/service.py`
- `wilq/briefing/ads_diagnostics.py`
- `wilq/schemas.py`
- `packages/shared-schemas/src/index.ts`
- `apps/dashboard/src/routes/App.tsx`
- `apps/dashboard/src/routes/App.test.tsx`
- `.agents/skills/wilq-ads-doctor/SKILL.md`
- `.agents/skills/wilq-ads-doctor/references/output-contract.md`
- `.agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
- `tests/test_api_contracts.py`
- `tests/test_codex_skill_eval_cases.py`
- `docs/evals/cases/wilq-skill-eval-cases.json`

Implemented contract:

- New ActionObject ID: `act_prepare_negative_keyword_review_queue`.
- New diagnostics contract:
  `/api/ads/diagnostics.negative_keywords_read_contract`.
- New Ads decision type: `review_negative_keyword_safety`.
- Candidates are built only from grouped `search_term_*` metric facts with
  activity and zero conversions/conversion value in current evidence.
- Candidate payloads require:
  `apply_allowed=false`, `destructive=false`,
  `required_validation=["90_day_safety_check", ...]` and evidence IDs.
- Dashboard `/ads-doctor` shows candidates as review/safety cards, not ready
  exclusions.
- `wilq-ads-doctor` smoke now fails if the negative keyword contract is ready
  without candidates/action ID or blocked without missing contracts.

Focused proof already passed:

```bash
uv run ruff check wilq/actions/google_ads/negative_keywords.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/schemas.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run mypy wilq/actions/google_ads/negative_keywords.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/schemas.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics or custom_segments or negative_keyword or route_specific'
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
```

Wynik:

- ruff: passed.
- mypy: passed.
- backend selected tests: 4 passed.
- dashboard typecheck: passed.
- shared schema typecheck: passed.
- dashboard route tests: 13 passed.

Full proof before commit:

```bash
scripts/verify.sh
```

Result:

- backend API contracts: `102 passed`;
- dashboard route tests: `13 passed`;
- Playwright e2e: `9 passed`;
- skill API smoke: passed;
- dashboard production build: passed;
- non-blocking warning: Vite main chunk is above 500 KB.

Fresh Codex eval proof:

- Artifact:
  `.local-lab/evals/codex-skill/20260619T065511Z/wilq-ads-doctor/result.json`.
- Result: `pl-PL`, Polish diacritics, `api_used=true`,
  `operator_usefulness_score=5`, no safety findings.
- Evidence IDs:
  `ev_connector_google_ads_status`,
  `ev_refresh_refresh_google_ads_c2f62ee2b43a`.
- Confirms `negative_keywords_read_contract.status=ready`,
  `candidate_count=7` and `act_prepare_negative_keyword_review_queue`.
- Blocks `negative keyword apply`, search-term waste, wasted budget, CPA and
  ROAS without `90_day_safety_check`, payload preview and validated
  ActionObject.
- Smoke script now summarizes `blocked_handoff=null` correctly for live Ads
  diagnostics instead of assuming an OAuth blocker object.
