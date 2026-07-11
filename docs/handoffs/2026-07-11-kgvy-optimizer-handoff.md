# Handoff — `kgvy` optimizer readiness seam

Data: 2026-07-11 20:05 Europe/Warsaw  
Ostatni commit: `327176f` (`docs: hand off next Ads decision seam`)  
`origin/main` = `327176f`

## Wykonane

- `build_optimizer_readiness_contract` i jego osiem typed readiness items są w
  `wilq/briefing/ads_optimizer.py`.
- `ads_diagnostics.py` deleguje do modułu, a response contract pozostaje ten
  sam. Zachowane są evidence IDs, source connectors, missing contracts,
  operator review gates, safe next steps oraz blokady CPA/ROAS/waste i mutacji.
- Nie przenoszono ponownie section/decision builderów już opisanych w Beadzie.

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
metric tiles albo marketer-label hydration. Preferowana granica to testowalny
builder decision queue, nie mechaniczny split bez testu zachowania.

## Kontrola repo

- Po commicie: `HEAD == origin/main == 327176f`, worktree czysty.
- Przed kolejnym slice’em sprawdź health API, Ads diagnostics i aktualny complexity
  report.
