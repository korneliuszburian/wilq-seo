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
- Trzeci seam: `packages/shared-schemas/src/marketing.ts` zawiera
  MarketingBrief/TacticalQueue schemas i aliasy typów; `index.ts` ma 3 532
  linii. Zależności MetricFact i connector summary nadal są importowane z
  istniejącego modułu, bez duplikacji i bez zmiany payloadów.
- Czwarty seam: `packages/shared-schemas/src/ads_campaigns.ts` zawiera Ads
  campaign/account/business/budget/readiness schemas (384 LOC), importując
  MetricFact i ActionPreview z istniejących domen. `index.ts` ma 3 168 LOC;
  shared schema/dashboard lint, build, tests i typecheck przechodzą.
- Piąty seam: `packages/shared-schemas/src/ads_review_contracts.ts` zawiera
  recommendations oraz impression-share schemas (124 LOC). `index.ts` ma
  3 057 LOC; shared schema/dashboard lint, build, tests i typecheck przechodzą.
- Szósty seam: campaign-triage i optimizer-readiness schemas dołączono do
  `ads_campaigns.ts` (516 LOC); `index.ts` ma 2 928 LOC. Review-only,
  blocked-claim i apply safety contracts pozostały bez zmian. Następny seam:
  search-term contracts.
- Siódmy seam: `packages/shared-schemas/src/ads_search_terms.ts` zawiera
  search-term metrics/review/n-gram/safety schemas (175 LOC); `index.ts` ma
  2 767 LOC. Read-only/safety eksporty zachowane, shared schema/dashboard
  lint, build, tests i typecheck przechodzą. Następny seam: keyword-match albo
  custom-segment contracts.

## Następny krok

- Po commit/push wybrać kolejny domain seam z `wilq-seo-ksiq` na podstawie
  aktualnego import/use audit. Nie wracać do connector schemas.
