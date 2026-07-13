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
- Ósmy seam: `packages/shared-schemas/src/ads_keyword_contracts.ts` zawiera
  keyword-match context row/read contract (40 LOC); `index.ts` ma 2 735 LOC.
  Eksporty i zależność `MetricFact` zachowane. Shared schema/dashboard lint,
  build, tests i typecheck przechodzą. Następny seam: custom-segment contracts.
- Dziewiąty seam: custom-segment preview/safety/forecast/candidate/read
  contracts są w `packages/shared-schemas/src/ads_custom_segments.ts` (177 LOC),
  a zależny Keyword Planner read contract w
  `packages/shared-schemas/src/ads_keyword_planner_contracts.ts` (34 LOC);
  `index.ts` ma 2 548 LOC. Payloady/eksporty zachowane, wszystkie focused gates
  przechodzą. Następny seam: negative-keyword contracts.
- Dziesiąty seam: `packages/shared-schemas/src/ads_negative_keywords.ts`
  zawiera payload preview, candidate i read contract wykluczeń (95 LOC);
  `index.ts` ma 2 467 LOC. Zależności keyword-match, MetricFact i
  ActionPreview zachowane, focused gates przechodzą. Następny seam:
  Ads change-history i impact-readiness contracts.
- Jedenasty seam: `packages/shared-schemas/src/ads_change_history.ts` zawiera
  change-history row/read oraz impact-readiness row/read contracts (99 LOC);
  `index.ts` ma 2 377 LOC. Read-only evidence/apply safety bez zmian, focused
  gates przechodzą. Następny seam: Ads decision/summary contracts.
- Dwunasty seam: `packages/shared-schemas/src/ads_decisions.ts` zawiera Ads
  decision queue item i operator summary (165 LOC); `index.ts` ma 2 240 LOC.
  Diagnostyka nadal korzysta ze stabilnego barrel, payloady bez zmian, focused
  gates przechodzą. Następny seam: Ads freshness i diagnostics response.
- Trzynasty seam: `packages/shared-schemas/src/ads_diagnostics.ts` zawiera Ads
  freshness assessment i pełny diagnostics response (89 LOC); `index.ts` ma
  2 161 LOC. Eksporty, endpointy i payloady bez zmian; focused gates przechodzą.
  Następny seam: Merchant diagnostic sections/response.
- Czternasty seam: `packages/shared-schemas/src/merchant_diagnostics.ts`
  zawiera sekcje, issue clusters, decision queue, freshness/unknowns, product
  readiness i Merchant diagnostics response (307 LOC); `index.ts` ma 1 872 LOC.
  Connector/evidence/action contracts bez zmian, focused gates przechodzą.
  Następny seam: Content diagnostic contracts.
- Piętnasty seam: `packages/shared-schemas/src/content_diagnostics.ts` zawiera
  content diagnostic section, Ahrefs candidate/cross-check, decision queue,
  operator summary, GSC contract, marketer decision i diagnostics response
  (264 LOC); `index.ts` ma 1 623 LOC. Content freshness współdzieli istniejący
  `contentWorkflow` contract, focused gates przechodzą. Następny seam: Content
  preflight contracts.
- Szesnasty seam: `packages/shared-schemas/src/content_preflight.ts` zawiera
  `ContentPreflightItem` oraz `ContentPreflightResponse` (50 LOC); `index.ts`
  ma 1 580 LOC. Statusy i gate'y create/draft/WordPress/canonical/duplicate bez
  zmian, focused gates przechodzą. Następny seam: GA4 diagnostic contracts.
- Siedemnasty seam: `packages/shared-schemas/src/ga4_diagnostics.ts` zawiera
  GA4 diagnostic sections, decision items, conversion readiness, freshness,
  operator summary i response (152 LOC); `index.ts` ma 1 440 LOC. Rozdział
  jakości ruchu od braków pomiaru bez zmian, focused gates przechodzą. Następny
  seam: Localo diagnostic contracts.
- Osiemnasty seam: `packages/shared-schemas/src/localo_diagnostics.ts` zawiera
  access probe, diagnostic sections, read-contract status, decision queue,
  operator summary i response (145 LOC); `index.ts` ma 1 308 LOC. Blokady
  braku rankingów/dowodów Localo bez zmian, focused gates przechodzą. Następny
  seam: Ahrefs diagnostic contracts.
- Dziewiętnasty seam: `packages/shared-schemas/src/ahrefs_diagnostics.ts`
  zawiera Ahrefs sections, decision items, gap records/read contract, operator
  summary i response (174 LOC); `index.ts` ma 1 146 LOC. Cross-check
  GSC/WordPress i status `manual_required` jawne, focused gates przechodzą.
  Następny seam: Expert/knowledge contracts.
- Dwudziesty seam: `packages/shared-schemas/src/expert_contracts.ts` zawiera
  ExpertRule/Summary/Capability (43 LOC), a
  `packages/shared-schemas/src/knowledge_contracts.ts` zawiera taxonomy,
  sources, cards, playbooks, compiler result, bindings i operating map
  (166 LOC); `index.ts` ma 961 LOC. Lifecycle/source lineage jawne, focused
  gates przechodzą. Następny seam: Command Center contracts.
- Dwudziesty pierwszy seam: `packages/shared-schemas/src/core_contracts.ts`
  zawiera `DecisionState` i `Opportunity` (45 LOC), a
  `packages/shared-schemas/src/command_center.ts` zawiera brief/demo/action
  plan, DailyDecision, WorkOrder, DailyCheck i Command Center response
  (222 LOC); `index.ts` ma 719 LOC. Dowody, freshness, next step i blokady bez
  zmian, focused gates przechodzą. Następny seam: Workflow contracts.
- Dwudziesty drugi seam: `packages/shared-schemas/src/workflow_contracts.ts`
  zawiera Workflow definition, input/output i run schemas (68 LOC); `index.ts`
  ma 662 LOC. Social history pozostaje osobnym kontraktem, status/evidence/
  action output bez zmian, focused gates przechodzą. Następny seam: Demand Gen
  readiness.
- Dwudziesty trzeci seam: `packages/shared-schemas/src/demand_gen.ts` zawiera
  Demand Gen readiness contract z kampaniami, assetami, landing quality, mode
  review i safety gates (89 LOC); `index.ts` ma 580 LOC. Blokady claimów i
  review-only apply bez zmian, focused gates przechodzą. Następny seam: Social
  history contracts.
- Dwudziesty czwarty seam: `packages/shared-schemas/src/social_history.ts`
  zawiera inventory source, discovery seed, metadata-only inventory i import
  audit (79 LOC); `index.ts` ma 511 LOC. Duplicate-free/publish claims nadal
  zablokowane do review, raw post bodies zabronione, focused gates przechodzą.
  Następny seam: WordPress authoring contracts.
- Dwudziesty piąty seam: `packages/shared-schemas/src/wordpress_authoring.ts`
  zawiera readiness/discovery, dev workspace profile, write boundary oraz
  draft payload preview/request/response (236 LOC); `index.ts` ma 287 LOC.
  Draft-only, publish=false, destructive-update=false i ActionObject gate
  pozostają wymuszone, focused gates przechodzą. Następny seam: Social
  publisher/context-pack contracts.

## Następny krok

- Po commit/push wybrać kolejny domain seam z `wilq-seo-ksiq` na podstawie
  aktualnego import/use audit. Nie wracać do connector schemas.
