# Handoff — `v9ab.7` daily-check workflow v0

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Dodano pierwszy API-owned daily-check projection bez tworzenia drugiego
runtime’u ani kopiowania logiki do dashboardu/skilla. Endpoint
`GET /api/marketing/daily-check` kompiluje istniejący command-center runtime do
typed `DailyCheckResult`.

## Wykonane

- `wilq/briefing/daily_check.py` mapuje istniejące decyzje, konektory i freshness
  do operatorowej kolejki po polsku.
- Wynik zawiera checked/skipped connectors, anomalies/risks/opportunities,
  blocked recommendations, safe next actions, do-not-touch, evidence IDs,
  source connectors, expert rule IDs i freshness.
- Brak pełnego śladu albo stale/missing source jest blockerem, nie rekomendacją.
- `do_not_touch` jawnie blokuje write/publish bez preview, review, confirm i audytu.
- Nie dodano vendor writes ani logiki biznesowej w React.

## Dowody

- `tests/api_contracts/test_daily_check_api.py` i istniejące
  `test_daily_check_contracts.py` przechodzą.
- Focused/full expert/Ads/GA4/Merchant/source suites, Ruff, mypy, complexity
  (`0` changed-code violations) i `git diff --check` przechodzą.
- Live API po restarcie: health `ok`; `/api/marketing/daily-check` zwraca
  `status=blocked`, 9 checked i 3 skipped connectors, freshness `stale`, 21
  evidence IDs, 8 expert rule IDs i 1 do-not-touch item.
- Browser proof: `.local-lab/proof/daily-check-command-center.png`; first
  viewport pokazuje 4 decyzje, 4 krytyczne blokady, odświeżenie źródeł,
  evidence i „Nie wolno dziś twierdzić” bez technicznego payloadu.

## Nie robić ponownie

- Nie budować drugiego cache/runtime’u dla daily-check; używaj
  `build_daily_runtime` i istniejących view-modeli.
- Nie zmieniać stale w `review_ready`; obecny live blocker jest prawidłowy.
- Nie traktować rule IDs ani required metrics jako dowodu live metryk.

## Następny slice

Po zamknięciu `v9ab.7` odblokowany jest `wilq-seo-v9ab.8`: false-positive
guards dla daily recommendations (stale connector, low volume, no baseline,
missing conversion, date window, source conflict i multi-source required).

## Repo

Przed kolejnym slice’em sprawdź `HEAD == origin/main`, czysty worktree i
`bd ready --json`; następnie claimuj `v9ab.8`.
