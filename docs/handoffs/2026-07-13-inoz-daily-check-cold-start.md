# Handoff — `inoz` daily-check cold start — 2026-07-13

## Decyzja

Nie zamykam `wilq-seo-inoz`. Wprowadzony slice ogranicza daily-check do
istniejącego runtime `connectors + command_center` i serializuje budowę
base-cache z ponownym odczytem cache, ale nie usuwa jeszcze opóźnienia pierwszego
requestu po readiness.

## Dowody

- `wilq/briefing/daily_runtime.py`: `DailyCheckRuntime` oraz lock/re-check dla
  współbieżnej budowy base-cache.
- `wilq/briefing/daily_check.py`: korzysta wyłącznie z wąskiego runtime.
- `apps/api/wilq_api/main.py`: prewarm wywołuje `build_daily_check_runtime`.
- Testy: `tests/test_daily_runtime_prewarm.py`,
  `tests/test_daily_check_runtime.py`, daily-check/command-center contracts.
- Ruff, mypy i `git diff --check` przechodzą.
- Managed restart HTTP: pierwszy `/api/marketing/daily-check` `13.991204 s`,
  następne `2.733938 s` i `2.824721 s`; API output pozostaje typed i bez
  vendor writes.
- Browser proof: `/content-workflow` pokazuje konkretną stronę publiczną,
  sygnały/braki, dev draft/ACF, sekcje szkicu i brak automatycznej publikacji;
  screenshot zapisany przez agent-browser jako
  `/home/krn/.agent-browser/tmp/screenshots/screenshot-1783971875381.png`.

## Następny krok

Zdecydować, czy gotowość API ma czekać na ukończenie prewarmu, czy daily-check
ma dostać jawny typed stan `prewarm_in_progress` z bezpiecznym retry. Nie
zmieniać metryk, evidence ani safety tylko po to, by ukryć cold latency.
