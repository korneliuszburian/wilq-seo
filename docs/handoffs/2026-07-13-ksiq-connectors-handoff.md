# Handoff — 2026-07-13 — shared connector schemas

## Stan

- Commit slice: `d8e0a135` zawiera poprzedni Ads seam; schema slice jest
  przygotowany do osobnego commit/push po finalnym Bead update.
- `packages/shared-schemas/src/connectors.ts` jest domenowym entrypointem dla
  connector status/refresh, freshness, evidence, refresh runs, metric-store i
  connector summary.
- `index.ts` pozostaje kompatybilnym barrem i zmniejszył się z 4 199 do 4 069
  linii. Nie zmieniono endpointów, nazw eksportów ani runtime payloadów.

## Dowód

- Shared schemas: lint, `tsc --noEmit`, Vitest 34 passed / 10 skipped.
- Dashboard: focused Vitest 2/2, lint i typecheck.
- `git diff --check` przechodzi.

## Kolejny zakończony seam

- `packages/shared-schemas/src/actions.ts` zawiera ActionObject, review,
  preview, mutation readiness i audit schemas oraz ich aliasy typów.
- `MetricFactSchema` został przeniesiony do współdzielonego modułu danych,
  dzięki czemu ActionObject nie importuje product logic z barrel.
- `index.ts` ma 3 638 linii; `actions.ts` 417, `connectors.ts` 156. Dashboard
  typecheck/lint oraz shared schema test/build przechodzą.

## Następny krok

- Po commit/push wybrać kolejny domain seam z `wilq-seo-ksiq` na podstawie
  aktualnego import/use audit. Nie wracać do connector schemas.
