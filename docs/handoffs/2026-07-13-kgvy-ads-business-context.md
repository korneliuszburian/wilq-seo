# Handoff — `kgvy` Ads business-context action seam

Data: 2026-07-13 Europe/Warsaw

## Wykonane

`live_business_context_actions` jest w
`wilq/actions/google_ads/business_context.py`. Fasada
`wilq/actions/service.py` przekazuje jeden aktualny `ConnectorRefreshRun` i
evidence lineage do istniejącej domenowej factory. Nie dodano endpointu ani
drugiej ścieżki zapisu; ActionObject pozostaje review-only.

Commit: `3eb9fc9e refactor: move Ads business context action assembly`

## Dowód

- Ads/action contract tests przechodzą.
- Ruff i mypy przechodzą dla zmienionych modułów.
- Complexity audit: tylko istniejący budżet fasady `service.py`; brak nowego
  wzrostu frozen-file.
- Managed API: `health=ok`, live Ads read, 21 akcji, `/api/ads/diagnostics`
  zwraca 9 action IDs i 5 decyzji.
- `vendor_write_possible_count=0`.
- `/content-workflow` HTTP `200`.

## Nie powtarzać

Nie przenosić ponownie business-context/target/strategy action builders ani
nie tworzyć nowego registry. Kolejny split `kgvy` wymaga świeżej, wspólnej
granicy orchestration i testu parytetu; jeśli granicy nie ma, zostawić kod w
istniejącym ownerze.

## Pozostałe blokery produktu

- Content queue: świeża, ale 1 actionable z wymaganych 3.
- Service Profile: 12 kart, 0 approved production-depth.
- `v9ab.13`/`jst`: packet UAT jest gotowy, ale brak realnego review Wilku albo
  jawnego owner deferu.

