# Handoff — `v9ab.5` ExpertRule contract

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Pierwszy zakres `v9ab.5` jest wykonany: ExpertRule nie jest już tylko opisem
diagnostyki. Każda realna platform-trap rule może teraz jawnie opisać warunek,
wymagane źródła/metriki/okno, segmentację, false-positive checks, blocked states,
safe recommendation, forbidden conclusions, safety level i eval case.

## Wykonane

- `ExpertRule` i `ExpertRuleSummary` mają typed pola kontraktu bez zmiany
  istniejących publicznych endpointów.
- Loader YAML waliduje listy, optional copy i `safety_level`; platform trap
  pozostaje osobnym typed kontraktem.
- Pięć rule packów ma wypełnione wymagane pola i source IDs; Ads/GA4/Merchant
  diagnostics nadal odwołują się do rule IDs.
- Nie przenoszono logiki do skilli, Reacta ani promptów.

## Dowody

- `tests/api_contracts/test_platform_trap_contracts.py` przechodzi wraz z
  focused Ads/GA4/Merchant contracts.
- Ruff, mypy, complexity (`0` changed-code violations) i `git diff --check`
  przechodzą.
- Live po managed restart: `/api/health` `ok`, `/api/metrics/status` 98 915
  facts / 4 572 refresh runs; `/api/expert/rules` zwraca pełne pola contractu.
- Ads live section zawiera `ads_platform_traps_v1`, Merchant decision queue
  zawiera `merchant_platform_traps_v1`.
- Browser proof po restarcie: `.local-lab/proof/v9ab5-expertrule-merchant-viewport.png`;
  first viewport utrzymuje stale blocker i review-only posture.

## Nie robić ponownie

- Nie dublować pól `PlatformTrapContract` w skillach ani dashboardzie.
- Nie traktować `safety_level` jako zgody na write; ActionObject loop pozostaje
  jedyną ścieżką zapisu.
- Nie zamieniać required metrics w zmyślone live metryki — to kontrakt wymagań,
  a nie dowód odczytu.

## Następny slice

Po zamknięciu `v9ab.5` roadmapa odblokowuje `wilq-seo-v9ab.7`: pierwszy
API-owned `/wilq-daily-check` workflow. Najpierw wykorzystaj istniejące
diagnostyki, evidence IDs, source connectors, freshness i rule IDs; nie twórz
równoległego product brain ani nowego endpointu, jeśli istniejąca granica może
zostać rozszerzona.

## Repo

Przed kolejnym slice’em sprawdź `HEAD == origin/main`, czysty worktree i aktualne
`bd ready --json`.
