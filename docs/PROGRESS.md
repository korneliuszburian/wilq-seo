# WILQ Progress Ledger

Krótki recovery ledger, nie append-only changelog. Historyczne proof pozostaje
w git, Beads i `docs/progress/archive/`.

## Stan bieżący — 2026-07-13

- `wilq-seo-c9h9.18` jest w realizacji: Ahrefs tactical queue ma osobny typed
  moduł `wilq/briefing/tactical_ahrefs.py`, który kompiluje
  `AhrefsCrossSourceMatcher` raz na batch i zachowuje exact/weak/missing,
  evidence/source connectors oraz brak akcji dla niepotwierdzonych tematów.
  Focused tactical/Ahrefs tests (8), Ruff, mypy i live
  `/api/marketing/tactical-queue` (24 items, 19 groups, 3 action IDs) przechodzą.
  Complexity pozostaje jawnie naruszona przez istniejący monolit
  `tactical_queue.py` (1311 LOC) i `_merchant_feed_items` (115 LOC); ten slice
  zmniejszył plik o 90+ LOC i wymaga dalszego, osobnego extraction Beada.
- Live rebaseline: API `ok`, 104 362 metric facts, 4 580 refresh runs, 9/12
  konektorów skonfigurowanych; kolejka contentowa ma 2 kandydatów i blocker
  `not_enough_actionable_candidates`, więc WILQ nie tworzy sztucznego tematu.
- `wilq-seo-0q74` rozpoczęty: `scripts/skill_smoke_harness.py` współdzieli
  transport JSON i guardrail polskiego evidence/source między Ads i GSC smoke.
  Ads smoke przechodzi na live API; GSC dociera do API, ale ujawnia istniejący
  rozjazd `marketer_decision.review_action_ids` względem bieżącej listy akcji
  `content_diagnostics`. To osobny follow-up kontraktu API, nie regresja
  harnessu.
- `wilq-seo-c9h9.19` zamknięty jako redundantny po managed restart i live proof:
  marketer review card była już API-owned; poprawiono wyłącznie GSC smoke, aby
  wiązał action IDs z wybraną decyzją, nie z globalną listą akcji. Handoff:
  `docs/handoffs/2026-07-13-0q74-smoke-harness-handoff.md`.
- `wilq-seo-pidl` pierwszy test seam: `ConnectorRefreshRunList` evidence/redaction
  behavior został przeniesiony z `App.test.tsx` do
  `ConnectorRefreshRunList.test.tsx`. App omnibus zmniejszył się o jeden
  niezależny route/component contract; 32 testy obejmujące oba pliki przechodzą.
- `wilq-seo-0q74` rozszerzony o Content Strategist: wspólny timeout-aware
  `request_json` i Polish guardrail, a smoke poprawnie traktuje Ahrefs-only
  decyzję bez akcji jako blocker review-only. Live Content Strategist smoke i
  Ruff przechodzą.
- `wilq-seo-0q74` rozszerzony o Merchant Feed: czwarty smoke używa wspólnego
  harnessu; live Merchant proof przechodzi (1 action, 7 decyzji, blocked claims
  dla reapproval/revenue/feed write), Ruff przechodzi.
- `wilq-seo-0q74` rozszerzony o Localo: piąty smoke używa wspólnego harnessu;
  live proof przechodzi (`access_ready`, 4 lokalizacje, 23 monitorowane frazy,
  review-only action), Ruff przechodzi.
- `wilq-seo-0q74` rozszerzony o GA4: szósty smoke używa wspólnego harnessu;
  live proof przechodzi z decyzjami `fix_measurement`/`review_traffic_quality`,
  blokadą `(not set)` jako problemu pomiaru i bez claimów ROAS/przychodu.
- `wilq-seo-0q74` rozszerzony o Demand Gen: siódmy smoke używa wspólnego
  harnessu; live proof przechodzi z 18 kampaniami bazowymi, 0 kampanii Demand
  Gen i jawnie zablokowanym statusem review-only.
- `wilq-seo-0q74` rozszerzony o Ahrefs: ósmy smoke używa wspólnego harnessu;
  live proof przechodzi z 338 gap facts, 6 manual cross-check candidates i bez
  action IDs dla niepotwierdzonych luk.
- `wilq-seo-0q74` rozszerzony o Campaign Builder i Social: dziesięć smoke’ów
  używa wspólnego transportu; live proof przechodzi, a Social zachowuje
  missing credentials/history jako jawny blocker review-only.
- `wilq-seo-0q74` rozszerzony o Custom Segments: jedenaście smoke’ów używa
  wspólnego transportu; live proof przechodzi z 1 kandydatem, blokadą Keyword
  Planner/forecast/audience size i `apply_allowed=false`.
- `wilq-seo-0q74` rozszerzony o Content Operator: dwanaście smoke’ów używa
  wspólnego transportu; live proof przechodzi z kolejką zablokowaną przy 2/3
  kandydatów, dry-run WordPress i `publish_allowed=false`.
- `wilq-seo-0q74` ma pierwszy wspólny seam asercji: `require_polish_language`
  i `require_evidence_sources` w harnessie; GA4, Merchant i GSC używają go bez
  zmiany API/product logic. Live smoke i Ruff przechodzą.
- Dodano drugi seam harnessu: `validate_action_ids` dla Campaign Builder i
  Social; ich live smoke, Ruff i diff check przechodzą bez zmiany safety gates.
- Complexity re-audit po `f1da411`: 443 Python files / 139381 non-empty LOC,
  changed files 0 i zero changed-code violations. Następny potwierdzony hotspot
  do wydzielenia to Content Strategist `validate_content_action_preview`
  (171 LOC / 67 branches), przed Ads `main` (1006/290).
- `validate_content_action_preview` wydzielony do
  `.agents/skills/wilq-content-strategist/scripts/content_action_preview.py`;
  live smoke/Ruff/diff przechodzą, a nowy moduł nie ma violationów. Pozostałe
  Content Strategist `main`/decision-queue/WordPress assertions są jawnie
  następnym zakresem.
- Decision queue i WordPress draft handoff assertions są teraz w
  `content_strategy_assertions.py`; live smoke/Ruff/diff przechodzą. Zmieniony
  complexity audit zostawia wyłącznie `smoke_skill_contract.py::main`
  (206 LOC/26 branches). Następny slice: rozdzielenie orkiestracji `main`.
- Orkiestracja Content Strategist smoke jest teraz w
  `content_strategy_runtime.py`; główny skrypt spadł do 94 LOC/11 branches.
  Runtime pobiera health/context-pack/content diagnostics, waliduje actiony,
  brief i statusy konektorów, bez zmiany API ani safety gates. Live smoke
  zweryfikował `ok`, 6 action validations i 9 query/page rows; runtime ma 52 LOC
  i 3 branches w głównym loaderze.
- GSC smoke dostał `scripts/gsc_refresh_contract.py`: odczyt latest completed
  vendor refresh i Search Analytics contract nie obciąża już głównego smoke.
  Live GSC smoke/Ruff/diff przechodzą; wynik ma 1 978 query/page metric facts.
  `main` spadł do 434 LOC/122 branches. Ads pozostaje osobnym blockerem
  diagnostycznym: `/api/ads/diagnostics` zwraca 8,6 MB, zwykły Ads context-pack
  213 KB, a full-context 11,2 MB; pierwsze krótkie uruchomienie przekroczyło
  limit sesji, ale dłuższy live proof został później zaliczony.
- Ads bootstrap smoke jest teraz w `scripts/ads_smoke_runtime.py`: health,
  context-pack budget, baseline języka/evidence/action IDs i blocked handoff są
  walidowane poza `main`. Live smoke zakończył się `exit 0` po około 73 s,
  potwierdził 6 poprawnych walidacji actionów, 18 kampanii i
  `apply_allowed=false`; `main` spadł do 970 LOC/274 branches. Duży payload
  jest znanym kosztem live proof, nie błędem safety.
- Ads `optimizer_readiness_contract` i budżetowa decyzja są teraz walidowane
  przez `scripts/ads_readiness_assertions.py`. Drugi live smoke kończy się
  `exit 0`, zachowuje 6 poprawnych action validations i `apply_allowed=false`;
  `main` spadł do 934 LOC/255 branches. Nowy moduł ma 48 LOC, 17 branches.
- Ads recommendations contract jest teraz w
  `scripts/ads_recommendation_assertions.py`, rozdzielony na ready/packed
  preview checks. Live smoke po zmianie kończy się `exit 0`; `main` ma 838
  LOC/214 branches, a helpery mieszczą się w budżecie (18/16 branches).
- Ads impression-share contract jest teraz w
  `scripts/ads_impression_share_assertions.py`. Live smoke po zmianie kończy
  się `exit 0`; `main` ma 820 LOC/207 branches, nowy helper 19 LOC/8 branches.
- Ads change-history read contract jest teraz w
  `scripts/ads_change_history_assertions.py`. Live smoke kończy się `exit 0`;
  `main` spadł do 794 LOC/196 branches, helper ma 25 LOC/12 branches.
- Ads change-impact readiness jest teraz w
  `scripts/ads_change_impact_assertions.py`. Live smoke kończy się `exit 0`;
  `main` ma 770 LOC/180 branches, helper 29 LOC/16 branches; blokady okien
  pre/post i human review pozostają aktywne.
- Ads search-term review summary jest teraz w
  `scripts/ads_search_term_review_assertions.py`. Live smoke kończy się
  `exit 0`; `main` ma 756 LOC/174 branches, helper 18 LOC/7 branches.
- Ads search-term safety contract jest teraz w
  `scripts/ads_search_term_safety_assertions.py`. Live smoke kończy się
  `exit 0`; `main` ma 737 LOC/167 branches, helper 19 LOC/8 branches.
- Ads keyword-match context contract jest teraz w
  `scripts/ads_keyword_match_assertions.py`. Live smoke kończy się `exit 0`;
  `main` ma 723 LOC/161 branches, helper 17 LOC/7 branches.
- Ads Keyword Planner contract jest teraz w
  `scripts/ads_keyword_planner_assertions.py`. Live smoke kończy się `exit 0`;
  `main` ma 692 LOC/150 branches, helper 27 LOC/13 branches. Blocker
  enrichment/forecast pozostaje jawny.
- Ads custom-segments contract jest teraz w
  `scripts/ads_custom_segments_assertions.py`. Live smoke kończy się `exit 0`;
  `main` ma 675 LOC/140 branches, helper 29 LOC/13 branches. Audience-size,
  skuteczność i zapis kierowania nadal pozostają zablokowane.
- Ads search-term n-gram contract jest teraz w
  `scripts/ads_search_term_ngram_assertions.py`. Live smoke kończy się `exit 0`;
  `main` ma 664 LOC/135 branches, helper 17 LOC/5 branches. N-gram-specific
  change-preview blocker pozostaje jawny.
- Ads negative-keyword contract jest teraz w
  `scripts/ads_negative_keyword_assertions.py`. Live smoke kończy się `exit 0`;
  `main` ma 644 LOC/125 branches, helper 22 LOC/9 branches. Payload preview,
  action ID i brak automatycznego wykluczenia pozostają jawne.
- Ads review action validation korzysta teraz bezpośrednio ze wspólnego
  `validate_action_ids` w `scripts/skill_smoke_harness.py`. Live smoke kończy
  się `exit 0`, 6 walidacji ma `valid/status=valid`; Ads `main` ma 633 LOC/122
  branches.
- Ads brief compaction jest teraz w `scripts/ads_report_compaction.py` i
  przepuszcza wyłącznie tytuł, kind, source connectors, evidence/action IDs
  oraz metric facts. Live smoke kończy się `exit 0`; `main` ma 619 LOC/121
  branches, helper 19 LOC.
- Connector status compaction korzysta z tego samego helpera i przekazuje tylko
  id/status/configured/missing credentials/error. Live smoke kończy się `exit 0`;
  `main` ma 607 LOC/120 branches, bez zmiany API ani redaction.
- Ads context-pack lineage assertion jest teraz w
  `scripts/ads_context_lineage.py`. Live smoke kończy się `exit 0`; `main` ma
  607 LOC/120 branches, helper 39 LOC/9 branches. Knowledge card i expert rule
  IDs muszą pozostać obecne w compact context.
- Final report shaping helpers (`compact_blocked_handoff`, `unique_ids`) są teraz
  w `scripts/ads_report_compaction.py`. Live smoke kończy się `exit 0`; `main`
  pozostaje na 607 LOC/120 branches, a final output nadal nie zawiera surowych
  vendor payloadów.
- GSC content action validation korzysta teraz ze wspólnego
  `validate_action_ids` harnessu. Live smoke kończy się `ok`, 1 walidacja ma
  `valid/status=valid`; GSC `main` spadł do 425 LOC/120 branches.
- GSC brief i connector status compaction są teraz w
  `scripts/gsc_report_compaction.py`; live smoke `ok` zweryfikował 4 brief items
  i 3 konektory. GSC `main` spadł do 398 LOC/118 branches, bez surowych
  payloadów vendorów.
- GSC freshness i Search Analytics contract są teraz walidowane przez
  `scripts/gsc_freshness_assertions.py`. Live smoke `ok` zweryfikował stan
  `fresh`; GSC `main` spadł do 336 LOC/82 branches, helper 52 LOC/22 branches.
- GSC decision parity jest teraz w `scripts/gsc_decision_parity.py`; live smoke
  `ok` zweryfikował 1 scoped decision, endpoint-subset evidence/action IDs i
  usunięcie Ahrefs scope. GSC `main` spadł do 315 LOC/72 branches, helper 51
  LOC/12 branches.
- GSC marketer decision card parity jest teraz w
  `scripts/gsc_marketer_card_assertions.py`. Live smoke `ok` zweryfikował kartę
  `Karta decyzji dla Wilka`, review fields i selected action IDs; `main` spadł
  do 278 LOC/59 branches, helper 39 LOC/13 branches.
- Merchant Feed context parity jest teraz w
  `scripts/merchant_context_parity.py`; live smoke `ok` zweryfikował 19 issue
  items, evidence/action parity i price readiness parity. Merchant `main` spadł
  do 343 LOC/107 branches, helper 27 LOC/8 branches.
- Merchant product sample/performance readiness jest teraz w
  `scripts/merchant_product_readiness.py`; live smoke `ok` potwierdził status
  performance `blocked` i blokady przychodu/ROAS/write. Merchant `main` spadł
  do 288 LOC/87 branches, helper 56 LOC/20 branches.
- Merchant price impact readiness jest teraz w
  `scripts/merchant_price_readiness.py`; live smoke `ok` potwierdził status
  `blocked`, preview contract i `apply_allowed=false`. Merchant `main` spadł
  do 242 LOC/67 branches, helper 51 LOC/18 branches.
- `wilq-seo-ipps` domyka kolejny seam: Merchant tactical queue jest teraz w
  `wilq/briefing/tactical_merchant.py`. Zachowano grupowanie issue/status,
  polskie etykiety, evidence/source connectors, blocked claims i ActionObject IDs.
  Focused contracts (17), Ruff, mypy i live tactical queue (24 items, 4 Merchant
  items) przechodzą. Complexity spadła do 1195 LOC; pozostałe naruszenie pliku
  jest jawnie odnotowane jako dalszy zakres, bez udawania pełnego splitu.
- `wilq-seo-c9h9.16` wydziela typed orchestrator snapshotu do
  `wilq/content/workflow/snapshot_assembly.py`. API pozostaje adapterem stage
  callbacks, a response shape i write gates nie zmieniają się. Focused content
  contracts: 12 passed; Ruff, mypy, diff check, live snapshot i browser proof
  `/content-workflow` przechodzą. Live snapshot jest `workflow_snapshot`, fresh,
  z 2 evidence IDs (GSC + WordPress); Service Profile, handoff i measurement
  pozostają jawnie review/blocker, bez publikacji. Complexity `api.py` spadła
  do 1470 LOC; pozostałe naruszenie pliku jest jawne i wymaga osobnego seama.
- `wilq-seo-zdm2` wydziela preflight i Sales Brief adapters do
  `wilq/content/workflow/stage_preparation.py`. 12 focused content tests,
  Ruff, mypy, live `workflow_snapshot` i evidence/freshness/write-gate proof
  przechodzą. `api.py` spadł do 1416 LOC; pozostały draft/review/handoff stage
  ma osobny follow-up `wilq-seo-mseb`.
- `wilq-seo-mseb` wydziela draft package, structured-generation i draft-variants
  adapters do `wilq/content/workflow/stage_drafts.py`. 12 focused content tests,
  Ruff, mypy, live snapshot i write-gate proof przechodzą; `api.py` spadł do
  1352 LOC. Human review/handoff mają osobny follow-up `wilq-seo-frgd`.
- `wilq-seo-frgd` wydziela human-review i WordPress handoff adapters do
  `wilq/content/workflow/stage_review.py`. 17 focused testów, Ruff, mypy,
  browser `/content-workflow` i live safety proof przechodzą; `api.py` spadł do
  1313 LOC. Handoff nadal ma blocker, a publish pozostaje nieaktywne. Measurement
  adapter ma osobny follow-up `wilq-seo-s8dl`.
- `wilq-seo-s8dl` wydziela measurement window/outcome adapters do
  `wilq/content/workflow/stage_measurement.py`. 19 focused content tests,
  Ruff, mypy, live snapshot i browser proof przechodzą; `api.py` spadł do 1272
  LOC. Measurement nadal zwraca blocker bez success claims; dalsze readiness
  helpers mają osobny follow-up `wilq-seo-kvgd`.
- `wilq-seo-kvgd` wydziela existing-draft update readiness projection do
  `wilq/content/workflow/stage_readiness.py`. Pełne content workflow contracts,
  Ruff, mypy, live snapshot i browser proof przechodzą; `api.py` spadł do 1201
  LOC. Update istniejącego draftu nadal jest jawnie zablokowany; pozostałe
  activation/write-readiness orchestration ma osobny Bead `wilq-seo-eieh`.
- `wilq-seo-eieh` wydziela typed WordPress activation packet projection do
  `wilq/content/workflow/stage_activation.py`. Focused activation/readiness
  tests, Ruff, mypy, live snapshot i browser proof przechodzą; `api.py` spadł do
  1148 LOC. Dry-run pozostaje fail-closed, a pozostałe readback/label helpers
  mają osobny follow-up `wilq-seo-nlax`.
- `wilq-seo-nlax` wydziela readback/activation label helpers do
  `wilq/content/workflow/stage_activation.py`. Focused activation/readiness
  tests, Ruff, mypy, live snapshot i browser proof przechodzą; `api.py` spadł do
  1017 LOC. Dry-run i readback pozostają fail-closed; pozostałe write-readiness
  orchestration ma osobny follow-up `wilq-seo-b0ja`.
- `wilq-seo-b0ja` wydziela write-readiness projection do
  `wilq/content/workflow/stage_write_readiness.py`. Focused readiness tests,
  Ruff, mypy, live snapshot i browser proof przechodzą; `api.py` spadł do 956
  LOC. Write remains fail-closed, a pozostałe audit helpers mają osobny
  follow-up `wilq-seo-fc5b`.
- `wilq-seo-fc5b` wydziela odczyt i interpretację audit trail WordPress do
  `wilq/content/workflow/stage_write_readiness.py`, zachowując kompatybilne
  wrappery API. Focused readiness tests, Ruff, mypy, complexity i diff check
  przechodzą; live readiness nadal zwraca `ready=false` oraz
  `actionobject_apply_path_required`, nawet przy skonfigurowanym adapterze i
  env. Browser route pozostaje dostępny, a zapis/publikacja nie są odblokowane.
- Nowy potwierdzony następny slice `wilq-seo-97a3`: wydzielenie snapshot stage
  adapters z `api.py` (868 LOC) do typed ownera, z zachowaniem parity i bez
  zmiany kontraktów ani safety.
- `wilq-seo-97a3` wykonany: snapshot stage adapters i helpery stanu są teraz w
  `wilq/content/workflow/stage_snapshot.py`, a API używa typed callbacks oraz
  kompatybilnego wrappera. `api.py` spadł do 644 LOC; focused content suite,
  Ruff, mypy, complexity i diff check przechodzą. Live snapshot homepage ma
  świeżość `fresh`, public canonical `https://www.ekologus.pl/`, 2 evidence
  IDs i konektory GSC/WordPress; browser `/content-workflow` pokazuje decyzję,
  sekcje public/dev, CTA preview i blokadę ActionObject.
- `wilq-seo-3bst.11` wykonany dla głównej trasy `/content-workflow`: pierwszy
  viewport używa copy „Podgląd na devie”, prowadzi do konkretnego CTA i obietnicy
  braku publikacji; mechanika ActionObject/centralnej akcji nie dominuje widoku.
  Vitest 15/15, ESLint, TypeScript, Vite build i screenshot desktop przechodzą.
- `wilq-seo-3bst.10` wykonany na `/content-workflow`: widoczny przełącznik
  `Marketer` / `Audyt techniczny` steruje zakresem pierwszego widoku i otwiera
  techniczne szczegóły dopiero w trybie audytu. Marketer widzi decyzję, blocker
  i następny krok; evidence IDs, kontrakty i ślad działania pozostają w audycie.
  Vitest 16/16, ESLint, TypeScript, Vite build, live API i screenshoty obu trybów
  przechodzą.
- Re-audyt `wilq-seo-3bst.5` nie znalazł luki do implementacji: `/opportunities`
  już renderuje kanoniczną „Kolejkę decyzji i akcji”, łączy work orders z
  ActionObjects, a testy i live API potwierdzają 5 opportunities oraz 21 akcji.
  Stary Bead zamknięto jako wykonany, bez duplikowania endpointu.
- `wilq-seo-3bst.12` wykonany: świeży packet `.local-lab/proof/dashboard-second-opinion/2026-07-13/`
  ma 6 screenshotów desktop/mobile, manifest, aktualny live API context i
  review prompt; zip packet jest wygenerowany lokalnie. Render review daje
  `/content-workflow` marketer 8/10, technical audit 8/10, queue 7/10,
  command center 7/10, mobile 7/10. To nie jest automatyczne 10/10 — główne
  braki to candidate density i skrócenie command center.
- `wilq-seo-3bst.9` wykonany: mobile triage na `/command-center` i
  `/content-workflow` pokazuje jedną pracę/decyzję, dwa blokery i jeden CTA;
  content ma disclosure evidence/freshness, a pełny workflow pozostaje niżej.
  Vitest 18/18, ESLint, TypeScript, Vite build i finalne screenshoty 390×844
  przechodzą. Render score wzrósł do 8/10 dla obu mobile surfaces.
- `wilq-seo-3bst.13` wykonany: `docs/roadmap/dashboard-target-visualization-2026-07-13.md`
  definiuje aktualny target brief dla design roastu, oparty wyłącznie na
  realnych WILQ routes/API, marketer-vs-audit IA, content workflow i ActionObject
  safety. Nie dodaje fikcyjnych możliwości ani endpointów.
- `wilq-seo-v9ab.11` wykonany: read-only redacted `WorkspaceDossier` jest
  API-owned w `wilq/knowledge/workspace_dossier.py` i dołączony do istniejącego
  `/api/marketing/daily-check`. Live response ma dossier Ekologus, znany false
  positive Ads account-scope oraz blockers candidate density i WordPress apply;
  focused daily-check/contracts, Ruff, mypy, complexity i diff check przechodzą.
- `wilq-seo-v9ab.12` wykonany: `RecommendationLogRecord` i istniejąca granica
  `AuditEvent` tworzą redacted ledger rekomendacji; `POST
  /api/marketing/daily-check/recommendations` zapisuje made/accepted/rejected/
  deferred, a GET daily-check zwraca ostatnią historię. Live POST/GET zachowuje
  evidence IDs i `redacted=true`, bez vendor mutation; focused tests, Ruff,
  mypy, complexity i diff check przechodzą.

- `wilq-seo-v9ab.4` platform-trap pack jest wykonany: typed
  `PlatformTrapContract` i pięć source-backed rule packs obejmują Google Ads,
  GA4, Merchant Center, GSC i WordPress. Istniejące diagnostyki Ads/GA4/Merchant
  odwołują się do nowych rule IDs; WordPress pack pozostaje dostępny przez ten
  sam `/api/expert/rules` i source registry. Nie dodano endpointu ani nowej
  ścieżki write.
- Live proof po managed restart: API `ok`, 99 906 metric facts, 4 577 refresh
  runs; `/api/expert/rules` zwraca pięć trap contracts z source IDs i safe next
  steps, a Merchant decision queue zawiera `merchant_platform_traps_v1`.
- `wilq-seo-v9ab.5` ma teraz pełny typed ExpertRule contract: condition,
  required connectors/metrics/window, segmentation, false-positive checks,
  blocked states, recommendation template, forbidden conclusions, safety level
  i eval case IDs. Pięć realnych rule packs wypełnia te pola; API summaries
  zachowują ten sam kontrakt. Focused expert/diagnostic tests, Ruff, mypy,
  complexity (0 changed-code violations) i diff check przechodzą.
- `wilq-seo-v9ab.7` ma pierwszy API-owned daily-check workflow przez istniejący
  runtime i nowy typed projection `/api/marketing/daily-check`. Wynik zwraca
  checked/skipped connectors, freshness, evidence IDs, source connectors,
  expert rule IDs, blocked recommendations, safe next actions i do-not-touch;
  live stan jest uczciwie `blocked` przy realnej blokadzie. Focused API/schema
  tests, Ruff, mypy, complexity i browser proof Command Center przechodzą.
- `wilq-seo-v9ab.8.1` domyka kolejny false-positive guard bez nowego endpointu:
  aggregate `decision_prepare_content_refresh_queue` przechodzi do review tylko,
  gdy oba WordPress source wymagane przez `wordpress_platform_traps_v1` mają
  własny typed `MetricFact` z evidence. Sama deklaracja konektora nie wystarcza.
  Guard nie dotyka indywidualnych publicznych work orderów, więc nie miesza
  `ekologus.pl` z osobnym sklepem. Live po restarcie: content queue ma
  `source_trace_ready`, `multi_source_ready`, `date_window_ready` oraz proof
  obu WordPress sources; focused contracts 27/27, Ruff i mypy przechodzą.
- `wilq-seo-v9ab.8.2` domyka osobny false positive: aggregate content queue
  wymaga teraz co najmniej jednego actionable work itemu z typed
  `ContentOpportunityMeasurementBaseline` (`ready_to_plan`, metryki,
  connectors i evidence). Publiczny URL sam nie wystarcza, blokowany Ahrefs
  candidate nie jest promowany, a wyjątek/mismatch fail-closed. Gdy jeden temat
  jest mierzalny, daily item zachowuje `review_required`, lecz jawnie mówi, że
  pełna kolejka pozostaje zablokowana przy 1 z 3 tematów; nie myli pojedynczego
  review z gotowym backlogiem.
- `wilq-seo-r564.5` domyka false positive Ahrefs bez nowego endpointu: jeden
  typed pure seam klasyfikuje cross-check GSC/WordPress jako `exact`, `weak`
  albo `missing` i jest wspólny dla content planning oraz tactical queue.
  Wyłącznie `exact` może oznaczyć popyt/inventory jako obecne, podbić score,
  wystawić review-only kolejkę lub wejść do preflight podobnych publicznych URL.
  `weak` zachowuje źródła i evidence, lecz jest ręcznym cross-checkiem bez
  ActionObjectu, briefu ani claimu duplikatu. Live po managed restarcie:
  Ahrefs `manual_required`, 6 kandydatów i 0 akcji; tactical queue ma 10 pozycji
  Ahrefs i 0 przypiętych akcji. Desktop/mobile proof jest w
  `.local-lab/proof/bdos-wilq-2026-07-12/`.
  Rekord WordPress bez publicznego URL, w tym identycznie zatytułowany szkic na
  `ekologus.dev.proudsite.pl`, jest odrzucany przed dopasowaniem frazy i nie
  może odblokować inventory, canonical ani kolejki.
- `wilq-seo-r564.6` domyka per-item Service Profile context bez nowego route:
  istniejący snapshot work itemu niesie teraz compact typed binding usługi,
  approval/claim status, freshness, evidence, source connectors, missing
  contracts i safe next step. Liczniki policy dotyczą tylko dopasowanej karty
  usługi, a pełny Claim Ledger pozostaje osobno. Binding pochodzi wyłącznie z
  istniejącego typed knowledge matcher; `service_fit` z enrichmentu pozostaje
  opisem tematu, nie podstawą claimów. W blocked snapshot context jest jawnie
  `not_evaluated`.
  Desktop i mobile pokazują jedną decyzję „Usługa i zasady twierdzeń” przy
  stronie publicznej, a techniczne ID są w disclosure.
- Live po managed restarcie: homepage `https://www.ekologus.pl/` ma binding
  `ekologus_service_homepage_overview`, źródło `public_site`, evidence
  `ev_content_service_profile_source_facts`, freshness signal `2026-07-02` i
  uczciwy status `blocked` z review przed finalnym draftem; write/publish
  pozostają false. Proof jest w `.local-lab/proof/r5646-service-profile/`.
- `wilq-seo-3bst.7` domyka jeden marketer-first slice diagnostyczny bez nowego
  endpointu ani reguły w React: `/ahrefs` pokazuje teraz przed galerią kart
  API-owned region „Najpierw zweryfikuj GSC i WordPress”. Rozróżnia on gotowość
  odczytu Ahrefs od decyzji, pokazuje 6 tematów do ręcznej oceny, po 0
  potwierdzeń GSC/WordPress, podsumowanie dowodów i jeden safe next step.
  Live `gap_read_contract` pozostaje `manual_required`, z zerem ActionObjectów;
  surowe ID nie wchodzą do pierwszego viewportu. Desktop 1440×900 i mobile
  390×844 są w `.local-lab/proof/3bst7-ahrefs/`; mobile ma `scrollWidth=390`.
  Re-review marketer/operator: 7/10 — w 30 sekund widać, że „gotowe” dotyczy
  danych, nie briefu ani publikacji; szczegóły Ahrefs zostają niżej.
- Parent `r564` pozostaje `blocked_by_external_state`, nie luką kolejki: GSC
  daje jeden unikalny publiczny URL, Ahrefsowe rekordy nie mają bezpiecznego
  `referenced_public_url`, a live queue ma 2 kandydatów / 1 actionable przy
  minimum 3. Nie twórz sztucznego trzeciego tematu.
- Complexity po `r564.6` ma jeden potwierdzony, śledzony dług techniczny:
  `wilq/content/workflow/api.py` ma 1500 LOC przy budżecie 800. Utworzony
  `c9h9.16` wydzieli tylko typed snapshot assembly seam; nie jest zgodą na
  mechaniczny split ani zmianę zachowania workflow.
- `wilq-seo-c9h9.17` domyka performance blocker Ahrefs bez cache'a i bez
  poluzowania freshness: live endpoint przed naprawą trwał `14.654183 s`,
  `15.872616 s`, a kolejny red-capable loop `17.760386 s`. Isolated profile
  znalazł 338-krotne budowanie tych samych rekordów GSC/WordPress dla 338 luk
  (`93 mln` wywołań, `46.961183 s` CPU). Immutable
  `AhrefsCrossSourceMatcher` kompiluje rekordy raz na batch, a dotychczasowy
  raw matcher pozostaje adapterem dla pojedynczych wywołań. Po managed
  restarcie trzy HTTP reads wyniosły `1.354044 s`, `1.351506 s` i `1.212189 s`.
  Kontrakt nie zmienił się: `manual_required`, 6 kandydatów, 0 exact GSC/WordPress
  i 0 akcji. Browser proof pierwszej decyzji jest w
  `.local-lab/proof/c9h9-17-ahrefs-latency/`.
- Podczas tego slice’a potwierdzono osobny dług monolitu tactical queue:
  `tactical_queue.py` ma 1400 LOC przy budżecie 800, więc nie ukryto w nim
  dodatkowej optymalizacji. Nowy `c9h9.18` wydzieli wyłącznie Ahrefs tactical
  branch do typed seamu przed użyciem compiled matcher; nie zmieni reguł
  exact/weak ani ActionObjectów.
- `wilq-seo-c9h9.15` domyka fałszywą blokadę bramki sekretów najwęższym
  wyjątkiem: celowa testowa nazwa pola redakcji ma inline
  `# pragma: allowlist secret` na jednej linii. Nowy scoped test potwierdza
  jednocześnie brak wyniku dla tej fixture, dokładnie jeden allowlisted
  `Secret Keyword` oraz wykrycie tego samego nieallowlistowanego pola w innym
  pliku tymczasowym. `scripts/security.sh` przechodzi z `{"results": {}}`;
  pip-audit nie znalazł znanych podatności, a semgrep pozostaje jawnie
  niedostępny, więc nie jest traktowany jako zaliczona bramka.

- Rebaseline `c9h9.2` został ponownie sprawdzony na `ba033433`: API health `ok`,
  99 906 metric facts, 4 577 refresh runs, 12 connectorów (9 configured,
  2 missing credentials), complexity 405 plików / 133 807 LOC / 0 changed-code
  violations. Dashboard usefulness audit zwraca 14 surfaces, 12 `demo_ready`,
  2 `review_ready`, `pass=true`; to nie znosi blokady stale źródeł.
- `c9h9.4` jest zamknięty i nie wymaga ponownej implementacji. Aktualny
  desktop/mobile browser proof `/content-workflow` jest w
  `.local-lab/proof/continuation-2026-07-12/`; `r564.3` jest zamknięty po
  świeżym proof, a parent `r564` nadal ma 2 kandydatów i tylko 1 actionable przy
  minimum 3; blocker `not_enough_actionable_candidates` pozostaje jawny.

- `kgvy` reconciliation boundary jest domknięty: `_reconcile_ads_change_history_contracts`
  oraz `_reconcile_ads_budget_and_business_context_contracts` wydzielają inline
  aktualizacje missing contracts. Nie zmieniają evidence/source/freshness ani
  blokad ActionObject; focused Ads contracts, Ruff, mypy, complexity i diff check
  przechodzą. Core i review assembly search-term contracts są domknięte; candidate
  assembly custom-segments/negative-keywords jest domknięty. Następny seam to
  campaign-triage/optimizer readiness assembly jest domknięty. Sections,
  blocked-handoff, decision_queue, response model i search contract-label hydration
  boundaries są domknięte; budget/recommendation/impression/change-history,
  change-impact/optimizer i core campaign/business/custom/derived labels są
  domknięte. Summary decision/candidate, response field compaction i primary
  read-contract bootstrap są domknięte, a parity jest potwierdzone. Najnowszy
  bounded seam to `_build_ads_action_enriched_contracts`, który skupia action-ID
  enrichment dla business context/change history/search-term n-gram,
  change-impact, custom segments i negative keywords bez zmiany kontraktu.
- Reconciliation boundary jest domknięty przez
  `_reconcile_ads_budget_and_business_context_contracts`; `build_ads_diagnostics`
  nie zawiera już inline aktualizacji missing contracts dla tych zależności.
  Complexity: 398 plików Python / 133264 LOC, 2 jawne violations (plik i główny
  orchestrator). Po tym seamu nie ma potwierdzonego kolejnego zachowania do
  mechanicznego wydzielenia; następny krok to świeży review pozostałego
  orchestratora i runtime proof, bez ponownego dotykania gotowych boundary.
- Główną trasą marketera jest `/content-workflow`; usunięty planner nie jest
  aktywną prawdą produktu.
- `ekologus.pl` pozostaje publicznym źródłem i canonical SEO. Proudsite jest
  wyłącznie workspace’em draft/dev.
- Managed API i dashboard są zdrowe. DuckDB ma 104 362 metric facts i 4 580
  refresh runs. Konektory: 12 ogółem, 9 skonfigurowanych, 2 bez credentials,
  1 wyłączony.
- Kolejka contentowa jest `blocked`: 2 kandydatów, 1 actionable, minimum 3.
  Homepage ma dowody z GSC i publicznego WordPressa; Ahrefs-only candidate nie
  ma bezpiecznego targetu/canonical.
- Queue i selected snapshot przenoszą teraz typed freshness; stale primary
  sources dają `content_sources_require_refresh`, `recommended_mode=block` i
  refresh-first `safe_next_step`. To zamyka P0 `c9h9.5`.
- `wilq-seo-3gre` i parent `4wwo` są domknięte: `/settings` uruchamia najwyżej
  jeden async `vendor_read` dla connectora, ale wyłącznie gdy API zwraca
  `automatic_refresh.eligible=true`. React nie ocenia stale/cooldown: po POST
  `queued` śledzi istniejący refresh-run przez GET i invaliduje `connectors` oraz
  tylko cache decyzji wskazanych przez API w `affected_decisions` dopiero po
  terminalnym wyniku. Błąd odczytu statusu pozostaje polskim blockerem z retry,
  a nie udawanym błędem vendora. Live proof: Ads, Merchant i Localo przeszły do
  `odświeżone`; 0 źródeł wymaga odświeżenia. LinkedIn i Facebook pozostają
  jawną blokadą dostępu.
  Live proof 2026-07-11: Google Sheets `refresh_google_sheets_1204e9337620`
  queued → completed, `external_call_attempted=false`, bez sekretów.
- Zamknięty `wilq-seo-jnra.1` naprawia realny rozjazd rejestru akcji: po live Google Ads
  read `/api/actions` ukrywał legacy OAuth repair, lecz direct lookup po ID
  zwracał go nadal. `list_actions()` i `get_action()` korzystają teraz z jednej
  canonical registry assembly. Live HTTP po managed restarcie: legacy action
  jest nieobecna z listy i zwraca 404, a aktywna akcja Keyword Planner nadal
  zwraca 200. Warm cache porównuje także key najnowszego Google Ads refreshu i
  zapisuje inventory tylko przy stabilnym fingerprint przed/po buildzie, więc
  przejście no-live → live nie zwraca stale legacy action. Full focused action
  contracts 48/48, evidence contracts 6/6, cache tests 4/4, Ruff i mypy
  przechodzą; WordPress mutation readiness nadal jest false/false/false bez
  vendor write.
- `wilq-seo-jnra.2` przenosi Keyword Planner eligibility i sanitizację blokady
  do istniejącego modułu Google Ads. Factory przyjmuje jeden refresh run,
  akceptuje wyłącznie completed `vendor_read` z potwierdzonymi danymi i znaną
  blokadą, a do ActionObjecta przekazuje tylko polski zsanityzowany powód oraz
  evidence. Focused factory/API/preview contracts przechodzą; live HTTP nadal
  pokazuje `prepare`, `apply_allowed=false`, `destructive=false` i brak raw
  vendor markers.
- `wilq-seo-jnra.3` przenosi politykę `confirmation_required` do istniejącego
  `review_gate.py`, który już składa required checks i apply blockers. Semantyka
  pozostaje fail-closed: `prepare` i `apply` wymagają confirmation, zaś
  `suggest` tylko przy case-sensitive checku zawierającym `human` i `confirm`.
  Focused review/confirmation contracts przechodzą; live prepare action nadal
  ma `confirmation_required=true`, `apply_allowed=false` i brak write path.
- Async refresh deduplikuje teraz aktywny run per connector: drugi queued/running
  request zwraca ten sam `run_id` i nie tworzy równoległego odczytu. Focused
  redaction/async contract suite: 4 passed; Ruff, mypy i diff check green.
- `refresh_state.refresh_allowed` jest fail-closed podczas aktywnego `queued` lub
  `running` runu. Test API potwierdza stan `queued`, `refresh_allowed=false` i
  bezpieczny krok „poczekaj”; runtime po restarcie health/metrics jest zdrowy.
- `/settings` nie omija już tego kontraktu w React: CTA odświeżenia renderuje się
  tylko dla stale źródła z `refresh_allowed=true`. Active-run test dashboardu
  ukrywa przycisk i pokazuje komunikat oczekiwania; focused Vitest 2/2,
  typecheck/lint green. Desktop render po zmianie zachowuje decyzję i CTA dla
  dozwolonych źródeł; proof `.local-lab/proof/4wwo-sources-refresh-state.png`.
- `wilq-seo-xu5s` domyka API-owned politykę kwalifikacji automatycznego
  read-only refresh: `ConnectorRefreshState.automatic_refresh` zwraca typed
  `eligible`, reason, Polish label, safe next step i 900 s cooldown. Tylko stale,
  configured, read-capable źródło bez credentials/aktywnego runu może zostać
  oznaczone `eligible_stale`; unknown, partial, failed, blocked, missing i
  cooldown są jawnie fail-closed. Live API po restarcie wskazuje obecnie
  Google Ads, Merchant i Localo jako eligible, bez uruchomienia żadnego vendor
  read. Backend 6/6, shared schema 34/34, dashboard focused 31/31, typecheck,
  lint, build, Ruff, mypy, complexity i diff check przechodzą. Dashboardowy
  trigger loop został domknięty przez `3gre` bez nowego endpointu ani write path.
- Po domknięciu refresh boundary przeszedłem do potwierdzonego `jnra`: read-only
  projekcje historii audytu i mutation auditów są teraz w
  `wilq/actions/audit_store.py`, z limitem 10 wpisów na akcję i bez zmiany
  ActionObject safety loop. Focused action suite 9 passed, Ruff/mypy/diff check
  green; complexity: 394 plików Python / 132243 LOC, `service.py` 4224 LOC.
- Kontynuacja `jnra` wydzieliła wybór pierwszej kandydatury zapisu oraz plan
  aktywacji/readiness do `wilq/actions/mutation_plan.py`. `service.py` zachowuje
  orkiestrację i ten sam ActionObject safety loop; live `/api/actions/mutation-readiness`
  raportuje 21 akcji, 0 vendor-write possible i 0 attempted, z WordPress
  draft-only jako pierwszą kandydaturą. Focused mutation/review/Goal 005 tests,
  Ruff, mypy, complexity i diff check przechodzą; `service.py` ma 4046 LOC.
- Następny mały seam `jnra` przeniósł kontrakt apply do
  `wilq/actions/mutation_contract.py`. Zachowane są `create_wordpress_draft`,
  `publication_allowed=false`, `destructive_allowed=false`, wymagane audyty,
  env gate i `None` dla nieobsługiwanych akcji; readiness/Goal 005 tests, Ruff,
  mypy, complexity i diff check pozostają zielone, a `service.py` ma 3868 LOC po
  kolejnych target/readiness seamach.
- Najnowszy seam `jnra` przeniósł WordPress-specific readiness requirements do
  `wilq/actions/wordpress_mutation_requirements.py`; `service.py` ma 3897 LOC,
  a dry-run/Claim Ledger blockers i ActionObject safety pozostają bez zmian.
  Focused readiness/review/Goal 005 tests, Ruff, mypy, complexity i diff check
  są zielone. Live po refreshu: 99906 metric facts, 4577 refresh runs,
  21 actions, 0 vendor-write possible i 0 attempted.
- Kolejny seam `jnra` przeniósł target projection readiness do
  `wilq/actions/mutation_target.py`; candidate ID, canonical URL i label
  fallback pozostają identyczne, a `service.py` ma 3868 LOC. Focused readiness
  tests, Ruff, mypy, complexity i diff check są zielone.
- Następny seam `jnra` przeniósł WordPress draft payload/handoff preview cards do
  `wilq/actions/wordpress_preview.py`; dispatcher zachowuje te same typed cards,
  labels i draft-only blockers przez jawne callbacks. Focused action/content
  preview tests, Ruff, mypy, complexity i diff check są zielone; `service.py` ma
  3782 LOC.
- Live action proof po restart: `/actions/act_prepare_wordpress_draft_handoff`
  renderuje typed WordPress cards z URL publicznym/kanonicznym, blocked claims i
  `zapis zmian zablokowany`; screenshot/text są w
  `.local-lab/proof/continuation-2026-07-12/action-preview-cards.*`.
- `kgvy` slice wykonany: optimizer-readiness assembly przeniesiono do
  `wilq/briefing/ads_optimizer.py`, a `ads_diagnostics.py` zmniejszył się o 358
  linii. Osiem obszarów zachowuje evidence IDs, source connectors, blocked claims
  i safe next steps; Ads contract suite, Ruff, mypy, complexity oraz runtime
  `/api/ads/diagnostics` po restarcie są zielone.
- `kgvy` pozostaje otwarty dla następnej granicy decision queue; nieprzeniesione
  kandydaty to metric tiles i marketer-label hydration. Wybór ma poprzedzić
  aktualny complexity report, żeby nie powtarzać optimizer/section/decision seams.
- Priority map decision queue jest już wydzielona do `ads_decision_queue.py`;
  focused contract potwierdza kolejność safety/review. Metric tiles nadal są
  otwartym seamem i nie zostały przeniesione mechanicznie.
- `kgvy` metric-tile continuation: formatowanie liczb i dwa pierwsze builders
  (`campaign_activity`, `campaign_triage`) są w nowych modułach; response i
  claim blockers pozostają bez zmian. Full Ads contracts, Ruff, mypy, complexity
  i diff check green. Pozostały dispatcher branches czekają na osobny bounded seam.
- Kolejny metric-tile continuation wydzielił `business_context` i `derived_kpi`;
  zachowane są target buckets, formatowanie i blokady CPA/ROAS. Complexity po
  seamu: 398 plików Python / 132419 LOC; pozostałe tile branches nie są jeszcze
  aktywną prawdą nowego modułu.
- Następny tile fragment wydzielił `budget_context` i `recommendations`;
  shared-budget, currency, impact i safety semantics pozostały bez zmian.
  Complexity dispatcher ma 122 linii; pozostałe branches czekają na kolejne
  bounded seamy.
- Kolejny fragment wydzielił `search_term_ngrams` i `impression_share`; zachowane
  są źródłowe koszty/kliknięcia i budget-loss count. Complexity dispatcher ma 12
  pozostałych, znanych violations; nie tworzymy nowego monolitu.
- Piąty tile fragment wydzielił `search_terms` i `search_term_safety`; query/
  click/cost oraz 90-dniowy safety context pozostają bez zmian. Complexity:
  398 plików Python / 132443 LOC; dispatcher branches nadal są jawnie śledzone.
- Szósty tile fragment wydzielił `negative_keyword_safety` i `custom_segments`;
  zachowane są urgent/high, preview, keyword context, source queries i KP ideas.
  Complexity: 398 plików Python / 132453 LOC; pozostałe branches czekają na osobny seam.
- Siódmy tile fragment wydzielił `change_history` oraz safety blocker tiles dla
  `block_write_actions`/`fix_ads_access`; change/campaign counts i safety counts
  pozostały bez zmian. Proste branches są zakończone, label hydration pozostaje
  osobnym zakresem.
- Label hydration został rozbity na cztery helpery orchestration w istniejącym
  `ads_diagnostics.py`; summary/decision/sections/nested contract labels i claim
  blockers zachowane. Complexity: 398 plików Python / 132477 LOC, 11 znanych
  pozostałych violations.
- Decision queue ma osobny `_blocked_ads_decision_queue` dla fail-closed OAuth/access
  handoff; evidence, blocked claims i priority lineage pozostają bez zmian.
- 90-dniowy search-term safety decision jest teraz w `ads_decision_queue.py` jako
  typed builder; rationale, evidence, source connector i blocked claims pozostają
  bez zmian. Complexity: 398 plików Python / 132481 LOC.
- `review_business_context` ma teraz osobny typed builder w
  `ads_decision_queue.py`; status, policy tile, evidence/action lineage i blocked
  profitability/scaling claims pozostają bez zmian. Complexity: 398 / 132485 LOC.
- `ads_block_write_actions_without_actionobject` ma teraz osobny typed builder w
  `ads_decision_queue.py`; fail-closed status, safety section evidence i blocked
  write claims pozostają bez zmian. Complexity: 398 / 132489 LOC; dispatcher ma
  11 znanych violations.
- `wilq-seo-v9ab.1` zamknięty po aktualizacji `PLANS.md` i master roadmapy:
  substrate `35-45%`, workflow parity `15-25%`, a real operator usefulness
  `10-20%` są rozdzielone; 35-45 nie jest już opisywane jako gotowość produktu.
- Ads decision assembler ma teraz osobny `_build_campaign_context_decisions` dla
  czterech pierwszych decyzji i `_build_ads_safety_decisions` dla fail-closed
  safety section. Complexity: 398 / 132512 LOC; violations spadły do 10.
- `_business_target_interpretation` deleguje blocked branch do
  `_blocked_business_target_interpretation`; brakujące kontrakty, blocked uses i
  evidence pozostają bez zmian. Complexity: 398 / 132535 LOC; 10 znanych violations.
- Ready/preliminary branch jest w `_preliminary_business_target_interpretation`;
  target ROAS/CPA context oraz strategy-review gate pozostają typed i fail-closed.
  Complexity: 398 / 132571 LOC; violations spadły do 9.
- Business-context summary/next-step copy jest w
  `_business_context_summary_and_next_step`; status, blokady i safe next step
  pozostają bez zmian. Complexity: 398 / 132572 LOC; 9 znanych violations.
- `_business_context_contract_state` przejął missing contracts, allowed metrics,
  target-missing i status; `AdsBusinessContextReadContract` pozostaje bez zmian.
  Complexity: 398 / 132597 LOC; 9 znanych violations.
- `_business_context_metric_tiles` przejął tile assembly kontekstu biznesowego;
  nazwy i wartości operator-facing pozostają bez zmian. Complexity: 398 /
  132616 LOC; 9 znanych violations.
- `_build_business_context_read_contract` przejął blocked claims i typed response
  assembly; target interpretation, strategy review, evidence i safe next step
  pozostają bez zmian. Complexity: 398 / 132665 LOC; violations spadły do 8.
- `_strategy_review_operator_state` przejął branch ready/blocked strategy review;
  missing contracts, action ID, safe next step i apply blockers pozostają bez zmian.
  Complexity: 398 / 132668 LOC; violations spadły do 7.
- `_compact_ads_candidate_contracts` przejął kompaktowanie custom segments,
  forecast rows i negative-keyword previews; summary limit i payload shape bez zmian.
  Complexity: 398 / 132675 LOC; violations spadły do 6.
- `_campaign_triage_source_context` przejął source metric/evidence aggregation i
  preview flags; triage row, action IDs i blocked claims pozostają bez zmian.
  Complexity: 398 / 132695 LOC; violations spadły do 5.
- `_negative_keyword_context_indexes` przejął indeksowanie 90-day safety i keyword
  context; candidate safety, evidence IDs i preview semantics pozostają bez zmian.
  Complexity: 398 / 132710 LOC; violations spadły do 4.
- Blocked negative-keyword read contracts są w dwóch helperach dla braku search
  terms i braku candidates; status, blocked claims, evidence i no-write semantics
  bez zmian. Complexity: 398 / 132728 LOC; violations spadły do 3.
- `_custom_segment_group_rows` i `_custom_segment_payload_and_score` przejęły
  grouping oraz preview/score orchestration; source terms, planner blockers i
  safety pozostają bez zmian. Complexity: 398 / 132760 LOC; violations spadły do 2.
- `_build_ads_diagnostic_sections` przejął typed section assembly z
  `build_ads_diagnostics`; kolejność, evidence lineage i safety section pozostają
  bez zmian. Complexity: 398 / 132801 LOC; główny orchestrator nadal jest kolejnym
  bounded targetem.
- `_reconcile_search_term_read_contracts` przejął reconciliation `90_day_safety_check`
  i `keyword match context`; search-term freshness i missing-contract semantics
  bez zmian. Complexity: 398 / 132815 LOC; 2 znane violations.
- `_reconcile_ads_recommendation_and_impression_contracts` przejął readiness
  reconciliation recommendations/impression share; evidence i missing contracts
  pozostają bez zmian. Complexity: 398 / 132848 LOC; 2 znane violations.
- Cold `/content-workflow` nie blokuje już pierwszej decyzji: API prewarmuje
  content diagnostics, queue reuse’uje ten sam build, a queue-owned karta
  renderuje się przed snapshotem. Focused E2E ma budżet queue `<5 s` i brak
  globalnego loadera; `c9h9.6` jest zamknięty.

## Zamknięty slice bezpieczeństwa

`c9h9.3` jest zamknięty:

- direct `POST /api/content/work-items/wordpress-draft-execution` zachowuje
  dry-run, ale nie dostaje realnego adaptera WordPress;
- `mode=live` zwraca `action_apply_required`,
  `external_write_attempted=false`, publish/destructive `false`;
- readiness jest zawsze fail-closed:
  `blocked_outside_action_apply`, `ready=false`, brak suggested authorization;
- React nie ma `runExecutionLive`, prepare-write CTA ani create-new-draft CTA;
  nawet sfabrykowane `ready=true` kończy się `dry_run` z autoryzacją `null`;
- istniejący draft jest tylko otwierany/podglądany, więc `r564.2` zamknięto;
- create przechodzi wyłącznie przez exact canonical apply z zamkniętego `c9h9.4`;
  direct content write pozostaje wyłączony.

`r564.4` również jest zamknięty. Existing-draft update action ma domenową typed
preview card z current/proposed/blocked state; raw payload pozostaje w technical
details. Screenshoty są lokalnie w
`.local-lab/proof/independent-review-2026-07-10/`.

## Zamknięty slice freshness

`c9h9.5` jest zamknięty:

- `ContentWorkItemQueueResponse`, kandydat i oba snapshot variants mają wspólny
  `ContentFreshnessAssessment` oraz typed queue candidate;
- stale/missing/blocked GSC lub publiczny WordPress blokują actionability przed
  planem, zachowując evidence IDs i source connectors;
- `/content-workflow` pokazuje refresh-first blocker above-fold na desktopie i
  mobile, bez raw payloadu;
- current freshness pochodzi z connector age/status, nie z regexu ani opisu.

Proof: live queue/snapshot HTTP, 5 focused backend test files, 31 shared schema
tests, dashboard typecheck/Vitest oraz screenshots w
`.local-lab/proof/independent-review-2026-07-11/`.

## Zamknięty slice cold-load

`c9h9.6` jest zamknięty:

- content diagnostics mają krótki, czyszczony po mutacji cache request-flow;
- pierwszy build reuse’uje content metric facts w tactical queue zamiast robić
  drugą lekturę metric store;
- API prewarmuje ten cache przed health w managed runtime, fail-open przy
  niedostępnym źródle;
- dashboard pokazuje queue-owned decyzję, dowody, źródła i safe next step, gdy
  snapshot/enrichment są jeszcze w toku; błędy są lokalne, nie globalne;
- browser proof: queue po prewarm `0.023 s`, focused Playwright `1 passed` z
  asercją `<5 s`, dashboard Vitest `138/138`.

## Aktualny browser/usefulness proof

- Desktop 1440×900 i mobile 390×844: stale-source blocker, źródła, powód i
  refresh-first next step są widoczne przed kolejką; homepage jest domyślnym
  wyborem zamiast Ahrefs-only braku canonical.
- Decision/CTA dla workflow mają queue-owned first card; mobile triage pokazuje
  decyzję, blocker i CTA w 390×844 na świeżych danych. `r564.3` jest zamknięty;
  dalsze candidate density należy do parenta `r564`.
- `c9h9.4` jest zamknięty: centralny apply ma typed `wordpress_draft` input,
  capability binding, route audit i dev-host guard; live CTA pozostaje
  zablokowane bez realnej gotowości.
- `r564.3` zamknięty: dodano mobile-only `Decyzja mobilna` po bannerze źródeł i
  statusach, z URL/tematem, rekomendacją, najważniejszym blockerem i bezpiecznym
  CTA otwierającym decyzję/dowody. CTA nie wykonuje zapisu. Focused
  ContentWorkflow Vitest 15/15, dashboard lint/typecheck green; live mobile
  screenshot `.local-lab/proof/continuation-2026-07-12/content-workflow-fresh-mobile.png`
  pokazuje uczciwy blocker `Za mało tematów gotowych do pracy` przy świeżych danych.
- Read-only odświeżenie dla `r564.3` 2026-07-12 zakończyło się dla WordPress
  sklep, GA4 i Ahrefs; queue ma teraz `fresh`/`requires_refresh=false`, ale
  nadal 2 kandydatów i 1 actionable przy minimum 3. Historyczna próba 2026-07-11
  pozostaje dowodem wcześniejszego timeoutu, nie aktualnym stanem.
- Historyczna próba read-only dla `r564.3` 2026-07-11: GSC zwrócił HTTP 200,
  ale kontrakt oznaczył odczyt jako niepełny (`evidence_count=2`); WordPress
  ekologus nie odpowiedział w 60 s. Kolejka po próbie nadal ma 2 kandydatów,
  1 actionable i blocker `not_enough_actionable_candidates`; stale pozostają
  sklep WordPress, GA4 i Ahrefs. Świeży, nieblokowany kandydat nadal nie jest
  potwierdzony. Ten wynik został zastąpiony świeżym odczytem z 2026-07-12.
- Mobile freshness banner jest skondensowany (summary poniżej desktop
  breakpointu), a pięć statusów źródeł tworzy poziomy scroll zamiast pięciu
  pionowych kart. Dzięki temu decision card wchodzi w 390×844; Vitest 17/17,
  lint/typecheck i świeży screenshot proof przechodzą.
- `c9h9.13` Merchant jest zamknięty: istniejący `/api/merchant/diagnostics` ma
  15-sekundowy cache i managed-runtime prewarm, bez nowego endpointu. HTTP po
  restarcie: `0.004860 s` pierwszy odczyt, `0.007203 s` drugi; desktop/mobile
  proof pokazuje Produkty, freshness, blocker i safe next step. Focused Merchant
  contracts 13/13, dashboard App 22/22, lint/typecheck, Ruff i mypy przechodzą.
- `c9h9.11` jest zamknięty: `/api/actions` używa istniejącej listy z 15-sekundowym
  cache/prewarm i po restarcie dał `0.061183 s` / `0.024930 s`; lista zachowuje
  evidence IDs bez ciężkiego detail buildera. Karta „Najbliższa bezpieczna akcja”
  pokazuje akcję także podczas oczekiwania na mutation readiness, ale oznacza
  readiness jako sprawdzane i zapis jako zablokowany. Focused action Vitest 2/2,
  dashboard lint/typecheck i backend cache test przechodzą; browser proof:
  `.local-lab/proof/c9h9-11-actions-cold-browser-final.png` oraz
  `.local-lab/proof/c9h9-11-actions-detail-cold-browser-loaded.png`.
- `c9h9.9` jest zamknięty: istniejący `/api/ads/diagnostics?view=summary` ma
  15-sekundowy cache read-through; po restarcie HTTP `1.426757 s` cold i
  `0.016956 s` warm. Shared schema przestał odrzucać API summary przez trzy
  nieadsowe pola review (defaults zamiast wymagań); 5 decyzji Ads i wszystkie
  mają evidence. Ads route nie blokuje już first paint na kolejce akcji i ma
  bezpieczny shell „Odczyt Ads w toku”. Proof: `.local-lab/proof/c9h9-9-ads-first-decision-fixed-loaded.png`;
  focused current Playwright `apps/dashboard/e2e/ads-summary-current.spec.ts`
  passes 1/1 in 7.8 s. Route-level cold first paint is still above the 5 s
  measured heading first paint `1.853 s` (<5 s). Lazy-route shell proof at 2 s:
  `.local-lab/proof/c9h9-9-ads-route-shell-2s.png`.
- `c9h9.12` jest zamknięty: `/knowledge` ładuje operating-map jako jedyny pierwszy
  odczyt, a karty/playbooki dopiero po disclosure. `list_workflows()` używa już
  tylko `build_daily_command_center()`, a standalone cold map core spadł do
  `4.878 s` (11 bindings, 15 kart, 14 playbooków). Cache mapy ma 15 s; po
  restarcie managed runtime uruchamia nieblokujący prewarm w tle: health pozostaje
  gotowy, a pierwszy HTTP odczyt mapy po rozgrzaniu wyniósł `0.003550 s`, drugi
  `0.003175 s`. Browser proof przy 3 s pokazuje
  decyzję i blokery bez pustego globalnego loadera:
  `.local-lab/proof/c9h9-12-knowledge-progressive-3s.png`; focused current
  Playwright `1/1` przechodzi w `2.7 s` (29.2 s z uruchomieniem harnessu). Po
  kolejnym managed restart health i map HTTP pozostały gotowe; świeżość źródeł
  wiedzy nadal jest niezależna od cache latency. Nie przywracaj współbieżnych
  katalogów ani nie traktuj starego payloadu jako świeżego.
- `c9h9.10` jest zamknięty: Custom Segments korzysta z istniejącego Ads summary
  projection zamiast pełnego payloadu; focused Playwright `1/1` w `4.4 s`
  potwierdza kandydatów, forecast, evidence i blokady claims bez audience-size
  ani write. Nie dodano endpointu.
- `c9h9.8` jest zamknięty: `apps/dashboard/e2e/dashboard-api.spec.ts` ma 13/13
  testów przechodzących po zmianie wyłącznie starych heading/assertion strings na
  aktualne zachowanie Ads, Content, Actions, Knowledge i Merchant. Nie podnoszono
  timeoutów, nie przywracano legacy IA, a pełny smoke nadal sprawdza brak raw IDs
  i technicznego copy above the fold.
- `jnra` dostał mały, zachowawczy seam: konstruktory ActionObjectów Google Ads
  dla kontekstu biznesowego i potwierdzenia celu przeniesiono do istniejącego
  `wilq/actions/google_ads/business_context.py`; service zachowuje readiness,
  evidence i delegację. Focused action contract `business_context` /
  `keyword_planner`, Ruff, mypy i diff check przechodzą. Większy split pozostaje
  otwarty i nie może omijać validate → preview → review → confirm → audit.
  Następny krok tego samego zakresu przeniósł konstruktor Keyword Planner do
  `wilq/actions/google_ads/keyword_planner.py`, zachowując zewnętrzną blokadę
  dostępu, evidence i `apply_allowed=false`; konstruktor strategy-review trafił
  do tego samego modułu biznesowego, zachowując human review gate.
- Static Google Ads OAuth repair ma teraz konstruktor w
  `wilq/actions/google_ads/oauth.py`; `seed_static_actions` zachowuje ten sam
  ID, helper commands, evidence i brak zapisu. Nie wydrukowano credentialów.
- Publiczny Service Profile knowledge-promotion constructor jest teraz w
  `wilq/actions/service_profile.py`; `service.py` nadal buduje profile/review
  rows, a domenowy seam zachowuje evidence, `apply_allowed=false` i blokadę
  production-depth. Focused content/API contract, Ruff, mypy i diff check
  przechodzą.
- `wilq-seo-v9ab.8` rozpoczęty bounded slice: `evaluate_source_trace_guard`
  blokuje stale/missing source, brak evidence albo brak expert rule przed
  rekomendacją. `DailyCheckItem` zachowuje `false_positive_guards`; live daily
  check pokazuje `stale_connector` przy obecnym stale stanie. Focused guard/API
  tests, Ruff, mypy i diff check przechodzą. `missing_conversion` korzysta z
  istniejącego `Ga4ConversionReadinessContract`; gotowy kontrakt daje
  `conversion_readiness_ready`. Pozostałe guards (low volume, baseline, date
  window, conflict, multi-source) pozostają otwarte.
- `v9ab.8` ma też `date_window`: daily-check korzysta z istniejącego
  `ContentGscSearchAnalyticsContract`, zwracając `date_window_ready` albo
  blokadę przy braku bounded availability/completeness. Live content item ma
  `stale_connector` + `date_window_ready`; focused tests, Ruff, mypy i
  complexity przechodzą.
- Prywatna Service Profile proposal-promotion ma teraz analogiczny konstruktor
  w `wilq/actions/service_profile.py`; service buduje tylko redacted review rows,
  a domenowy moduł zachowuje `redacted`, evidence, `apply_allowed=false` i
  zablokowane prywatne twierdzenia. Oba Service Profile review seams są pokryte
  focused content/API tests.
- WordPress draft-handoff constructor jest teraz w istniejącym
  `wilq/actions/wordpress_draft.py`; service zachowuje wybór brief previews,
  content gating i evidence. Prepare-only, canonical/duplicate/legal review oraz
  `apply_allowed=false` pozostają bez zmian. Apply-mode constructor również jest
  domenowym delegatem; service zachowuje builder typed apply contract jako
  granicę bezpieczeństwa.
- Static Google Ads recommendation-review seed jest teraz w istniejącym
  `wilq/actions/google_ads/recommendations.py`; fallback read-required evidence,
  required validation i blokada apply pozostały identyczne. Merchant, GA4 i
  content static seeds są osobnymi domenowymi seamami.
- Static Merchant feed-issue seed jest teraz w `wilq/actions/merchant.py`;
  `seed_core_prepare_actions` zachowuje connector evidence, review steps,
  prepare-only i zablokowane twierdzenia. Focused Merchant action/API tests
  przechodzą. GA4 i content static seeds pozostają kolejnymi seamami.
- Static GA4 tracking-quality seed jest teraz w
  `wilq/actions/ga4/tracking_quality.py`; fallback breakdowns, preview, evidence
  i blokady conversion/revenue/ROAS są zachowane. Focused GA4 source/context/action
  contracts przechodzą.
- Static content refresh seed jest teraz w `wilq/actions/content_refresh.py`;
  `seed_core_prepare_actions` deleguje bez zmiany evidence, preview URL/canonical
  gates, blokad claimów i `apply_allowed=false`. Inventory, ActionObject i API
  contracts oraz Ruff, mypy i diff check przechodzą; runtime `/api/actions`
  pokazuje prepare-only content action z evidence i bez vendor write.
- `seed_metric_action_candidates` ma teraz cienką granicę orkiestratora, a grupy
  Merchant, GA4, Content, Google Ads, Localo i Social są osobnymi helperami.
  Social został przeniesiony do `wilq/actions/social.py`, a priorytety i
  deduplikacja do `wilq/actions/metric_utils.py`. Focused ActionObject/content/
  Social API tests, Ruff, mypy i diff check przechodzą; runtime zachowuje 21
  akcji, oba social draft actions w `prepare` z sześcioma evidence i centralne
  `write_capable=0`. Localo również działa w `prepare` z jednym evidence;
  Merchant działa w `prepare` z jednym evidence i `apply_allowed=false`;
  GA4 działa w `prepare` z jednym evidence i zachowuje blokadę konwersji/ROAS;
  Content ma typed candidate factory w `wilq/actions/content_refresh.py`, a
  WordPress handoff nadal ma `apply_blocked`; `service.py` spadł do 5 046 LOC.
- Google Ads campaign review ma teraz candidate factory w
  `wilq/actions/google_ads/campaign_review.py`; prepare-only, evidence i blokada
  budżetu/zapisu pozostają bez zmian. Runtime pokazuje kampanię w `prepare` z
  jednym evidence i centralne `write_capable=0`; `service.py` spadł do 5 035 LOC.
- Google Ads recommendation review ma teraz candidate factory w
  `wilq/actions/google_ads/recommendations.py`; typ rekomendacji, preview wpływu,
  blokady zapisu i evidence pozostają bez zmian. Runtime pokazuje rekomendacje w
  `prepare` z jednym evidence i `apply_allowed=false`; `service.py` spadł do
  5 020 LOC.
- Google Ads change-history impact ma teraz candidate factory w
  `wilq/actions/google_ads/change_history.py`; okno wpływu, preview i blokada
  zapisu pozostają bez zmian. Runtime pokazuje action w `prepare` z jednym
  evidence i centralne `write_capable=0`; `service.py` spadł do 5 007 LOC.
- Google Ads search-term n-gram ma teraz candidate factory w
  `wilq/actions/google_ads/search_term_ngrams.py`; n-gram preview, blokada
  wykluczeń i evidence pozostają bez zmian. Runtime pokazuje action w `prepare`
  z jednym evidence i `apply_allowed=false`; `service.py` spadł do 4 996 LOC.
- Google Ads custom segment ma teraz candidate factory w
  `wilq/actions/google_ads/custom_segments.py`; terminy źródłowe, safety preview,
  blokada kierowania i evidence pozostają bez zmian. Runtime pokazuje action w
  `prepare` z jednym evidence i centralne `write_capable=0`; `service.py` spadł
  do 4 983 LOC.
- Google Ads negative-keyword ma teraz candidate factory w
  `wilq/actions/google_ads/negative_keywords.py`; 90-day safety, exact-match
  preview, evidence i blokada zapisu pozostają bez zmian. Runtime pokazuje action
  w `prepare` z jednym evidence i `90_day_safety_check`; `service.py` spadł do
  4 970 LOC.
- Google Ads Demand Gen readiness ma teraz pełny candidate factory w
  `wilq/actions/google_ads/demand_gen.py`; zachowuje kampanijny kontekst, GA4
  cross-check, evidence IDs, brakujące kontrakty, `prepare` i
  `apply_allowed=false`. Runtime pokazuje akcję z pięcioma evidence i dwoma
  brakującymi kontraktami; `service.py` spadł do 4 788 LOC, a centralny
  `write_capable=0` pozostał bez zmian.
- Predykaty bezpieczeństwa payloadu (`apply_allowed` i
  `api_mutation_ready`) mają teraz mały typed seam w
  `wilq/actions/payload_readiness.py`; service zachowuje istniejącą granicę
  preview i zachowanie centralnego apply gate.
- Action status/risk/mode/evidence/mutation labels mają teraz typed seam w
  `wilq/actions/operator_labels.py`; service zachowuje te same polskie etykiety,
  źródła connectorów i safety semantics.
- Pełne mapowanie `_action_gate_label` jest teraz w
  `wilq/actions/gate_labels.py`; service zachowuje kompatybilny delegat i te same
  blokady claims, evidence, review i apply.
- Review-gate assembly jest teraz w `wilq/actions/review_gate.py`; service
  zachowuje odczyt eventów, blocker calculation i callbacki audit/labels, a
  moduł składa ten sam typed `ActionReviewGate`. Complexity po seamu: service.py
  4 468 LOC, bez zmiany `write_capable=0`.
- Mapping blockerów mutation readiness jest teraz w
  `wilq/actions/mutation_readiness.py`; wymagania i kolejność blokad pozostają
  service-owned, a każdy niespełniony warunek nadal daje polski blocker i safe
  next step. Complexity po seamu: service.py 4 341 LOC.
- Bazowa lista requirements mutation readiness jest w
  `wilq/actions/mutation_requirements.py`, a typed response assembly w
  `wilq/actions/mutation_response.py`. Service zachowuje WordPress-specific
  readiness i adapter gates; obecny runtime nadal ma 0 write-capable actions.
- Mutation readiness summary assembly jest teraz w
  `wilq/actions/mutation_summary.py`; service zachowuje wybór kandydatów,
  blocker counts i operator next-step callbacks, a typed summary nadal raportuje
  21 akcji i 0 write-capable.
- `4wwo` ma teraz istniejący `/api/connectors` rozszerzony o typed
  `refresh_state`: stan odczytu, `refresh_allowed`, ostatni run, safe next step i
  affected decisions. `/settings` pokazuje tę informację ponad ręcznym CTA;
  browser proof jest w `.local-lab/proof/4wwo-sources-refresh-state.png`.
- Complexity po rozszerzeniu connector schema: 392 pliki / 132005 non-empty LOC;
  jedyny changed-file budget finding to wcześniejszy `_metric_dimension_value_label`
  w `wilq/schemas/core.py`, niezwiązany z refresh-state slice.
- W `c9h9.4` dodano warunkowy review-only CTA w panelu dev draft: pojawia się
  tylko po `draft_package_ready && handoff_ready`, prowadzi do istniejącej
  akcji `act_apply_wordpress_draft_handoff` i jawnie mówi, że nie wykonuje
  zapisu/publikacji. Live stale queue nadal nie pokazuje CTA; browser proof
  `.local-lab/proof/content-workflow-c9h9-4-review-only.png` pokazuje refresh-first
  blocker i brak nieautoryzowanego CTA above fold.
- `/actions/act_prepare_wordpress_existing_draft_update`: first viewport mówi
  „Przygotuj i oceń bez zapisu zmian” oraz „Zapis zablokowany”; pełny render ma
  typed preview i technical disclosure.
- `jnra` ma kolejny bounded seam: składanie `wordpress_draft_payload_preview_v1`
  przeniesiono do `wilq/actions/wordpress_payload_preview.py`. `content_refresh`
  zachowuje policy helpers, evidence/source lineage, canonical/duplicate gates,
  blocked claims i `apply_allowed=false`; nowy moduł składa ten sam typed payload
  przez jawny support boundary. Focused action/content contracts, Ruff, mypy,
  complexity i diff check przechodzą.
- Live proof po managed restart: API health `ok`, 99 906 metric facts / 4 577
  refresh runs, content queue `fresh` lecz zablokowana przy 1 actionable z 3,
  a WordPress handoff nadal ma cztery typed preview cards i brak ścieżki zapisu.
- Następny bounded seam `jnra`: social preview cards są teraz składane przez
  `wilq/actions/social.py`, a `service.py` przekazuje tylko presentation
  callbacks. Live `/api/actions` nadal pokazuje LinkedIn/Facebook w trybie
  `prepare` z evidence IDs, czterema kartami `social_draft_input_review` i bez
  publikacji; focused social/action tests, Ruff, mypy i complexity przechodzą.
- Kolejny bounded seam Ads: renderer `budget_apply_preview_v1` jest teraz w
  `wilq/actions/google_ads/previews.py`; service przekazuje callbacks do rows,
  money labels i safety labels. Live Ads action ma `prepare`, evidence ID,
  cztery `google_ads_budget_review` cards, `apply_allowed=false` i
  `api_mutation_ready=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-budget-preview-cards.png`.
- Następny seam Ads recommendations jest w `wilq/actions/google_ads/recommendations.py`;
  dispatcher zachowuje `recommendation_apply_preview_v1`, evidence i blocked
  claims, a live action ma cztery `google_ads_recommendation_review` cards,
  `apply_allowed=false` i `api_mutation_ready=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-recommendation-preview-cards.png`.
- Następny seam Ads negative keywords jest w istniejącym
  `wilq/actions/google_ads/negative_keywords.py`; live action ma dwa typed
  `google_ads_negative_keyword_review` cards, evidence ID, 90-dniowe warunki
  sprawdzenia i `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-negative-preview-cards.png`.
- Następny seam Ads custom segments jest w istniejącym
  `wilq/actions/google_ads/custom_segments.py`; live action ma typed
  `google_ads_custom_segment_review` card, evidence ID, Keyword Planner/
  audience-size blockers, blocked claims i `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-custom-preview-cards.png`.
- Change-history preview jest teraz w `wilq/actions/google_ads/change_history.py`;
  dodatkowo usunąłem potwierdzony przeciek raw event IDs, enumów i nazw pól z
  karty above fold. Behavior test i browser proof potwierdzają genericzne rows,
  4 cards, evidence ID, blocked claims i brak zapisu:
  `.local-lab/proof/continuation-2026-07-12/ads-change-history-preview-cards.png`.
- Demand Gen readiness preview jest teraz wydzielony do
  `wilq/actions/google_ads/demand_gen_preview.py`; `service.py` przekazuje tylko
  jawne callbacks do rows/labels. Live action
  `act_review_demand_gen_readiness` ma jeden typed card, 4 evidence IDs,
  freshness z Google Ads/GA4, brakujące kontrakty dla landing quality i mode
  control oraz `apply_allowed=false`/`api_mutation_ready=false`. Behavior test,
  Ruff, mypy, complexity i browser proof przechodzą; pierwszy viewport jasno
  pokazuje „Zapis zablokowany”, a karta chowa techniczne payloady:
  `.local-lab/proof/continuation-2026-07-12/ads-demand-gen-preview-cards.png`.
- Search-term n-gram preview jest teraz wydzielony do
  `wilq/actions/google_ads/search_term_ngram_preview.py`; live action ma cztery
  typed cards z metrykami, przykładami zapytań, freshness/evidence i blokadą
  przejścia do wykluczeń. `apply_allowed=false` i
  `api_mutation_ready=false`; focused behavior test, Ruff, mypy, complexity i
  browser proof przechodzą:
  `.local-lab/proof/continuation-2026-07-12/ads-search-ngram-preview-cards.png`.
- GA4 tracking-quality preview jest teraz wydzielony do
  `wilq/actions/ga4/tracking_preview.py`; live action zachowuje landing/source/
  campaign rows, metric snapshot, tracking gaps, blocked claims i
  `apply_allowed=false`/`api_mutation_ready=false`. Focused behavior test, Ruff,
  mypy, complexity i browser proof przechodzą:
  `.local-lab/proof/continuation-2026-07-12/ga4-tracking-preview-cards.png`.
- Localo visibility preview jest teraz wydzielony do
  `wilq/actions/localo/visibility_preview.py`; live action zachowuje typed
  agregaty widoczności, dozwolone i brakujące kontrakty, blocked claims oraz
  `apply_allowed=false`/`api_mutation_ready=false`. Focused behavior test, Ruff,
  mypy, complexity i browser proof przechodzą:
  `.local-lab/proof/continuation-2026-07-12/localo-visibility-preview-cards.png`.
- Merchant feed preview jest teraz wydzielony do
  `wilq/actions/merchant_preview.py`; service zachowuje istniejący kontrakt
  klas problemów, priorytety próbek i polskie etykiety. Live action ma cztery
  typed cards, evidence, product-sample context i `apply_allowed=false`/
  `api_mutation_ready=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/merchant-feed-preview-cards.png`.
- Keyword Planner access factory i preview są teraz w istniejącym
  `wilq/actions/google_ads/keyword_planner.py`; live action ma 2 evidence IDs,
  zsanityzowaną zewnętrzną blokadę dostępu, bezpieczny next step, blocked claims
  i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/keyword-planner-access-preview.png`.
- Ads target-guardrail preview jest teraz w istniejącym
  `wilq/actions/google_ads/business_context.py`; service przekazuje callback do
  business-context rows i safety labels. Live action ma 2 evidence IDs,
  brak potwierdzonego ROAS/CPA, blocked KPI/budget claims i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-target-guardrail-preview.png`.
- Ads strategy-review preview jest teraz w istniejącym
  `wilq/actions/google_ads/business_context.py`; service przekazuje callback do
  business-context rows, summary i safety labels. Wspólne wiersze kontekstu,
  etykieta podsumowania review oraz liczniki źródeł pozostają w module domenowym,
  a service przekazuje tylko callbacks prezentacyjne. Live action ma 2 evidence IDs,
  brak zapisanego wyniku ludzkiego review, blocked KPI/budget claims i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-strategy-review-preview.png`.
- Service Profile knowledge-promotion i private-proposal preview cards są teraz
  składane w istniejącym `wilq/actions/service_profile.py`; service zachowuje
  tylko dispatcher i callbacks prezentacyjne. Publiczne source facts oraz
  redacted private proposal nadal mają evidence, review gates, blocked claims i
  `apply_allowed=false`; świeży private browser proof:
  `.local-lab/proof/continuation-2026-07-12/service-profile-private-preview-live.png`.
- Content brief preview card jest teraz w nowym, wąskim
  `wilq/actions/content_preview.py`; `service.py` przekazuje callbacks do rows,
  list i safety labels, a content-refresh payload pozostaje API-owned. Live
  action ma 3 evidence IDs, trzy typed `content_brief_review` cards, publiczne
  URL-e i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-brief-preview-live.png`.
- Content-refresh preview composition (brief cards + reviewed WordPress draft
  card) jest teraz w `wilq/actions/content_preview.py`; `service.py` przekazuje
  jedynie typed callbacks i zachowuje istniejący WordPress preview adapter.
  Live output nadal ma 3 `content_brief_review` cards, 3 evidence IDs i blokadę
  zapisu; świeży browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-refresh-composition-live.png`.
- Localo metric snapshot rows używane przez preview są teraz w istniejącym
  `wilq/actions/localo/visibility_preview.py`; service przekazuje domenowy
  helper zamiast posiadać własną kopię. Live action zachowuje 1 evidence ID,
  agregaty widoczności, blocked GBP/konkurencja claims i `apply_allowed=false`;
  browser proof:
  `.local-lab/proof/continuation-2026-07-12/localo-metric-helper-live.png`.
- GA4 metric snapshot rows i formatter są teraz w istniejącym
  `wilq/actions/ga4/tracking_preview.py`; service przekazuje domenowy helper.
  Live action zachowuje 1 evidence ID, landing/source/campaign context,
  blocked ROAS/revenue claims i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/ga4-metric-helper-live.png`.
- Review summary/blocker label assembly jest teraz w istniejącym
  `wilq/actions/review_gate.py`; service zachowuje tylko callbacki do outcome,
  contract labels, gate labels i zredagowanych claimów. Safety loop i Polish
  review copy pozostają bez zmian; browser proof:
  `.local-lab/proof/continuation-2026-07-12/review-gate-summary-live.png`.
- Parsery szczegółów review URL i draft-readiness są teraz w nowym wąskim
  `wilq/actions/content_review_details.py`; `service.py` zachowuje tylko
  składanie ActionReviewDetails. Dozwolone klucze i redakcja nieznanych pól są
  pokryte testem; live content action zachowuje 3 evidence IDs, typed cards i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-review-details-live.png`.
- Review outcome label, latest human-review event selection i event-to-outcome
  projection są teraz w istniejącym `wilq/actions/review_gate.py`; service
  zachowuje tylko orchestrację gate. Live Ads strategy action ma 2 evidence IDs,
  `kontrola WILQ poprawna` i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/review-outcome-projection-live.png`.
- Preview, confirmation, impact-check i apply blocker rules są teraz w nowym
  `wilq/actions/action_blockers.py`; service przekazuje tylko Ads guardrail,
  mutation-adapter i readiness callbacks. Live strategy action zachowuje jawne
  blocked claims, `apply_allowed=false` i brak vendor write; browser proof:
  `.local-lab/proof/continuation-2026-07-12/action-blockers-live.png`.
- Confirmation event types, confirmation summaries, Ads target summaries i
  impact-check summaries są teraz w `wilq/actions/action_blockers.py`; service
  przekazuje tylko etykiety i callbacki domenowe. Live strategy action zachowuje
  2 evidence IDs, jawne blocked claims i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/action-summary-live.png`.
- Audit summary/operator text normalization, raw contract detection and
  identifier redaction są teraz w istniejącym `wilq/actions/audit_store.py`;
  `service.py` zachowuje kompatybilną fasadę. Live strategy action nadal ma 2
  evidence IDs, blokadę zapisu i redacted operator surface; browser proof:
  `.local-lab/proof/continuation-2026-07-12/audit-summary-live.png`.
- Mapowanie etykiet zdarzeń audytu jest teraz w istniejącym
  `wilq/actions/audit_store.py`; `service.py` deleguje labelowanie znanych
  review/preview/confirm/impact/apply eventów i bezpieczny fallback, bez zmiany
  ActionObject safety loop. Focused audit/review tests, Ruff, mypy, complexity,
  managed runtime i świeży browser proof przechodzą; live Ads strategy action
  ma 2 evidence IDs, `apply_allowed=false` i stan `Zapis zablokowany`;
  proof: `.local-lab/proof/continuation-2026-07-12/event-label-live.png`.
- Hydracja etykiet payloadów akcji jest teraz w istniejącym
  `wilq/actions/operator_labels.py`; statusy, bramki, typy Ads i statusy
  WordPress zachowują dotychczasowy polski kontrakt, a `service.py` ma tylko
  kompatybilną fasadę. Focused operator/action tests, Ruff, mypy, complexity,
  managed restart i browser proof przechodzą; live Ads strategy action nadal
  ma 2 evidence IDs, `Zapis zablokowany` i `apply_allowed=false`;
  proof: `.local-lab/proof/continuation-2026-07-12/operator-labels-live.png`.
- Read-only helpery metryk `latest_metric_facts_by_identity`,
  `metric_fact_sort_time` i `facts_by_connector` są teraz w istniejącym
  `wilq/actions/metric_utils.py`; `service.py` zachowuje kompatybilne fasady,
  a deduplikacja po źródle/nazwie/wymiarach, kolejność `collected_at` i kolejność
  faktów w grupach pozostają identyczne. Focused metric/action tests (6 passed),
  Ruff, mypy, complexity, managed runtime i browser proof przechodzą; live
  `/api/actions` ma 21 akcji, 0 write-capable, a strategy action zachowuje 2
  evidence IDs i `apply_allowed=false`; proof:
  `.local-lab/proof/continuation-2026-07-12/metric-utils-live.png`.
- Localo-specific fallback po probe-only faktach jest teraz własnością
  istniejącego `wilq/actions/localo/visibility.py`; storage i refresh-run I/O
  pozostają callbackami service. Focused Localo/metric/action tests (7 passed),
  Ruff, mypy, complexity, managed runtime i browser proof przechodzą; ciepły
  detail HTTP 200 ma 10 metryk, evidence ID i `apply_allowed=false`;
  proof: `.local-lab/proof/continuation-2026-07-12/localo-metric-fallback-live.png`.
- Re-audit utworzył i domknął `wilq-seo-zbre`: `get_action()` korzysta z kopii
  istniejącego prewarmed registry cache, po czym nadal nakłada świeży
  validation/audit/review gate. Pierwszy Localo action-detail po pełnym
  restarcie spadł z wcześniejszego timeoutu >60 s do HTTP 200 w `0.013299 s`;
  10 metryk, evidence ID i `apply_allowed=false` pozostały bez zmian. Browser
  proof: `.local-lab/proof/continuation-2026-07-12/localo-cold-fixed-live.png`.
- Parser kolejności preview payloadów i wyboru kontraktu jest teraz w
  istniejącym `wilq/actions/payload_readiness.py`; `service.py` zachowuje cienkie
  fasady, a `apply_allowed`, `api_mutation_ready`, preview i review gate używają
  tej samej kolejności fallbacków. Focused payload/cache/metric tests (7 passed),
  Ruff, mypy, complexity, managed runtime i browser proof przechodzą; Localo i
  Ads detale mają HTTP 200, evidence, `zapis zmian zablokowany` i
  `apply_allowed=false`; proof:
  `.local-lab/proof/continuation-2026-07-12/payload-readiness-live.png`.
- Wybór `required_checks` i `operator_checklist` jest teraz w istniejącym
  `wilq/actions/review_gate.py`; service przekazuje tylko parser payloadu,
  `string_list` i deduplikację. Localo i Ads detail po restarcie zachowują po 5
  wymaganych checks/checklist, `kontrola WILQ poprawna`, evidence i
  `apply_allowed=false`; focused review/payload tests (8 passed), Ruff, mypy,
  complexity i browser proof przechodzą; proof:
  `.local-lab/proof/continuation-2026-07-12/review-gate-builders-live.png`.
- Selekcja najnowszego Google Ads `vendor_read` i recency tie-breaker są teraz
  w istniejącym `wilq/actions/google_ads/business_context.py`; service tylko
  dostarcza listę refresh runs. Ads strategy detail zachowuje 2 evidence IDs,
  5 checks, świeży gate i `apply_allowed=false`; Localo pozostaje bez zmian.
  Focused Ads/review tests (9 passed), Ruff, mypy, complexity, managed runtime
  i browser proof przechodzą; proof:
  `.local-lab/proof/continuation-2026-07-12/ads-vendor-read-selection-live.png`.
- Filtrowanie najnowszych Google Ads metric facts po completed vendor-read i
  `source_connector=google_ads` jest teraz w tym samym module
  `google_ads/business_context.py`; service przekazuje tylko metric-store
  callback. Focused Ads/review tests (10 passed), Ruff, mypy, complexity,
  managed runtime i browser proof przechodzą; Ads strategy zachowuje 2
  evidence IDs, świeży gate i `apply_allowed=false`; proof:
  `.local-lab/proof/continuation-2026-07-12/ads-latest-facts-live.png`.
- Manual usefulness `/content-workflow` pozostaje 6/10: freshness i pierwsza
  decyzja są jawne, ale pełna karta świeżego workflow i mobile triage nadal
  wymagają dopracowania.

- Selektory najnowszych zdarzeń preview/confirmation/impact oraz mutation audit
  są teraz w istniejącym `wilq/actions/audit_store.py`; `service.py` zachowuje
  tylko kompatybilne fasady. Typy eventów i sortowanie po `created_at` pozostały
  bez zmian. Focused audit/review tests (10 passed), Ruff, mypy, complexity,
  managed runtime i browser proof przechodzą; Ads i Localo zachowują evidence,
  `Zapis zmian zablokowany` oraz `apply_allowed=false`; proof:
  `.local-lab/proof/continuation-2026-07-12/audit-selectors-live.png`.
- Generyczna projekcja `preview_items` (karty i surowe payload rows) jest teraz
  w istniejącym `wilq/actions/payload_readiness.py`; service przekazuje tylko
  callbacki etykiet/wierszy. Zachowano limity, kontrakt WordPress candidate ID,
  statusy i blokady zapisu. Focused payload/preview/confirmation tests: 19
  passed, Ruff/mypy/complexity/diff check zielone. Po restarcie Ads detail ma
  HTTP 200, 1 kartę, evidence i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/payload-items-live.png`.
- Wspólne fabryki preview row, state/readiness labels, string-list sanitization
  i preview-contract label są teraz w `wilq/actions/payload_readiness.py`;
  service zachowuje delegację domenową bez duplikowania copy. Focused payload
  suite: 20 passed, Ruff/mypy/complexity/diff check oraz managed API/browser
  proof przechodzą; Ads detail nadal pokazuje evidence, blokadę zapisu i
  `apply_allowed=false`; proof:
  `.local-lab/proof/continuation-2026-07-12/payload-labels-live.png`.
- Google Ads money formatter dla wartości micros jest teraz własnością
  `wilq/actions/google_ads/business_context.py`; service przekazuje istniejący
  formatter do preview builderów. Brakujące wartości pozostają jawnie
  `kwota niepotwierdzona`, bez wymyślania kosztu. Focused Ads preview suite:
  26 passed, Ruff/mypy/complexity/diff check, API smoke i browser proof zielone;
  proof: `.local-lab/proof/continuation-2026-07-12/money-label-live.png`.
- Summary podglądu akcji (liczba pokazanych pozycji, blokada zapisu i brak
  zewnętrznego zapisu) jest teraz w istniejącym `wilq/actions/action_blockers.py`;
  `service.py` zachowuje tylko orkiestrację. Focused preview/confirmation/review
  tests: 26 passed, service LOC spadł do 2351, a runtime Ads detail zachowuje
  evidence, `Zapis zmian zablokowany` i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/preview-summary-live.png`.
- Składanie szczegółów human review (outcome, reviewer, checked items,
  blokady oraz content URL/draft readiness details) jest teraz w istniejącym
  `wilq/actions/review_gate.py`; service dostarcza tylko callbacki content
  review. Focused preview/confirmation/review tests: 26 passed, service LOC
  spadł do 2344, a live Ads detail zachowuje evidence, blokadę zapisu i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/review-details-live.png`.
- Redakcja technicznych szczegółów audytu (raw payload/mapping/claim IDs) jest
  teraz w istniejącym `wilq/actions/audit_store.py`; service przekazuje tylko
  callbacki etykiet review. Focused audit/preview/review tests: 29 passed,
  service LOC spadł do 2312, a live Ads detail zachowuje evidence, blokadę
  zapisu i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/audit-details-live.png`.
- Projekcja etykiet `ActionReviewGate` (status, blokady, review outcome,
  impact, mutation adapter i ślad audytu) jest teraz w istniejącym
  `wilq/actions/operator_labels.py`; service zachowuje tylko callbacki dla
  review outcome i count blockerów. Focused audit/preview/review tests: 30
  passed, service LOC spadł do 2266, a live Ads detail zachowuje evidence,
  blokadę zapisu i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/gate-labels-live.png`.
- Projekcja `AuditEvent` dla operatora (event label, bezpieczny summary i
  zredagowane details) jest teraz w istniejącym `wilq/actions/audit_store.py`;
  service zachowuje tylko callbacki etykiet review. Focused audit/preview/review
  tests: 31 passed, service LOC spadł do 2261, a live Ads detail zachowuje
  evidence, blokadę zapisu i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/event-projection-live.png`.
- Składanie operatorowego `ActionObject` view-modelu jest teraz w istniejącym
  `wilq/actions/operator_labels.py`; service przekazuje callbacki connectora,
  evidence, review gate, preview cards i audit event. Zachowano typed labels,
  preview i redakcję audytu. Focused audit/preview/review tests: 32 passed,
  service LOC spadł do 2248, a live Ads detail zachowuje evidence, blokadę
  zapisu i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/action-projection-live.png`.
- Filtr raw human-review audit events dla content refresh jest teraz w
  istniejącym `wilq/actions/content_review_details.py`; `service.py` nie
  posiada już content-specific wyjątku. Zachowano dokładny scope action ID,
  prefix eventu i redakcję raw contract. Focused audit/preview/review tests: 33
  passed, service LOC spadł do 2245, a live Ads detail zachowuje evidence,
  blokadę zapisu i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-filter-live.png`.
- Wyznaczanie `operator_next_step` dla mutation readiness jest teraz w
  istniejącym `wilq/actions/mutation_readiness.py`; service zachowuje tylko
  delegację. Zachowano kolejność WordPress handoff/package → preview/review/
  confirm oraz fail-closed apply. Focused mutation/audit/preview/review tests:
  34 passed, service LOC spadł do 2225, a live readiness raportuje
  `vendor_write_possible=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/mutation-next-live.png`.
- Reguła `vendor_write_possible` jest teraz w istniejącym
  `wilq/actions/mutation_readiness.py`; service deleguje z tą samą bramką
  `apply + adapter + payload_apply_allowed + api_mutation_ready`. Focused
  mutation contract test oraz readiness/API proof przechodzą, a live readiness
  nadal raportuje `vendor_write_possible=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/vendor-write-live.png`.
- WordPress draft write-readiness requirements są teraz składane w istniejącym
  `wilq/actions/wordpress_mutation_requirements.py`; service deleguje bez
  zmiany czterech typed requirements, evidence blockerów i autoryzacji audytu.
  Focused WordPress/mutation readiness tests przechodzą, service LOC spadł do
  2195, a live readiness zachowuje `vendor_write_possible=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/wp-readiness-live.png`.
- Budowanie `ActionMutationAuditRecord` i bezpiecznego mutation summary jest
  teraz w istniejącym `wilq/actions/audit_store.py`; service deleguje assembly.
  Zachowano status, adapter reach, external-write flags, evidence, blockers i
  redacted vendor payload. Focused audit/mutation tests przechodzą, service LOC
  spadł do 2161, a live readiness nadal raportuje `vendor_write_possible=false`;
  browser proof: `.local-lab/proof/continuation-2026-07-12/mutation-audit-live.png`.
- Mapowanie błędów apply na event audytu (`apply_succeeded`,
  `apply_confirmation_missing`, `apply_blocked`) jest teraz w istniejącym
  `wilq/actions/audit_store.py`; service zachowuje tylko kompatybilną fasadę.
  Focused audit/mutation tests przechodzą, service LOC spadł do 2154, a live
  Ads detail zachowuje evidence, blokadę zapisu i `apply_allowed=false`; browser
  proof: `.local-lab/proof/continuation-2026-07-12/apply-event-live.png`.
- Odczyt env `WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES` jest teraz własnością
  istniejącego `wilq/actions/wordpress_mutation_requirements.py`; service nie
  duplikuje WordPress write policy ani credential lookup. Focused WordPress /
  mutation tests, source Ruff/mypy/complexity/diff check i managed runtime
  przechodzą; live readiness pozostaje fail-closed; browser proof:
  `.local-lab/proof/continuation-2026-07-12/wp-env-live.png`.
- Formatowanie blockerów wykonania WordPress draft jest teraz w istniejącym
  `wilq/content/handoff/wordpress_execution.py`; service przekazuje typed
  execution result bez własnej interpretacji statusu. Zachowano fail-closed
  labels/reasons i redacted adapter trace; focused WordPress/mutation tests,
  source Ruff/mypy/complexity/diff check oraz browser proof przechodzą:
  `.local-lab/proof/continuation-2026-07-12/wp-errors-live.png`.
- Rozpoznawanie obsługiwanego mutation adaptera jest teraz w istniejącym
  `wilq/actions/mutation_contract.py`; service nie definiuje już własnej
  capability predicate. Canonical WordPress draft-only operation pozostaje
  jedyną obsługiwaną ścieżką, a publish/arbitrary operation zwraca brak adaptera.
  Focused mutation contract tests, source Ruff/mypy/complexity/diff check i
  browser proof przechodzą: `.local-lab/proof/continuation-2026-07-12/adapter-boundary-live.png`.
- Najnowszy slice `jnra` przeniósł buildery `wordpress_draft_write_readiness`
  i `wordpress_draft_activation_packet` do istniejącego modułu
  `wilq/actions/wordpress_mutation_requirements.py`; `service.py` zachowuje
  kompatybilne fasady, a kontrakt apply pozostaje draft-only. Focused mutation
  readiness/action tests (7 testów), Ruff, mypy, complexity, diff check oraz
  live API smoke przechodzą; brak nowych endpointów i vendor writes.
- Kolejny slice `jnra` usunął martwy helper `_mutation_requirement` z
  `wilq/actions/service.py`; świeży `rg` potwierdza brak referencji, a typowane
  readiness requirements nadal pochodzą z istniejących modułów. 48 focused
  testów akcji, Ruff, mypy, complexity i diff check przechodzi.
- Kolejny mały slice `jnra` usunął lokalną fasadę
  `_wordpress_draft_execution_errors`; `service.py` korzysta bezpośrednio z
  istniejącego formattera `wilq/content/handoff/wordpress_execution.py`.
  Focused mutation/WordPress execution tests, Ruff, mypy, complexity i diff
  check przechodzą; kontrakt oraz fail-closed execution errors bez zmian.
- Kolejny slice `jnra` usunął nieużywany `_mutation_audit_summary` i jego
  import z `service.py`; formatter pozostaje własnością `audit_store.py`.
  21 focused audit/mutation tests, Ruff, mypy, complexity i diff check
  przechodzą; brak zmiany eventów audytu lub safety loop.
- Kolejny slice `jnra` usunął jedno-wywołaniową fasadę `_vendor_write_possible`
  z `service.py`; readiness korzysta bezpośrednio z istniejącego predicate w
  `mutation_readiness.py`. 22 focused audit/mutation tests, Ruff, mypy,
  complexity, diff check i live WordPress readiness smoke przechodzą; API nadal
  raportuje `vendor_write_possible=false`.
- Kolejny slice `jnra` usunął trzy lokalne fasady readiness/audit używane tylko
  wewnątrz `service.py`: `_wordpress_draft_*`, `_apply_audit_event_type` i
  `_action_mutation_audit_record`. Service wywołuje istniejące owner modules
  bezpośrednio; focused WordPress/mutation/audit tests, Ruff, mypy, complexity,
  diff check i API smoke przechodzą. `ready_to_request_apply=false` pozostaje.
- Najnowszy slice `jnra` przeniósł typed `WordPressDraftApplyCapability` i
  walidację exact work item/handoff/draft package/canonical URL/confirm actor do
  istniejącego `wilq/actions/wordpress_mutation_requirements.py`; service
  zachowuje jedną kompatybilną fasadę dla istniejących testów. 39 focused
  WordPress/mutation/audit tests, Ruff, mypy, complexity i diff check przechodzą.
  Po managed restart API health jest `ok`; readiness nadal fail-closed. Fresh
  browser proof: `.local-lab/proof/continuation-2026-07-12/wordpress-capability-desktop.png`,
  `wordpress-capability-mobile-after-restart.png`.
- Kolejny slice `jnra` przeniósł wykonanie obsługiwanego adaptera WordPress
  (`execute_supported_wordpress_mutation_adapter`) do tego samego ownera
  `wilq/actions/wordpress_mutation_requirements.py`; service zachowuje tylko
  cienką fasadę orkiestracyjną. 39 focused testów, Ruff, mypy, complexity i
  diff check przechodzą. Po restarcie cold readiness wymagało rozgrzania
  istniejącego diagnostics path (pierwszy request przekroczył 20 s), następnie
  HTTP 200 w 18.9 s; kontrakt nadal `ready_to_request_apply=false`,
  `vendor_write_possible=false`, `publication_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/wordpress-adapter-owner-desktop.png`,
  `wordpress-adapter-owner-mobile.png`.
- Re-audyt runtime początkowo ujawnił >20 s cold latency dla
  `/api/actions/act_apply_wordpress_draft_handoff/mutation-readiness`, ale po
  zamknięciu osieroconych instancji Chrome quiet proof wyniósł queue 0.003760 s,
  readiness 1.442645 s. `wilq-seo-c9h9.14` zamknięto jako external-state false
  positive; nie zostawiamy zadania dla problemu, którego kod nie reprodukuje.
- Niezależne hardening cache jest potwierdzone testem: default diagnostics TTL
  wzrósł z 15 do 60 s, a activation packet korzysta z cached diagnostics.
  Refresh/mutation nadal jawnie czyszczą cache; brak zmiany freshness/evidence
  contractów.
- Fresh mobile browser proof po quiet managed stack: `.local-lab/proof/continuation-2026-07-12/c9h9-14-cache-mobile.png`;
  decyzja, blocker i bezpieczne CTA pozostają marketer-facing, a technical
  details są niżej.
- Kolejny slice `jnra` przeniósł składanie `_action_review_gate` do istniejącego
  `wilq/actions/review_gate.py` jako callback-based typed seam. Service zachowuje
  tylko domenowe callbacki (payload, adapter, labels, audit summary), a owner
  module składa status, blockers, review/confirm/impact/mutation audit i
  `apply_allowed`. 67 focused review/action/mutation tests, Ruff, mypy,
  complexity, diff check i live API smoke przechodzą; brak nowych endpointów i
  vendor writes.
- Kolejny slice `jnra` przeniósł kolejność preflight blockerów apply do
  istniejącego `wilq/actions/action_blockers.py` jako
  `action_apply_preflight_blockers`. `apply_action` zachowuje orchestration,
  typed capability i adapter safety, ale nie duplikuje już 15 warunków
  fail-closed. 68 focused review/action/mutation tests, Ruff, mypy, complexity,
  diff check i live API safety smoke przechodzą.
- Kolejny slice `jnra` przeniósł budowanie apply `AuditEvent` do istniejącego
  `wilq/actions/audit_store.py` (`build_apply_audit_event`). `apply_action`
  pozostaje orkiestratorem, ale event type, operator label, summary, actor i
  evidence są składane w jednym owner module. 55 focused audit/review/action
  tests, Ruff, mypy, complexity, diff check i live safety smoke przechodzą.
- Najnowszy slice `jnra` wyciął routing previewów z `service.py` do nowego
  `wilq/actions/action_previews.py`. Kontrakty previewów są mapowane w jednym
  typed dispatcherze, a renderery pozostają w modułach domenowych; usunięto 311
  lokalnych wrapperów/fasad bez zmiany ActionObject safety loop. Nowy test
  routingu Merchant oraz `test_action_preview_contracts.py` +
  `test_action_object_contracts.py` przechodzą, Ruff/mypy/complexity/diff check
  i managed API smoke przechodzą.
- Kolejny slice `jnra` przeniósł konstrukcję human-review `AuditEvent` do
  `wilq/actions/audit_store.py` (`build_human_review_audit_event`).
  `record_action_review` pozostaje orkiestratorem review gate i operator
  projection; event type, actor, summary, details i evidence mają jednego
  ownera. Nowy test audit-store oraz focused review/preview tests przechodzą;
  Ruff, mypy i diff check są zielone.
- Następny slice `jnra` przeniósł dry-run `action_preview_generated` event do
  `audit_store.py` (`build_preview_audit_event`). `preview_action` nadal tworzy
  tylko podgląd (`mutation_allowed=false`) i liczy blocker/status lokalnie, ale
  event ID, label, actor, summary i evidence mają wspólny audit owner. Focused
  audit/preview tests, Ruff i mypy przechodzą; brak zmian endpointu lub vendor write.
- Kolejny slice `jnra` przeniósł confirmation `AuditEvent` do
  `audit_store.py` (`build_confirmation_audit_event`). `confirm_action` zachowuje
  obliczanie blockerów, Ads target summary, status i review gate, a store składa
  event ID/type/label/actor/summary/evidence. 39 focused audit/review/preview
  testów, Ruff, mypy, managed API smoke i diff check przechodzą; confirm nadal
  nie wykonuje zapisu vendorowego.
- Następny slice `jnra` przeniósł impact-check `AuditEvent` do
  `audit_store.py` (`build_impact_check_audit_event`). `impact_check_action`
  nadal wylicza status, metryki, source connectors, blocker i evidence union;
  store składa event type/label/actor/summary z jawnym lineage. 40 focused
  audit/review/preview testów, Ruff, mypy, diff check i API smoke przechodzą.

## Weryfikacja

- Backend baseline: 765 passed, 2 skipped; ten slice: 5 content test files
  passed, 1 deprecation warning; Ruff i mypy dla zmienionych modułów
  modułów przechodzą.
- Shared schemas: 31 passed, 10 skipped.
- Dashboard: 24 files, 138/138 Vitest; lint, typecheck i production build
  przechodzą. Potwierdzony full-suite flake Service Profile naprawiono lokalnym
  async budgetem bez usuwania asercji (`c9h9.7`, zamknięty).
- Focused content/action UI: 31/31; action-detail Playwright przechodzi.
- Security, 7/7 API smoke, oba CLI smoke, brief/action/language guard oraz daily
  + 12 deterministic skill smokes przechodzą.
- Skill coverage: 13/13, 0 gaps/warnings; wszystkie 13 evali są fresh/passing,
  score 9–10. GSC i Custom Segments przechodzą `quick_validate`.
- Goal 005 pozostaje `blocked_missing_goal_005_uat_proof`: potrzebny jest realny
  wynik Wilku UAT albo jawny owner defer z residual risk. To stan zewnętrzny, nie
  brak eval coverage.
- Najnowszy zamknięty slice `c9h9.4`: typed ActionApplyRequest w backendzie i
  `@wilq/shared-schemas`, dashboardowy `applyAction` korzysta z tej samej
  granicy `/apply`; realny builder capability wiąże work item/handoff/draft
  package/canonical URL/confirm actor, a connector blokuje public/arbitrary host
  przed HTTP. Focused action mutation, shared-schema, dashboard API, WordPress
  adapter i content execution tests przechodzą; route-level proof i review-only
  CTA są zamknięte w Beadzie.
- Pełny `dashboard-api.spec.ts` przechodzi 13/13 po rebaseline asercji do
  bieżących nagłówków i zachowania; nie podnoszono timeoutów i nie przywracano
  legacy route strings. Pozostałe pełne testy/review mają własne Beads i nie są
  ukrywane przez ten smoke.
- Latest `c9h9.6` complexity run: 10 changed files, 2 frozen growth files and 2
  focused budget violations in `wilq/briefing/content_diagnostics.py`. Main and
  diagnostics changed only for the documented cache/prewarm seam; no broad
  split was introduced.
- Aktualny rebaseline complexity po `jnra.3`: 423 Python files / 136751
  non-empty LOC; `service.py` ma 1608 LOC. Standardowy changed audit zatrzymuje
  się na jawnie frozen facade oraz istniejącym dużym pliku testowym; dopuszczony
  wariant dla udokumentowanego seamu przechodzi i nie ukrywa tych wcześniejszych
  budżetów jako sukcesu zmiany.

## Kolejność wykonania

1. `r564` — pozyskać kolejne candidate wyłącznie przez evidence-backed workflow;
   nie wymyślać trzeciego tematu przy blockerze `not_enough_actionable_candidates`.
2. `jnra` — najmniejszy bezpieczny seam monolitu Action Service, po potwierdzeniu
   że nie narusza ActionObject safety loop.
3. `d380` albo `0q74` — kolejny potwierdzony utrzymaniowy slice po wyborze
   zależności; nie tworzyć mechanicznego splitu bez zakresu i testu użyteczności.

`docs/audits/2026-07-10-cleanup-rebaseline.md` zawiera bieżącą mapę statusów i
ryzyk. Pełne specyfikacje pozostają wyłącznie w Beads.
# 2026-07-13 — d380 React dashboard boundary

- Confirmed `wilq-seo-d380` is still open and its current requirement is a
  documented React standard plus a real route seam, not a blind LOC split.
- Added `docs/architecture/dashboard-react-standards.md` covering route shell,
  domain query hook, typed API-owned view-models, presentational components and
  technical disclosure rules.
- Extracted `apps/dashboard/src/routes/contentWorkflowQueries.ts`; the primary
  content route now delegates queue/work-item/enrichment/WordPress readiness
  query orchestration to that typed hook.
- Added `contentWorkflowArchitecture.test.ts` so reintroducing the primary
  route's queue query boundary fails a focused test.
- Verification: focused dashboard suite 18/18, ESLint and TypeScript passed;
  no endpoint or business rule changed.
- Remaining d380 scope: apply the same boundary review to ActionDetailSurface
  and replace stale route-string E2E assertions with behavior/fixture proof.
- Follow-up seam completed in the same slice: `ActionDetailSurface` now uses
  `actionDetailQueries.ts` for action/readiness reads; architecture test covers
  both primary route boundaries. Focused ActionDetail suite is 20/20.
- Replaced the stale `/content-workflow` Playwright assertions that expected a
  refresh-only queue and `0 z 2` state. Current E2E now proves the live route's
  decision, public URL, current page/signals/dev workspace, safe draft-preview
  CTA, evidence section, no loader, and no horizontal overflow. Playwright
  passes 1/1 in 19.1s with a refreshed screenshot proof.
