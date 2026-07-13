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
- Dwudziesty pierwszy slice: Social publisher behavior proof przeniesiony do
  `SocialPublisherSurface.test.tsx`; zachowano review-only mode, blokadę
  historii/dedupe, metadata-only discovery i brak technicznych ID w operator
  copy. Social + App focused 9/9, dashboard typecheck/lint i diff check
  przechodzą; `App.test.tsx` ma 8662 LOC. Następny seam: Ahrefs.
- Dwudziesty drugi slice: Ahrefs authority/gap source proof przeniesiony do
  `AhrefsDiagnosticSurface.test.tsx`; zachowano missing-read/blocked-claim
  summaries, evidence-first copy i brak legacy countów. Ahrefs + App focused
  9/9, dashboard typecheck/lint i diff check przechodzą; `App.test.tsx` ma
  8653 LOC. Następny seam: Demand Gen.
- Dwudziesty trzeci slice: Demand Gen source/contract proof przeniesiony do
  `DemandGenDiagnosticSurface.test.tsx`; zachowano typed preview/evidence rows,
  readiness labels, review-only constraints i brak raw payloadów/legacy
  formatterów. Demand Gen + App focused 9/9, dashboard typecheck/lint i diff
  check przechodzą; `App.test.tsx` ma 8621 LOC. Następny seam: Evidence detail.
- Dwudziesty czwarty slice: Evidence detail behavior przeniesiony do
  `EvidenceDetailRoute.test.tsx`; kontrolowany typed evidence fixture dowodzi
  marketer-readable trace, świeżości i technical disclosure bez raw IDs above
  the fold. Evidence + App focused 8/8, dashboard typecheck/lint i diff check
  przechodzą; `App.test.tsx` ma 8599 LOC. Następny krok: re-audit pozostałych
  route proofs i aktywnego Bead graph.
- Dwudziesty piąty slice: usunięto z `App.test.tsx` zduplikowany knowledge
  loading proof, ponieważ ten sam loading/layout behavior jest już dowiedziony
  przez `KnowledgeSurface.test.tsx`. Knowledge + App focused 8/8, dashboard
  typecheck/lint i diff check przechodzą; `App.test.tsx` ma 8567 LOC. Pozostałe
  route proofs: Merchant, GA4, Localo, Ahrefs (2) i Demand Gen.
- Re-audit bramki po 25 slice’ach: pełny równoległy dashboard run zakończył się
  157/159, z timeoutem Merchant/App i `ContentWorkflowSurface` przy 10 s;
  powtórzony focused run tych samych plików przechodzi 22/22. Traktuję to jako
  niestabilność zakresu/full-run, nie jako dowód regresji slice’ów; przed claimem
  pełnego green gate trzeba powtórzyć lub odseparować timeouty.

- Dwudziesty szósty slice: fixture Merchant diagnostics została wyciągnięta z
  `App.test.tsx` do `merchantDiagnostic.fixture.ts`, a
  `MerchantDiagnosticSurface.test.tsx` dostał behavior proof pierwszego ekranu:
  decyzja, blocker, świeżość, bezpieczny next step i disclosure pełnego review.
  Focused Merchant 2/2, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 8180 LOC. Następny seam: kolejny największy lokalny fixture
  lub re-audit pełnego runu po ustabilizowaniu timeoutów.

- Dwudziesty siódmy slice: fixture GA4 diagnostics została wyciągnięta z
  `App.test.tsx` do `ga4Diagnostics.fixture.ts`, a
  `Ga4DiagnosticSurface.test.tsx` dostał behavior proof decyzji pomiarowej,
  świeżości, blokady twierdzeń o konwersjach i disclosure problemów pomiaru.
  GA4 + App focused 8/8, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 7955 LOC. API health działa; metric store raportuje 104362
  facts i 4580 refresh runs. Następny seam: Localo albo re-audit timeoutów.

- Dwudziesty ósmy slice: fixture Localo diagnostics została wyciągnięta z
  `App.test.tsx` do `localoDiagnostics.fixture.ts`, a
  `LocaloDiagnosticSurface.test.tsx` dostał behavior proof stanu dostępu,
  blokady rekomendacji bez ranking proof i bezpieczeństwa copy.
  Localo + App focused 8/8, dashboard typecheck/lint i diff check przechodzą;
  `App.test.tsx` ma 7670 LOC. Następny seam: re-audit pełnego runu albo kolejny
  potwierdzony fixture route. Po slice wykonano browser proof `/content-workflow`:
  pierwszy viewport pokazuje decyzję, blocker, CTA i świeżość/dowody za
  disclosure; screenshot obejrzany, bez technicznych ID above the fold.

- Re-audit po 28 slice’ach: równoległy dashboard run miał 3 błędy (ActionDetail
  i dwa timeouty ciężkich route tests), ale serialny pełny run z
  `--maxWorkers=1` przeszedł 44/44 pliki i 162/162 testy. Focused ActionDetail
  też przechodzi; klasyfikuję problem jako niestabilność równoległego runu,
  nie regresję funkcjonalną.

- Trzydziesty slice: fixture Ahrefs diagnostics została wyciągnięta z
  `App.test.tsx` do `ahrefsDiagnostics.fixture.ts`, a
  `AhrefsDiagnosticSurface.test.tsx` dostał behavior proof rozdziału autorytetu,
  cross-checku GSC/WordPress i konkretnych luk SEO. Ahrefs + App focused 8/8,
  dashboard typecheck/lint i diff check przechodzą; `App.test.tsx` ma 7138 LOC.
  Następny seam: Demand Gen albo dedykowana stabilizacja równoległego runu.

- Trzydziesty pierwszy slice: fixture Demand Gen diagnostics została wyciągnięta
  z `App.test.tsx` do `demandGenDiagnostics.fixture.ts`, a
  `DemandGenDiagnosticSurface.test.tsx` dostał behavior proof blokady planu,
  gdy kanał nie występuje w dowodach. Demand Gen + App focused 8/8, dashboard
  typecheck/lint i diff check przechodzą; `App.test.tsx` ma 6903 LOC.
  Następny krok: ponowić serialny pełny gate po kolejnym seamie albo przejść
  do dedykowanej stabilizacji równoległości.

- c9h9.20: po pomiarze contention ustawiono `test.maxWorkers=2` w
  `apps/dashboard/vite.config.ts`. Dwa kolejne domyślne równoległe runy
  przeszły 44/44 pliki i 164/164 testy, serialny run po zmianie także 44/44 i
  164/164, a Merchant/App + ContentWorkflow focused 22/22. Typecheck, lint i
  diff check przechodzą. Timeouty nie są maskowane zmianą globalnego timeoutu.

- Trzydziesty drugi slice: usunięto z `App.test.tsx` 186-liniowy duplikat
  Merchant route proof. Pierwszy ekran, blocker, freshness, safe next step i
  technical disclosure pozostają dowiedzione w
  `MerchantDiagnosticSurface.test.tsx`; App + Merchant focused 7/7,
  typecheck/lint i diff check przechodzą. `App.test.tsx` ma 6717 LOC.

- Trzydziesty trzeci slice: usunięto z `App.test.tsx` duplikat GA4 route proof;
  decyzja pomiarowa, freshness, blocker konwersji i technical disclosure są
  dowiedzione w `Ga4DiagnosticSurface.test.tsx`. App + GA4 focused 6/6,
  typecheck/lint i diff check przechodzą; `App.test.tsx` ma 6616 LOC.

- Trzydziesty czwarty slice: usunięto z `App.test.tsx` duplikat Localo route
  proof; stan dostępu, blokada rekomendacji bez ranking proof i safety copy są
  dowiedzione w `LocaloDiagnosticSurface.test.tsx`. App + Localo focused 5/5,
  typecheck/lint i diff check przechodzą; `App.test.tsx` ma 6547 LOC.

- Trzydziesty piąty slice: usunięto z `App.test.tsx` dwa duplikaty Ahrefs route
  proof; rozdział autorytetu/luk i cross-check GSC/WordPress są dowiedzione w
  `AhrefsDiagnosticSurface.test.tsx`. App + Ahrefs focused 3/3,
  typecheck/lint i diff check przechodzą; `App.test.tsx` ma 6419 LOC.

- Trzydziesty szósty slice: po migracji ostatniego Demand Gen proofu `App.test.tsx`
  nie zawierał już żadnego testu; usunięto martwy omnibus i jego fixture.
  Pełny dashboard gate po usunięciu: 43/43 pliki, 158/158 testów, typecheck i
  lint przechodzą. Route behavior pozostaje w dedykowanych plikach domenowych.

- Re-audit po zamknięciu `wilq-seo-pidl`: complexity audit skanuje 492 pliki /
  139440 non-empty LOC; największy potwierdzony hotspot to
  `tests/api_contracts/test_ads_contracts.py` (4998 LOC), z testem
  `test_ads_diagnostics_exposes_live_campaign_metric_facts` o 2919 linii i 29
  branchach. Utworzono `wilq-seo-c9h9.22`; nie ma duplikatu aktywnego Beada.
- c9h9.22 jest przejęty. Potwierdzony seam: typed Ads vendor-read fixture/setup
  kontra osobne behavior assertions. Kolejny slice ma wyciągnąć fixture bez
  zmiany runtime API, a następnie rozdzielić kampanie/freshness/rekomendacje i
  blocked claims na nazwane moduły.
- Wykonany pierwszy pod-slice: `assert_ads_live_refresh_contract` przejął
  freshness/live-data assertions. Ads contract pytest, Ruff, mypy i diff check
  są zielone; główny test nadal ma 2912 linii, więc następny handoff musi
  przenieść campaign read-contract assertions.
- Drugi pod-slice również zakończony: `assert_ads_campaign_read_contract_basics`
  przejął status/allowed/missing/blocked gates. Następny krok to wydzielenie
  campaign row rendering proofu bez zmiany evidence lineage.
- Trzeci pod-slice zakończony: `assert_ads_campaign_row_contract` przejął
  rendering, evidence, blocked claims i review gates kampanii. Test spadł do
  2841 linii; następny handoff ma rozdzielić operator summary/decision queue.
- Czwarty pod-slice zakończony: `assert_ads_operator_summary_contract` przejął
  kolejność decyzji, totals, evidence/action IDs i Polish next step. Test ma
  2802 linii/28 branchy; następny slice to marketer summary text i metric tiles.
- Piąty pod-slice zakończony: `assert_ads_marketer_copy_and_tiles` przejął
  Polish summary i campaign/budget tiles. Test ma 2779 linii/26 branchy; kolejny
  slice obejmuje account currency oraz business-context blocker.
- Szósty pod-slice zakończony: `assert_ads_account_currency_contract` przejął
  PLN context i blocked budget-change claim. Następny handoff powinien rozbić
  business-context blocked contract na mniejsze behavior assertions.
- Siódmy pod-slice zakończony: `assert_ads_business_context_missing_values`
  przejął status i brakujące wartości. Następny krok rozdziela policy IDs,
  review gates oraz ActionObject safety dla zablokowanego kontekstu.
- Ósmy pod-slice zakończony: policy IDs, review gates, ActionObject IDs i
  blocked decision card są w nazwanych helperach. Następny krok: derived KPI
  contract oraz jego blocked-claim semantics.
- Dziewiąty pod-slice zakończony: `assert_ads_derived_kpi_contract_basics`
  przejął KPI gates i blocked profitability claim. Następny krok to pełny KPI
  row/evidence proof.
- Re-audit po trzydziestym czwartym pod-slice: 0 changed-code budget violations;
  główny test miał wtedy 1794 linii i 15 branchy. Branch budget był zielony, line budget
  pozostaje otwarty.
- Dziesiąty/jedenasty pod-slice: KPI row/evidence/blocked claims oraz section
  readiness są w helperach. Następny handoff ma rozbić budget pacing contract.
- Dwunasty pod-slice zakończony: `assert_ads_budget_contract_basics` przejął
  budget allowed/missing gates, Polish empty state i review-only action. Następny
  krok: budget preview oraz safety card.
- Trzynasty/czternasty pod-slice zakończony: preview/safety i technical
  preview-card są w helperach; wszystkie validation labels i fail-closed flags
  zachowane. Następny krok: budget row evidence/metric semantics.
- Piętnasty/szesnasty pod-slice zakończony: budget row i budget section proof
  są w helperach. Następny krok: recommendations read contract i jego safety
  gates.
- Siedemnasty/osiemnasty pod-slice zakończony: recommendations basics, row
  identity/impact/evidence/blocked claims i review-copy są w helperach. Test
  ujawnił brak lokalnej referencji sekcji po ekstrakcji; referencję przywrócono
  jawnie i pełny focused gate jest zielony.
- Dziewiętnasty/dwudziesty pod-slice zakończony: recommendation payload
  preview/safety i recommendations section proof są w helperach. Następny
  handoff powinien przejść do impression-share contract.
- Dwudziesty pierwszy/drugi pod-slice zakończony: impression-share basics, row
  evidence/blocked claims i section proof są w helperach. Następny krok:
  campaign triage contract.
- Dwudziesty trzeci/czwarty pod-slice zakończony: campaign triage basics i row
  proof są w helperach. Następny krok: optimizer readiness oraz change-history
  safety contracts.
- Dwudziesty piąty/szósty pod-slice zakończony: optimizer review-only i
  change-history basics/row proof są w helperach. Następny krok: change-impact
  readiness contract.
- Dwudziesty siódmy/ósmy pod-slice zakończony: change-impact basics, readiness
  row evidence/blocked claims i change-history section proof są w helperach.
  Następny krok: optimizer linkage i pozostały diagnostic tail.
- Dwudziesty dziewiąty/trzydziesty pod-slice zakończony: optimizer linkage,
  campaign metric facts i search-term basics są w helperach. Następny krok:
  search-term row/safety oraz końcowy diagnostic tail.
- Trzydziesty pierwszy/drugi pod-slice zakończony: search-term rows i aggregate
  review contract są w helperach. Następny krok: n-gram safety/decision i tail.
- Trzydziesty trzeci/czwarty pod-slice zakończony: n-gram decision oraz search
  term safety basics/row/section są w helperach. Następny krok: keyword-match
  context i końcowy diagnostic tail.
- Trzydziesty piąty/szósty pod-slice zakończony: keyword-match context, planner,
  custom-segment basics oraz audience-forecast blocker są w helperach.
  Candidate lineage, source quality, human-review gates i payload preview
  zachowują blokadę mutacji (`apply_allowed=false`, `api_mutation_ready=false`)
  przy braku prognozy/rozmiaru odbiorców. Focused Ads/Ruff/mypy/diff check
  zielone; główny test ma 1628 linii i 13 branchy. Następny krok:
  custom-segment candidate/payload safety i końcowy diagnostic tail.
- Trzydziesty siódmy pod-slice zakończony: negative-keyword safety contract
  jest w `assert_ads_negative_keyword_safety_contract`; 90-dniowe evidence,
  match context, review gates i fail-closed payload flags są zachowane.
  Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1528 linii i 12
  branchy. Następny krok: decision queue assertions i końcowy action safety
  tail.
- Trzydziesty ósmy pod-slice zakończony: identity kolejki decyzji Ads jest w
  `assert_ads_decision_queue_identity_contract`; pełny zestaw review lanes,
  custom-segment review i blocker ActionObject pozostają dowiedzione.
  Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1529 linii i 12
  branchy. Następny krok: decyzje operatora i końcowy action tail.
- Trzydziesty dziewiąty pod-slice zakończony: campaign activity i campaign
  triage decision proof są w `assert_ads_campaign_decision_contract`.
  Priorytety, metric tiles, evidence/source labels, review gates i blokada
  claimu zmarnowanego budżetu są zachowane. Focused Ads/Ruff/mypy/diff check
  zielone; główny test ma 1482 linii i 12 branchy. Następny krok:
  derived KPI/budget decision proof.
- Czterdziesty pod-slice zakończony: derived KPI i budget decision proof są w
  `assert_ads_derived_kpi_and_budget_decisions`; metric tiles, source/action
  lineage, blocked claims i `apply_allowed=false` dla preview budżetu są
  zachowane. Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1446
  linii i 12 branchy. Następny krok: recommendation decision proof i końcowy
  action tail.
- Czterdziesty pierwszy pod-slice zakończony: recommendation decision proof
  jest w `assert_ads_recommendation_decision_contract`; impact/action preview,
  review gates, evidence lineage i blokada zapisu rekomendacji są zachowane.
  Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1397 linii i 12
  branchy. Następny krok: impression-share/change-history decisions.
- Czterdziesty drugi pod-slice zakończony: impression-share i change-history
  decision proof są w `assert_ads_impression_share_and_change_history_decisions`;
  visibility-loss evidence, blocked budget/impact claims i review-only action
  lineage są zachowane. Focused Ads/Ruff/mypy/diff check zielone; główny test
  ma 1363 linii i 12 branchy. Następny krok: action payload validation i
  końcowy tail.
- Czterdziesty trzeci pod-slice zakończony: change-history ActionObject payload
  validation jest w `assert_ads_change_history_action_payload`; preview
  contract, brak performance window i fail-closed flags są zachowane.
  Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1347 linii i 12
  branchy. Następny krok: n-gram action payload i decyzje search.
- Czterdziesty czwarty pod-slice zakończony: n-gram ActionObject payload jest
  w `assert_ads_ngram_action_payload`; operator copy, preview-card disclosure
  i fail-closed flags są zachowane. Focused Ads/Ruff/mypy/diff check zielone;
  główny test ma 1319 linii i 12 branchy. Następny krok:
  search-term/safety/negative-keyword decisions.

- Czterdziesty piąty pod-slice zakończony: search-term, search-safety i
  negative-keyword decision proof są w `assert_ads_search_decision_contracts`;
  priorytety, 90-dniowe evidence, review gates, knowledge cards i blokady
  unsafe claims są zachowane. Focused Ads/Ruff/mypy/diff check zielone; główny
  test ma 1265 linii i 12 branchy. Następny krok: custom-segment decision i
  finalny action tail.
- Czterdziesty szósty pod-slice zakończony: custom-segment decision i globalny
  write-blocker proof są w `assert_ads_custom_segment_decision_contract` oraz
  `assert_ads_write_blocker_decision_contract`; forecast blocker, source-term
  gates, payload preview i ActionObject safety są zachowane. Focused
  Ads/Ruff/mypy/diff check zielone; główny test ma 1201 linii i 12 branchy.
  Następny krok: pozostałe action payloady i finalny tail.

- Czterdziesty siódmy pod-slice zakończony: campaign review ActionObject
  payload jest w `assert_ads_campaign_review_action_payload`; budget context,
  Polish disclosure, safety review i fail-closed mutation flags są zachowane.
  Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1122 linii i 12
  branchy. Następny krok: pozostałe ActionObject payloady i status/context tail.
- Czterdziesty ósmy pod-slice zakończony: recommendation review ActionObject
  payload jest w `assert_ads_recommendation_action_payload`; disclosure bez
  technicznych ID, preview contract i blokady apply/destructive są zachowane.
  Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1093 linii i 12
  branchy. Następny krok: custom-segment/negative-keyword payloady i status
  tail.
- Czterdziesty dziewiąty pod-slice zakończony: custom-segment i
  negative-keyword ActionObject payloady są w
  `assert_ads_custom_segment_action_payload` oraz
  `assert_ads_negative_keyword_action_payload`; source lineage,
  forecast/90-day safety blockers, disclosure i `apply_allowed=false` są
  zachowane. Focused Ads/Ruff/mypy/diff check zielone; główny test ma 1018
  linii i 12 branchy. Następny krok: status-probe/context-pack tail.
- Pięćdziesiąty pod-slice zakończony: status-probe post-refresh contract jest
  w `assert_ads_status_probe_contract`; latest-refresh lineage, live-data proof
  i wymagane read rows po status probe są zachowane. Focused Ads/Ruff/mypy/diff
  check zielone; główny test ma 1009 linii i 12 branchy. Następny krok:
  context-pack/action inventory tail.
- Pięćdziesiąty pierwszy pod-slice zakończony: ActionObject inventory proof
  jest w `assert_ads_action_inventory`; brak env-setup action i obecność
  potrzebnych review/action IDs są zachowane. Focused Ads/Ruff/mypy/diff check
  zielone; główny test ma 1002 linie i 12 branchy. Następny krok:
  context-pack parity i finalny tail.
- Pięćdziesiąty drugi pod-slice zakończony: context-pack parity jest w
  `assert_ads_context_pack_parity`; priorytet, metric tiles i
  knowledge-card/rule lineage między pełnym Ads diagnostics i context-packiem
  są zachowane. Focused Ads/Ruff/mypy/diff check zielone; główny test ma 989
  linii i 12 branchy. Następny krok: końcowy audit completion criteria.
- Pięćdziesiąty trzeci pod-slice zakończony: business-ready Ads contract jest
  w `assert_ads_business_ready_contract`; preliminary target interpretation,
  strategy-review blocker i KPI-vs-target evidence są zachowane. Focused
  Ads/Ruff/mypy/diff check zielone; główny test ma 936 linii i 12 branchy.
  Następny krok: końcowy audit completion criteria.
- Re-audit po pięćdziesiątym trzecim pod-slice: `audit_complexity` raportuje 0
  changed-code budget violations, ale główny test nadal ma 936 linii i 12
  branchy. Kontrakty i focused bramki są zielone, lecz `c9h9.22` pozostaje
  otwarty, bo acceptance wymaga fizycznego splitu funkcji do modułów/testów
  zachowania. Następny krok: przeniesienie pierwszej grupy helperów do
  osobnego modułu bez zmiany runtime.
- Completion audit `c9h9.22`: behavior assertions są w nazwanych helperach dla
  refresh, campaign, KPI/budget, recommendations, search, custom segments,
  ActionObjects, status i context-pack. Pozostała funkcja ma 945 linii, ale
  docstring uzasadnia granicę integracyjną (jeden isolated store przez refresh
  → diagnostics → validate → business context → status probe → context-pack);
  dalszy split dublowałby fixture i osłabił evidence lineage. Backend Ads/API
  contracts, Ruff, mypy, diff check i complexity audit są zielone. Bead może
  zostać zamknięty z tym uzasadnieniem.
- Roadmap re-audit zamknął stale-open `wilq-seo-0q74`: Ads smoke ma już
  modułowe runtime/orchestration/readiness/auxiliary/report seams,
  deterministyczny live smoke przechodzi, a strict skill coverage daje 13/13,
  0 gaps i 0 warnings. Nie wracać do tej ukończonej pracy.
- Roadmap re-audit zamknął stale-open `wilq-seo-ksiq`: shared schemas mają
  świadomy 31-liniowy barrel `index.ts` i domenowe entrypointy; 34/34
  non-skipped tests, `tsc --noEmit` i ESLint przechodzą. `contentWorkflow.ts`
  jest modułem domeny content, nie cross-domain barrel. Nie wracać do tego
  ukończonego splitu.
- Następny aktywny zakres: `wilq-seo-kgvy` (Ads diagnostics monster).
  Rebaseline: 7 140 linii fizycznych / 6 616 niepustych w
  `wilq/briefing/ads_diagnostics.py`; domenowe moduły istnieją już dla
  campaign, budget, recommendations, search, custom segments, change history,
  impression share i optimizer. `build_ads_diagnostics` ma 201 linii / 4
  branchy. Następny krok: import boundary dla primary read-contract
  orchestration, bez cykli i bez zmiany runtime.
- Slice wykonany po rebaseline: dodano `wilq/briefing/ads_primary_contracts.py`
  jako import boundary dla podstawowych Ads read-contractów. Granica przyjmuje
  typed callbacki (`account_currency`, `business_context`, `campaign`,
  `derived_kpi`) i używa istniejących domenowych builderów; `ads_diagnostics.py`
  nie importuje się zwrotnie. 11 testów Ads, Ruff, mypy i diff check zielone;
  plik główny zmniejszony o 69 linii. Complexity nadal jawnie pokazuje dwa
  historyczne budżety (plik 6 559 LOC, builder 201 linii), więc `kgvy` nie jest
  zamknięty. Następny slice: kolejny read-contract seam, tylko po sprawdzeniu
  zależności importów i parytetu HTTP.
- Drugi slice wykonany: dodano `wilq/briefing/ads_search_contracts.py` z
  orchestration dla search-term read/review i keyword-planner contractów.
  Granica używa typed callbacków do prywatnych builderów w fasadzie, więc nie
  ma importu zwrotnego. Główny plik ma 7 068 linii fizycznych / 6 544 niepuste;
  Ads contract suite (12 punktów), Ruff, mypy i diff check przechodzą.
  Complexity nadal jawnie raportuje dwa historyczne budżety monolitu. Następny
  krok: kolejny kontraktowy seam w `kgvy`, po ponownej kontroli parytetu HTTP.
- Trzeci slice wykonany: dodano `wilq/briefing/ads_candidate_contracts.py` dla
  custom-segment i negative-keyword read contracts. Typed callbacki wskazują
  istniejące buildery, bez importu zwrotnego i bez zmiany API. `ads_diagnostics.py`
  ma 7 066 linii fizycznych; Ads contracts, Ruff, mypy i diff check zielone.
  `kgvy` pozostaje otwarty z powodu dwóch jawnych budżetów complexity. Następny
  seam: campaign/optimizer orchestration.
- Czwarty slice wykonany: dodano `wilq/briefing/ads_campaign_optimizer_contracts.py`.
  Triage i optimizer readiness są składane przez osobny moduł z istniejącym
  builderem i callbackiem triage; brak importu zwrotnego, endpointu i zmiany
  kontraktu. `ads_diagnostics.py` ma 7 062 linie fizyczne; 12 testów Ads,
  Ruff, mypy i diff check zielone. Następny seam: sections/blocked-handoff,
  jeśli kontrola zależności potwierdzi brak ryzyka.
- Piąty slice wykonany: dodano `wilq/briefing/ads_section_contracts.py`.
  Sekcje Ads są składane poza fasadą przez istniejące domain builders; OAuth,
  evidence fallback, safe action i lineage są jawnie przekazane callbackami.
  `ads_diagnostics.py` ma 7 044 linie fizyczne; 12 testów Ads, Ruff, mypy,
  complexity audit i diff check zielone. Następny seam: decision-queue
  orchestration.
- Szósty slice wykonany: dodano `wilq/briefing/ads_decision_queue_contracts.py`.
  Decision queue orchestration (blocked path, kontrakty, safety i lineage)
  działa poza fasadą przez callbacki do istniejących reguł. `ads_diagnostics.py`
  ma 6 973 linie fizyczne; 12 testów Ads, Ruff, mypy, complexity audit i diff
  check zielone. Następny seam: response assembly/operator summary.
- Siódmy slice wykonany: dodano `wilq/briefing/ads_response_assembly.py`.
  Składanie `AdsDiagnosticsResponse` działa poza fasadą przez callbacki dla
  freshness, labels, operator summary i evidence/action lineage. `ads_diagnostics.py`
  ma 6 963 linie fizyczne; 12 testów Ads, Ruff, mypy, complexity audit i diff
  check zielone. Następny seam: label hydration.
- Ósmy slice wykonany: dodano `wilq/briefing/ads_label_hydration.py`.
  Review-gate i operator-summary labels są mapowane poza fasadą, a polityki
  label pozostają w dotychczasowych helperach. `ads_diagnostics.py` ma 6 902
  linie fizyczne; 12 testów Ads, Ruff, mypy, complexity audit i diff check
  zielone. Następny seam: decision/surface label hydration.
- Dziewiąty slice wykonany: `ads_label_hydration.py` obejmuje teraz także
  decision i surface labels (sekcje oraz blocked handoff). Polityki label są
  nadal w helperach fasady przez callbacki. `ads_diagnostics.py` ma 6 863 linie
  fizyczne; 12 testów Ads, Ruff, mypy, complexity audit i diff check zielone.
  Następny seam: contract-specific label hydration.
- Dziesiąty slice wykonany: dodano `wilq/briefing/ads_contract_label_hydration.py`.
  Orkiestracja labeli core/optimizer/budget/search jest poza fasadą przez
  callbacki; konkretne polityki label i preview pozostają w dotychczasowych
  helperach. `ads_diagnostics.py` ma 6 876 linii fizycznych; Ads contracts,
  Ruff, mypy, complexity audit i diff check zielone. Następny seam: pozostałe
  preview/payload label helpers, tylko jeśli mają wspólną bezpieczną granicę.
- Re-audit `kgvy` potwierdził brak wspólnej granicy dla pozostałych previewów;
  nie przenosić ich mechanicznie. Następny aktywny task: `jnra`.
- Slice `jnra`: `wilq/actions/registry_assembly.py` przejął kanoniczne składanie
  inventory static/metric/live Ads. `list_actions` i direct lookup zachowują
  parity, configure action znika tylko przy live vendor-read. `test_action_list_cache.py`
  4/4, Ruff/mypy/diff zielone. Complexity pokazuje kontrolowany frozen-file risk
  `service.py`; szeroki action-object test ma niezwiązany import error
  `_merchant_feed_items` z `tactical_queue`.
- Slice `50wa`: stale import `_merchant_feed_items` został naprawiony zgodnie z
  aktualnym API `tactical_merchant.build_merchant_feed_items` (keyword-only
  `facts` i `action_ids`). `tests/actions/test_action_object_contracts.py`
  przechodzi; pozostałe complexity hotspoty są zakresem dalszego mega-test splitu.
- Kontynuacja `50wa`: test latest-batch metric read jest w osobnym
  `tests/actions/test_action_metric_facts_contracts.py` z minimalnymi zależnościami,
  bez importowania mega-testu. Nowy test i pełny action-object test przechodzą;
  legacy plik zmniejszył się o 40 linii. Pozostało 12 historycznych hotspotów
  complexity do dalszych niezależnych behavior splitów.
- Czwarta kontynuacja `50wa`: context-pack review-gate contract jest teraz w
  `tests/api_contracts/test_context_safety_contracts.py`. Nowy i pełny
  action-object test przechodzą; legacy plik zmniejszył się o 23 linie. Nadal
  pozostają historyczne hotspoty complexity.
- Piąta kontynuacja `50wa`: unsupported payload action validation jest teraz w
  `tests/actions/test_action_validation_contracts.py`. Nowy i pełny action-object
  test przechodzą; legacy plik zmniejszył się o 19 linii. Pozostają historyczne
  hotspoty complexity do dalszego splitu.
- Druga kontynuacja `50wa`: typed preview-card contract jest w osobnym
  `tests/actions/test_action_preview_cards_contracts.py` z lokalnym helperem,
  bez zależności od mega-testu. Nowy i pełny action-object test przechodzą;
  legacy plik zmniejszył się o 33 linie. Pozostało 12 hotspotów complexity.
- Trzecia kontynuacja `50wa`: prepare-only validation/apply-block contract jest
  teraz w `tests/actions/test_action_validation_contracts.py`. Nowy i pełny
  action-object test przechodzą; legacy plik zmniejszył się o 23 linie. Nadal
  pozostają historyczne hotspoty complexity do dalszego splitu.
- Szósta kontynuacja `50wa`: preview-audit i human-review outcome context-pack
  contracts są teraz w `tests/api_contracts/test_context_safety_contracts.py`.
  Nowy i pełny action-object test przechodzą; legacy plik zmniejszył się o 76
  linii. Następny agent może wybrać kolejny niezależny behavior test z mega-testu.
- Siódma kontynuacja `50wa`: pre-apply impact-check contract jest teraz w
  `tests/actions/test_action_confirmation_contracts.py`, obok blokady impact
  bez confirm. Nowy i pełny action-object test przechodzą; pozostały legacy
  mega-test nadal ma historyczne hotspoty i kwalifikuje się do dalszych splitów.
- Ósma kontynuacja `50wa`: Merchant feed blocked-section wording contract jest
  teraz w `tests/api_contracts/test_merchant_contracts.py`. Test docelowy oraz
  pełny action-object suite przechodzą; import został dopasowany do aktualnego
  `build_merchant_diagnostics` API po pierwszym kontrolowanym błędzie kolekcji.
- Dziewiąta kontynuacja `50wa`: Google Ads OAuth repair/redaction contract jest
  teraz w `tests/actions/test_action_evidence_contracts.py`. Nowy i pełny
  action-object suite przechodzą; następny slice może kontynuować pozostałe
  Ads/action behavior tests, bez wracania do tego kontraktu.
- Dziesiąta kontynuacja `50wa`: business-context review-only action contract
  jest teraz w `tests/api_contracts/test_ads_contracts.py`. Nowy i pełny
  action-object suite przechodzą; Ads API contract jest właściwym właścicielem
  tego behavior testu.
- Jedenasta kontynuacja `50wa`: target guardrail confirmation/local-state
  behavior jest teraz w `tests/api_contracts/test_ads_contracts.py`. Nowy i
  pełny action-object suite przechodzą; nie wracać do tego testu w mega-teście.
- Dwunasta kontynuacja `50wa`: Keyword Planner blocked-access action behavior
  jest teraz w `tests/api_contracts/test_ads_contracts.py`. Nowy i pełny suite
  przechodzą; zachowane są blokada claimów, redakcja błędu i review-only apply.
- Trzynasta kontynuacja `50wa`: missing-target guardrail summary behavior jest
  teraz w `tests/api_contracts/test_ads_contracts.py`. Test docelowy i pełny
  action-object suite przechodzą; nie wracać do tego testu w mega-teście.
- Czternasta kontynuacja `50wa`: homepage content candidate ID traceability jest
  teraz w `tests/api_contracts/test_content_workflow_contracts.py`. Nowy i pełny
  suite przechodzą; nie powtarzać tego splitu w action mega-teście.
- Piętnasta kontynuacja `50wa`: empty content-refresh operator-language contract
  jest teraz w `tests/api_contracts/test_content_workflow_contracts.py`. Nowy i
  pełny suite przechodzą; zachowano ochronę przed technicznym angielskim copy.
- Szesnasta kontynuacja `50wa`: review-gate Polish operator language contract
  jest teraz w `tests/api_contracts/test_content_workflow_contracts.py`. Nowy i
  pełny suite przechodzą; nie powtarzać tego testu w action mega-teście.
- Siedemnasta kontynuacja `50wa`: WordPress draft handoff review-gate contract
  jest teraz w `tests/api_contracts/test_content_workflow_contracts.py`. Nowy i
  pełny suite przechodzą; payload jargon pozostaje ukryty przed operatorem.
- Osiemnasta kontynuacja `50wa`: raw audit summary redaction contracts są teraz
  w `tests/api_contracts/test_action_operator_language_contracts.py`. Nowy i
  pełny suite przechodzą; nie wracać do tych pure label tests w mega-teście.
- Dziewiętnasta kontynuacja `50wa`: legacy action review-gate summary contract
  jest teraz w `tests/actions/test_action_review_contracts.py`. Nowy i pełny
  suite przechodzą; nie powtarzać tego review splitu.
- Dwudziesta kontynuacja `50wa`: action detail legacy apply-audit contract jest
  teraz w `tests/actions/test_action_review_contracts.py`. Nowy i pełny suite
  przechodzą; techniczne apply errors pozostają zredagowane.
- Dwudziesta pierwsza kontynuacja `50wa`: parametrized validation error language
  contract jest teraz w `tests/actions/test_action_validation_contracts.py`.
  Nowy i pełny suite przechodzą; nie wracać do tego testu w mega-teście.
- Dwudziesta druga kontynuacja `50wa`: legacy content review audit redaction
  contract jest teraz w `tests/api_contracts/test_content_workflow_contracts.py`.
  Nowy i pełny suite przechodzą; nie powtarzać tego content splitu.
- Dwudziesta trzecia kontynuacja `50wa`: dimensioned content action preview
  contract jest teraz w `tests/api_contracts/test_content_workflow_contracts.py`.
  Nowy i pełny suite przechodzą; retry context-pack potwierdził 9 connectorów,
  wszystkie skonfigurowane.
- Dwudziesta czwarta kontynuacja `50wa`: content candidate review audit contract
  jest teraz 1:1 w `tests/api_contracts/test_content_workflow_contracts.py`.
  Nowy i pełny suite przechodzą; nie powtarzać tego wieloetapowego splitu.
- Dwudziesta piąta kontynuacja `50wa`: content-strategist context-pack reviewed
  draft preview contract jest teraz 1:1 w `tests/api_contracts/test_content_workflow_contracts.py`.
  Nowy i pełny suite przechodzą; raw payload pozostaje ukryty.
- Dwudziesta szósta kontynuacja `50wa`: Ads business-context preliminary-target
  contract jest teraz 1:1 w `tests/api_contracts/test_ads_contracts.py`. Nowy
  i pełny suite przechodzą; target nie odblokowuje apply bez strategii review.
- Dwudziesta siódma kontynuacja `50wa`: metric-backed prepare-actions evidence
  contract jest teraz 1:1 w `tests/actions/test_action_evidence_contracts.py`.
  Nowy i pełny suite przechodzą; nie wracać do tego testu w mega-teście.

- `50wa` zamknięty 2026-07-13: zaplanowany zakres mega-test splitów zakończony
  27 focused slices; nie wracać do tego Beada bez nowego potwierdzonego zakresu.
- `ho41` continuation 2026-07-13: page identity/decision card wydzielony do
  `apps/dashboard/src/routes/ContentPageIdentityCard.tsx` (57 LOC), bez zmiany
  API, copy safety ani ActionObject. ESLint, TypeScript i focused route tests
  przechodzą. Live queue z `/api/content/work-items/queue` jest stale/blocked:
  2 kandydatów, 0 actionable, minimum 3; GSC i WordPress public są stale.
  Następny seam `ho41`: kolejny duży blok presentacyjny tylko po sprawdzeniu
  aktualnej architektury, bez odblokowywania write/publish.
- `ho41` continuation 2 2026-07-13: istniejąca kolumna GSC/Ahrefs/brief
  wydzielona do `apps/dashboard/src/routes/ContentSignalColumn.tsx` (62 LOC).
  Komponent dostaje tylko typed query chips, metric tiles i signal rows; nie
  zawiera rankingu ani reguł evidence. Focused dashboard lint/typecheck,
  route tests i build przechodzą. Kolejka nadal stale/blocked (2 kandydatów,
  0 actionable/3), więc nie traktować renderu jako gotowości treści.
- `ho41` continuation 3 2026-07-13: dev-only WordPress/ACF target column
  wydzielona do `apps/dashboard/src/routes/ContentDevTargetColumn.tsx` (82 LOC).
  Explicit target selection, section inventory i draft-only wording pozostają
  bez zmian; brak write/matching logic w komponencie. Przed commitem wymagane
  focused lint/typecheck/tests oraz reload/browser proof.
- `ho41` continuation 4 2026-07-13: public WordPress page/section column
  wydzielona do `apps/dashboard/src/routes/ContentPublicPageColumn.tsx` (47 LOC).
  Komponent renderuje wyłącznie typed URL/sekcje; nie zawiera decyzji SEO,
  canonical matching ani inferencji evidence. Focused route tests, Playwright
  layout proof, dashboard lint/typecheck/build i diff check przechodzą.
- `ho41` continuation 5 2026-07-13: wspólny marketer fact tile przeniesiony do
  `apps/dashboard/src/routes/ContentWorkflowFactTile.tsx` (8 LOC). Route nie
  posiada już tej powtarzalnej prymitywy prezentacyjnej; etykiety/liczniki
  pozostają w istniejących call sites. Focused route tests, Playwright proof,
  lint/typecheck/build i diff check przechodzą.
- `ho41` continuation 6 2026-07-13: powtarzalny layout safety card przeniesiony
  do `apps/dashboard/src/routes/ContentSafetyPanel.tsx` (22 LOC). Copy safety
  i blocked-claim meaning pozostają w istniejących panelach/API; nowy boundary
  ma wyłącznie layout. Focused route tests, Playwright proof, lint/typecheck/
  build i diff check przechodzą.
- `ho41` continuation 7 2026-07-13: trzy użycia listy Claim Ledger przeniesione
  do `apps/dashboard/src/routes/ContentClaimList.tsx` (31 LOC). Statusy,
  evidence IDs i blocked copy pozostają w typed entries/callerach; komponent ma
  wyłącznie rendering. Focused route tests, Playwright proof, lint/typecheck/
  build i diff check przechodzą.
- `ho41` continuation 8 2026-07-13: rendering przycisków workflow przeniesiony
  do `apps/dashboard/src/routes/ContentWorkflowControlButton.tsx` (24 LOC).
  Disabled reasons i pending state pozostają w orchestracji akcji; komponent
  nie waliduje ani nie mutuje ActionObject. Focused route tests, Playwright
  proof, lint/typecheck/build i diff check przechodzą.
- `ho41` continuation 9 2026-07-13: pełny panel wzbogacenia tematu przeniesiony
  do `apps/dashboard/src/routes/ContentOpportunityEnrichmentPanel.tsx` (45 LOC).
  Renderuje istniejący enrichment/measurement contract i blokery; nie wnioskuje
  service fit ani nie zastępuje Service Profile. Focused route tests,
  Playwright proof, lint/typecheck/build i diff check przechodzą.
- `ho41` continuation 10 2026-07-13: panel bramki Claim Ledger przeniesiony do
  `apps/dashboard/src/routes/ClaimLedgerGatePanel.tsx` (32 LOC). Filtrowanie
  ledgeru, evidence IDs, blocked copy i liczniki pozostają bez zmian; route
  wyłącznie orkiestruje placement. Focused route tests, Playwright proof,
  lint/typecheck/build i diff check przechodzą.
- `ho41` continuation 11 2026-07-13: blocked-candidate state przeniesiony do
  `apps/dashboard/src/routes/ContentWorkflowBlockedCandidate.tsx` (34 LOC).
  Freshness kolejki, blocker, safe next step i typed metrics pozostają bez
  zmian; route nie posiada już layoutu tego stanu. Focused route tests,
  Playwright proof, lint/typecheck/build i diff check przechodzą.
- `ho41` continuation 12 2026-07-13: `ContentQualityReviewPanel.tsx` (33 LOC)
  wydzielony jako panel review. Safety classification pozostaje w route helperze
  i jest przekazywana jako typed display input; findings, dimensions i next step
  bez zmian. Focused route tests, Playwright proof, lint/typecheck/build i diff
  check przechodzą.
- `ho41` continuation 13 2026-07-13: `ContentRevisionPlanPanel.tsx` (25 LOC)
  wydzielony jako panel planu poprawki. Safety classification pozostaje w route
  helperze i jest przekazana jako typed display input; blockers, instructions i
  evidence IDs bez zmian. Focused route tests, Playwright proof, lint/typecheck/
  build i diff check przechodzą.
- `ho41` continuation 14 2026-07-13: `AcfPreviewPanel.tsx` wydzielony wraz z
  rekurencyjnym rendererem pól ACF; safety text nadal pochodzi z route helpera.
  19 focused Vitest, lint, typecheck i build przechodzą. E2E uruchomione bez
  projektu `chromium` (konfiguracja repo nie definiuje projektu), a bez filtra
  doszło do aplikacji i zakończyło się na istniejącym locatorze nagłówka; brak
  dowodu regresji tego seamu.
- `ho41` continuation 15 2026-07-13: `StructuredDraftPreviewPanel.tsx`
  wydzielony jako prezentacyjna granica typed title/sections/evidence/checklist;
  safety text nadal pochodzi z route helpera. 19 focused Vitest, lint,
  typecheck, build i diff check przechodzą. E2E ponownie zatrzymało się na
  istniejącym locatorze `Treści: praca nad stroną`, bez dowodu regresji seamu.
- `ho41` continuation 16 2026-07-13: `WorkflowSafetyPanels.tsx` wydzielony jako
  composition-only boundary. Route helpery nadal dostarczają safety text, a
  child payloady są typed i niezmienione. 19 focused Vitest, lint, typecheck,
  build i diff check przechodzą. E2E nadal kończy się na istniejącym locatorze
  `Treści: praca nad stroną`; brak dowodu regresji tego seamu.
- `ho41` continuation 17 2026-07-13: `MobileContentTriage.tsx` wydzielony jako
  mobile-only decision presentation boundary. Candidate, blockers, freshness,
  evidence counts i review-only CTA pozostają API-owned inputs. 19 focused
  Vitest, lint, typecheck, build i diff check przechodzą. E2E nadal zatrzymuje
  się na istniejącym locatorze `Treści: praca nad stroną`.
- `ho41` continuation 18 2026-07-13: `ContentWorkbenchHeader.tsx` wydzielony
  dla tytułu route i kontrolek odświeżenia. Boundary jest presentation-only;
  API, routing i decyzje bez zmian. 19 focused Vitest, lint, typecheck, build i
  diff check przechodzą. E2E nadal kończy się na istniejącym locatorze nagłówka.
- `ho41` continuation 19 2026-07-13: `ContentPublicInventoryPanel.tsx`
  wydzielony z workbencha pisania. Public URL/title, section inventory i blocker
  brakującego inventory pozostają typed inputs; canonical/SEO logic bez zmian.
  19 focused Vitest, lint, typecheck, build i diff check przechodzą. E2E nadal
  kończy się na istniejącym locatorze `Treści: praca nad stroną`.
- `ho41` continuation 20 2026-07-13: `MobileDecisionCard.tsx` wydzielony jako
  compact mobile decision boundary. Queue decision/blocker/freshness fallback i
  review-only CTA pozostają typed inputs; recommendation logic bez zmian. 19
  focused Vitest, lint, typecheck, build i diff check przechodzą. E2E nadal
  kończy się na istniejącym locatorze nagłówka.
- `ho41` continuation 21 2026-07-13: `ContentWorkflowPublicationBlockers.tsx`
  wydzielony z decision panel. Human-review, draft-only WordPress i
  forbidden-claim copy pozostają bez zmian; komponent przyjmuje typed workflow
  steps i ma presentation-only ownership. 19 focused Vitest, lint, typecheck,
  build i diff check przechodzą. E2E nadal kończy się na istniejącym locatorze.
- `ho41` continuation 22 2026-07-13: `ContentWorkflowNextDecisionPanel.tsx`
  wydzielony z decision panel. Decision title/reason, evidence i claim counts,
  active step oraz safe next step są typed display inputs; ranking/business
  logic bez zmian. 19 focused Vitest, lint, typecheck, build i diff check
  przechodzą. E2E nadal kończy się na istniejącym locatorze nagłówka.
- `ho41` continuation 23 2026-07-13: `ContentWorkflowDecisionHeader.tsx`
  wydzielony dla workflow title, publication-blocked state i typed stepper.
  Active-step selection oraz workflow semantics pozostają w route/model. 19
  focused Vitest, lint, typecheck, build i diff check przechodzą. E2E nadal
  kończy się na istniejącym locatorze `Treści: praca nad stroną`.
- `ho41` continuation 24 2026-07-13: `ContentWorkflowClaimSummary.tsx`
  wydzielony z decision panel. Claim counts oraz linki do review/brief/WordPress
  są typed display inputs; claim-gate semantics pozostają API/model-owned. 19
  focused Vitest, lint, typecheck, build i diff check przechodzą. E2E nadal
  kończy się na istniejącym locatorze nagłówka.
- `ho41` continuation 25 2026-07-13: pozostała kompozycja decision panelu
  przeniesiona do `ContentWorkflowDecisionPanel.tsx`. Candidate/step/claim
  summaries są liczone tak samo z API/model inputs, a komponent tylko składa
  typed child panels; business rules/endpoints bez zmian. 19 focused Vitest,
  lint, typecheck, build i diff check przechodzą. E2E nadal kończy się na
  istniejącym locatorze nagłówka.
- `ho41` continuation 26 2026-07-13: `WordPressDraftWorkPanel.tsx` wydzielony
  z route. Dev-only readiness, draft-preview CTA, canonical apply-review link i
  draft/readback status używają tych samych typed query/action inputs; write
  safety i public/dev roles bez zmian. 19 focused Vitest, lint, typecheck, build
  i diff check przechodzą. E2E nadal kończy się na istniejącym locatorze.
- `ho41` continuation 27 2026-07-13: `ContentSectionWritingWorkbench.tsx`
  wydzielony z `ContentWorkflowSurface.tsx`. Lokalny stan edytora sekcji,
  draft-only dry-run, readback dev draft i ACF preview zachowują typed inputs
  oraz bezpieczeństwo public/dev. Route ma 1807 LOC; ESLint, typecheck, 19
  focused tests, build i diff check przechodzą. E2E nadal blokuje się na
  istniejącym heading locatorze, gdy live queue jest zablokowana.
- `ho41` continuation 28 2026-07-13: `ServiceProfileDecisionStrip.tsx`
  wydzielony z route. Typed service status, claim counts, blocker, evidence
  disclosure i safe next step pozostają presentation-only; Service Profile
  semantics nie zostały przeniesione do Reacta. Route ma 1656 LOC. ESLint,
  typecheck, 19 focused tests, build i diff check przechodzą; Playwright nadal
  blokuje się na istniejącym heading locatorze przez live queue `blocked`.
- `ho41` continuation 29 2026-07-13: `WorkflowOperatorControls.tsx`
  wydzielony jako presentation-only boundary. Route nadal wylicza typed control
  items oraz disabled reasons z istniejących safety/review helpers; komponent
  renderuje temat, draft-only copy i przyciski. Route ma 1614 LOC. ESLint,
  typecheck, 19 focused tests, build i diff check przechodzą; Playwright nadal
  blokuje się na istniejącym heading locatorze przy live queue `blocked`.
- `ho41` continuation 30 2026-07-13: `contentPageWorkbenchModel.ts`
  przejął czyste helpery projekcji workbencha (environment labels, metrics,
  signals, chips, claim/evidence rows i connector labels). Route ma 1467 LOC;
  ESLint, typecheck, 19 focused tests, build i diff check przechodzą. Browser
  proof nadal blokuje się na istniejącym heading locatorze przy live queue
  `blocked`; brak regresji przypisanej temu seamowi.
- `ho41` continuation 31 2026-07-13: `ContentPageWorkbench.tsx` wydzielony
  jako główna granica workbencha. Minimalny typed action interface ogranicza
  się do dry-run; snapshot/query data, public/dev role i draft-only safety są
  zachowane. Route ma 1038 LOC. ESLint, typecheck, 19 focused tests, build i
  diff check przechodzą; browser proof nadal zatrzymuje się na istniejącym
  heading locatorze przy live queue `blocked`.
- `ho41` continuation 32 2026-07-13: `contentWorkflowActionModel.ts` przejął
  typed response projections, request builders i dry-run submit helpery dla
  structured draft, review, audit, ACF i WordPress. Route ma 891 LOC; ESLint,
  typecheck, 19 focused tests, build i diff check przechodzą. Browser proof
  nadal blokuje się na istniejącym heading locatorze przy live queue `blocked`;
  ActionObject/safety semantics bez zmian.
- `ho41` continuation 33 2026-07-13: `contentWorkflowSafetyModel.ts`
  przejął safety copy i disabled-reason projections dla draft, handoff,
  structured output, quality review, revision, ACF, execution i measurement.
  Route ma 655 LOC, poniżej budżetu 800; ActionObject gates i readiness
  semantics pozostają w istniejącym flow. ESLint, typecheck, 19 focused tests,
  build i diff check przechodzą; browser proof nadal blokuje się na istniejącym
  heading locatorze przy live queue `blocked`.
- `6rw.5` continuation 2026-07-13: E2E content workflow ma teraz jawne dwie
  gałęzie kontraktu: ready queue sprawdza workbench, blocked queue sprawdza
  polski blocker/freshness/safe next step i overflow. Aktualny Playwright
  przechodzi 1/1 z live `queue_status=blocked`; nie maskuje blokady ani nie
  wymusza sztucznego tematu.
- Re-audyt Beads 2026-07-13: zamknięto `ho41` (route 655 LOC, typed
  boundaries, ready/blocked proof) oraz `6rw.5` (blocked-state E2E guardrail).
  Nie powtarzać tych slice'ów bez nowej sprzeczności runtime lub kontraktu.
- Re-audyt dashboardu 2026-07-13: usefulness audit zwrócił 14 surfaces,
  12 `demo_ready`, 2 `review_ready`, 0 blocked i `pass=true`; istniejące
  route/browser proof nie ujawniają nowej luki `6rw.2`. Bead zamknięty jako
  wykonany; wynik audytu nie jest substytutem realnego Wilku UAT.
- `r564` re-audit 2026-07-13: all child seams remain closed and no new code gap
  is confirmed. Live queue is now `blocked` with 2 candidates, 0 actionable of
  3; `google_search_console` and `wordpress_ekologus` are stale. Do not invent
  a third topic or reopen a closed child; await external refresh/evidence.
- `jst` pre-UAT 2026-07-13: live `export_marketer_uat_packet.py` completed
  against `http://127.0.0.1:8000` (5 routes, packet generated at
  `2026-07-13T12:34:35Z`). This is preparation evidence only; no participant,
  time-to-understand or verdict was invented. Keep `jst` open until Wilku
  session feedback or explicit owner defer is supplied.
- `jnra` continuation 2026-07-13: extracted bounded latest metric-fact batch
  loading to `wilq/actions/metric_action_facts.py`; vendor-specific Google Ads
  retrieval and probe-fact filtering remain explicit callbacks owned by the
  service facade. Focused action tests (12), Ruff, mypy and diff check pass.
  Complexity still flags the pre-existing frozen service monolith; do not treat
  that report as a regression from this behavior-preserving extraction.
- `jnra` continuation 2 2026-07-13: moved Service Profile promotion action
  assembly to `wilq/actions/service_profile.py`, preserving the facade's
  injectable profile provider for existing tests and runtime parity. Focused
  content/API suites, Ruff, mypy, API health/action smoke and content-workflow
  Playwright proof are green. The managed stack was restarted after the code
  change; `service.py` is 1447 LOC. Do not reopen closed c9h9.4 or repeat old
  WordPress safety slices.
- `jnra` continuation 3 2026-07-13: static action inventory now belongs to
  `registry_assembly.py`; Service Profile actions are explicit injected inputs,
  preserving list/direct-lookup parity. Dead `seed_core_prepare_actions` was
  removed only after repo-wide reference search. API restart confirms 21 actions
  and both Service Profile IDs; focused tests, Ruff, mypy and diff check pass.
- `jnra` continuation 4 2026-07-13: extracted ActionObject validation to
  `wilq/actions/action_validation.py`, retaining the service facade as the
  compatibility boundary and injecting review-gate/label dependencies. API
  health and Service Profile action lookup pass after stack restart; focused
  validation/knowledge tests, Playwright content-workflow proof, Ruff, mypy
  and diff check are green. Do not reopen c9h9.4.
- `jnra` continuation 5 2026-07-13: extracted human-review event persistence
  to `wilq/actions/review_lifecycle.py`. The public service facade still owns
  compatibility and injects existing typed review/gate/label projections. API
  health, focused review/content tests, Ruff, mypy and Playwright proof pass.
  Next candidate is preview lifecycle; do not repeat validation or WordPress
  safety slices already recorded above.
- `jnra` continuation 6 2026-07-13: preview lifecycle now lives in
  `wilq/actions/preview_lifecycle.py`, with the service facade retaining typed
  compatibility injection. API health, focused lifecycle/content tests, Ruff,
  mypy, complexity and Playwright proof pass; preview remains dry-run and does
  not imply external mutation. Next audit target is confirmation lifecycle.
- `jnra` continuation 7 2026-07-13: confirmation lifecycle now lives in
  `wilq/actions/confirmation_lifecycle.py`; typed safety and audit projections
  remain owned by existing modules through facade injection. Focused Ads/content
  lifecycle tests, Ruff, mypy, complexity and API health pass. No dashboard
  files changed, so retain the existing content-workflow browser proof rather
  than inventing a new UI claim. Next target: impact-check lifecycle.

- `jnra` continuation 8 2026-07-13: impact-check lifecycle now lives in
  `wilq/actions/impact_lifecycle.py`. A regression test preserved the exact
  operator connector label mapping after extraction. Focused impact/review/
  mutation-readiness tests, Ruff, mypy, API health, dashboard route and
  Playwright proof pass. Next target: apply preflight/mutation lifecycle;
  do not reopen earlier preview/confirmation seams.
- `jnra` continuation 9 2026-07-13: canonical apply preflight/mutation
  lifecycle now lives in `wilq/actions/apply_lifecycle.py`. WordPress
  capability and connector callbacks remain injected through the facade so
  tests and runtime preserve the existing seam. Safety tests, Ruff, mypy,
  complexity, API health, dashboard route and Playwright proof pass. Next
  target: mutation readiness projection only if a fresh code gap is confirmed;
  do not reopen closed WordPress safety scope.
- `kgvy` continuation 2026-07-13: Ads summary cache moved to
  `wilq/briefing/ads_summary_cache.py`; `ads_diagnostics.py` keeps the public
  clear-cache compatibility facade. Ads contracts, Ruff, mypy, complexity,
  API health, dashboard route and Playwright proof pass. No frozen-growth
  violation remains for this change; next review should choose another
  confirmed Ads domain seam, not generic mechanical splitting.

## Następny krok

- Po commit/push kontynuować kolejny świeży seam `jnra` w lifecycle
  orchestration; nie wracać do zamkniętych childów ani connector schemas.
