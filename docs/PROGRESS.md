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
- Command Center Ads nie pokazuje już ogólnego statusu connectora jako insightu.
  Live `/api/dashboard/command-center` pokazuje teraz decyzję
  `Ads: kolejki budżetu, rekomendacji i zapytań` z licznikami:
  `kampanie=18`, `zapytania=50`, `podgląd budżetu=18`, `rekomendacje=4`,
  `wykluczenia=6`, `segmenty=1`. Ten sam prompt i ActionObjecty trafiają do
  scoped `/api/codex/context-pack` dla `wilq-daily-command`.
- Command Center tłumaczy teraz marketer-facing blocked claims w ogólnych
  kartach decyzyjnych/tactical/brief: API nadal niesie stabilne raw
  `blocked_claims`, ale UI pokazuje np. `ponowne zatwierdzenie produktu`,
  `wzrost leadów`, `opłacalność` i `zmarnowany budżet` zamiast
  `approval restored`, `lead uplift`, `profitability` albo `wasted budget`.
  Prompt Ads w `daily_decisions` i scoped `wilq-daily-command` context-pack
  też używa polskiego brzmienia: `Nie twierdź opłacalności, zmarnowanego
  budżetu ani wdrożenia zmian...`.
- Command Center nie pokazuje już marketerowi angielskich etykiet
  `Evidence` / `Przykładowe evidence` na kartach decyzji, taktyk i briefów.
  Widoczne etykiety to teraz `Dowody`, `Dowody: N ID(s)` i
  `Przykładowe dowody`; API nadal używa stabilnych pól `evidence_ids`.
- Command Center GA4 nie buduje już osobnego ogólnego skrótu z samych metric
  facts. Daily decision i scoped `wilq-daily-command` context-pack używają
  teraz tego samego `Ga4DiagnosticsResponse.decision_queue`, co `/ga4`, więc
  pokazują liczby `grupy ruchu`, `decyzje`, `pomiar`, `jakość ruchu` i
  `braki kontraktu` zamiast angielskich `landing groups` i ogólnego
  "brak pełnego kontraktu" jako głównego przekazu.
- Content diagnostics i scoped `wilq-content-strategist` context-pack pokazują
  teraz typed decyzje z marketer-facing tytułem, summary, `primary_query`,
  `total_clicks`, `total_impressions`, `aggregate_ctr` i
  `best_average_position`. Live proof po `scripts/local_stack.sh restart`:
  top decyzje to `SEO: odśwież lub scal "bdo co to" (1 zapytanie)` z
  `4429 wyświetleń`, `4 kliknięcia`, CTR `0.09%` oraz
  `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` z
  `2902 wyświetlenia`, `123 kliknięcia`, CTR `4.24%`. Context-pack zachowuje
  evidence IDs i `act_prepare_content_refresh_queue`.
- `wilq-ads-doctor` smoke przeszedł na świeżym API i potwierdza ten sam
  recommendations contract w scoped context-packu.
- Pełny `scripts/verify.sh` przeszedł po Command Center Ads review queues slice:
  backend API contracts `117 passed`, dashboard route tests `14 passed`,
  Playwright e2e `9 passed`, security, skill/API smokes i dashboard production
  build passed.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. Content decision queue marketer summary, 2026-06-20 02:38 CEST.
   `/api/content/diagnostics.decision_queue` ma teraz skondensowane, polskie
   decyzje contentowe zamiast URL-i jako głównych tytułów. API dodaje
   `summary`, `primary_query`, `total_clicks`, `total_impressions`,
   `aggregate_ctr` i `best_average_position`; kolejka sortuje GSC/WordPress
   decyzje po realnym popycie z GSC, a dashboard `/content-planner` renderuje
   te pola jako pierwszorzędne liczby. Live proof po
   `scripts/local_stack.sh restart`: główne decyzje contentowe to BDO
   (`4429 wyświetleń`, `4 kliknięcia`, CTR `0.09%`), Zielony Ład
   (`2902 wyświetlenia`, `123 kliknięcia`, CTR `4.24%`), Remediacja i brand.
   Scoped `wilq-content-strategist` context-pack niesie te same pola,
   `google_search_console` + `wordpress_ekologus` evidence IDs i
   `act_prepare_content_refresh_queue`. Focused ruff, mypy, backend
   `content_diagnostics` tests, dashboard lint/typecheck and `App.test.tsx`
   passed. Full `scripts/verify.sh` also passed: backend `117 passed`,
   dashboard unit `14 passed`, Playwright e2e `9 passed`, security,
   skill/API smokes and dashboard production build passed.

2. Command Center GA4 decision queue, 2026-06-20 02:14 CEST.
   Command Center GA4 daily decision now consumes the same
   `Ga4DiagnosticsResponse.decision_queue` contract as `/ga4` and the
   `wilq-ga4-analyst` context-pack path. Live proof after
   `scripts/local_stack.sh restart`: `decision_review_ga4_landing_quality`
   shows title `GA4: pomiar i jakość ruchu do kontroli`, metric tiles
   `grupy ruchu=10`, `decyzje=6`, `pomiar=2`, `jakość ruchu=4`,
   `braki kontraktu=1`, and still blocks ROAS/revenue/conversion/tracking-fixed
   claims. Full `scripts/verify.sh` passed: backend `117 passed`, dashboard
   unit `14 passed`, Playwright e2e `9 passed`, security, skill/API smokes and
   dashboard production build passed.

3. Command Center evidence label cleanup, 2026-06-20 01:57 CEST.
   Dashboard Command Center, tactical cards, daily decision cards and
   brief/action surfaces keep the stable `evidence_ids` API contract, but render
   marketer-facing labels as `Dowody`, `Dowody: N ID(s)` and
   `Przykładowe dowody` instead of English `Evidence` / `Przykładowe evidence`.
   Legacy route config copy for Ads, GA4, GSC, Localo, Social, Content and
   Merchant now uses Polish `dowody`, `odczyt`, `podgląd akcji` and
   `brama bezpieczeństwa` language. Focused dashboard lint, typecheck, unit
   `App.test.tsx` and real-browser Command Center smoke passed.

4. Command Center blocked-claim label cleanup, 2026-06-20 01:43 Europe/Warsaw.
   Dashboard Command Center, tactical cards and brief/action cards now translate
   raw blocked-claim contract values into Polish marketer-facing labels without
   changing API IDs. Live proof after `scripts/local_stack.sh restart`: Ads
   Codex prompt in `/api/dashboard/command-center` and scoped
   `/api/codex/context-pack` says `Nie twierdź opłacalności, zmarnowanego
   budżetu ani wdrożenia zmian`, while real-browser Command Center smoke
   verifies Polish labels and absence of raw `approval restored`, `lead uplift`,
   `search-term waste`, `profitability` and `wasted budget`. Focused ruff,
   mypy, command-center API tests, dashboard lint/typecheck/unit and Playwright
   Command Center smoke passed.

5. Command Center Ads review queues, 2026-06-20.
   Command Center i `wilq-daily-command` context-pack konsumują teraz istniejące
   Ads diagnostics zamiast pokazywać generyczne "live metrics" albo
   connector/readiness prose. Live proof po `scripts/local_stack.sh restart`:
   `daily_ads_status` ma title `Ads: kolejki budżetu, rekomendacji i zapytań`,
   status `ready`, priority `16`, liczniki `kampanie=18`, `zapytania=50`,
   `podgląd budżetu=18`, `rekomendacje=4`, `wykluczenia=6`, `segmenty=1` oraz
   ActionObjecty `act_prepare_ads_campaign_review_queue`,
   `act_prepare_google_ads_recommendation_review_queue`,
   `act_prepare_custom_segments_from_search_terms` i
   `act_prepare_negative_keyword_review_queue`. `/api/codex/context-pack`
   niesie ten sam prompt do `wilq-ads-doctor`. Focused ruff, mypy i
   `uv run pytest tests/test_api_contracts.py -q -k 'command_center'` passed.
   Full `scripts/verify.sh` passed: backend `117 passed`, dashboard unit
   `14 passed`, Playwright e2e `9 passed`, security, skill/API smokes and
   dashboard production build passed.

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
