# Handoff: `jnra` Google Ads vendor-read selection — 2026-07-12

## Decyzja

Selekcja najnowszego Google Ads `vendor_read` została przeniesiona z
`wilq/actions/service.py` do istniejącego
`wilq/actions/google_ads/business_context.py`:

- status-probe i inne tryby są ignorowane;
- wybór jest deterministyczny po `completed_at` (fallback `started_at`) oraz
  `id`, więc równy timestamp nie zmienia kolejności losowo.

Service nadal pobiera refresh runs i deleguje; evidence IDs, freshness,
business-context gates, preview i ActionObject safety loop pozostają bez zmian.

## Dowód produktu

- Ads strategy detail po managed restarcie: HTTP 200 w `0.017025 s`, 2 evidence
  IDs (`ev_connector_google_ads_status`, `ev_refresh_refresh_google_ads_d71876fb0c4d`),
  5 required checks, `kontrola WILQ poprawna`, `apply_allowed=false`,
  `zapis zmian zablokowany`.
- Localo detail: HTTP 200 w `0.012680 s`, 10 metryk, evidence i
  `apply_allowed=false` — brak regresji wspólnego registry.
- Browser first viewport: decyzja Ads, blocker i technical disclosure:
  `.local-lab/proof/continuation-2026-07-12/ads-vendor-read-selection-live.png`
  oraz `ads-vendor-read-selection-live.txt`.
- Nie wykonano review/confirm/impact/apply POST ani vendor write.

## Weryfikacja

- Focused Ads/review/payload tests: 9 passed.
- Ruff, mypy, complexity i `git diff --check`: zielone; jedyny complexity
  finding to znany frozen-file budget `service.py`.
- Managed API/dashboard i live evidence: zielone.

## Beads

- `wilq-seo-jnra` pozostaje `in_progress`; Ads read-selection seam jest domknięty.
- `c9h9.4`, `c9h9.11` i `zbre` pozostają zamknięte.
- Następny seam wymaga świeżego review pozostałego orchestratora, bez powrotu do
  gotowych payload/readiness/review/cache boundaries.

## Commit

Implementacja i handoff: `64f12529` (`refactor: centralize Ads vendor read selection`).
