# Handoff: `3gre` dashboardowy auto-refresh — 2026-07-12

## Decyzja

Dashboard `/settings` wykonuje teraz bez ręcznego rytuału tylko te read-only
odczyty, które API jawnie oznaczy jako `automatic_refresh.eligible`. Nie
ustala stale, cooldownu ani bezpieczeństwa w React. Każdy connector identity
jest zlecany najwyżej raz w danym mount. POST `queued` przechodzi przez
istniejący GET refresh-run do stanu terminalnego; dopiero wtedy odświeżane są
source i API-wskazane decision view-models.

## Dowody

- `apps/dashboard/src/routes/GenericSurface.tsx`: istniejący refresh endpoint
  dostaje `mode=vendor_read` i `run_async=true`; multi-run polling zachowuje
  statusy kolejki/w trakcie/terminalne. Po terminalnym wyniku invalidowany jest
  cache źródeł oraz tylko cache decyzji z `refresh_state.affected_decisions`.
  Nieudany GET statusu pokazuje blocker „stan niepotwierdzony” i pozwala ponowić,
  bez przypisywania błędu vendorowi.
- `apps/dashboard/src/routes/App.test.tsx`: automatyczny trigger wysyła jeden
  POST dla API-eligible GA4, zero POST dla cooldown i active-run fixture, a
  payload nie jest write-capable. `partial` i `failed` pozostają widocznymi
  API-owned stanami bez automatycznej próby ponowienia. Istniejący test nadal
  sprawdza manualny read-only refresh oraz wynik odczytu.
- Dashboard: focused Vitest `App.test.tsx` + `RegistryPanels.test.tsx` 38/38,
  typecheck, lint i production build przechodzą. `git diff --check` i changed
  complexity audit (0 violations) przechodzą.
- Managed runtime: API i dashboard są zdrowe. Przez UI zlecono tylko read-only
  joby; Google Ads, Merchant Center i Localo wróciły do `ready`. Screenshoty
  desktop/mobile: `.local-lab/proof/continuation-2026-07-12/3gre-settings-terminal-{desktop,mobile}.png`.
- Mutation readiness WordPress nadal zwraca `ready_to_request_apply=false`,
  `vendor_write_possible=false` oraz `would_attempt_vendor_write=false`.

## Granice

Nie dodano endpointu, ActionObjecta, adaptera write ani reguły biznesowej w
dashboardzie. `automatic_refresh` pozostaje API-owned policy z `xu5s`.
Nieodświeżalne stany (`missing_credentials`, `unknown`, `partial`, `failed`,
`blocked`, aktywny run i cooldown) nie spełniają warunku triggera.

## Beads

- `wilq-seo-3gre` jest zamknięty: acceptance dotyczące one-shot, queued →
  terminal, API-scoped invalidacji, testów i browser proof jest pokryte.
- `wilq-seo-4wwo` jest zamknięty: stale warning, active run oraz
  partial/failed/status-read-error state mają focused proof; nie tworzyć drugiej
  implementacji auto-refresh.

## Następny krok

Zacommitować i wypchnąć domknięty slice, następnie kontynuować `jnra` od
następnego faktycznie potwierdzonego seam z `service.py`.
