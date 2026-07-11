# Handoff — `kgvy` optimizer readiness seam

Data: 2026-07-11 20:05 Europe/Warsaw  
Ostatni commit: `7278093` (`refactor: split Ads negative keyword indexes`)  
`origin/main` = `7278093`

## Wykonane

- `build_optimizer_readiness_contract` i jego osiem typed readiness items są w
  `wilq/briefing/ads_optimizer.py`.
- `ads_diagnostics.py` deleguje do modułu, a response contract pozostaje ten
  sam. Zachowane są evidence IDs, source connectors, missing contracts,
  operator review gates, safe next steps oraz blokady CPA/ROAS/waste i mutacji.
- Nie przenoszono ponownie section/decision builderów już opisanych w Beadzie.
- Priority map decyzji została dodatkowo przeniesiona do istniejącego
  `ads_decision_queue.py`; metric tiles pozostały poza zakresem tego małego seamu.
- Pierwszy formatter-safe metric-tile fragment jest teraz w
  `ads_metric_utils.py`/`ads_metric_tiles.py` dla `campaign_activity` i
  `campaign_triage`; pozostałe gałęzie dispatchera nie zostały przeniesione.
- Drugi fragment obejmuje `business_context` i `derived_kpi`; nie wracaj do tych
  dwóch branchy w dispatcherze.
- Trzeci fragment obejmuje `budget_context` i `recommendations`; nie wracaj do
  tych branchy ani do ich formatterów w dispatcherze.
- Czwarty fragment obejmuje `search_term_ngrams` i `impression_share`; nie wracaj
  do tych branchy w dispatcherze.
- Piąty fragment obejmuje `search_terms` i `search_term_safety`; nie wracaj do
  tych branchy ani ich formatterów w dispatcherze.
- Szósty fragment obejmuje `negative_keyword_safety` i `custom_segments`; nie
  wracaj do tych branchy ani ich formatterów w dispatcherze.
- Siódmy fragment obejmuje `change_history` i safety blocker tiles; nie wracaj
  do tych branchy w dispatcherze. Proste tile branches są zakończone.
- Label hydration jest rozbita na summary/decision/surface/contract helpers;
  nie wracaj do jednego monolitycznego `_hydrate_ads_marketer_labels`.
- Fail-closed `blocked_handoff` decision branch jest w `_blocked_ads_decision_queue`;
  nie wracaj do inline OAuth blocker assembly.
- Search-term safety decision jest w `build_search_term_safety_decision`;
  nie wracaj do inline 90-dniowej decyzji w diagnostics.
- Business-context decision jest w `build_business_context_decision`; nie wracaj
  do inline policy/rationale assembly w diagnostics.
- Safety decision jest w `build_block_write_actions_decision`; nie wracaj do
  inline `ads_block_write_actions_without_actionobject` assembly.
- Campaign/context/derived-KPI decisions są w `_build_campaign_context_decisions`,
  a safety section w `_build_ads_safety_decisions`; nie wracaj do jednego
  `_ads_decision_queue` assemblera dla tych grup.
- Blocked business-target path jest w `_blocked_business_target_interpretation`;
  nie wracaj do inline branch dla brakującej marży/celu.
- Ready/preliminary business-target path jest w
  `_preliminary_business_target_interpretation`; nie wracaj do inline target
  ROAS/CPA albo strategy-review branches.
- Business-context summary/next-step copy jest w
  `_business_context_summary_and_next_step`; nie wracaj do inline status copy.
- Missing contracts/status/allowed metrics są w `_business_context_contract_state`;
  nie wracaj do inline readiness-state assembly.
- Business-context tiles są w `_business_context_metric_tiles`; nie wracaj do
  inline metric-tile dictionary.
- Typed business-context response assembly jest w
  `_build_business_context_read_contract`; nie wracaj do inline blocked-claims
  ani target/strategy contract construction.
- Strategy-review ready/blocked branch jest w `_strategy_review_operator_state`;
  nie wracaj do inline status/action/missing-contract branch.
- Compact candidate payloads są w `_compact_ads_candidate_contracts`; nie wracaj
  do inline custom-segment/negative-keyword compaction.
- Campaign triage source context jest w `_campaign_triage_source_context`; nie
  wracaj do inline evidence/metric aggregation.
- Negative-keyword context indexes są w `_negative_keyword_context_indexes`; nie
  wracaj do inline 90-day safety/keyword-context indexing.

## Dowody

- `tests/api_contracts/test_ads_contracts.py` przechodzi w całości.
- Ruff, mypy, complexity audit i `git diff --check` przechodzą.
- Runtime po restarcie: `/api/health` `ok`; `/api/ads/diagnostics` zwraca
  `live_data_available=true` i blokady niedozwolonych twierdzeń.
- Browser proof po restarcie: `.local-lab/proof/ads-business-context-seam.png`;
  `/ads-doctor` pokazuje kolejkę decyzji, dowody, świeżość Ads/GA4 i blokady
  ROAS/przychód/waste bez technicznego payloadu above the fold.
- Zmniejszenie `ads_diagnostics.py`: 358 linii.

## Nie robić ponownie

- Nie wracać do optimizer-readiness assembly w `ads_diagnostics.py`.
- Nie usuwać blokad twierdzeń ani `apply` safety podczas kolejnych refaktorów.

## Następny slice

Następny potwierdzony seam to `_negative_keywords_read_contract` (110 linii),
wybrany po aktualnym complexity audit. Zachować 90-day safety, evidence IDs,
blocked claims i `apply_allowed=false`.

## Kontrola repo

- Po commicie: `HEAD == origin/main == 7278093`, worktree czysty.
- Przed kolejnym slice’em sprawdź health API, Ads diagnostics i aktualny complexity
  report.
