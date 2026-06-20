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
- `/api/ga4/diagnostics.decision_queue` ma teraz operator-facing `status`,
  `priority` i `metric_tiles`, a `/ga4` renderuje te kafelki per decyzja.
  Live proof po `scripts/local_stack.sh restart`: 6 decyzji GA4, 2 z
  `status=blocked` dla `(not set)` pomiaru i 4 z `status=ready` dla review
  jakości ruchu; kafelki pokazują `aktywni`, `sesje`, `zdarzenia`, `odsłony`
  i `engagement`, np. `(not set)/(not set)` ma `aktywni=179`, `sesje=179`,
  `engagement=0%`. Scoped `wilq-ga4-analyst` context-pack niesie te same
  pola bez redakcji GA4.
- `/api/ads/diagnostics.decision_queue` ma teraz operator-facing `priority` i
  `metric_tiles`, a `/ads-doctor` renderuje kafelki z typed API zamiast
  frontendowo zgadywać liczby z głębokich tablic. Live proof po
  `scripts/local_stack.sh restart`: 11 decyzji Ads, `null_priority_count=0`,
  `empty_tiles=[]`; top campaign decision pokazuje `kampanie=18`,
  `kliknięcia=117`, `wyświetlenia=3075`, `koszt=161`, `konwersje=2`.
  Search terms pokazują tylko istniejące evidence-backed kafelki
  `zapytania=50`, `kliknięcia=7`; `koszt` jest pomijany, gdy bieżący
  search-term evidence nie ma `cost_micros`. Scoped `wilq-ads-doctor`
  context-pack niesie te same `priority` i `metric_tiles` bez redakcji Ads.
- `/api/opportunities` nie jest już rejestrem connectorów. Live proof po
  `scripts/local_stack.sh restart`: zwraca 4 decision-backed opportunities:
  Merchant feed review, Content refresh queue, GA4 measurement/traffic review
  i Ads review queue. ID zaczynają się od `opp_decision_*`, nie
  `opp_connector_*`; karty mają `metric_tiles`, evidence IDs, source
  connectors, ActionObject IDs i polski safe next step. Full Codex
  context-pack `top_opportunities` niesie ten sam zestaw bez redakcji
  `opportunities`.
- `/api/workflows` nie jest już listą 15 identycznych placeholderów. Live proof
  po `scripts/local_stack.sh restart`: 15 workflowów, w tym 4 `ready`,
  4 `blocked` i 7 `planned`; core workflowy (`daily_command`,
  `merchant_feed_review`, `gsc_content_doctor`, `ga4_data_analyst`,
  `ads_daily_check`) mają route, skill, metric tiles, source connectors,
  evidence IDs i ActionObject IDs. Stare stringi `Workflow definition runs
  against WILQ API` i `Fetch WILQ API context` są nieobecne. Ciepły
  `/api/workflows` zwraca około 23 KB w `0.008-0.012s`.
- Content diagnostics i scoped `wilq-content-strategist` context-pack pokazują
  teraz typed decyzje z marketer-facing tytułem, summary, `primary_query`,
  `total_clicks`, `total_impressions`, `aggregate_ctr` i
  `best_average_position`. Live proof po `scripts/local_stack.sh restart`:
  top decyzje to `SEO: odśwież lub scal "bdo co to" (1 zapytanie)` z
  `4429 wyświetleń`, `4 kliknięcia`, CTR `0.09%` oraz
  `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` z
  `2902 wyświetlenia`, `123 kliknięcia`, CTR `4.24%`. Context-pack zachowuje
  evidence IDs i `act_prepare_content_refresh_queue`.
- Command Center first screen i scoped `wilq-daily-command` context-pack używają
  teraz tej samej content decision zamiast starego skrótu
  `Content: GSC query/page + WordPress inventory`. Live proof:
  `daily_decisions` dla `/content-planner` ma title
  `Przejrzyj kolejkę SEO z GSC i WordPress`, liczby `query/page=10`,
  `WP match=10`, `decyzje=4`, `wyświetlenia=7852`, `kliknięcia=138`,
  top reason `bdo co to` i brak `[REDACTED]` w `co_widzimy` /
  `dlaczego_to_ma_znaczenie`.
- Merchant diagnostics, `/merchant`, Command Center i scoped
  `wilq-merchant-feed-operator` context-pack używają teraz wspólnej
  `MerchantDiagnosticsResponse.decision_queue`, a nie osobno składanych raw
  facts. Live proof po `scripts/local_stack.sh restart`:
  `/api/merchant/diagnostics` pokazuje `product_count=10900`,
  `issue_count=15`, `issue_clusters=11`, `decision_count=8`; top decyzja:
  "Merchant: sprawdź brak potencjalnie wymaganego atrybutu / miara ceny
  jednostkowej", `issue_count=892`,
  `ev_refresh_refresh_google_merchant_center_a3ef2f66703f` i
  `act_review_merchant_feed_issues`. Scoped context-pack niesie tę samą
  decyzję bez redakcji w `merchant_diagnostics.decision_queue`, a Command
  Center pokazuje `produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`,
  `decyzje=8`, `blockery=0`.
- `wilq-ads-doctor` smoke przeszedł na świeżym API i potwierdza ten sam
  recommendations contract w scoped context-packu.
- Pełny `scripts/verify.sh` przeszedł po Merchant decision queue bridge slice:
  backend API contracts `117 passed`, dashboard route tests `14 passed`,
  Playwright e2e `9 passed`, security, skill/API smokes i dashboard production
  build passed.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. Workflows decision contract, 2026-06-20 07:33 CEST.
   `/api/workflows` and `/workflows` now expose operator workflows as typed
   WILQ API contracts, not generic automation placeholders. Core workflows are
   derived from daily decisions and carry `status`, `route`, `skill_id`,
   `metric_tiles`, source connectors, evidence IDs, ActionObject IDs, blocked
   claims and safe next steps. Planned workflows explicitly list missing
   contracts instead of implying automation exists. Live proof after
   `scripts/local_stack.sh restart`: 15 workflows, 4 `ready`, 4 `blocked`,
   7 `planned`; `daily_command` has `decyzje=4`, `blockery=1`, `źródła=6`,
   `akcje=7`; `ads_daily_check` has Ads review tiles and 4 review-only
   ActionObjects. Full `scripts/verify.sh` passed: backend `118 passed`,
   dashboard unit `14 passed`, Playwright e2e `10 passed`, security,
   skill/API smokes and dashboard production build passed.

2. Opportunities decision bridge, 2026-06-20 07:13 CEST.
   `/api/opportunities`, `/opportunities` and full Codex context-pack
   `top_opportunities` now consume the same daily decisions as Command Center
   instead of the old connector registry cards. Live proof after
   `scripts/local_stack.sh restart`: 4 opportunities with IDs
   `opp_decision_review_merchant_feed_issues`,
   `opp_decision_prepare_content_refresh_queue`,
   `opp_decision_review_ga4_landing_quality` and
   `opp_decision_review_ads_campaign_metrics`; each carries `metric_tiles`,
   evidence IDs, source connectors and safe ActionObject IDs. No
   `opp_connector_*` opportunities or `opportunities` redaction paths are
   present in the live proof. Full `scripts/verify.sh` passed after this
   slice: backend `117 passed`, dashboard unit `14 passed`, Playwright e2e
   `9 passed`, security, skill/API smokes and dashboard production build
   passed.

3. Ads decision metadata bridge, 2026-06-20 06:55 CEST.
   `/api/ads/diagnostics.decision_queue` now exposes explicit `priority` and
   `metric_tiles` for every Ads decision, and `/ads-doctor` renders those tiles
   directly from typed API state. Shared schemas and `wilq-ads-doctor`
   context-pack carry the same fields. Live proof after
   `scripts/local_stack.sh restart`: 11 Ads decisions, `null_priority_count=0`,
   `empty_tiles=[]`; campaign review has `kampanie=18`, `kliknięcia=117`,
   `wyświetlenia=3075`, `koszt=161`, `konwersje=2`; recommendations have
   `rekomendacje=4`, `podgląd wpływu=2`, `podgląd akcji=4`; search terms omit
   cost when `cost_micros` is absent from evidence instead of showing a false
   `0.00`.

4. GA4 decision metadata bridge, 2026-06-20 06:34 CEST.
   `/api/ga4/diagnostics.decision_queue` now exposes explicit `status`,
   `priority` and `metric_tiles` for each GA4 decision, and `/ga4` renders the
   tiles on decision cards. Live proof after `scripts/local_stack.sh restart`:
   6 GA4 decisions, 2 `blocked` measurement decisions for `(not set)` rows and
   4 `ready` traffic-quality review decisions; tiles include `aktywni`,
   `sesje`, `zdarzenia`, `odsłony` and `engagement`. Scoped
   `wilq-ga4-analyst` context-pack carries the same fields with no GA4
   redaction paths, and no `status`/`priority`/`metric_tiles` nulls are present.
   Full `scripts/verify.sh` passed: backend `117 passed`, dashboard unit
   `14 passed`, Playwright e2e `9 passed`, security, skill/API smokes and
   dashboard production build passed.

5. Marketing Brief daily-decision bridge, 2026-06-20 04:18 CEST.
   `/api/marketing/brief` and full/scoped Codex context-packs now consume the
   same `CommandCenterResponse.daily_decisions` state as Command Center instead
   of rebuilding the daily brief from older raw metric/action summaries. Live
   proof after `scripts/local_stack.sh restart`: `what_we_know` titles are
   `Przejrzyj kolejkę problemów Merchant Center`, `Przejrzyj kolejkę SEO z GSC
   i WordPress`, `GA4: pomiar i jakość ruchu do kontroli`,
   `Przejrzyj kolejki Ads do oceny bez apply` and `Ahrefs: domain_rating = 90`;
   `what_blocks_us` contains the GA4 contract blocker; `recommended_focus`
   mirrors ready daily decisions; scoped `wilq-daily-command` context-pack has
   the same brief titles and Command Center decision titles with no
   `marketing_brief` redaction paths. Stale strings such as
   `feed/product issues`, `active_products=12`, `disapproved_products=3`,
   `active_users=20`, `sessions=30` and `feed issue queue` are absent from the
   live brief. Full `scripts/verify.sh` passed after this slice: backend
   `117 passed`, dashboard unit `14 passed`, Playwright e2e `9 passed`,
   security, skill/API smokes and dashboard production build passed.


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
