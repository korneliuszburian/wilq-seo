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
- Dwudziesty szósty seam: `packages/shared-schemas/src/social_publisher.ts`
  zawiera review-only social draft context i publisher context-pack (38 LOC),
  a `packages/shared-schemas/src/context_pack.ts` agreguje pełny API context
  pack (43 LOC); `index.ts` ma 227 LOC. Dedupe blocker, publish=false i
  evidence lineage wymuszone, focused gates przechodzą. Następny seam:
  remaining aggregate/type aliases.
- Dwudziesty siódmy seam: aliasy typów zostały przeniesione do
  `packages/shared-schemas/src/types.ts` (160 LOC), dzięki czemu
  `packages/shared-schemas/src/index.ts` ma 31 LOC i pełni tylko rolę export
  map. Publiczne nazwy pozostają kompatybilne; build/test shared-schemas,
  dashboard typecheck/lint oraz `git diff --check` przechodzą. Następny krok:
  świeży import/use audit i wybór kolejnego potwierdzonego seama.
- `wilq-seo-pidl` continuation: podstawowe zachowanie `/settings` zostało
  przeniesione do `apps/dashboard/src/routes/SettingsSurface.test.tsx` z
  `settingsSurface.fixture.ts`. Test bez App omnibusu sprawdza zdrowie źródeł,
  freshness, blokery decyzji i techniczne disclosure. App.test.tsx zmalał do
  9522 LOC; focused test 1/1, dashboard typecheck/lint i `git diff --check`
  przechodzą. Następny seam: pozostałe settings/source refresh behaviors.
- Kontynuacja `wilq-seo-pidl`: read-only refresh źródła została przeniesiona do
  `SettingsSourceRefresh.test.tsx`; fixture zawiera typed queued/completed
  refresh runs. Test dowodzi POST `vendor_read`, polling i finalnego komunikatu
  bez App omnibusu. `App.test.tsx` ma 9471 LOC; focused 2/2, dashboard
  typecheck/lint i `git diff --check` przechodzą. Następny seam: blocker/error
  path dla statusu refresh.
- Trzeci settings slice: polling/error path jest teraz w
  `SettingsSourceRefresh.test.tsx`; test dowodzi, że błąd odczytu statusu
  pozostawia blocker i przywraca retry CTA zamiast udawać świeżość. Focused
  2/2 w tym pliku, dashboard typecheck/lint i diff check przechodzą.
  `App.test.tsx` ma 9388 LOC. Następny seam: automatyczny refresh eligibility.
- Czwarty settings slice: API-owned `automatic_refresh.eligible` jest teraz
  pokryte w `SettingsSourceRefresh.test.tsx`; test dowodzi pojedynczego
  read-only POST-u, pollingu i wyniku końcowego bez oceniania eligibility w
  React. Focused 3/3, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 9388 LOC. Następny seam: aktywny run ukrywający CTA.
- `wilq-seo-pidl.1` zamknięty: warning duplicate-key pochodził z adversarialnego
  testu, który sześć razy zwracał ten sam obiekt Ahrefs. Fixture klonuje rekordy
  ze stabilnym sufiksem ID; App/Ahrefs focused 26/26 przechodzi bez warningu,
  dashboard typecheck/lint i diff check przechodzą. Brak zmian produkcji/API;
  browser proof nie był potrzebny dla fixture-only zmiany.
- Piąty settings slice: aktywny-run guard jest teraz pokryty w
  `SettingsSourceRefresh.test.tsx`; przy `refresh_allowed=false` i
  `active_run` CTA nie wykonuje POST-u, a operator widzi kolejkę. App/settings
  focused 29/29, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 9354 LOC. Następny seam: API terminal-state freshness.
- Szósty settings slice: terminal-state freshness jest teraz pokryte w
  `SettingsSourceRefresh.test.tsx`; świeży odczyt usuwa blocker, pokazuje
  status Aktywny i nie wykonuje kolejnego refreshu. App/settings focused 29/29,
  dashboard typecheck/lint i diff check przechodzą; `App.test.tsx` ma 9312 LOC.
  Następny seam: pozostałe partial/failed/unknown state matrix.
- Siódmy settings slice: macierz `partial/failed/unknown/blocked` została
  przeniesiona do `SettingsSourceRefresh.test.tsx` z typed helperem fixture.
  Każdy stan pokazuje API-owned next step i nie uruchamia retry/POST-u.
  App/settings focused 29/29, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 9243 LOC. Następny seam: pozostałe settings error paths.
- Ósmy slice `wilq-seo-pidl`: secondary utility route behavior przeniesiony do
  `GenericSurface.test.tsx`; `/google-sheets` i `/security` mają focused proof
  compact blockerów bez registry/payload dumpów. App + GenericSurface focused
  24/24, dashboard typecheck/lint i diff check przechodzą; `App.test.tsx` ma
  9222 LOC. Następny seam: system route technical disclosure.
- Dziewiąty slice: system-route technical disclosure przeniesiony do
  `SystemSurface.test.tsx` z kontrolowanymi typed connector/workflow fixtures.
  Test dowodzi audytowego widoku, eksperymentalnych obszarów i braku raw
  payloadów. App + System focused 19/19, dashboard typecheck/lint i diff check
  przechodzą; `App.test.tsx` ma 9197 LOC. Następny seam: actions route proof.
- Dziesiąty slice: actions route proof przeniesiony do
  `ActionsSurface.test.tsx` z kontrolowanymi ActionObject fixtures i
  mockowanym API boundary. Test dowodzi marketer-facing kolejki, bezpiecznej
  akcji, lifecycle oraz ukrycia raw IDs/registry dumpów. App + Actions focused
  18/18, dashboard typecheck/lint i diff check przechodzą; `App.test.tsx` ma
  9152 LOC. Następny seam: mutation-readiness loading proof.
- Jedenasty slice: `ActionsSurface.test.tsx` ma teraz kontrolowany pending
  mutation-readiness promise; test dowodzi, że pierwsza akcja, blocker i CTA
  pozostają użyteczne podczas ładowania, a po resolve pojawia się
  `podgląd gotowy`. App + Actions focused 18/18, dashboard typecheck/lint i
  diff check przechodzą; `App.test.tsx` ma 9128 LOC. Następny seam: pozostające
  actions/diagnostic surfaces.
- Dwunasty slice: Ads Doctor source/contract proof przeniesiony do
  `AdsDoctorSurface.test.tsx`; zachowano evidence/action summaries, blocked
  claims, typed panel fields i brak raw payloadów/legacy routes. Ads + App
  focused 16/16, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 8914 LOC. Następny seam: Custom Segments diagnostic proof.
- Trzynasty slice: Custom Segments source/contract proof przeniesiony do
  `CustomSegmentsDiagnosticSurface.test.tsx`; zachowano validation status,
  missing-read i blocked-claim labels, evidence/action summaries oraz preview
  card, bez raw payloadów i legacy formatterów. App + Custom Segments focused
  15/15, dashboard typecheck/lint i diff check przechodzą; `App.test.tsx` ma
  8892 LOC. Następny seam: legacy operating routes.
- Czternasty slice: zachowanie ukrytego `/ads-doctor/search-terms` oraz kontrakt
  Ahrefs przeniesione do `LegacyOperatingRoutes.test.tsx`; test renderuje
  bezpieczny link do `/ads-doctor`, blocker i brak registry dumpów. App + legacy
  focused 14/14, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 8874 LOC. Następny seam: workflow route proof.
- Piętnasty slice: workflow route proof przeniesiony do
  `WorkflowsSurface.test.tsx`; kontrolowany fixture API dowodzi decyzji procesu,
  brakujących kontraktów, zablokowanych twierdzeń, persisted run oraz disclosure
  evidence/action. App + workflow focused 13/13, dashboard typecheck/lint i diff
  check przechodzą; `App.test.tsx` ma 8831 LOC. Następny seam: knowledge route.
- Szesnasty slice: knowledge route proof przeniesiony do
  `KnowledgeSurface.test.tsx`; kontrolowany typed API fixture dowodzi kolejki
  review, blokady twierdzeń, braku raw registry oraz użytecznego layoutu podczas
  ładowania operating map. App + knowledge focused 13/13, dashboard typecheck/
  lint i diff check przechodzą; `App.test.tsx` ma 8786 LOC. Następny seam:
  Merchant route.
- Siedemnasty slice: Merchant source/contract proof przeniesiony do
  `MerchantDiagnosticSurface.test.tsx`; zachowano typed action/evidence labels,
  readiness blockers, bezpieczne disclosure i brak legacy formatterów/raw
  payloadów. Merchant + App focused 12/12, dashboard typecheck/lint i diff check
  przechodzą; `App.test.tsx` ma 8763 LOC. Następny seam: GA4 route.
- Osiemnasty slice: GA4 source/contract proof przeniesiony do
  `Ga4DiagnosticSurface.test.tsx`; zachowano evidence/action summaries,
  conversion-readiness blockers, review-only copy i brak payload preview/legacy
  formatterów. GA4 + App focused 12/12, dashboard typecheck/lint i diff check
  przechodzą; `App.test.tsx` ma 8749 LOC. Następny seam: content route.
- Dziewiętnasty slice: dwa content workflow contract proofs przeniesione do
  `ContentWorkflowDiagnosticSurface.test.tsx`; zachowano API-owned workbench,
  public/dev rozdział, draft-only publication gate, Polish review copy i brak
  legacy formatterów. Content + App focused 11/11, dashboard typecheck/lint i
  diff check przechodzą; `App.test.tsx` ma 8711 LOC. Następny seam: Localo.
- Dwudziesty slice: Localo source/contract proof przeniesiony do
  `LocaloDiagnosticSurface.test.tsx`; zachowano missing-read blocker, API-owned
  technical disclosure i brak legacy count/placeholder copy. Localo + App
  focused 10/10, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 8706 LOC. Następny seam: Social.

## Następny krok

- Po commit/push wybrać kolejny domain seam z `wilq-seo-ksiq` na podstawie
  aktualnego import/use audit. Nie wracać do connector schemas.
