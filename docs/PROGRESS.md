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
  zapisany wynik/akceptacja review strategii przez człowieka. Sam review gate
  jest już typed: `human_strategy_review`, `review_recommendation_type`,
  `review_impact_metrics`, `review_change_history`, `review_business_goal`,
  `recommendation_apply_preview`, `google_ads_rmf_compliance_review`,
  `human_confirm_before_apply`.
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
- Ads business context nie jest już ukryty tylko w `/ads-doctor`.
  Live proof po `scripts/local_stack.sh restart`:
  `/api/dashboard/command-center.blocker_count=2`, a `operator_brief` i
  `daily_decisions` mają osobny blocked item
  `daily_ads_business_context` / `decision_ads_business_context_before_budget_decisions`
  z `braki=4`, `marża=brak`, `cel biznesowy=brak`, `cel budżetu=brak` oraz
  blocked claims `profitability`, `margin verdict`, `budget scaling`,
  `budget apply`, `recommendation apply`, `wasted budget`. Ten sam blocker
  jest w `/api/marketing/brief.what_blocks_us` i scoped
  `wilq-daily-command` context-pack, bez dołączania pełnego
  `ads_diagnostics`. Downstream registry surfaces pozostają decyzjami
  operacyjnymi: `/api/opportunities` nadal ma 4 action-backed opportunities
  bez czystego Ads business blockera, a `/api/workflows` i
  `/api/knowledge/operating-map` wybierają `ads_daily_check` jako `ready`
  Ads review queue z 4 ActionObjectami.
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
- Ads recommendations nie mieszają już human review z brakującymi read
  contracts. Live proof po `scripts/local_stack.sh restart`: rekomendacje i
  decision `ads_review_recommendations` mają `missing_read_contracts=[]` oraz
  `operator_review_gates` z `human_strategy_review`,
  `review_recommendation_type`, `review_impact_metrics`,
  `review_change_history`, `review_business_goal`,
  `recommendation_apply_preview`, `google_ads_rmf_compliance_review` i
  `human_confirm_before_apply`. Scoped `wilq-ads-doctor` context-pack zachowuje
  te gates bez `[REDACTED]`.
- `/api/ads/diagnostics.search_term_safety_read_contract` i
  `keyword_match_context_read_contract` nie traktują już
  `human_intent_review` jako brakującego kontraktu danych, kiedy 90-dniowe
  safety rows i keyword match context istnieją. Live proof po
  `scripts/local_stack.sh restart`: oba kontrakty mają
  `missing_read_contracts=[]` oraz
  `operator_review_gates=["human_intent_review"]`; decyzje
  `ads_review_search_term_safety` i `ads_review_negative_keyword_safety`
  niosą tę samą bramkę. To nadal nie odblokowuje negative keyword apply.
- Scoped `wilq-campaign-builder` context-pack ma workflow-specific
  `active_action_objects`: tylko `act_prepare_ads_campaign_review_queue` i
  `act_prepare_google_ads_recommendation_review_queue`. Negative keywords i
  custom segments zostają w swoich skillach, żeby campaign-builder nie mieszał
  intencji i trzymał payload poniżej limitu 200 KB. Fresh API-process proof:
  `191737 bytes`.
- Scoped `wilq-ads-doctor` context-pack wrócił poniżej non-daily skill budget.
  Live proof po `scripts/local_stack.sh restart`: payload over the wire
  `174292 bytes`, smoke-reported `context_pack_bytes=183152`; `sections` i
  zduplikowane row payloads w `decision_queue` są pominięte, budget preview w
  kontrakcie jest ograniczony do 4 rows, a full endpoint pointer zostaje
  `/api/ads/diagnostics`.
- Scoped `wilq-demand-gen-operator` context-pack jest teraz honest-blocked:
  `160734 bytes`, `active_action_objects=[]`, `ads_diagnostics.action_ids=[]`
  i `demand_gen_readiness.status=blocked`. Missing read contracts są jawne i
  nieredaktowane: `demand_gen_campaign_rows`,
  `demand_gen_asset_group_rows`, `demand_gen_creative_asset_rows`,
  `demand_gen_landing_quality_by_campaign`,
  `demand_gen_migration_constraints`, `demand_gen_action_object`.
  Skill smoke `wilq-demand-gen-operator` egzekwuje teraz ten kontrakt i failuje,
  jeśli adjacent ActionObject wróci jako aktywna akcja Demand Gen.
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
- `/api/knowledge/operating-map` i `/knowledge` mapują teraz wiedzę źródłową na
  decyzje, workflowy i skille zamiast pokazywać tylko katalog kart/playbooków.
  Live proof po `scripts/local_stack.sh restart`: 11 bindingów, 15 source
  cards, 14 playbooków i 31 expert rules. Core bindingi obejmują
  `knowledge_daily_command`, `knowledge_merchant_feed_review`,
  `knowledge_gsc_content_doctor`, `knowledge_ads_daily_check`,
  `knowledge_ga4_data_analyst` i `knowledge_localo_visibility_review`; Ads
  wiąże `card_google_ads_search_playbook`, `google_ads_search_playbook`,
  `ads_search_terms_v1` i 4 review-only ActionObjecty z `/ads-doctor` oraz
  `wilq-ads-doctor`, a Localo jawnie blokuje `local_ranking_rows`,
  `gbp_performance_rows` i `review_rows`.
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
  `decyzje=8`, `blockery=0`. Latest Merchant follow-up:
  `MerchantDecisionItem` ma teraz typed `priority` i numeric `metric_tiles`;
  live proof: 8 decyzji, `null_priority=[]`, `empty_tiles=[]`, top decyzja
  ma `priority=21` i `metric_tiles.zgłoszenia=892`.
- `wilq-ads-doctor` smoke przeszedł na świeżym API i potwierdza ten sam
  recommendations contract w scoped context-packu.
- Pełny `scripts/verify.sh` przeszedł po Ads scoped context-pack compaction
  slice:
  backend API contracts `119 passed`, dashboard route tests `14 passed`,
  Playwright e2e `11 passed`, security, skill/API smokes i dashboard production
  build passed.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. Ads business context contract, 2026-06-20 10:12 CEST.
   `AdsDiagnosticsResponse` exposes typed
   `business_context_read_contract`, shared Zod schema and Ads Doctor UI
   labels. Live proof after `scripts/local_stack.sh restart`:
   `/api/ads/diagnostics.business_context_read_contract.status=blocked`,
   missing contracts are `profit_margin`, `business_goal`,
   `human_budget_goal`, `target_roas_or_cpa`; decision
   `ads_review_business_context` has `priority=22`,
   metric tiles `braki=4`, `blokady=6`, `ustawione pola=0`, and Ads
   `blocker_count=2`. `wilq-ads-doctor` smoke passed with the same contract
   in scoped context-pack (`context_pack_bytes=186844`, still under 200 KB).

2. Ads scoped context-pack compaction, 2026-06-20 09:46 CEST.
   `wilq-ads-doctor` context-pack no longer ships duplicated Ads sections or
   row payloads inside `decision_queue`. Live proof: 174292 bytes over the wire
   and smoke-reported `context_pack_bytes=183152`; `sections_omitted=true`,
   `decision_row_payloads_omitted=true`, budget payload preview included rows
   capped at 4, full endpoint pointer preserved. The smoke script now fails if
   `wilq-ads-doctor` exceeds 200 KB.

3. Ads intent review gates, 2026-06-20 09:35 CEST.
   Search-term safety, keyword match context and negative keyword review now
   expose `human_intent_review` as `operator_review_gates` instead of a missing
   read contract when supporting Ads evidence exists. Live proof:
   search-term safety and keyword context both have
   `missing_read_contracts=[]`, `operator_review_gates=["human_intent_review"]`;
   decisions `ads_review_search_term_safety` and
   `ads_review_negative_keyword_safety` carry the same gate. Full
   `scripts/verify.sh` passed: backend `119 passed`, dashboard unit
   `14 passed`, Playwright `11 passed`, skill/API smokes and production build
   passed.

4. Localo priority and metric tiles, 2026-06-20 09:19 CEST.
   `LocaloDecisionItem` now exposes typed `priority` and `metric_tiles`, with
   the Zod schema, `/localo` UI and API tests updated. Live proof after stack
   restart: 2 decisions, no null priorities, no empty metric tiles;
   access-ready decision shows `dostęp MCP=1`, `fakty Localo=0`,
   `braki kontraktu=5`; visibility blocker shows `blokady claimów=5`.
   Full `scripts/verify.sh` passed: backend `119 passed`, dashboard unit
   `14 passed`, Playwright `11 passed`, production build passed.

5. Merchant priority and metric tiles, 2026-06-20 09:07 CEST.
   `MerchantDecisionItem` now exposes typed `priority` and numeric
   `metric_tiles`, with the Zod schema, `/merchant` UI and API tests updated.
   Live proof after stack restart: 8 decisions, no null priorities, no empty
   metric tiles, top issue decision `priority=21` and `zgłoszenia=892`.
   Full `scripts/verify.sh` passed: backend `119 passed`, dashboard unit
   `14 passed`, Playwright `11 passed`, production build passed.

## Active Gaps

- Demand Gen is honest-blocked, not useful yet. It still needs real
  Demand Gen read contracts: campaign rows, asset groups, creative assets,
  landing quality by campaign, migration constraints and a Demand Gen
  ActionObject.
- Full BDOS-class Ads optimizer is not done. Remaining areas include setting
  and using business targets (`WILQ_ADS_PROFIT_MARGIN`,
  `WILQ_ADS_BUSINESS_GOAL`, `WILQ_ADS_BUDGET_GOAL`,
  `WILQ_ADS_TARGET_ROAS` or `WILQ_ADS_TARGET_CPA_MICROS`), Keyword Planner
  enrichment, forecast/audience size, recorded human strategy review outcome,
  budget apply safety/confirmation, impact sanity checks and mutation audit.
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
