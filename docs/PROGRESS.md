# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwum sprzed kompaktowania:
`docs/progress/archive/2026-06-19-progress-ledger.md`.

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 slice'ów, aktywne luki i następny
  krok.
- Nie dopisuj kolejnych setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Git i dedykowane ledgery są źródłem długiej historii. Ten plik ma pomagać po
  utracie contextu.

## Current Snapshot

Data: 2026-06-20

Stan produktu:

- Goal 001 nadal aktywny: `docs/goals/001-goal.md`.
- WILQ API jest system brain. Dashboard i Codex skills mają korzystać z tych
  samych kontraktów API, evidence IDs, ActionObject IDs i source connectors.
- Lokalny stack prowadź przez `scripts/local_stack.sh start|stop|restart|status|logs`.
  Kanoniczne URL-e: API `http://127.0.0.1:8000`, dashboard
  `http://127.0.0.1:5173/command-center`.
- Operator-facing output ma być po polsku z polskimi znakami.
- Nie wolno naprawiać błędów reasoning przez dopisywanie edge-case'ów do skill
  references. Naprawa ma iść przez typed API state, knowledge cards, expert
  rules, context-packi, evale i dashboard.

Aktualny proof produktowy:

- Najnowszy live Ads proof: `refresh_google_ads_60956db2c42f` /
  `ev_refresh_refresh_google_ads_60956db2c42f` odczytał
  `customer_currency_code=PLN`, 18 kampanii, 50 search terms, 200 wierszy
  90-dniowego search-term safety, 211 keyword context rows i 4 aktywne
  rekomendacje Google Ads.
- `/api/ads/diagnostics.account_currency_read_contract.status=ready`,
  `currency_code=PLN`; `account_currency` zniknęło z brakujących kontraktów
  derived KPI. Profitability, margin verdict i budget apply nadal są
  zablokowane.
- `/api/ads/diagnostics.recommendations_read_contract.status=ready`; impact
  preview jest dostępny dla 2 z 4 rekomendacji, a review-only apply payload
  preview dla 4 z 4 rekomendacji. Brakujący kontrakt pozostaje celowo wąski:
  `human_strategy_review`.
- `wilq-ads-doctor` smoke przeszedł na świeżym API i potwierdza ten sam
  recommendations contract w scoped context-packu.
- Pełny `scripts/verify.sh` przeszedł po recommendation apply-preview slice: backend
  API contracts `115 passed`, dashboard route tests `13 passed`, Playwright
  e2e `9 passed`, security, skill/API smokes i dashboard production build passed.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. Ads recommendation apply payload preview, 2026-06-20 00:20 Europe/Warsaw.
   Google Ads recommendations mają teraz review-only apply payload preview w
   typed API, dashboardzie, ActionObject i scoped `wilq-ads-doctor`
   context-packu. To nie jest apply support: payload używa
   `operation_type=ApplyRecommendationOperation`, ale wymaga
   `review_recommendation_type`, `review_impact_metrics`,
   `review_change_history`, `review_business_goal`,
   `recommendation_apply_preview`, `google_ads_rmf_compliance_review` i
   `human_confirm_before_apply`, a każdy preview ma
   `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`.
   Live proof: `refresh_google_ads_60956db2c42f` /
   `ev_refresh_refresh_google_ads_60956db2c42f`; 4 aktywne rekomendacje,
   2 z impact preview, 4 z apply payload preview. `/api/actions` wystawia
   `act_prepare_google_ads_recommendation_review_queue` jako prepare-only
   ActionObject. Focused ruff, mypy, backend tests, shared/dashboard
   typecheck, `App.test.tsx` i `wilq-ads-doctor` smoke passed. Full
   `scripts/verify.sh` passed: backend `115 passed`, dashboard unit
   `13 passed`, Playwright e2e `9 passed`, security, skill smokes and
   dashboard production build passed. `uv.lock` zaktualizowany przy okazji
   security gate: `msgpack 1.2.0 -> 1.2.1`.

2. Ads recommendation impact preview, 2026-06-19 23:44 Europe/Warsaw.
   Google Ads recommendations query pobiera read-only `recommendation.impact`.
   WILQ zapisuje impact metric facts jako
   `recommendation_impact_{base|potential}_*`, `/api/ads/diagnostics` pokazuje
   `impact_available`, delty kliknięć/wyświetleń/kosztu/konwersji per
   recommendation row, scoped `wilq-ads-doctor` context-pack niesie ten sam
   kontrakt, a dashboard `/ads-doctor` pokazuje impact preview bez apply
   claimów. Live proof: `refresh_google_ads_978ef3a667f6` /
   `ev_refresh_refresh_google_ads_978ef3a667f6`; 4 aktywne rekomendacje, 2 z
   impact preview, 8 impact metric facts. Focused ruff, mypy, backend tests,
   shared schemas typecheck, dashboard typecheck, `App.test.tsx` i
   `wilq-ads-doctor` smoke passed. Full `scripts/verify.sh` passed: backend
   `115 passed`, dashboard unit `13 passed`, Playwright e2e `9 passed`, skill
   smokes and dashboard production build passed.

3. Ads account currency read contract, 2026-06-19 23:12 Europe/Warsaw.
   Google Ads campaign read query pobiera `customer.currency_code` jako
   read-only fact. WILQ zapisuje `account_currency_code` z evidence ID,
   `/api/ads/diagnostics` wystawia `account_currency_read_contract`, scoped
   `wilq-ads-doctor` context-pack przenosi ten sam kontrakt, a dashboard
   `/ads-doctor` formatuje koszty kampanii, KPI, budżetów, search terms i
   negative keyword review w walucie `PLN`. Live proof:
   `refresh_google_ads_26cb4673eee2` /
   `ev_refresh_refresh_google_ads_26cb4673eee2`. Focused backend,
   TypeScript, dashboard tests i skill smoke passed. Full `scripts/verify.sh`
   passed: backend `115 passed`, dashboard unit `13 passed`, Playwright e2e
   `9 passed` and dashboard production build passed.

4. Non-daily skill context-pack compaction, 2026-06-19 22:45 Europe/Warsaw.
   Default context-packs pomijają ciężkie diagnostic sections i metric facts
   dla content, GA4 i Merchant scoped packs. Campaign Builder nie ciągnie już
   Merchant jako domyślnego scope'u i używa lekkiego `content_landing_context`.
   Demand Gen buduje Ads + GA4 równolegle i nie ciągnie Merchant bez konkretnego
   kontraktu Demand Gen/Merchant. Live proof po `scripts/local_stack.sh restart`:
   `wilq-campaign-builder` `90711 bytes`, cold `1.867s`, warm `0.158s`;
   `wilq-demand-gen-operator` `100349 bytes`, cold `2.574s`, warm `0.156s`;
   `wilq-content-strategist` `91731 bytes`, cold `2.044s`, warm `0.166s`;
   `wilq-ga4-analyst` `28578 bytes`, cold `1.927s`, warm `0.147s`;
   `wilq-merchant-feed-operator` `24007 bytes`, cold `1.819s`,
   warm `0.153s`; `wilq-ads-doctor` `185126 bytes`, cold `1.392s`,
   warm `0.156s`; `wilq-custom-segments` `187121 bytes`, cold `1.408s`,
   warm `0.194s`; `wilq-daily-command` `120504 bytes`, cold `1.918s`,
   warm `0.236s`. Full `scripts/verify.sh` passed.

5. Custom segments review-only payload preview, 2026-06-19 22:08
   Europe/Warsaw. `/api/ads/diagnostics.custom_segments_read_contract` exposes
   `payload_preview` with `member_type=KEYWORD`, `api_mutation_ready=false`,
   `apply_allowed=false` and `destructive=false`. Remaining missing contracts:
   `keyword_planner_enrichment` and `forecast_or_audience_size`. Non-interactive
   eval passed:
   `.local-lab/evals/codex-skill/20260619T201200Z/wilq-custom-segments/result.json`.
   Full `scripts/verify.sh` passed.

## Active Gaps

- Demand Gen cold context-pack is still about `2.6s`; payload and warm runtime
  are inside budget, but cold path should be improved if it stays visible in
  browser/Codex proof.
- Full BDOS-class Ads optimizer is not done. Remaining areas include Keyword
  Planner enrichment, forecast/audience size, profit-margin/business-goal
  interpretation, human strategy review, budget/apply previews, apply safety,
  impact sanity checks and mutation audit.
- Command Center/dashboard is moving toward a usable marketer cockpit, but Goal
  001 remains active until the goal file's API/dashboard/skills/evals/safety
  requirements are all verified.
- Knowledge base/source-map work exists, but the long-term knowledge compiler
  and memory layer are not complete. Do not replace that with prompt stuffing.

## Next Best Slice

Continue with Goal 001 in this order unless live state shows a stronger blocker:

1. Improve the next marketer-facing cockpit surface that still repeats or hides
   useful decisions.
2. Continue Ads optimizer read contracts toward safe, review-only decisions.
3. Add or strengthen non-interactive skill evals only when they test real
   product usefulness, not just schema compliance.
4. Keep `docs/PROGRESS.md` compact; archive older entries instead of appending
   long history here.

## Recovery Pointers

- Active goal: `docs/goals/001-goal.md`.
- Recovery index: `docs/CONTEXT.md`.
- Skill eval ledger: `docs/evals/skill-eval-ledger.md`.
- Marketing source map: `docs/research/wilq-marketing-source-map.md`.
- BDOS-class architecture target:
  `docs/architecture/bdos-class-wilq-operating-system.md`.
- Full pre-compaction progress archive:
  `docs/progress/archive/2026-06-19-progress-ledger.md`.
