# Handoff: `xu5s` API-owned auto-refresh eligibility — 2026-07-12

## Decyzja

Dodano `ConnectorRefreshState.automatic_refresh` jako typed policy API, a nie
regułę wymyślaną przez React. Kontrakt zwraca `eligible`, reason, label, safe
next step i 900-sekundowy cooldown. W tym slice nie uruchomiono automatycznego
odczytu vendorów: policy jest jedynie bezpiecznym wejściem dla późniejszego
dashboardowego loopa.

## Dowody

- `wilq/schemas/core.py`: enum reason i typed trigger policy; statyczne
  metric-dimension labels wydzielone do osobnej funkcji, aby touched-schema
  complexity gate pozostał zielony.
- `wilq/connectors/registry.py`: eligibility jest true tylko dla stale,
  configured, read-capable connectora bez credentials i bez aktywnego/świeżo
  zakończonego odczytu. `unknown`, `partial`, `failed`, `blocked`, missing,
  active run i cooldown są fail-closed.
- `packages/shared-schemas`: dashboard parsuje ten sam kontrakt, a zły reason
  enum jest odrzucany.
- Backend `tests/api_contracts/test_connector_refresh_redaction_contracts.py`:
  6/6; shared schemas 34/34; dashboard focused `App`/`RegistryPanels` 31/31;
  dashboard typecheck, lint i build; Ruff, mypy, complexity (0 violations) i
  `git diff --check` przechodzą.
- Managed restart: API health `ok`. Live `GET /api/connectors` wskazuje
  `google_ads`, `google_merchant_center` i `localo` jako `eligible_stale`; nie
  wywołano POST refresh ani vendor write.

## Beads

- `wilq-seo-xu5s` jest domkniętym child taskiem `wilq-seo-4wwo`.
- `wilq-seo-4wwo` pozostaje otwarty: brakuje dashboardowego loopa, który
  konsumuje tylko `automatic_refresh.eligible` i istniejący async read-only
  endpoint.

## Następny slice

Utworzyć i wykonać osobny, bounded dashboard loop: jednorazowo zlecić async
refresh wyłącznie dla API-eligible stale connectora, obserwować istniejący run,
odświeżyć query caches po terminalnym statusie i nie powtarzać żądania podczas
cooldown/queued/running. Bez nowych endpointów i bez write-capable ActionObject.

## Pozostałe blokery

- Content queue: 1 actionable przy wymaganych 3; brak sztucznego trzeciego
  tematu.
- 2 konektory nadal nie mają credentials; policy poprawnie je blokuje.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
