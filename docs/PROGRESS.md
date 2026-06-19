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

- Command Center ma teraz 30-sekundowy operator snapshot cache po stronie WILQ
  API i dashboardu. Live proof po `scripts/local_stack.sh restart`:
  `/api/dashboard/command-center` `27856 bytes`, cold `1.777s`, potem
  `0.007s`, `0.009s`, `0.010s`, `0.007s` w oknie cache; daily Codex
  context-pack `126449 bytes`, `0.382s`, potem `0.237s`, `0.234s`.
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
- `/api/ads/diagnostics.budget_pacing_read_contract.payload_preview` ma 18
  review-only `CampaignBudgetOperation` preview rows. ActionObject
  `act_prepare_ads_campaign_review_queue` ma 8 budżetowych preview rows,
  `preview_contract=budget_apply_preview_v1`, `apply_allowed=false`,
  `destructive=false` i waliduje się jako `valid=true`. To nadal nie jest
  budget apply support.
- `wilq-ads-doctor` smoke przeszedł na świeżym API i potwierdza ten sam
  recommendations contract w scoped context-packu.
- Pełny `scripts/verify.sh` przeszedł po budget apply-preview slice: backend
  API contracts `116 passed`, dashboard route tests `14 passed`, Playwright
  e2e `9 passed`, security, skill/API smokes i dashboard production build passed.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. Ads campaign budget apply preview, 2026-06-20 00:52 Europe/Warsaw.
   Google Ads budget context ma teraz review-only
   `CampaignBudgetOperation` payload preview w typed API, shared schemas,
   dashboardzie `/ads-doctor` i ActionObject
   `act_prepare_ads_campaign_review_queue`. Preview pokazuje bieżący budżet,
   ewentualną rekomendowaną kwotę/deltę z Google, evidence IDs, required
   validation i blocked claims. Każdy preview ma `api_mutation_ready=false`,
   `apply_allowed=false`, `destructive=false`; WILQ nadal blokuje budget apply
   bez `human_budget_goal`, apply safety i mutation audit. Live proof po
   `scripts/local_stack.sh restart`: `/api/ads/diagnostics` zwraca 18 budget
   preview rows i decision `ads_review_budget_context` z
   `action_ids=["act_prepare_ads_campaign_review_queue"]`;
   `/api/actions/act_prepare_ads_campaign_review_queue` zwraca 8 preview rows,
   `preview_contract=budget_apply_preview_v1`, a walidacja ActionObject daje
   `valid=true`. Focused ruff, mypy, backend Ads tests, shared schema
   typecheck, dashboard typecheck i `App.test.tsx` passed. Full
   `scripts/verify.sh` passed: backend `116 passed`, dashboard unit
   `14 passed`, Playwright e2e `9 passed`, security, skill/API smokes and
   dashboard production build passed.

2. Command Center operator cache, 2026-06-20 00:31 Europe/Warsaw.
   Daily runtime cache TTL wzrósł z 2s do 30s
   (`WILQ_DAILY_RUNTIME_CACHE_SECONDS` nadal może to nadpisać), a dashboardowy
   TanStack Query client używa `staleTime=30000` i
   `refetchOnWindowFocus=false` jako domyślnego server-state cache. Semantyka
   danych nie zmienia się: cache jest czyszczony po connector refresh oraz
   action validation/apply paths. Live proof po `scripts/local_stack.sh restart`:
   `/api/dashboard/command-center` `27856 bytes`, cold `1.777s`, potem
   `0.007s`, `0.009s`, `0.010s`, `0.007s` w oknie cache. Focused ruff, mypy,
   backend cache tests, dashboard `App.test.tsx`, dashboard typecheck passed.

3. Ads recommendation apply payload preview, 2026-06-20 00:20 Europe/Warsaw.
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

4. Ads recommendation impact preview, 2026-06-19 23:44 Europe/Warsaw.
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

5. Ads account currency read contract, 2026-06-19 23:12 Europe/Warsaw.
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

## Active Gaps

- Demand Gen cold context-pack is still about `2.6s`; payload and warm runtime
  are inside budget, but cold path should be improved if it stays visible in
  browser/Codex proof.
- Full BDOS-class Ads optimizer is not done. Remaining areas include Keyword
  Planner enrichment, forecast/audience size, profit-margin/business-goal
  interpretation, human strategy review, budget apply safety/confirmation,
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
