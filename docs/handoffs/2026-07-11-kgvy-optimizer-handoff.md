# Handoff — `kgvy` optimizer readiness seam

Data: 2026-07-11 20:05 Europe/Warsaw  
Ostatni commit: `eead305` (`refactor: extract Ads blocked decision branch`)  
`origin/main` = `eead305`

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

## Dowody

- `tests/api_contracts/test_ads_contracts.py` przechodzi w całości.
- Ruff, mypy, complexity audit i `git diff --check` przechodzą.
- Runtime po restarcie: `/api/health` `ok`; `/api/ads/diagnostics` zwraca
  `live_data_available=true` i blokady niedozwolonych twierdzeń.
- Zmniejszenie `ads_diagnostics.py`: 358 linii.

## Nie robić ponownie

- Nie wracać do optimizer-readiness assembly w `ads_diagnostics.py`.
- Nie usuwać blokad twierdzeń ani `apply` safety podczas kolejnych refaktorów.

## Następny slice

Ponownie sprawdzić `bd ready` i wybrać kolejną nieprzeniesioną granicę `kgvy`:
następny mały fragment metric tiles albo marketer-label hydration. Każdy tile
fragment rozbijać na małe helpery; nie przenosić całego dispatchera jako nowego
monolitu.

## Kontrola repo

- Po commicie: `HEAD == origin/main == eead305`, worktree czysty.
- Przed kolejnym slice’em sprawdź health API, Ads diagnostics i aktualny complexity
  report.
