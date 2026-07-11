# Handoff — `kgvy` optimizer readiness seam

Data: 2026-07-11 20:05 Europe/Warsaw  
Ostatni commit: bieżący `HEAD` (handoff jest częścią końcowego pointer commitu)  
`HEAD == origin/main` po weryfikacji pushu

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
- Blocked negative-keyword states są w `_negative_keywords_missing_search_terms_contract`
  i `_negative_keywords_no_candidates_contract`; nie wracaj do inline blocked
  contract branches.
- Custom-segment grouping i payload/score assembly są w `_custom_segment_group_rows`
  i `_custom_segment_payload_and_score`; nie wracaj do inline grouping ani preview
  orchestration.
- Typed Ads section assembly jest w `_build_ads_diagnostic_sections`; nie wracaj
  do inline listy sekcji w `build_ads_diagnostics`.
- Search-term read-contract reconciliation jest w
  `_reconcile_search_term_read_contracts`; nie wracaj do inline freshness
  reconciliation.
- Recommendations/impression-share reconciliation jest w
  `_reconcile_ads_recommendation_and_impression_contracts`; nie wracaj do inline
  missing-contract updates.
- Change-history reconciliation jest w `_reconcile_ads_change_history_contracts`;
  nie wracaj do inline aktualizacji missing contracts po gotowym odczycie historii.
- Budget/business-context reconciliation jest w
  `_reconcile_ads_budget_and_business_context_contracts`; nie wracaj do inline
  `budget_apply_preview`, `profit_margin` ani `human_budget_goal` updates.
- Reconciliation boundary jest domknięty przez dwa ostatnie extraction slices;
  aktualny complexity report ma 398 plików / 133173 LOC i dwa jawne violations
  (monolityczny plik oraz orchestrator), więc kolejny seam wymaga świeżego review.
- Core search-term read-contract assembly jest w `_build_ads_search_term_read_contracts`;
  nie wracaj do inline builderów `terms`, `safety`, `keyword match` ani `planner`.
- Search-term review assembly jest w `_build_ads_search_term_review_contracts`;
  nie wracaj do inline `review_summary`/`ngram` construction. Hydration action IDs
  pozostaje osobnym późniejszym krokiem.
- Candidate read-contract assembly jest w `_build_ads_candidate_read_contracts`;
  nie wracaj do inline `custom_segments`/`negative_keywords` construction.
- Campaign-triage i optimizer readiness assembly jest w
  `_build_ads_campaign_optimizer_contracts`; nie wracaj do inline konstrukcji
  tych dwóch kontraktów.
- Sections i blocked-handoff assembly jest w
  `_build_ads_sections_and_blocked_handoff`; nie wracaj do inline listy sekcji
  ani fail-closed handoffu.
- Decision queue response assembly jest w `_build_ads_decision_queue_response`;
  nie wracaj do inline wywołania `_ads_decision_queue` z `build_ads_diagnostics`.
- Typed response construction jest w `_build_ads_diagnostics_response`; nie wracaj
  do inline `AdsDiagnosticsResponse` constructor. Label hydration pozostaje osobnym
  seamem.
- Lifecycle label hydration jest w `_hydrate_ads_response_labels`; nie zmieniaj
  kolejności review-gate labels → marketer labels ani polskiego copy.
- Search contract-label hydration jest w `_hydrate_ads_search_contract_labels`;
  nie wracaj do inline summary/negative-keyword/keyword-match label updates.
- Budget/performance contract-label hydration jest w
  `_hydrate_ads_budget_performance_contract_labels`; nie wracaj do inline budget,
  recommendation, impression-share ani change-history label updates.
- Optimizer/change-impact contract-label hydration jest w
  `_hydrate_ads_optimization_contract_labels`; nie wracaj do inline readiness ani
  change-impact label updates.
- Core campaign/business/custom/derived label hydration jest w
  `_hydrate_ads_core_contract_labels`; nie wracaj do inline tych czterech grup.
- Summary decision/candidate compaction jest w `_prepare_ads_summary_compaction`;
  nie wracaj do inline top-decision selection ani fallback row limits.

## Dowody

- `tests/api_contracts/test_ads_contracts.py` przechodzi w całości.
- Ruff, mypy, complexity audit i `git diff --check` przechodzą.
- Runtime po restarcie: `/api/health` `ok`; `/api/ads/diagnostics` zwraca
  `live_data_available=true`; `/api/metrics/status` raportuje 98 899 metric facts
  i 4 564 refresh runs.
- Browser proof po restarcie: `.local-lab/proof/ads-summary-compaction.png`;
  `/ads-doctor` pokazuje kolejkę decyzji, dowody, świeżość Ads/GA4 i blokady
  ROAS/przychód/waste bez technicznego payloadu above the fold.
- Zmniejszenie `ads_diagnostics.py`: 358 linii.

## Nie robić ponownie

- Nie wracać do optimizer-readiness assembly w `ads_diagnostics.py`.
- Nie usuwać blokad twierdzeń ani `apply` safety podczas kolejnych refaktorów.

## Następny slice

Reconciliation, search-term, candidate, optimizer, sections, blocked-handoff,
decision_queue, response model, wszystkie label hydration groups i summary
decision/candidate compaction są domknięte. Następny kandydat to summary response
field compaction po świeżym complexity/review; zachowaj marketer-facing labels,
evidence/source/freshness oraz ActionObject safety.

## Kontrola repo

- Po commicie: sprawdź `git rev-parse --short HEAD`, `git rev-parse
  --short origin/main` i `git status --short`; handoff używa symbolicznego HEAD,
  więc nie zostawia fałszywego hasha po swoim własnym pointer commicie.
- Przed kolejnym slice’em sprawdź health API, Ads diagnostics i aktualny complexity
  report.
