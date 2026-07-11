# Handoff — `kgvy` optimizer readiness seam

Data: 2026-07-11 20:05 Europe/Warsaw  
Ostatni commit: `0b7567d` (`refactor: extract Ads campaign metric tiles`)  
`origin/main` = `0b7567d`

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

- Po commicie: `HEAD == origin/main == 0b7567d`, worktree czysty.
- Przed kolejnym slice’em sprawdź health API, Ads diagnostics i aktualny complexity
  report.
