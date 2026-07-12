# Handoff: `jnra` latest Ads metric facts — 2026-07-12

## Decyzja

Polityka wyboru metric facts z najnowszego Google Ads vendor-read została
przeniesiona do istniejącego `wilq/actions/google_ads/business_context.py`.
Builder wymaga completed run, `vendor_data_collected`, evidence IDs i filtruje
wyłącznie `source_connector=google_ads`; service dostarcza callback do metric
store. Nie zmieniono evidence lineage, freshness, ActionObject ani write gates.

## Dowód produktu

- Ads strategy detail: HTTP 200 w `0.015912 s`, 2 evidence IDs,
  `kontrola WILQ poprawna`, `apply_allowed=false`, `zapis zmian zablokowany`.
- Localo detail: HTTP 200 w `0.013661 s`, 10 metryk i `apply_allowed=false`;
  brak regresji wspólnego action registry.
- `/api/actions` po restarcie zwraca 21 akcji; Ads campaign/recommendation
  actions zachowują metric facts i evidence z Google Ads.
- Browser first viewport: decyzja Ads, blocker i technical disclosure:
  `.local-lab/proof/continuation-2026-07-12/ads-latest-facts-live.png`
  oraz `ads-latest-facts-live.txt`.
- Nie wykonano review/confirm/impact/apply POST ani vendor write.

## Weryfikacja

- Focused Ads/review/payload tests: 10 passed.
- Ruff, mypy, complexity i `git diff --check`: zielone; znany frozen-file
  budget `service.py` pozostaje jedynym findingiem.
- Managed API/dashboard i live evidence: zielone.

## Beads

- `wilq-seo-jnra` pozostaje `in_progress`; latest metric facts seam jest domknięty.
- `c9h9.4`, `c9h9.11` i `zbre` pozostają zamknięte.
- Następny wybór wymaga świeżego review orchestratora, bez powrotu do gotowych
  Ads/payload/review/cache boundaries.

