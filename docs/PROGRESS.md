# WILQ Progress Ledger

Ostatnia aktualizacja: 2026-07-19.

To jest krótki stan bieżący. Historia zmian i proofów pozostaje w git, Beads
i lokalnych katalogach `.local-lab/proof/`; ten plik nie jest kroniką.

## Aktywny kierunek

- Kanoniczny bieżący cel jest w `docs/goals/001-goal.md`; archiwalny Goal 005
  nie jest już aktywnym recovery entrypointem. Operacyjna kolejka pozostaje
  wyłącznie w Beads pod `wilq-seo-1oa` i review-only `wilq-seo-v9ab`.
- Priorytetem jest jeden użyteczny workspace `/content-workflow`, a nie nowe
  ekrany ani kolejne warstwy ceremonii.
- 2026-07-19: bounded second-opinion campaign
  `wilq-content-ops-engineering-standard` zakończył dwa research shard’y i
  syntezę na czystym fixed poincie `d310de05164f0431217c3865fc35af6c2d4b345c`;
  wszystkie wyniki przeszły walidację. Disposition jest poza repo w katalogu
  passu. Najważniejsze follow-upy to `wilq-seo-v1um` (stale window — lab test),
  `wilq-seo-tcd7` (jeden in-flight slot przez digesty), `wilq-seo-k8i5`
  (server-owned focus) i `wilq-seo-1dke` (durable runner). Żaden wynik review
  nie jest PASS/UAT/approval.
- 2026-07-19: selected `content_decision_*` ma już katalogowy fast path.
  Najpierw rozwiązywany jest exact URL przez ten sam inventory catalog, a API
  zwraca jednego kandydata bez pełnego diagnostics queue; live BDO potwierdza
  `candidate_count=1`. Pomiar lokalny: katalog 0,319 s vs pełne diagnostics
  2,682 s. Bead `wilq-seo-z023` zamknięty; zimny refresh zewnętrzny i nieznane
  lub niejednoznaczne ID nadal bezpiecznie wracają do pełnego kontraktu.
- 2026-07-19: lab durable runnera zachował trzy istotne dowody bez migracji
  produkcyjnego storage: świeży `ContentPlanningProposalStore` odczytuje
  queued row po restarcie obiektu, stale job można ponownie zakolejkować, a
  dwa identyczne enqueue kończą się dokładnie `queued` + `existing`. APScheduler
  dotyczy tylko connector jobs i ma `autostart=false`, więc nie udaje się go
  jeszcze jako recovery runnera planowania; migracja pozostaje odroczona do
  osobnego crash-injection/no-duplicate proofu z autoryzacją właściciela.
- 2026-07-19: `/content-workflow` pokazuje teraz marketerowi istniejący
  kontrakt gotowości korpusu źródłowego dokładnie przy wejściu do kolejki.
  Przy obecnym stanie UI mówi `7/15` materiałów zaimportowanych i `8` w
  kontrolowanym imporcie oraz jasno zaznacza, że generowanie używa wyłącznie
  dostępnych zatwierdzonych faktów. Przy gotowym korpusie komunikat znika;
  nie powstał nowy score ani równoległa logika blokad.
- Follow-up po checkerze: komunikat rozróżnia teraz `import_pending` od
  `excerpt_review_required`, pokazuje API-owy `next_step` i ma jawny degraded
  state przy błędzie odczytu readiness. Nie ukrywa już awarii jako pozornej
  gotowości i nie składa własnej obietnicy o zachowaniu backendu.
- Kanoniczny przebieg marketera ma pięć kroków:
  `scope → section_map → draft → review → dev_draft`.
- 2026-07-18: świeży BDO plan został najpierw poprawnie zablokowany przez
  datowany nagłówek wydarzenia w istniejącym inventory, a następnie ponowiony
  po filtrze transportowym dla nagłówków datowanych/promocyjnych/nawigacyjnych.
  Canonical planning input i pełne inventory nie są filtrowane; tylko envelope
  modelu pomija presentation noise. Live re-run jest `ready`:
  `content_planning_proposal_d0e26eb81e7a4d909e83ed831511454c`,
  `codex_content_planning_60536efbe93e46bf913e8e0241e0183f`, 6 sekcji, 4 FAQ,
  2 CTA, 1 link. `publish_ready=false`; review człowieka nadal wymagany.
- WILQ API jest właścicielem stanu, dowodów, wersji, decyzji, ActionObjectów
  i audytu. React renderuje typed view-model i przechowuje tylko niezapisane
  edycje formularza.
- Ograniczony executor działa po stronie serwera przez Codex app-server i
  istniejący `codex login`. OpenAI API key, Agents SDK, Ollama ani drugi model
  nie są zależnościami produktu. Browser nie łączy się z Codex bezpośrednio.
- Realny daily-check po read-only refreshach Ads, Merchant i Localo ma świeży
  stan, 24 dowody, 7 źródeł, 8 reguł eksperckich, 3 bezpieczne akcje i 1
  `do_not_touch`. Nadal jest poprawnie `blocked` przez review jakości landing
  page i pomiaru GA4; `v9ab.13` wymaga rzeczywistego werdyktu Wilka albo defer.

- `scripts/local_stack.sh` uruchamia lokalny API z jawnym `WILQ_API_RELOAD=1`
  (domyślnie), pokazuje tryb w `status` i pozwala go wyłączyć wartością `0`.
  To wyłącznie ergonomia lokalnego developmentu; produkcyjny/deploy runtime
  nie dziedziczy tej flagi. Live log po zmianie `wilq/schemas/core.py` zawiera
  `StatReload detected changes` i ponowne uruchomienie procesu serwera.

- Content queue ma teraz bounded comparison contract: exact page facts muszą
  mieć dwa kompletne okresy i rozróżnialne evidence. Przy jednym świeżym dniu
  UI pokazuje `brak dwóch porównywalnych okresów`, a nie udaje spadku/wzrostu.
  Helper `compare_exact_page_metric_periods` zachowuje okresy i evidence dla
  GSC/GA4; focused aggregate + queue proof to 11 testów, shared schemas i
  dashboard typecheck są zielone. Live BDO obecnie jawnie zwraca
  `comparison_status=not_available` dla pojedynczego snapshotu.

- Comparison jest teraz częścią `ContentPlanningInput`, a nie tylko projekcją
  kolejki. `ContentWorkItem` przenosi sanitized metric facts do planning seam;
  digest obejmuje status, exact okresy, evidence i wartości baseline/observation.
  Zmiana wartości metryki zmienia planning input digest, więc stary proposal,
  review i revision nie mogą zostać potraktowane jako aktualne. Focused
  planning-input proof przechodzi razem z testami dynamic proposal.

- Review-bound measurement outcome sprawdza teraz jakość i settlement źródła:
  `partial/unverified` oraz `settling` stają się typed limitations i nie mogą
  przyznać `success_claim_allowed` ani feedbacku do kolejki. Metadata runu jest
  przenoszone do obserwowanej metryki; zwykły plan nadal może użyć częściowego
  GSC jako sygnału z caveatem. Focused outcome suite przechodzi 5 testów.

- Propagacja jest potwierdzona osobnym proofem: refresh run → observed metric
  zachowuje `quality_state`, `settlement_state` i caveats, a outcome odrzuca
  taki sygnał jako review-bound. Wspólny focused zestaw measurement/planning/
  queue ma 24 przejścia; nie uruchamiałem szerokiego `verify.sh` bez potrzeby.

- Po checker findingu F1 naprawiono ciche pomijanie niepełnego okresu: brak
  baseline albo observation tworzy obserwowaną metrykę z `None` i caveatem,
  a dowolny metric blocker zatrzymuje outcome przed sukcesem/feedbackiem nawet
  wtedy, gdy inne metryki wyglądają dobrze. Focused regression obejmuje oba
  przypadki; finding został lokalnie zweryfikowany i przełożony na produkcyjną
  poprawkę.

- Shared browser/API schema `ContentMeasurementObservedMetric` przenosi teraz
  także `quality_state`, `settlement_state` i `interpretation_caveats`, więc
  UI nie gubi blokady jakości przy readbacku outcome. Shared typecheck i 42
  kontraktowe testy przechodzą.

- Read-only odczyt materiału WordPress dla wybranego inventory itemu ma jawny
  cache 30 s kluczowany przez URL i bieżące `evidence_id`. Powtórny reload nie
  odpala tego samego requestu sieciowego, ale nowy refresh/evidence wymusza
  ponowny odczyt; cache obejmuje również typed `blocked`, bez ukrywania
  blockera. Focused inventory suite: 8 testów. Live timing wybranego queue:
  pierwszy odczyt 2,50 s, kolejne 0,17–0,19 s na tym samym fixed poincie.

- Aktualny browser proof potwierdza dwa krytyczne zachowania workflow: wybrany
  inventory item pokazuje mięso przed sztucznie opóźnioną odpowiedzią kolejki,
  a bezpośrednie wejście na URL inventory otwiera właściwy workflow zamiast
  pustego stanu. Playwright: 2 testy passed (desktopowy lokalny API na porcie
  proofowym 8875).

- 2026-07-19: live inventory proof dla URL-only `/badania-obecnosci-radonu/`
  potwierdził, że wybór strony uruchamia ten sam dynamiczny seam WordPress:
  `POST /api/content/inventory/bind` zwrócił `ready`, metryki GSC (17
  wyświetleń, 2 kliknięcia), materiał `content_and_structure`, źródło
  `rendered_html`/`the_content`, `review_required` i lineage
  `public_html.main_or_article`. Nie jest to approval ani gotowość do draftu;
  `tests/content/test_inventory_catalog.py` przechodzi 13/13.

- 2026-07-19: po odświeżeniu inventory BDO miał poprawnie `stale`, więc został
  ponownie zaplanowany przez API na aktualnym digest `6239551e…`. Terminalny
  wynik jest `ready`: proposal
  `content_planning_proposal_021231208f884ee099f1658810f4ec76`, 12 sekcji,
  5 FAQ, 2 CTA, 1 link, 7 zatwierdzonych materiałów i 4 karty wiedzy. Sześć sekcji
  roboczych ma lineage do materiałów/faktów, a sześć pobocznych pozostaje
  `remove_review_required`. To nie tworzy draftu, approvalu ani publikacji.

- 2026-07-18: cold selected queue nie wykonuje już synchronicznego pełnego
  odczytu WordPress. Jawnie wybrany inventory item dostaje szybki, katalogowy
  decision z `material pending`, a snapshot zachowuje dokładny read-only seam
  dla `the_content`/ACF i nadal blokuje plan/draft, gdy materiału nie da się
  potwierdzić. Katalog jest prewarmowany w tle po gotowości API. Managed proof:
  queue 1,077 s po restarcie, potem 0,503/0,176/0,222/0,229 s; queue tests 5/5,
  ContentWorkflowSurface 30/30. Commit `301125a0` został wypchnięty na
  `origin/main`. Checker `workflow-latency-ZBoaoR` ma zero findingów, ale
  evidence gaps z powodu braku excerptów; nie traktujemy go jako PASS.

- Niezależny checker dla cache materiału został uruchomiony na świeżym fixed
  poincie, ale lokalny walidator odrzucił wynik, bo Claude podał dla `F1`
  zakres dowodu większy niż dozwolone 20 linii. Pass i disposition są w
  `~/coding/krn/second-opinion-review/wilq-seo/check/2026-07-17-inventory-material-cache-v2-Ry8VDY/`;
  nie ma reviewerowego PASS ani zaakceptowanego findingu.

- Naprawiono marketer-facing dead end w katalogu: adresy `url_only` nie są już
  oznaczane jako „Brak materiału do workflow”. Przycisk uruchamia teraz ten sam
  API-owned binding, który próbuje publiczny HTML/`the_content`, zachowując
  `review-required` dla materiału bez REST/ACF. Dashboard typecheck i
  `ContentWorkflowSurface` 30 testów przechodzą.

- Wykonano realny read-only pilot GSC + GA4 + WordPress dla exact landingu
  `/rewolucja-w-decyzjach-o-warunkach-zabudowy-co-zmienia-sie-od-2026/`.
  WordPress i GA4 są połączone przez path match, a pakiet zapisuje evidence,
  21 aktywnych użytkowników, 218 zdarzeń i 48,15% engagement z jawnym
  `stale` (~49 h) oraz blokadą interpretacji konwersji/ROAS. Dwa odczyty API
  zwróciły identyczny digest `e8214bd88ebd04b42df8713caae3013ba1a45c22b3b51e7f9aa4a9ec9ec0fae1`;
  realny werdykt Wilku pozostaje otwarty.

- Naprawiono rozjazd synchronicznego i asynchronicznego refreshu konektorów:
  `_persist_refresh_result` korzysta teraz z tego samego `_quality_contract`
  co ścieżka bez kolejki. Live async GA4 refresh
  `refresh_google_analytics_4_5b60fde574ae` zapisuje okno `2026-06-19` →
  `2026-07-16`, `settling`, `unverified` i caveat o rozliczaniu danych zamiast
  pustego `covered_window`/`unknown`. Focused quality suite: 4 testy.

- GA4 read obsługuje teraz do 20 wybranych publicznych URL-i jako bounded
  target query (`EXACT landingPagePlusQueryString`, limit 20), z licznikami
  żądanych i zwróconych wierszy. Live run `refresh_google_analytics_4_421d4f76d1f4`
  zwrócił 2 wiersze dla landingu pilota; brak hosta w wymiarze GA4 nadal daje
  `path_only/review_required`, więc planner nie udaje exact URL.

- Checker nowego async-quality/target-read fixed pointu został uruchomiony, ale
  lokalny walidator odrzucił `F1` za zakres cytowania większy niż 20 linii.
  Disposition jest zapisane poza repo; nie ma reviewerowego PASS ani zmiany
  produktu opartej na tym niewalidowanym wyniku.

- 2026-07-19: Ads landing identity ma teraz typed join do WordPress inventory i
  Service Profile. `approved_current` jest jedynym stanem, który może zasilać
  usługę; `review_required`, `unbound` i `ambiguous` blokują planning. Ten stan
  jest widoczny w tabeli Ads obok mapowania landingu, a raw URL nadal nie trafia
  do kontraktu. Live Ads ma 23 wiersze, ale bez zatwierdzonej karty nie udajemy
  exact-service pilotu.

- 2026-07-19: Ahrefs gap records pokazują derived method, sample/limit coverage
  i `mapping_status`; exact WordPress URL awansuje rekord dopiero po jednym
  typed exact cross-checku. Live stan ma 8 rekordów i 0 exact mapowań. Odczyt
  rozlicza także estymowany zakres 13 wywołań i failed stages (`partial=false`).
  GA4 planning przyjmuje tylko pełny URL z exact/tracking-only/host-alias;
  path-only pozostaje zablokowane. Focused proofy są zielone, ale realny
  GSC/GA4/WordPress pilot i Wilku verdict nadal pozostają otwarte.

## Ostatnie zakresy i proofy

- `wilq-seo-v9ab.18.2` ma pierwszy produkcyjny slice wspólnej tożsamości
  landing page. Typed kontrakt rozróżnia exact, tracking-only, alias hosta,
  path-only, functional-query, ambiguity, missing i no-match; scheme oraz port
  należą do originu, wadliwy URL konektora daje `invalid`, a tylko rozpoznane
  parametry trackingowe są usuwane. Ten sam matcher filtruje demand contentu,
  exact GSC snapshot, WordPress publication binding i publication-bound
  measurement. Wariant funkcjonalny, sama ścieżka GA4 oraz sprzeczne URL
  dimensions nie mogą zasilić wyniku; UTM-only facts łączą się bez duplikacji,
  a oba zatwierdzone aliasy hosta Ekologus są odczytywane. Drugi slice zapisuje
  wyliczoną identity w prywatnej przestrzeni dimensions nowych metryk, usuwa
  wszystkie caller-supplied `_wilq_*`, uzupełnia request-scoped index wyłącznie
  dla pasujących legacy rows i stosuje exact identity przed SQL `LIMIT`.
  Evidence-scoped read liczy poprzednią wartość nad pełną historią właściwych
  konektorów, zanim odfiltruje żądane evidence IDs. Dynamiczne przepinanie LAG
  po identity zostało wycofane po regresji wydajności i ryzyku fałszywego
  trendu; pozostaje jawnym zakresem wymagającym trwałego klucza lub maintenance
  window. Niezależny review drugiego slice'u znalazł P1, w którym populated
  `"(not set)"` w drugim URL dimension mogło wyprzeć poprawny fakt dopiero po
  limicie; identity wymaga teraz resolved i zgodnego wyniku dla każdego
  populated URL dimension, a publiczny falsyfikator oraz re-review są zielone.
  Claude checker na tym dirty fixed poincie zakończył się statusem 1 bez JSON,
  więc nie jest przedstawiany ani jako finding, ani PASS. Focused proof,
  mypy, Ruff i diff check są zielone; niezależny read-only review znalazł
  cztery błędy, po poprawkach potwierdził PASS w tym zakresie. Claude checker
  nie dał werdyktu: pierwszy pass poprawnie zgłosił brak osadzonego evidence,
  drugi zakończył się timeoutem bez outputu. Trzeci slice przenosi typed landing
  tiers do demand i wersjonowanego `ContentPlanningInput` v2, wymaga dokładnie
  dziesięciu unikalnych ocen źródeł, filtruje stale/blocked evidence przed
  modelem i wiąże inventory wyłącznie z jednym pasującym rekordem oraz
  rozwiązywalnym evidence WordPress. GET nadal nie uruchamia modelu, a POST
  zwraca blocker przed kontrolą stale digestu. Dashboard nie nazywa starego
  planu gotowym i nie pozwala generować przy zablokowanym źródle. Dwa piloty
  przechodzą ten sam input v2 na syntetycznie zatwierdzonych kartach; realne
  karty nadal czekają na owner review. Czwarty slice łączy kliknięty search
  term Ads z `expanded_final_url` i pięcioma metrykami w tym samym 30-dniowym
  wierszu bez `LIMIT`; do storage trafia tylko redagowany digest landingu,
  status i flagi. Content boundary wymaga jednego `ready` statusu tego samego
  evidence/periodu oraz kompletnego, równo policzonego zestawu clicks,
  impressions, cost, conversions i conversion value. Malformed, częściowy,
  wrażliwy lub non-finite batch jest typed blockerem. Świeżość jest per
  connector: stare Ads pozostają widocznym diagnostycznym sygnałem, ale nie
  trafiają do model-authorized portfolio. Focused proof ma 24 testy; shared
  schema ma 42, dashboard 177, oba typechecki i Ruff są zielone. Niezależny
  review znalazł cztery P1/P2, wszystkie poprawiono, a finalny fixed-point
  review dał PASS. Legalność GAQL potwierdzono z metadata v24; nie wykonano
  live vendor calla, migracji ani vendor write. Bead pozostaje otwarty na
  trwały kontrakt partycjonowania LAG i finalny cross-source pilot.
- `wilq-seo-1oa.36.8` domyka pełny, source-bound review WILQ na fixed commicie
  `d2649f15`: cztery niezależne ledgery contentu, dashboardu marketera,
  skillów/skryptów oraz metrics/actions/learning mają łącznie 37 zwalidowanych
  findings. Pierwsza synteza została poprawnie odrzucona za cytowanie źródła
  nieoznaczonego jako użyte i nie ma opublikowanego wyniku. Fresh replacement
  przypiął cztery ledgery SHA-256 i zwalidował 30 deduplikowanych pozycji.
  Lokalny disposition oznaczył jako już naprawione negative reviews, fake
  toolbar i capability registry, a późniejsze commity `246c6020` i `5dfd3065`
  naprawiły reaktywny URL content work itemu oraz uczciwy mobile overflow.
  Istniejące Beads przejęły findings konektorów i redukcji skryptów; nowe
  `.36.20`–`.36.25` posiadają brakujące measurement, history, execution-binding,
  redaction, live-mode i operator-label contracts. Review nie wykonał vendor
  write, migracji, realnego model generation, approval ani UAT.
- `wilq-seo-v9ab.18.1` usuwa fałszywe `ready` dla konwersji GA4. API rozdziela
  dostępność kolumn, zaobserwowane niezerowe fakty i potwierdzenie konfiguracji
  zdarzeń kluczowych; bieżący runtime ma 275 faktów konwersyjnych, 0 niezerowych
  obserwacji i brak potwierdzenia konfiguracji, więc zwraca `review_required`
  oraz blokuje wnioski o konwersji, przychodzie i opłacalności. Daily guard,
  dashboard schema i `wilq-ga4-analyst` używają tego samego kontraktu.
- `wilq-seo-v9ab.18.5` wiąże capability registry z realnymi adapterami. Ads,
  Merchant, Localo, WordPress sklep, LinkedIn i Facebook nie reklamują już
  vendor write; Ahrefs, GSC i pozostałe źródła nie wystawiają fikcyjnych typów
  akcji. Typed `read_adapter`, `mutation_adapter`, `action_scope` i blocker
  przechodzą przez API, shared schema, settings dashboard i context-pack.
  Jedyną aktywną ścieżką zapisu pozostaje exact WordPress ekologus.pl
  draft-only; nie dodano vendor write ani nowego skryptu.
- `wilq-seo-1oa.36.17` rozdziela prawidłową decyzję człowieka od approval.
  `needs_changes`, `rejected` i `deferred` są zapisywalne i po realnym zapisie
  wracają jako `recorded`, aktualizując stan reviewed itemu, ale nadal nie
  odblokowują WordPress. Czysty preflight mówi tylko `recordable`; błędny work
  item, brak reviewera/checklisty/dowodów lub niepasujący draft nie trafia do
  storage. Latest review wynika z kolejności zapisu, a nie leksykalnego ID.
- `wilq-seo-1oa.36.7` redukuje paczkę dla marketera do czterech dokumentów
  wynikowych bez generatora, manifestu i raw payloadu. Po managed restarcie
  aktualny WILQ API zwrócił dla BDO 65 wyświetleń, 0 kliknięć, 11 wierszy GSC,
  H1 i 12 nagłówków WordPress. Outsourcing ma 50 wyświetleń, 0 kliknięć i 26
  wierszy GSC oraz jest poprawnie `bound` do własnej karty. Brakujące wtedy
  inventory sekcji WordPress odzyskuje `.36.13`. Obie karty pozostają
  `source_backed_review_required`, wybór usługi nie jest potwierdzony, revision
  count wynosi 0, a GET planera nie uruchomił modelu. Wykryta wtedy luka, w
  której mapa BDO przypisywała niemal każde query do obu generycznych sekcji,
  została zamknięta przez `.36.9`. Nie wykonano model generation, realnego UAT
  ani WordPress write.
- `wilq-seo-1oa.36.11` wyrównuje `wilq-content-operator` z bieżącym pełnym
  workflowem API. Skill najpierw zapisuje baseline scope review z exact wyborem
  usługi, odświeża planning input, generuje plan, prowadzi osobne review scope i
  section map, a następnie initial draft, persistowane semantic review,
  poprawkę wybranych stabilnych sekcji, human review i revision-bound WordPress
  draft-only. Walidator smoke rozróżnia aktualny wynik od legalnego
  historycznego `stale` i odrzuca obce work itemy, karty, digests oraz run IDs.
  Usunięto szeroki `build_uat_packet.py` i duplikujący content UAT snapshot wraz
  z testami; nie dodano nowego exportera, a cztery sanitizowane dokumenty
  marketera pozostały bez zmian. Focused kontrakty przechodzą 5/5, Ruff i live
  managed-stack smoke są zielone; realny BDO nadal uczciwie blokują
  `service_selection_not_confirmed` oraz `service_card_not_approved`. Smoke nie
  uruchomił modelu ani vendor write i nie jest realnym Wilku UAT.
- `wilq-seo-1oa.36.13` naprawia ogólny publiczny inventory read dla stron
  usługowych bez wyjątku po URL. Sitemap produkcyjny miał 116 postów przed
  grupą stron, a jeden globalny limit 50 pobrań metadata obejmował BDO na
  pozycji 41, lecz nigdy stronę outsourcingu. Metadata ma teraz osobne bounded
  budżety dla `posts`, `pages` i pozostałych typów; surowy marker grupy nie
  trafia do MetricFact. Po read-only vendor refresh exact outsourcing ma
  canonical URL, tytuł/H1, 12 odczytanych nagłówków,
  `confirmed_current_inventory` i świeże evidence WordPress; BDO zachowuje 12
  nagłówków i ten sam gate. Układ bez H2/H3 pozostaje pustym inventory. Publiczny
  HTML nie jest przedstawiany jako readback ACF: status ACF nadal uczciwie
  wynosi `missing`. Klient WordPress został rozcięty na właściciela inventory i
  wspólne czyszczenie tekstu; wszystkie zmienione moduły mieszczą się w
  budżetach złożoności. Focused adapter/planner/authoring proof, Ruff i mypy są
  zielone; nie wykonano WordPress write, model generation ani UAT.
- `wilq-seo-1oa.37` dodaje persistowane advisory review semantyczne dokładnej
  rewizji v2. GET jest model-free; POST wymaga exact revision digestu, bieżącego
  planning inputu i ocenia dziewięć jawnych wymiarów bez approval, ActionObjectu
  ani vendor write. Review, kryteria i terminalny `CodexRun` zapisują się
  atomowo i idempotentnie. Findings wskazują stabilne `section_id`; dopiero po
  decyzji człowieka `needs_changes` Wilku wybiera sekcje, a istniejący
  `codex-proposal` tworzy niezmienną child revision, zachowując page assets,
  FAQ, CTA i linki. Syntetyczny proof przechodzi ten sam kontrakt dla BDO i
  outsourcingu, awaria runtime nie zostawia review, historyczne exact review
  wraca jako `stale`, a nie `not_generated`. Realny local-state bez nowej tabeli
  zwraca `storage_activation_required` przed modelem; aktywacja nadal wymaga
  backupu i maintenance window.
- `wilq-seo-2xmw` podłącza pierwszy pełny tekst do tego samego dynamicznego
  planu, zamiast używać osobnego generatora. Exact POST wymaga bieżących decyzji
  scope/section map, `approved_current` service card, proposal ID oraz obu
  digestów; istniejąca rewizja i stale request kończą się `409` przed modelem.
  Typed turn dostaje 10 ocen źródeł, inventory, query portfolio, dokładne facts,
  knowledge/claim constraints i measurement metrics. Serwer nadaje lineage i
  stabilne ID, przeprowadza wąski claim-safety gate i zapisuje pełną rewizję v2
  wraz z terminalnym `CodexRun` w jednej transakcji. Syntetyczne BDO oraz
  outsourcing tworzą różne dokumenty tym samym kontraktem; failure runtime nie
  zostawia częściowej rewizji, a GET snapshotu nie uruchamia modelu. Dashboard
  nie oferuje modelowego fallbacku do ręcznej pierwszej rewizji: pokazuje jeden
  przycisk generowania oraz pełny page preview, z metrykami i trace poniżej
  fold. Nie uruchomiono realnego modelu, migracji ani WordPress write; obie
  prawdziwe karty nadal czekają na owner review.
- Planner i initial-draft odrzucają teraz nieznany placement CTA/linku zamiast
  po cichu mapować go na koniec strony. Jawnie dozwolone są `after_lead`,
  `after_content` albo dokładny nagłówek zaplanowanej sekcji, później wiązany ze
  stabilnym `section_id`. Niezależny checker dla wcześniejszego fixed pointu nie
  potwierdził defektu, ale wskazał tę lukę dowodową; lokalny review zaklasyfikował
  ją jako `accept_and_fix`, a publiczny API falsifier potwierdza fail-closed.

- `wilq-seo-1oa.36.1` naprawia pierwszy realny content entry gap. Content
  diagnostics nie dziedziczy już limitu z cross-domain tactical queue:
  kompletny zestaw evidenced GSC+WordPress stron trafia najpierw do własnego
  rankera. Live kolejka wzrosła z 2 do 5 kandydatów i z 1 do 4 actionable;
  exact strona BDO jest pierwszą wykonalną pracą. Snapshot wiąże ją z kartą
  `ekologus_service_bdo_reporting`, 11 wierszami GSC, aktualnym WordPress
  inventory i 0 zgadywanych Ads/Planner rows. Marketer mode ma zwarty picker,
  a exact `work_item_id`, API-owned nagłówek sekcji i pasujący
  `planning_digest` pozostają w URL po reloadzie. Nieznany work item, nagłówek
  lub stale digest bezpiecznie wraca do istniejącej opcji bez requestu do
  obcego snapshotu. Wybór sekcji jest tylko fokusem sesji:
  scope i section map nadal wymagają człowieka, a karta BDO pozostaje
  `source_backed_review_required`.
- `wilq-seo-1oa.36.3` przywraca ogólny wybór usługi dla dwóch pilotowych
  case'ów bez wyjątków w kodzie. Normalizacja URL, myślników, odstępów i
  polskich znaków wiąże stronę BDO z `ekologus_service_bdo_reporting`, a stronę
  doradztwa i outsourcingu z
  `ekologus_service_environmental_consulting_outsourcing`; `subdomena` ani
  obcy temat nie wiążą karty BDO. Snapshot pokazuje wyłącznie kandydatury
  wynikające z dokładnych fraz kart, wraz z lifecycle i powodem dopasowania.
  Scope review utrwala jawnie wybraną kartę w istniejącym planie, odrzuca obcy
  identyfikator i oznacza dozwolony wybór inny niż rekomendowany jako
  `human_override_review_required`. Read-only proof po managed restarcie
  potwierdził oba wiązania; kolejka pokazuje odpowiednio 11 i 26 zapytań.
  Plan BDO ma 11 dokładnych wierszy GSC oraz 0 Ads/Planner, natomiast plan
  outsourcingu poprawnie pozostaje zablokowany do owner review jego karty.
  Żadna decyzja człowieka ani write do WordPressa nie zostały wykonane.
- `wilq-seo-1oa.36.4` dodaje jeden wersjonowany `ContentPlanningInput` dla
  istniejącego planera. Digest obejmuje exact stronę, potwierdzoną usługę,
  publiczne inventory WordPress, wiedzę, source facts, metryki i wersję
  kryteriów; wszystkie dziesięć rozważanych źródeł ma jawny status
  `used/not_applicable/missing/stale/blocked`. `GET/POST
  /api/content/work-items/{id}/planning-proposals` używa istniejącego
  serwerowego Codex app-servera: GET nie uruchamia modelu ani nie inicjalizuje
  tabeli, POST wymaga expected digestu, jest idempotentny i atomowo wiąże
  niezmienny plan z exact `CodexRun`. Syntetyczne zatwierdzone karty i tymczasowy
  SQLite udowodniły dwa różne plany dla exact BDO i outsourcingu, obcy service
  ID `422`, stale input `409` oraz brak częściowego zapisu po błędzie runtime.
  Dashboard podłącza pierwsze trzy kroki przez jawny wybór usługi, stan
  gotowości i jeden przycisk „Wygeneruj plan”; browser nie wywołuje Codexa ani
  WordPressa bez tej decyzji. Realne karty nadal wymagają owner review, realny
  model nie został uruchomiony, a nowa tabela nie została aktywowana w local
  state bez maintenance window.
- `wilq-seo-1oa.36.5` dodaje kompatybilną rewizję pełnego dokumentu v2.
  Immutable rekord przechowuje WordPress title, meta, H1, lead, sekcje ze
  stabilnymi ID, FAQ, CTA, linki i exact bindingi plan/service/inventory.
  Historyczne v1 zachowuje dawny digest; w v2 zmiana dowolnego page assetu
  zmienia digest, usuwa aktualność review i wraca w readbacku. Child revision
  zachowuje wszystkie nieedytowane assety. Revision-bound WordPress dry-run
  renderuje pełne body, ale meta pozostaje w payloadzie z typed blockerem do
  czasu potwierdzenia mapowania ACF/SEO. Focused proof używa tymczasowego SQLite
  i nie aktywuje nowych tabel w realnym local state. Linki wewnętrzne wymagają
  lineage i publicznego hosta Ekologus. Naprawiono też false positive redaktora,
  który traktował długi slug z myślnikami jak sekret, niszczył tytuł/body i mógł
  błędnie uznać zmieniony zapis za idempotentny; publiczny API falsifier ponownie
  zwraca `409 stale_base`, zachowując widoczny tekst marketera.
- `wilq-seo-1oa.36.9` zastępuje token-overlap ogólnym, intent-aware query mapperem.
  Query GSC nie dziedziczą już wszystkich sekcji przez wspólny refresh-level
  evidence ID ani pojedynczy token tematu. Mapper rozróżnia definicję,
  zastosowanie, obowiązek, proces, usługę i lokalność, wymaga jednego najlepszego
  dopasowania, a niepewność pozostawia jako `page_only`. Live GET z zarządzanego
  API przeszedł tym samym kontraktem oba exact piloty: BDO przypisuje `bdo dla
  kogo` i `mikroprzedsiębiorca bdo` wyłącznie do sekcji zastosowania; outsourcing
  przypisuje exact ogólne doradztwo tylko do sekcji usługi i exact Śląsk tylko
  do sekcji lokalnej, a Ruda Śląska, Bydgoszcz, Warszawa, Kraków, Katowice i
  Szczecin pozostają bez zgadywania. Typed schema oraz dashboard rozróżniają aktualne
  `intent_relevance`, historyczne `lexical_relevance` i `page_only`. GET pozostał
  model-free; scope nadal wymaga decyzji Wilka, Service Profile review ownera,
  a proof nie jest realnym UAT ani generacją tekstu.
- `wilq-seo-1oa.36.10` przywraca jeden evidence-bound internal-link path zamiast
  planistycznego `maxItems=0`. `ContentPlanningInput` v3 rozwiązuje kierunek z
  reviewed scope wyłącznie do dokładnego, publicznego faktu inventory WordPress
  z evidence należącym do bieżącego wejścia. Output schema ogranicza URL i
  cardinality, a lineage odrzuca obcy host/URL, evidence, claim i placement bez
  persystencji. Focused public proof przeprowadza oba piloty przez generated
  proposal i atomową rewizję v2; link zachowuje target, anchor, stable ID,
  placement i evidence w rendererze WordPress. Live read-only proof dla BDO i
  outsourcingu rozwiązał `Kontakt - Ekologus` do bieżącego WordPress evidence;
  realne karty nadal czekają na owner review, więc nie wykonano model generation,
  approval, WordPress write ani UAT.
- Epiki `wilq-seo-c9h9` (43/43 dzieci), `wilq-seo-3bst` (28/28) i
  `wilq-seo-amj2` (10/10) są zamknięte po ponownym odczycie grafu. Nie zamyka to
  aktywnego celu pilota: `lt1` nadal wymaga reviewed knowledge, `jst` realnego Wilku UAT, a
  `v9ab.13` review realnego daily-check output.
- Parent `wilq-seo-r564` jest zamknięty po świeżym fixed-point proof: wszystkie
  14 dzieci są closed, dashboard przechodzi 164/164, a live snapshot pokazuje
  konkretny homepage work item, 2 evidence IDs, jawny Service Profile review
  gate i `publish_ready=false`. Follow-up read-only refresh
  `wordpress_sklep` i Ahrefs zakończył się po 2 dowody i bez błędów; snapshot
  zwraca teraz `fresh`, bez stale/missing/blocked connectorów. Wybrany item
  nadal używa GSC i `wordpress_ekologus`. To nie jest Wilku UAT ani dowód
  jakości tekstu 10/10.
- `wilq-seo-c9h9.28` usuwa jedną brittle asercję wymagającą dokładnej frazy CTA
  mimo równoważnego, bezpiecznego brzmienia. Test nadal chroni realny kontrakt:
  `review_required`, `draft_allowed=false`, przypisane knowledge cards i
  `publish_ready=false`. Nie zmieniono copy ani produkcji i nie dodano snapshotu.
- `wilq-seo-or2e` usuwa stale test, który utożsamiał obcy nagłówek `Host` z
  remote peerem. Istniejący kanoniczny ASGI proof sprawdza rzeczywisty socket
  peer: remote + spoofed local Host daje `403`, loopback + malicious Host daje
  `200`. Middleware produktu nie został zmieniony; focused security file jest
  zielony 14/14.
- `wilq-seo-amj2.10` tworzy trwały learning proposal wyłącznie z atomowo
  utrwalonego, zamkniętego measurement window i pasującego outcome. Proposal
  zachowuje WordPress/GSC/GA4 evidence, metric-fact i refresh lineage, ale ma
  literalne `review_required`, `human_acceptance_required=true` oraz wszystkie
  uprawnienia do zmiany wiedzy, kolejki i claimu sukcesu ustawione na `false`.
  Przed outcome i po `insufficient_data` endpoint zwraca `409`; caller-supplied
  `approved` zwraca `422`. Nie dodano acceptance ani automatycznej zmiany wiedzy.
- `wilq-seo-amj2.9` wiąże okno pomiaru z utrwalonym live-created WordPress
  draftem oraz exact post ID/URL widocznym później jako `publish` w odczycie
  WordPress. Daty, dozwolone metryki, evidence i wynik pochodzą wyłącznie ze
  store WILQ; publiczne komendy przyjmują tylko `work_item_id`, więc klient nie
  może podać własnego okresu, wartości ani `measured_success`. Okno i wynik są
  trwałe. Syntetyczny proof potwierdza blokadę przed publikacją, `422` dla obu
  client-owned payloadów, `insufficient_data` dla snapshotu bez porównywalnego
  okresu lub z dodatkowym segmentem oraz server-derived wynik dopiero z
  okresowych page-aggregate faktów GSC. Exact-URL query nie zależy od
  przypadkowego top-N całego connectora, a nowe fakty GA4 zachowują zakres
  raportu. Realny stack nie został restartowany ani zmigrowany: brak
  maintenance window i potwierdzonego realnego publication event pozostają jawne.
- `wilq-seo-amj2.8` nadaje SQLite i DuckDB jawne wersje schematu oraz
  transakcyjnie chroni istniejącą migrację metryk. `wilq storage
  backup|restore` kopiuje oba store'y wyłącznie do nowych alternatywnych
  ścieżek i zwraca proof wersji oraz liczników rewizji, auditów i metryk.
  Syntetyczny backup→restore zachował 1 rewizję, 3 audity i 1 metric fact,
  a przerwana migracja
  zachowała stary readback. Realny runtime nie został zmigrowany ani użyty do
  restore drill — to wymaga maintenance window.
- `wilq-seo-amj2.7` wymusza prywatne prawa lokalnego pilota: runtime i
  kanoniczny state dir 0700, pid/log/SQLite/DuckDB 0600. Start normalizuje
  istniejące artefakty bez zmiany treści. Custom DB path nie zmienia praw
  istniejącego współdzielonego katalogu; 0700 dostaje tylko katalog utworzony
  przez WILQ. Managed restart potwierdził tryby i zdrowie obu usług.
- `wilq-seo-amj2.6` oddziela client-supplied etykietę aktora od autorytetu.
  Planning review, revision review i ActionObject review/confirm/impact/apply
  zapisują server-owned principal `local_operator`, workspace
  `ekologus_local_pilot` i trust `local_unverified`. Tekst typu
  `authenticated_expert` pozostaje wyłącznie etykietą; nie tworzy owner/expert
  acceptance. To nie jest authentication ani multi-tenant.
- `wilq-seo-c9h9.27` usuwa historyczny `CODEX_API_KEY` z aktywnego kontraktu
  runtime'u. `openai_codex` i system status korzystają z jednej typed readiness:
  obecność lokalnego CLI oraz lokalnej sesji `codex login`, sprawdzanej bez
  odczytu pliku, ujawnienia ścieżki i uruchamiania modelu. Live status po
  managed restarcie to `configured`, `required_env=[]`, źródło
  `local_codex_login`; runtime pozostaje poza daily evidence i vendor refresh.
- `wilq-seo-amj2.4` wyrównuje skilla `wilq-content-operator` z jednym
  kanonicznym journey dashboardu i API: kolejka → snapshot → zapisane decyzje
  planu → exact revision/review → opcjonalny exact Codex proposal →
  revision-bound ActionObject → WordPress draft-only. Skill nie opisuje już
  client-owned preflightów, legacy wariantów ani direct WordPress execution.
  Live smoke zachował realny blocker `scope`, 2 wiersze GSC i 0 zgadywanych
  Ads/Planner; non-interactive eval ma usefulness 9/10. To jest proof obsługi
  decyzji, nie jakości 10/10 realnego tekstu ani owner UAT.
- `wilq-seo-amj2.3` projektuje typed popyt bez nowego endpointu: live scope ma
  2 świeże wiersze GSC powiązane exact page i evidence ID z 3 sekcjami.
  Operatorowe zapytania z wieloma `-site:` nie wypierają zwykłych fraz z
  limitu faktów. Ads/Planner pozostają opcjonalne i obecnie pokazują 0, bo brak
  exact term+page+service mappingu; WILQ nie dopowiada słów. Desktop/mobile
  proof 1/1, zero content POST:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T23-53-12-663Z/`.
- `wilq-seo-amj2.5` zamyka lokalną granicę sieciową pilota: API autoryzuje
  rzeczywisty peer socket zamiast nagłówka `Host`, dawny
  `WILQ_ALLOW_REMOTE_API` nie omija ochrony, a kanoniczny manager odrzuca bind
  API lub dashboardu inny niż `127.0.0.1`/`localhost` przed utworzeniem plików
  runtime. README wskazuje wyłącznie `local_stack.sh`; po restarcie oba serwisy
  są zdrowe na loopback.
- `wilq-seo-r564.7` jest zamknięty i wypchnięty w `b23e413a`. Widok marketera
  pokazuje task mapę i tylko jeden aktywny workspace; rozbudowane szczegóły są
  dostępne wyłącznie w trybie `Audyt techniczny`.
- `wilq-seo-r564.8` jest zamknięty: append-only store wersji tekstu ma
  serwerowy numer, bazową wersję, digest treści i digest całej paczki planu.
  Save/review są idempotentne, wykrywają stale base, stale review i zmianę
  planu sekcji lub adresu.
- Review jest związane z dokładnym `revision_id` i digestem. Akceptacja v1 nie
  przechodzi na v2 ani na zmieniony plan/evidence. Przy zmianie planu editor
  rebasuje się do aktualnych sekcji i dowodów, zachowując tekst tylko dla
  zgodnych nagłówków.
- Dashboard zapisuje, odtwarza po reloadzie i pokazuje dokładną treść wersji
  przed decyzją. Konflikt zachowuje lokalny tekst i podaje polski następny krok.
- `wilq-seo-r564.9` wiąże handoff WordPress i cały ActionObject z jednym
  immutable bindingiem: work item, handoff, revision, digest treści, paczka i
  jej digest, decyzja approval oraz canonical. Legacy review/audit bez tego
  bindingu nie może autoryzować apply.
- Adapter dostaje tytuł i body sekcji wyłącznie z zatwierdzonej rewizji. Apply
  ponownie sprawdza aktualny snapshot i zapisany ślad preview → approved review
  → confirm → impact; publish, update i delete pozostają wyłączone.
- Zgoda exact bindingu jest atomowo konsumowana w kanonicznym SQLite przed
  adapterem. Równoległy drugi apply nie dociera do adaptera, a append/re-review
  nie może wyprzedzić trwającego zapisu. Nieudana lub niepewna próba zużywa
  starą zgodę i wymaga nowej wersji oraz review.
- Przed HTTP zapisywany jest durable `action_apply_started`; po odpowiedzi jedna
  transakcja utrwala claim status, apply audit, mutation audit i execution/post
  ID. Przerwany proces pozostawia jawny stan unknown/claimed. Po 300 sekundach
  lokalna komenda `wilq wordpress-apply reconcile` wymaga inspekcji i dla
  `applied` potwierdza draft przez readback; nigdy nie ponawia write i nie udaje
  uwierzytelnionego aktora.
- Identyfikatory lineage zachowują traceability, ale nie omijają redakcji:
  sekretopodobna wartość w zagnieżdżonym bindingu jest redagowana przed zapisem
  audytu.
- Stary mutable zapis structured output został usunięty po potwierdzeniu braku
  referencji. Istniejąca tabela w lokalnej bazie nie została usunięta ani
  migrowana.
- `wilq-seo-r564.10` osadza exact-binding ActionObject bezpośrednio w kroku
  `dev_draft`. Marketer widzi tylko aktywny etap: podgląd, review,
  potwierdzenie, kontrolę bezpieczeństwa albo zapis draftu; nie przechodzi na
  ogólny ekran akcji i nie rekonstruuje bindingu w React.
- Resume używa najnowszych uporządkowanych eventów tej samej rewizji. Nowszy
  binding, nieudany etap albo typed `409` zatrzymuje przebieg bez retry. Po
  syntetycznym sukcesie odświeżane są akcja, snapshot, activation/readback i
  readiness.
- `wilq-seo-r564.11` dodaje jeden API-owned seam propozycji poprawki wybranych
  sekcji. Endpoint sam pobiera dokładną najnowszą wersję `needs_changes` albo
  `rejected`, pełny generation input, brief, Claim Ledger, source facts,
  constraints i poprzedni review. Dynamiczne pola pozostają w kontekście
  `untrusted`; zwykła instrukcja jest statyczna. App-server działa
  ephemeral/read-only na izolowanym profilu bez user configu, MCP i sekretów
  środowiska oraz bez fallbacku.
- Znane capabilities narzędziowe są wyłączone, a każda zaobserwowana próba tool
  lub server request unieważnia wynik. Stockowy app-server nie udostępnia jednak
  ogólnej, twardej gwarancji wyłączenia każdego przyszłego built-inu; nie wolno
  opisywać tego runtime'u jako bezwarunkowo `tool-free`.
- Wynik może utworzyć wyłącznie niezatwierdzoną child revision. Tytuł,
  nieedytowane sekcje i evidence mapping są kopiowane z bazy. Obcy identyfikator
  claimu/dowodu, literalny znany blocked claim oraz wąski zestaw niezadeklarowanych
  obietnic efektu lub zgodności zatrzymują zapis. To nie jest pełny detektor
  semantyczny: rewizja utrwala run ID, wybrane sekcje i evidence/claim IDs, a
  człowiek nadal musi sprawdzić znaczenie tekstu. Review ma zakres
  `persisted_selected_sections_and_declared_lineage`; modelowe CTA, linki,
  meta i FAQ, których child revision nie przechowuje, nie podnoszą jego oceny.
- Zapis child revision i terminalnego `CodexRun` jest jedną transakcją SQLite.
  Inny run/provenance nie może dostać idempotentnej rewizji poprzedniego runu;
  błąd finalizacji wycofuje child revision.
- `wilq-seo-r564.13` podłącza ten exact proposal seam do aktywnego kroku
  `draft`. Browser dostaje tylko typed readiness i nagłówki, a nie prompt,
  `model_input` ani konfigurację runtime. Wilku wybiera sekcje, widzi pending,
  dokładny diff baza/child, lineage, findings i bramkę semantycznego review.
  Wynik nie może zatwierdzić treści ani dotknąć WordPressa. Zmiana work itemu,
  obcy work item albo brak wybranej sekcji unieważnia porównanie.
- Marketerowy WordPress dry-run udający ocenę tekstu i pięć osieroconych paneli
  zostały usunięte po pełnym reference proof. Techniczny payload dry-run nadal
  istnieje wyłącznie w audycie technicznym.
- `wilq-seo-r564.14` usunął pięć publicznych ścieżek ujawniających full generation
  contract: legacy generation/runtime/dwa preview oraz `draft-variants`. Usunięto
  OpenAI SDK/API-key runtime, dependency, env flags i browser schemas. Późniejsze
  planning/initial-draft/section-revision POST-y nadal współdzielą jeden
  server-side app-server; internal contract, output i preview blockers pozostają
  częścią jego serwerowego działania.
- `wilq-seo-c9h9.25` normalizuje bounded backend proof dla wykonawcy: jeden
  runner odkrywa aktualne pliki `test_*.py` i dzieli je deterministycznie na
  rozłączne shardy. `AGENTS.md` wymaga focused-first, jednego kosztownego procesu
  naraz, braku duplikatów pytest i niepowtarzania zielonych etapów bez zmiany kodu.
- `wilq-seo-v9ab.15` wiąże podgląd wykluczającego słowa i review ActionObject z
  pasującym dowodem 90 dni dla dokładnego terminu, kampanii i grupy reklam.
  Sam dowód 30 dni pozostawia kandydata jako `needs_90_day_review`, bez preview
  i bez action ID. Poprawny dowód nadal tworzy wyłącznie review z `apply=false`.
- `wilq-seo-3bnt` usuwa oczekiwanie operatora na sumę cold buildów po expiry.
  Daily-check rozpoznaje nieaktualny Command Center/GA4/content cache, atomowo
  uruchamia jeden background prewarm i natychmiast zwraca istniejący typed
  `daily_check_runtime_prewarm`. TTL, freshness, endpointy i invalidacja po
  connector/action/job pozostają bez zmian; content cold miss ma single-flight.
- `wilq-seo-amj2.2` usuwa historyczny fałszywy blocker kroku `dev_draft`.
  Snapshot wylicza gotowość z tego samego exact revision-bound handoffu, który
  zasila ActionObject. Aktualna zatwierdzona rewizja ma `ready/can_submit=true`;
  brak handoffu, zmieniony kontekst i obcy binding nadal pozostają fail-closed.
  Nie odblokowuje to publikacji ani zapisu poza preview/review/confirm/impact.
- `wilq-seo-amj2.1.1` utrwala pierwszą API-owned wersję decyzji planistycznych.
  Snapshot pokazuje exact digest zakresu i mapy sekcji oraz najnowsze decyzje
  `scope` i `section_map`. Review jest idempotentne, stary digest i próba
  zatwierdzenia mapy przed zakresem kończą się typed `409`. Pierwszej rewizji
  nie można zapisać, dopóki obie decyzje nie są aktualne i `approved`.
- `wilq-seo-amj2.1.2` podłącza ten kontrakt do jednego aktywnego workspace'u.
  `scope` pokazuje stronę, usługę, intencję, odbiorcę, problem, moment decyzji,
  CTA i linkowanie; `section_map` pokazuje tylko uporządkowane sekcje, ich cel
  i liczbę dowodów. Dawna trzykolumnowa ściana w tym kroku została usunięta.
  Typed `409` zachowuje notatkę i daje jawny reload; zapis odświeża API-owned
  krok. Nie dodano promptu, Codex call ani WordPress write.
- `wilq-seo-amj2.1.3` wiąże każdą nową rewizję i exact WordPress binding z
  digestem aktualnie zatwierdzonego planu. Digest wchodzi do content digestu i
  child revision Codexa. `needs_changes`, zmiana proposal albo brak legacy
  bindingu ustawia revision context jako stale, blokuje review/Codex/handoff i
  ActionObject bez usuwania historii.

## Bieżący proof

- Realny expiry proof po 31 s zwrócił typed blocker w 0,003 s. Po background
  rebuildzie pełne odczyty trwały 0,018/0,020/0,018 s i zachowały ten sam hash
  statusu, freshness, 23 evidence IDs, 7 source connectors, 8 action IDs oraz
  blocked claims. Focused expiry/concurrency/guard testy 44/44, Ruff i mypy są
  zielone; świeży browser Command Center przechodzi 1/1 w 3,2 s.
- Po managed restarcie live Ads summary ma 5 kandydatów, 5 pasujących preview
  90 dni i jeden review-only action; wszystkie preview mają `apply=false`.
  Focused public API/validator 3/3, shared schemas 37/37, Ruff i mypy są zielone.
  Browser `/ads-doctor` zachowuje evidence-first pierwszy ekran; heading pojawił
  się po 1,432 s, bez technicznych ID nad foldem.
- Publiczny live snapshot po managed restarcie zwraca wyłącznie
  `structured_generation_readiness`; rekursywny smoke dla obu kandydatów nie
  znalazł `structured_generation`, promptów, `model_input` ani output schema.
- Focused backend content API doszedł do 100%; Ruff i mypy są zielone. Shared
  schema 38/38, focused dashboard 29/29, TypeScript, ESLint i build są zielone.
- Browser proposal proof przechodzi 1/1 dla 1440×900 i 390×844: dokładny POST,
  pending, baza/child, `weak_cta`, semantic review, `publish_ready=false`, run ID
  w disclosure, zero WordPress requestów i zero horizontal overflow. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T19-06-55-670Z/`.
- Exact dev-draft proof: 13 focused wariantów API/operator journey przechodzi,
  w tym aktualny approved binding oraz stale-context blocker; focused React
  1/1, TypeScript, Ruff i mypy są zielone. Playwright przeszedł pełny syntetyczny
  save → reload → exact review → inline ActionObject na desktop/mobile 1/1, bez
  realnego WordPress write. Live item bez rewizji poprawnie pozostaje
  `missing_revision_bound_draft`.
- Planning UI proof: focused React 2/2, pełny dashboard 163/163, TypeScript,
  ESLint i shared schemas 37/37 są zielone. Live desktop/mobile browser 1/1
  pokazuje `scope`, zablokowany submit bez review i brak dawnych paneli, bez
  żadnego content POST. Proof: `.local-lab/proof/dashboard-content-workflow/2026-07-15T23-08-03-347Z/`.
- Planning-to-revision proof: zatwierdzony plan tworzy rewizję i handoff z tym
  samym digestem; późniejsze `scope=needs_changes` cofa workflow do `scope`,
  zachowuje revision ID, ale ustawia `context_current=false` i usuwa handoff.
  Focused public API 2/2, store/revision 19/19, ActionObject binding 1/1, Ruff,
  mypy, TypeScript i ESLint są zielone.
- Review użyteczności marketera/operatora daje 6/10 dla samego workflow, lecz
  utrzymuje 5/10 dla jakości realnego tekstu: poprzedni 38-słowny output nadal
  był generyczny i `needs_changes`; Service Profile i realny Wilku UAT są otwarte.
- Focused backend, shared schema, dashboard tests, Ruff, mypy, TypeScript,
  ESLint i diff check przechodzą. Szeroki code gate potwierdził 977 backend
  testów (2 skip), 36 shared i 164 dashboard testy oraz security/API/skill
  smokes.
- Stateful browser proof przechodzi dla 1440×900 i 390×844:
  zapis → reload → exact review → preview → review akcji → confirm → impact →
  syntetyczny apply → draft-only readback, bez horizontal overflow.
- Proof wykonuje osiem kontrolowanych POST-ów na viewport. Sześć endpointów
  ActionObjectu jest przechwyconych przez Playwright; żaden request nie dociera
  do WordPressa, a publish/update/delete nie istnieją w przebiegu. Zrzuty są w
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T11-50-52-058Z/`.
- Focused API/UI testy przechodzą 32/32, TypeScript i ESLint są zielone, a
  niezależny Standards+Spec review nie znalazł uchybień. Browser proof
  przechodzi 1/1.
- Po usunięciu zbyt krótkiego 15-sekundowego timeoutu startowego pełny browser
  gate przechodzi 21/21, a dashboard build przechodzi. Nie zmieniono runtime'u
  produktu ani ścieżki danych.
- Kanoniczny stack manager czeka teraz do 40 sekund na rzeczywisty cold start;
  restart kończy się zdrowym API `:8000` i dashboardem `:5173`. Live metrics:
  109 541 faktów, 4 791 refresh runs, 8 connectorów. Queue nadal jest uczciwie
  density-blocked: 2 pozycje, 1 wykonalna przy wymaganych 3.
- Po managed restarcie live snapshot pozostaje uczciwie na `scope`: typed plan
  i 64-znakowy digest istnieją, obie decyzje są niezapisane, a pierwsza rewizja
  ma `can_save=false`. Nie zapisano decyzji w realnym lokalnym stanie.
- Syntetyczny publiczny proof ActionObject utworzył dokładnie jeden draft przez
  spy-adapter. Siedem manipulacji bindingiem, eventy legacy, późniejsza v2,
  równoległy drugi apply i replay tej samej zgody zwróciły typed `409` z
  `adapter_reached=false` i `external_write_attempted=false`. Focused claim,
  crash recovery, action/audit i redaction proof przechodzi 27/27, a osobny
  publiczny exact-revision apply 1/1.
- Focused falsifier propozycji Codex przechodzi: pełny API-owned `model_input`
  dociera do adaptera; obcy claim ID, known blocked phrase i niezadeklarowany
  high-risk promise kończą się `proposal_contract_blocked` bez child revision,
  a zgodny wynik tworzy v2 i pozostawia workspace `unreviewed`. Transport proof
  sprawdza izolację profilu i fail-closed tool
  attempt, a dwa testy trwałości chronią provenance i atomowy rollback. Focused
  zestaw proposal/store/preview ma 29 zielonych testów; Ruff i mypy są zielone.
  Complexity audit nie wykrywa naruszeń w nowych modułach; raportuje cztery
  starsze limity `workflow/store.py`, dotkniętego przez konieczny atomowy seam.
- Finalny realny proof po trust split i izolacji profilu utworzył v2 dla jednej
  sekcji: 38 słów, dwa evidence IDs z `google_search_console` i
  `wordpress_ekologus`, `item_types=userMessage/reasoning/agentMessage`,
  `external_call_attempted=false`, zero mutation auditów, `publish_ready=false`.
  Verdict to uczciwe `needs_changes`: brak trwałego typed CTA i linkowania
  wewnętrznego, review-required brief oraz brak measurement window. Wcześniejszy
  wynik z obcymi referencjami został zablokowany; nie dodano fallbacku ani
  luźniejszej ścieżki.
- Szeroki `scripts/verify.sh` ujawnił niezależną regresję context-packu:
  bezpieczny `normalized_page_path` był redagowany jako token. `wilq-seo-r564.12`
  zachowuje teraz wyłącznie zwalidowaną absolutną ścieżkę treści; tokenowe,
  sekretowe, traversalowe i malformed wartości nadal kończą jako `[REDACTED]`.
  Focused redaction przechodzi 5/5, a pierwotny publiczny context-pack repro 1/1.
- `/knowledge` ma teraz osobną, pierwszoplanową listę 14 zredagowanych
  `source-facts` z URL/path, statusem review, evidence i blokowanymi claimami.
  Legacy seed-karty/playbooki są jawnie opisane jako warstwa operacyjna, nie
  jako słowa Ekologusa. W odnalezionym repozytorium materiałów potwierdzono 15
  plików `materials_clean/approved`; ich manifest i hash-prefixy są zapisane w
  `docs/research/approved-ekologus-materials-2026-07-17.md`. Pełny import
  redacted excerptów nadal wymaga kontrolowanego seamu i owner review.
- Po świeżym checkerze source facts mają jawny `generation_status`: wyłącznie
  approved + commit-safe + evidence może być `eligible`; prywatne kandydatury
  są `blocked_review_required`. Focused falsifier w Sales Brief sprawdza, że
  fact bez evidence nie przechodzi do structured model input. Live API po
  restarcie zwróciło oba statusy poprawnie.
- `/knowledge` ma również metadata-only endpoint i panel manifestu 15
  materiałów z zatwierdzonego korpusu (`import_pending`): nazwa, rola, word
  count i hash-prefix są widoczne, ale surowy prywatny tekst nie trafia do
  WILQ. UI nazywa tę warstwę „Źródła i wiedza” i jasno oddziela materiały od
  wtórnych kart/playbooków.
  Live endpoint zwrócił 15 rekordów i 3 183 słowa z manifestu; focused API,
  dashboard i TypeScript proof przechodzą.
- Browser proof `/knowledge` rozszerzono o source-facts i manifest materiałów:
  1/1 przechodzi na live API, a Ruff dla nowych Python seams jest zielony.
- Pełny draft/page preview ma teraz aktualny focused proof 1/1 po poprawieniu
  testowego wejścia na jawnie wybrany `work_item_id`; `/content-workflow` nie
  udaje już automatycznie wybranego tematu na pustym wejściu.
- 2026-07-17: planowanie działa przez API-owned `ThreadPoolExecutor`, więc POST
  nie czeka na ciężki snapshot/Codex; exact retry/dedup i stale queued-job
  recovery mają focused proof. Initial full-draft slice przechodzi 1/1,
  publication-bound measurement 5/5. Selected inventory queue po restarcie
  zwrócił HTTP 200 w 3.22 s z realnymi 43 impressions, 1 click i 11 query;
  secondary snapshot zwrócił 200 w 5.76 s. Zimna ścieżka pozostaje obserwowana,
  ale nie blokuje pierwszego panelu.
- 2026-07-17: pomiar nie może już użyć starego, niepowiązanego execution
  work-itemu; wymaga exact handoff + revision digest. Trzeci checker Claude
  `.../exact-measurement-and-pipeline-final-check-LuscRL/checker.review.json`
  jest strukturalnie ważny, ale ma `findings=[]` wyłącznie dlatego, że nie
  dostał literalnych excerptów kodu; jego `evidence_gaps` zamieniono na Beads
  `wilq-seo-j54`, `wilq-seo-7trz` i `wilq-seo-7wdf`. Nie traktujemy tego jako
  PASS ani jako zamknięcia pipeline.
- 2026-07-17: source-backed review wykrył niespójne service-card scoping w
  stale-checku planu; `latest(work_item_id, service_card_id=...)` i route seam
  są teraz zgodne, z focused proofem 3 testów store. Terminalny błąd executora
  nie wycieka jako 500, a status GET nie odbudowuje snapshotu: czyta najnowszy
  queued/failed job bez skanowania metryk. Szeroki test został przerwany po
  ponad 10 minutach w znanym legacy metric-store hot path; nie traktujemy go
  jako PASS ani jako dowodu gotowości.
- 2026-07-17: usunięto hot path w `list_metric_facts_for_content_url`: każdy
  exact URL nie buduje już tymczasowego indeksu legacy na całej tabeli DuckDB;
  używa bezpośrednich predykatów URL i końcowej walidacji landing identity.
  Managed proof po restarcie: selected queue 200/0,17 s, snapshot 200/3,065 s
  cold i 200/0,768 s warm. To jest poprawa runtime, nie dowód semantic quality
  ani pełnego UAT.
- 2026-07-17: publication-bound measurement dostał server-owned aggregate seam
  dla exact URL + exact ISO period. GSC sumuje clicks/impressions i wylicza CTR,
  GA4 sumuje sessions/engaged_sessions i wylicza engagement rate; average
  position wymaga impressions. Mixed evidence lineage, złe okresy, brak
  mianownika i niepełny rdzeń źródeł są typed exclusions. Focused aggregate
  proof 3/3 oraz istniejący publication suite 5/5. Live BDO nadal ma głównie
  `period=connector_refresh`, więc realny measurement pilot pozostaje jawnie
  zablokowany jako brak exact covered window.
- Niezależny checker Claude dla agregacji (`measurement-aggregate-seam-vFeain`)
  wykrył trzy realne hardeningi: pusty licznik ratio, ciche nieznane metryki i
  brak jednostki derived ratio — wszystkie naprawione. Czwarty finding o
  deduplikacji odrzucono po sprawdzeniu pełnego JSON `MetricFact` i 15/15 testów
  metric store. Pass ma disposition i nie jest przedstawiany jako approval.
- GSC connector nie zapisuje już nowych query/page facts jako bezokresowego
  `connector_refresh`: bierze `date_start/date_end` z odpowiedzi Search Analytics.
  Metric store potrafi też nadać ten exact period starszemu refreshowi, jeśli
  run ma daty w `metric_summary`; GA4 już używa zakresów dat. Vendor contract i
  metric-store proof przechodzą 16 testów. Historyczne fakty bez dat nadal są
  jawnie blokowane, dopóki nie pojawi się świeży refresh z covered window.
- 2026-07-17: świeży vendor-read GSC `refresh_google_search_console_666a2c20f82c`
  potwierdził realne okno `2026-07-15/2026-07-15`, `partial_possible`, brak
  truncation i stan `settled/partial`; dla BDO agregat exact URL ma 1 klik,
  266 wyświetleń, CTR 0,003759 i średnią pozycję 12,55. `ConnectorRefreshRun`
  przechowuje teraz typed `covered_window`, `settlement_state` i
  `quality_state`; GA4 bez sygnału settling pozostaje `unknown`, nie udajemy
  uniwersalnej świeżości.
- 2026-07-17: kolejne odświeżenia tego samego okresu nie powodują już fałszywego
  `ambiguous_source_lineage`: aggregate seam wybiera najnowszy refresh po
  `collected_at`, a przy remisie nadal blokuje. BDO readback po refreshu 666 ma
  exact evidence, 1 klik, 266 impressions, CTR 0,003759 i weighted position
  13,7878; 544 historycznych `connector_refresh` rows pozostaje wykluczonych.
- 2026-07-17: reprodukcja live wykazała, że POST nowego planu po zmianie
  metryk był odrzucany przez porównanie do starego proposal digestu, mimo że
  operator wysyłał aktualny digest. Usunięto ten błędny gate: nowy digest może
  wejść do kolejki, a worker nadal waliduje go względem odbudowanego snapshotu.
  Live proof zwrócił `generating`; po 120 s Codex poprawnie przeszedł w typed
  `runtime_failed/codex_timeout` bez częściowego zapisu. To pozostaje limit
  runtime, nie spinner bez końca.
- 2026-07-17: panel planowania nie eksponuje już Codexa jako głównego języka
  marketera. Stan generowania mówi wprost, że plan powstaje z aktualnej strony,
  metryk i usługi, ma `aria-live` oraz informuje, że nie trzeba uruchamiać
  drugiego planu; techniczny runtime pozostaje w sekcji „Dlaczego”. Dashboard
  typecheck przechodzi.
- 2026-07-17: planowanie ma osobny bounded timeout Codexa: domyślnie 60 s
  (`WILQ_PLANNING_CODEX_TIMEOUT_SECONDS`), niezależnie od draftu i semantic
  review. Focused proof potwierdza konfigurację; live status po wcześniejszej
  próbie jest jawnie `failed/runtime_failed`, bez partial write i z retry.
- 2026-07-17: niezależny health probe minimalnego turnu Codexa również
  timeoutuje przy 20 s, więc ostatnie timeouty planera są problemem runtime,
  nie rozmiarem wejścia (plan: 25,9 KB danych + 9,6 KB schema). Nie dodano
  fallbacku ani zmyślonego planu; failure pozostaje typed i retryable.
- 2026-07-17: WordPress public REST importer zachowuje teraz zwykłe pola ACF
  także wtedy, gdy strona nie ma flexible-content rows. Live refresh
  `refresh_wordpress_ekologus_fa66b5c70328` dla BDO zapisał
  `acf_field_names=["wyswietlenia"]`, brak sekcji flexible i pełny
  `the_content`; katalog po restarcie pokazuje `content_and_structure` zamiast
  udawać brak ACF.
- 2026-07-17: dodano metadata-only endpoint `GET
  /api/knowledge/source-materials/readiness` oraz banner w powierzchni Wiedza.
  Manifest 15 materiałów pozostaje jawnie `import_pending` (0/15), więc
  generowanie nie udaje dostępu do transkrypcji ani bazy wiedzy. Kontrakt
  pokazuje liczności, blocker i bezpieczny następny krok: kontrolowany import
  redagowanych excerptów po owner review. Focused API/dashboard proof przechodzi.
- 2026-07-17: pełny browser proof `/content-workflow` przeszedł 6/6 testów.
  Proof wiąże prawdziwy URL BDO przez `/api/content/inventory/bind` zamiast
  używać historycznego ID, pokazuje wybrany inventory przed wolną kolejką,
  przechodzi desktop/mobile planning, pięć sekcji, poprawkę wybranej sekcji
  oraz trwały review → draft-only wizard bez publikacji. W trakcie proofu
  naprawiono brak przycisku zapisu pierwszej wersji; backend nadal wymusza
  aktualny scope/mapę, exact sekcje i lineage.
- 2026-07-17: live proof drugiego dokładnego case'u potwierdził ogólny seam
  URL → workflow dla `https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/`.
  Bind zwrócił `ready`, a snapshot po odczycie dynamicznym zidentyfikował kartę
  `ekologus_service_environmental_consulting_outsourcing`, 52 zapytania GSC,
  731 wyświetleń, 0 kliknięć, CTR 0% i najlepszą średnią pozycję 1,00.
  Początkowy katalog ma `url_only`, ale workflow nie zgaduje: dopiero snapshot
  potwierdza publiczny HTML jako `review_required` i pozostawia draft zablokowany
  do dalszego review.
- 2026-07-17: checker `second-opinion-review` dla fixed pointu browser proof
  przeszedł walidację. Przyjęte findings: live Codex timeout i 0/15
  zaimportowanych materiałów są blockerami, 6/6 browser proof nie jest UAT ani
  dowodem produkcji, a pojedynczy BDO bind nie dowodzi wszystkich możliwych URL-i.
  Nie przedstawiamy tych dowodów jako pełnej gotowości; pass retained w
  `~/coding/krn/second-opinion-review/wilq-seo/check/2026-07-17-wilq-content-pipeline-browser-proof-kQsMkb`.

## Następny bezpieczny zakres

Fixed-point review jest zapisany w Beads jako epic `wilq-seo-amj2`. Kolejność
pilota nie jest już luźną listą pomysłów:

1. Typed demand evidence i zgodny content skill są domknięte w `amj2.3`–`.4`;
   nie dodawać alternatywnego content entrypointu.
2. Lokalna granica pilota `.5`–`.8` ma loopback-only, server-owned identity,
   prywatne tryby i syntetyczny versioned recovery proof. Realny restore drill
   nadal wymaga maintenance window.
3. Measurement, review-only learning i peer-scope proof są domknięte. Ponownie
   odczytać roadmapę; nie zamykać epica pilota bez realnego Wilku UAT i
   owner-reviewed Service Profile.

Architektoniczne tickety `wilq-seo-jnra`, `wilq-seo-djly` i `wilq-seo-kgvy`
zostały zamknięte po świeżym parity proof. Dalsze mechaniczne rozcinanie
`service.py` lub Ads bez konkretnego ryzyka produktu jest poza roadmapą.

## Jawne blokery i ograniczenia

- Brakuje owner-reviewed, `approved_current` Service Profile do finalnej pracy
  treściowej.
- Brakuje realnej sesji Wilku UAT albo jawnego owner defer z ryzykiem
  rezydualnym.
- Queue nie ma wymaganych trzech wykonalnych pozycji; WILQ nie tworzy sztucznej
  trzeciej propozycji.
- Principal `local_operator` ma jawny trust `local_unverified`; nadal nie jest
  uwierzytelnionym ownerem, ekspertem ani tenant/actor contractem.
- Obecny runtime jest wymuszony jako loopback-only, state/logi mają prywatne
  prawa, a recovery ma syntetyczny proof na alternatywnych ścieżkach. Realna
  migracja i restore drill wymagają maintenance window. Remote deployment
  wymaga osobnego auth/TLS/owner
  contractu; bieżący runtime nie ma zdalnego bypassu.
- PostgreSQL/HA, monitoring i alerting, retencja/legal hold, realny restore
  drill, rotacja credentials oraz publiczny reverse proxy pozostają decyzjami
  ownera/IOD albo pracą wymagającą maintenance window. Nie są dowodem lokalnego
  pilota i nie są zamknięte.
- Goal 005, produkcyjna gotowość i pełna użyteczność dla marketera nie są
  zakończone.
### 2026-07-17 — nowa sanitizowana paczka do realnego Wilku UAT

- Dodano `docs/review-packets/2026-07-17-wilku-live/` z instrukcją „otwórz
  mnie”, live proof, osobnym opisem synthetic proof, formularzem oceny oraz
  instrukcją prawdziwego nagrania. Paczka nie kopiuje surowych materiałów ani
  nie udaje, że fixture'y są UAT.
- Poprzednie paczki zawierały opisy, które mogły sugerować `approved_current`
  i stare wartości GSC. Nowa wersja kwalifikuje stan: obie ścieżki są
  `service_match_required`, knowledge readiness to `import_pending` 0/15, a
  live Codex generation i realny WordPress draft pozostają nieudowodnione.
- Odczyt live 17.07: DuckDB 133895 facts / 4855 refresh runs; GSC świeży
  17.07, GA4 ostatni udany odczyt 15.07, Ads read/review-only; LinkedIn/Facebook
  bez dostępu, Google Sheets wyłączony.
- Paczka jest przekazywalna marketerowi, ale nie zamyka pilota. Do zamknięcia
  nadal wymagane są: realne nagranie i formularz Wilku, owner review kart,
  kontrolowany import materiałów, udane pełne generation/review oraz exact
  draft-only dry-run.

### 2026-07-17 — binding URL-u rozwiązuje publiczny materiał

- `POST /api/content/inventory/bind` nie zwraca już fałszywego `url_only`, gdy
  katalog REST ma tylko URL, ale wybrany adres ma czytelny publiczny
  `the_content`/HTML. Binding wykonuje jeden read-only resolver dla wybranego
  adresu i zwraca `content_summary` albo `content_and_structure` oraz tytuł.
- Live proof po restarcie stacka: BDO i doradztwo/outsourcing zwracają
  `ready`, `content_and_structure`, tytuł i `metrics_status=available`; oba
  nadal prawidłowo mają `service_match_required` oraz
  `blocked_until_service_and_metrics`.
- Falsifier: `tests/content/test_inventory_catalog.py` — 7/7 passed.
  Ruff dla produkcyjnego `wilq/content/workflow/catalog.py` i `git diff --check`
  są zielone. Szerszy testowy plik ma wcześniejsze, niezwiązane naruszenia
  formatowania/importów; nie przedstawiam ich jako regresji tego slice'u.
- Dashboard smoke dla inventory-bound workflow również przeszedł `1/1` po
  restarcie stacka; nie uruchamia modelu ani vendor write.

### 2026-07-17 — baseline planu przestaje produkować nagłówkowy slop

- Baseline dla istniejącej strony korzysta teraz z rzeczywistych nagłówków
  materiału zamiast tworzyć „Co wiemy z zapytań: …”. Odfiltrowuje nagłówki
  nawigacji, related content, „Więcej”, „Oferta…” i zaufanych klientów, a
  ogólny BDO-owy lead normalizuje do „Najczęstsze pytania dotyczące BDO”.
- Zniknęło też powtarzanie H1 i CTA w każdej pustej sekcji. Placeholder ma
  teraz reader-first purpose, a pełny tekst nadal wymaga planu modelowego,
  review i zatwierdzenia człowieka.
- Falsifiers: `tests/content/test_decision_mapping.py` i istniejący sales brief
  — 20 testów passed; Ruff dla zmienionych modułów i `git diff --check` zielone.
- Live snapshot po restarcie: outsourcing pokazuje nagłówki „Korzyści ze
  współpracy z nami”, „Doradztwo ekologiczne” i „Potrzebujesz doradztwa…”, a
  BDO „Najczęstsze pytania dotyczące BDO”, bez prefiksu „Co wiemy z zapytań”.
- Próba ponownego live planningu outsourcingu na aktualnym digest zakończyła
  się po bounded deadline typed `runtime_failed/codex_timeout`; GET zwrócił
  blocker, bez częściowego proposal. To nadal zewnętrzny blocker runtime’u,
  nie powód do fallbacku ani twierdzenia, że pełny pipeline działa.
- Checker Claude dla tego slice'u ponownie został odrzucony przez validator za
  cytację ponad 20 linii; brak ważnego JSON/PASS pozostaje jawny.

### 2026-07-17 — retry orphaned planning jobów

- Minimalny `codex exec` probe kończy się poprawnie w około 8 s, więc login i
  podstawowy app-server są zdrowe. Live structured planning outsourcingu nadal
  może kończyć się `codex_timeout` przy większym wejściu/schema.
- Naprawiono lifecycle queued joba: stale orphan nie jest już prezentowany jako
  terminalny `failed` bez digestu. Po przekroczeniu 120 s GET odbudowuje aktualny
  input i zwraca retryable `stale` z exact `planning_input_digest`; następny POST
  może ponowić plan od razu zamiast czekać 15 minut.
- Falsifier store: `tests/content/test_generated_proposal_store.py` 3/3 passed;
  live GET po restarcie zwrócił `stale` z digestem, a retry POST `generating`.

### 2026-07-17 — pełny input, kompaktowy transport modelu

- Pomiar aktualnego kontraktu wykazał 54,9 KB dla BDO i 79,1 KB dla
  outsourcingu; największym polem jest portfolio GSC (31/52 exact rows), w
  których powtarzały się te same refresh-level evidence IDs.
- `content_planning_turn_request` zachowuje pełny `ContentPlanningInput` dla
  digestu, stale detection, walidacji i readbacku, ale przekazuje do modelu
  niemutujący envelope: wszystkie exact query rows, bez `null` i z maksymalnie
  trzema powtarzającymi się evidence IDs oraz czterema nagłówkami na wiersz.
  Coverage (`rows_available`/`rows_included`) jest jawne, a pełny top-level
  evidence set i output schema pozostają niezmienione.
- Falsifier: `test_model_planning_envelope_compacts_repeated_query_lineage_without_dropping_rows`
  oraz `tests/content/test_dynamic_planning_input_sources.py` — focused test
  passed; Ruff i `git diff --check` passed. Nie jest to jeszcze dowód udanego
  live Codex generation; poprzednia próba nadal kończyła się typed timeoutem.
- Po restarcie stacka wykonano nowy live POST dla outsourcingu na digest
  `418322…`; kolejka ruszyła, ale po bounded deadline ponownie zapisała
  `runtime_failed/codex_timeout` bez proposal/partial write. Kompaktowanie samo
  nie rozwiązuje runtime transportu; nie dodano fallbacku ani drugiego modelu.
- Niezależny execution-binding review zgłosił potencjalny legacy path. Lokalny
  exact lookup w `stage_measurement.py` oraz falsifier
  `test_unbound_legacy_execution_cannot_unlock_measurement_window` przeszedł
  1/1, więc brak reprodukcji i brak nieautoryzowanej zmiany tego kontraktu.

### 2026-07-17 — structured planning działa po pełnym bounded retry

- Bezpośredni probe aktualnego outsourcingowego inputu (57,9 KB envelope,
  schema 15,9 KB) zakończył się poprawnym structured outputem po 85,6 s przy
  limicie 120 s. Wcześniejsze 60 s było fałszywym runtime blockerem; planner
  pozostaje asynchroniczny, więc nie wydłuża requestu przeglądarki.
- Domyślny planning deadline zmieniono z 60 do 120 s, z env override i testem
  kontraktu. Live retry outsourcingu zakończył się `ready`, proposal
  `content_planning_proposal_a200ee01d1114440bf7bf2b1eb524cd3`, bez blockerów.
- Dodano deterministyczną bramkę slopu dla nagłówków nawigacyjnych,
  promocyjnych, datowanych i related-content. Istniejący BDO plan został
  poprawnie oznaczony `quality_gate_failed`, a wersja kryteriów została
  podniesiona do `wilq_people_first_planning_v3`, aby stare propozycje nie
  przechodziły przez idempotency.
- Live BDO i outsourcing przeszły ten sam kontrakt v3: odpowiednio
  `content_planning_proposal_cc06635ba2e547ab9ddc15151b28c175` i
  `content_planning_proposal_f764da84dc19483488e59501db5ccb07`, oba `ready`,
  `publish_ready=false`, bez noise headings i bez automatycznej akceptacji.
- Focused falsifiers: bounded-timeout, quality-gate, compact-envelope oraz
  `unbound_legacy_execution` — zielone; Ruff i `git diff --check` zielone.
- Niezależny checker Claude dla planning v3 został uruchomiony w dozwolonym
  oknie, ale runner ponownie nie opublikował `checker.review.json`; validator
  odrzucił brak outputu. Nie przedstawiam tego jako PASS ani jako findingu.

### 2026-07-17 — initial full draft i mocniejsza bramka materiału

- Na BDO wykonano synthetic local-operator scope + section-map review (jawnie
  nie owner/Wilku UAT), a initial full draft zakończył się `created`:
  revision `content_revision_228d0f04d0594c9e889ee2e2cd715344`, digest
  `74c6528254505f1bb53a35932106fcda912f5193a5bbae541b7e28d20c59d46e`.
  Rewizja v2 ma trwałe page assets (title, meta, H1, lead), 8 sekcji, 5 FAQ,
  2 CTA i 1 link; pozostaje `unreviewed`, `publish_ready=false`.
- Próba semantic review tej rewizji zatrzymała się typed
  `missing_planning_input`, bo bieżący materiał WordPress ma
  `material_confidence=review_required`. To ujawniło niespójność: initial
  draft korzystał z filtrowanego `planning_generation_blockers()` i omijał
  wymaganie review materiału.
- Naprawiono seam: initial full draft używa pełnego zbioru readiness blockers.
  Po synthetic scope + section-map review outsourcingu ponowny initial-draft
  POST zatrzymuje się przed modelem jako `stale_planning_input` z
  `wordpress_material_review_required`, bez rewizji i bez runtime call.
- Wniosek: publiczny rendered `the_content` może zasilać plan reviewable, ale
  nie może sam zasilać trwałego pełnego draftu ani semantic review. Kontrolowany
  import/redakcja/owner review materiałów pozostaje realnym blockerem.
- Dodatkowo revision workspace nie pokazuje historycznej rewizji jako
  reviewable, gdy bieżący materiał ma `review_required`: live snapshot BDO ma
  `status=unreviewed`, `can_review=false`, `can_save=false` i jawny następny
  krok zatwierdzenia źródłowego materiału.
- Semantic review ma teraz osobny typed blocker
  `source_material_review_required` zamiast ogólnego `missing_planning_input`,
  z następnym krokiem kontrolowanego importu/redakcji i owner review. Live POST
  BDO potwierdza blocker bez uruchamiania Codexa.

### 2026-07-17 — wspólny proof pełnego draftu dla dwóch usług

- Testowy harness został przełączony ze starych `content_decision` IDs na ten
  sam kanoniczny `inventory_work_item_id(url)`, którego używa produkcja. URL
  outsourcingu poprawiono do rzeczywistego `/oferta/...`; nie dodano wyjątku w
  kodzie produkcyjnym.
- Syntetyczny harness jawnie oznacza materiał jako `source_bound`, aby testować
  atomowy zapis dokumentu po zatwierdzeniu materiału; produkcyjny
  `review_required` nadal blokuje initial draft i semantic review.
- Falsifier przeszedł: `test_initial_full_draft_uses_the_same_atomic_contract_for_both_services`.
  Ten sam przepływ dla BDO i doradztwa/outsourcingu utworzył trwałe rewizje v2
  z pełnymi page assets, bez częściowego zapisu; `publish_ready=false`.
- Ruff dla zmienionego harnessu i `git diff --check` są zielone. To synthetic
  contract proof, nie owner/Wilku UAT ani zgoda na WordPress write.
- Niezależny execution-binding review ponownie sprawdził `stage_measurement`:
  exact lookup wymaga work itemu, handoff ID, revision ID i content digest;
  ścieżka bez bindingu przekazuje `None`. `test_publication_bound_measurement.py`
  przeszedł 5/5, więc nie dodano redundantnej zmiany.
- Dodatkowa bramka store jest all-or-none: częściowy zestaw
  `handoff_id/revision_id/revision_digest` zwraca `None` zamiast legacy
  work-item execution. Falsifier obejmuje próbę częściowego lookupu po
  zapisanym legacy execution; testy pomiaru 5/5 i Ruff przechodzą.

### 2026-07-17 — source quality bez uniwersalnego SLA

- Świeży WILQ context: 133895 faktów metrycznych, 4855 refreshów, 12
  konektorów / 9 skonfigurowanych; GSC i WordPress są świeże, GA4 ma ostatni
  udany odczyt 2026-07-15.
- `_quality_contract` rozróżnia teraz semantykę źródeł: GA4 ma
  `settling` + `unverified`, Ahrefs i Localo `not_applicable` dla settlementu
  oraz jawne caveaty snapshotu/coverage. Localo zapisuje w summary zakres
  `date_start/date_end` dla agregatu 30-dniowego.
- GSC content diagnostics przestał dołączać `seo_content_decay_v1` i
  `seo_cannibalization_v1`, ponieważ obecny odczyt nie ma historii ani okresu
  porównawczego. Reguły pozostają w katalogu wiedzy, ale decyzja ich nie
  cytuje bez wymaganych danych.
- Falsifier: `tests/connectors/test_refresh_quality_contract.py` 3/3,
  Ruff i `git diff --check` zielone. Pełne porównania okresów są kolejnym
  otwartym slice'em, nie zostały udawane tym ograniczeniem.

### 2026-07-18 — Campaign Builder i spójność waluty Ads

- Campaign Builder został sprowadzony do rzeczywistego kontraktu API: kolejka
  review istniejących kampanii, landing/context, KPI, brakujące kontrakty,
  human gates i niemutujący preview. Skill/agent/output contract jawnie blokują
  keywords, assety, sitelinki, copy, targetowanie, budżet docelowy, prognozy i
  readiness bez osobnego typed źródła. Live smoke zwrócił 2 poprawne actions i
  4 landing candidates; focused context/eval tests 15 passed.
- Ads account currency nie wybiera już pierwszego kodu przy niespójnym evidence:
  wiele walut daje typed `account_currency_consistency` blocker. Falsifier
  mixed-currency przeszedł; agregacja okien i summary limits pozostaje osobnym
  zadaniem.
- `AdsAggregationContract` domyka ten osobny seam: API, shared schema i panel
  marketera pokazują `LAST_7_DAYS`, okna search terms 30/90 dni, limit skrótu,
  returned/available rows, `is_exhaustive`, podstawę pacingu, status waluty i
  caveaty. Live summary: 18 kampanii dostępnych, 5 pokazanych, 50 wierszy
  search-term z bounded read. Full Ads contract suite i dashboard typecheck
  przechodzą.
- Cross-source landing identity nie traci już trendu na ścieżce contentowej:
  `list_metric_facts_for_content_url` filtruje identity przed bounded read,
  liczy identity-partitioned LAG i zwraca `previous_value`, delta oraz trend;
  stare legacy URL-e są normalizowane, a mieszane wymiary nadal odpadają przed
  limitem operatora. Metric-store suite 16/16 i focused outsourcing proof
  przechodzą.
- Niezależny second-opinion znalazł i wymusił dodatkową korektę: legacy/noisy
  URL nie może uczestniczyć w historii przed Pythonowym filtrem identity. SQL
  zwraca kandydatów bez LAG, a historia jest liczona dopiero po
  `metric_dimensions_match_landing`; interloper proof pokazuje exact row po
  błędnym nowszym wierszu i zachowuje poprzedni exact evidence. Finding został
  zapisany w Beadzie; wcześniejszy checker nie jest przedstawiany jako PASS.

### 2026-07-18 — source quality w planning input v5

- `ContentPlanningSourceAssessment` niesie teraz `refresh_run_id`, exact
  `covered_window`, `settlement_state`, `quality_state` i caveats. Pola są
  projektowane z `ContentFreshnessAssessment`, więc należą do wejścia planu,
  summary i digestu, a nie tylko do panelu konektora.
- Zmieniono schema name z `wilq_content_planning_input_v4` na
  `wilq_content_planning_input_v5`; zmiana jakości (np. GSC partial → verified)
  zmienia `planning_input_digest` i nie może przejść jako idempotentny stary plan.
- Falsifier `test_source_quality_is_part_of_planning_lineage_and_digest` pokazał
  readback pól oraz różne digesty po zmianie quality state. Input/planning tests
  8/8, Ruff i diff-check zielone.
- Po restarcie managed stack live snapshot BDO zwrócił nowe pola jakości w
  `freshness_assessment`; API zachowało 133895 faktów i 4855 refreshów.
- `ConnectorCoveredWindow` niesie dodatkowo `cadence`, `snapshot_date`,
  `coverage_scope` i `coverage_count`: Ahrefs jest jawnie manualnym
  `manual_lag_1_snapshot` bez zgadywania daty vendora, a Localo ma
  `trailing_30_days` i liczbę aktywnych miejsc.
- Shared schema oraz `/content-workflow` pokazują nieblokujące ostrzeżenie
  jakości (np. GA4 do rozliczenia, GSC częściowy odczyt) nawet przy świeżym
  źródle. Dashboard focused test 2/2 i typecheck przechodzą.
### 2026-07-18 — naprawa wejścia z pełnego inventory do workflow

Reprodukowalny błąd ścieżki marketera został naprawiony na granicy API:
`POST /api/content/inventory/bind` zwracał poprawny `work_item_id`, ale
następny `GET /api/content/work-items/queue?work_item_id=...` budował kartę z
`read_material=False`. Każdy nowy adres z inventory wyglądał więc jak
`block`, mimo że materiał WordPress był dostępny; dashboard sprawiał wrażenie,
że tylko odświeża stronę. Wybrany adres teraz czyta ten sam materiał
read-only, który został zweryfikowany przy bindzie, bez uruchamiania pełnej
diagnostyki. Focused falsifier sprawdza `read_material=True` i brak pełnego
diagnostics; live odczyt dla `content_work_item_inventory_0454c020b0ddbad0062b3d08`
zwrócił `recommended_mode=refresh` zamiast `block` po restarcie stacka.
### 2026-07-18 — comparison periods visible in the marketer journey

The selected-page context now renders the exact comparison status/reason from
the queue search-metrics contract. When two complete periods exist it shows
their date range; otherwise it explicitly says that no trend is inferred.
This keeps the useful metric snapshot above the fold while preventing a single
period from being read as growth or decline. Proof: dashboard typecheck and
`ContentWorkflowSurface.test.tsx` (30 tests) pass.
### 2026-07-18 — bounded coverage for Ads search terms

Search-term-derived Ads decisions now carry one typed coverage contract: exact
window, returned rows, connector cap, whether the cap was hit, bounded/empty/
blocked status and Google's low-volume privacy omission caveat. The 30-day
read is explicitly capped at 50 rows; the 90-day safety read remains capped at
200. The contract propagates to n-grams, review summaries and negative-keyword
review, and the dashboard shows the coverage above detail tables. No claim of
complete search-term universe is made. Focused Ads contracts, shared schema,
dashboard typecheck/tests and Ruff pass.
### 2026-07-18 — WordPress sitemap coverage is explicit

The WordPress inventory connector now retains source sitemap count, returned
count, truncation and the 500-URL limit in its typed refresh metric summary.
This distinguishes a complete read from a bounded inventory without exposing
raw content or credentials. Existing vendor-read and inventory contract tests
(15) pass.
### 2026-07-18 — inventory coverage reaches the marketer catalog

`ContentInventoryCatalogResponse` now exposes the latest WordPress sitemap
coverage. The dashboard shows returned/source counts and a caveat; historical
refreshes without the new counters remain `coverage niepotwierdzone`, never
implicitly complete.

### 2026-07-19 — GA4 landing facts carry host-bound identity

GA4 behavior reads now request `hostName` alongside
`landingPagePlusQueryString`, source and campaign. The canonical metric seam
combines a GA4 path with that host into an exact landing identity; a path
without host remains `path_only` and is not promoted to an exact match. This
prevents cross-host joins while allowing fresh GA4 facts to participate in
the existing metric-store and publication-bound measurement loop. Focused
vendor and identity proof: 3/3, Ruff and diff-check pass. No vendor write or
storage migration was performed.

### 2026-07-19 — content workflow exposes the full evidenced page queue

The content diagnostics builder no longer truncates the ranked decision queue
to five rows before `/api/content/work-items/queue`. Ranking is preserved, but
every evidenced GSC/WordPress page decision is now available to the marketer;
the live queue grew from 5 to 54 candidates (53 actionable) without creating
synthetic topics. A focused regression proves all seven ranked pages survive
the builder, and the live API confirms the expanded page inventory. No model
call, vendor write or approval is implied.

The selected-decision follow-up now has a real resolver-through-catalog API
falsifier; it forbids the full diagnostics builder while using the canonical
BDO decision work-item ID. A local timing probe measured the cached catalog at
0.319s versus 2.682s for the full diagnostics build (same process, same local
state), so the fast path has a measured cost boundary rather than an implicit
latency claim. Cold external refresh and all non-inventory IDs remain outside
this proof.

### 2026-07-19 — one planning turn per page/service

Planning generation is now serialized by `(work_item_id, service_card_id)`,
not only by the exact input digest. A fresh metrics or inventory digest cannot
start a sibling Codex turn while another generation is queued; the API returns
`runtime_blocked` with the active run ID and a five-second retry hint. Exact
same-input requests remain idempotent, stale jobs remain retryable, and
terminal proposal history is unchanged. Focused store and API falsifiers,
Python typecheck/Ruff, and shared-schema typecheck/tests pass.

### 2026-07-19 — selected diagnostics pages use the catalog fast path

The selected queue endpoint now resolves the canonical diagnostics work-item
key from the same WordPress inventory catalog used for inventory binding. It
returns one typed candidate for an existing page without rebuilding the full
54-item diagnostics queue; ambiguous bounded-slug matches are refused instead
of opening the wrong page. Focused queue/catalog falsifiers pass, and the live
BDO decision URL returns `candidate_count=1` with no model call or vendor write.

### 2026-07-19 — live BDO planning retry ends as a typed runtime blocker

The current BDO input digest `35497582…` was submitted through the canonical
planning POST with `requested_by=operator_local_dashboard`. The API returned
`generating` immediately, then persisted `runtime_failed` with source code
`codex_timeout` after the bounded 180-second app-server deadline. No proposal,
revision or WordPress write was created; subsequent GET returns the durable
failed state and its retry step. This is an honest app-server/runtime blocker,
not a planning or content-quality PASS. The next retry requires runtime health
evidence, not a client-side fallback or a second parallel model path.

Additional transport diagnosis: a native Codex 0.144.6 probe answered the
`initialize` JSON-RPC request, while debug stderr showed repeated online model
catalog refreshes and a `failed to refresh available models` timeout before a
turn could start. The same isolated client then timed out even for a tiny
structured request. This identifies the current external/runtime seam as
model-catalog/network startup, not WILQ prompt size or planning digest logic.

### 2026-07-19 — isolated provider compatibility fixed, runtime still unproven

Commit `57f6e216` carries only the selected model and non-secret provider fields
into the isolated Codex app-server command, keeps the copied login available
through thread/turn lifetime, and propagates the model returned by
`thread/start` into `turn/start`. Focused transport pytest, Ruff and mypy pass.
The real isolated structured-turn probe still ended in typed `codex_timeout`
after 90 seconds, so this is a compatibility attempt rather than a successful
runtime proof. The BDO planning retry remains blocked; no proposal, revision or
vendor write was created.

The independent Claude checker pass
`~/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-codex-provider-runtime-GAxNxh`
was schema-validated. It returned no line-cited findings but recorded eight
evidence gaps, chiefly the missing completion proof and insufficient evidence
that the installed provider path works end to end. Its disposition explicitly
does not claim PASS or UAT.

### 2026-07-19 — transient provider reconnects remain an honest runtime failure

The app-server now ignores only `error` events explicitly marked
`willRetry=true`, allowing Codex's own reconnect loop to reach the terminal
`turn/completed` event. A focused fake-transport falsifier covers that seam;
transport pytest, Ruff and mypy pass (`64428c29`). The live tiny structured
turn now reaches the turn and waits through reconnects, then returns typed
`codex_turn_failed` after roughly 42 seconds. Native stderr identifies the
upstream response stream as disconnected and reports temporary high demand;
this is not a WILQ prompt or digest failure. Planning remains blocked until a
successful or otherwise diagnosable provider response is available; no
fallback model, vendor write or approval was introduced.

### 2026-07-19 — current API context and diagnostic blocker contract

Live WILQ context is reachable: 12 connectors, 9 configured and 2 missing
credentials; the content queue contains 54 evidenced candidates, 53
actionable. GA4, Ads and Ahrefs diagnostics report fresh configured reads. The
approved knowledge corpus remains `import_pending` (7/15 materials), so
generation is correctly blocked until the remaining controlled import/owner
review. BDO's snapshot dynamically resolves 12 `the_content` headings, 842
words and no ACF/flexible-content sections; the source note explicitly says
not to invent an editor layout.

Commit `de9cbf32` adds a secret-safe typed category for structured
`responseStreamDisconnected` errors and a focused falsifier. The live provider
still returns generic `codex_turn_failed` after its reconnect loop, so no
successful plan is claimed. Independent checker pass
`~/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-codex-error-classification-rDkEz8`
is schema-valid; its line-1 findings were rejected as source-omission
artifacts and its evidence gaps are retained in the disposition.

### 2026-07-19 — candidate picker now shows decision meat

Commit `ff8fc09f` adds an evidence summary to each content candidate card:
exact impressions, clicks, API-provided CTR, primary query and available page
section count. Sparse candidates receive a neutral missing-data message; no
score, forecast, approval or performance claim is added. Focused dashboard
Vitest (2) and TypeScript typecheck pass. Checker pass
`~/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-marketer-candidate-evidence-ui-VHdFNR`
is schema-valid; its line-1 findings were rejected as source-omission
artifacts and the disposition preserves the evidence limits.

### 2026-07-19 — pre-plan query mapping uses current page inventory

Commit `28d93d26` adds a generic fallback for GSC demand mapping: when a new
draft package has no matching evidence IDs yet, WILQ compares the query against
the exact current WordPress inventory headings supplied by snapshot assembly.
ACF and `the_content` use the same path; ambiguous or unmatched terms remain
`page_only`. Focused demand/dynamic-input tests (22), Ruff and mypy pass. Live
BDO smoke confirms no forced mapping for its broad `bdo co to` terms.

Checker pass
`~/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-content-inventory-demand-mapping-GYvpUL`
is schema-valid. Five low-severity findings are retained as confirmations,
not defects; four evidence gaps remain explicit. This does not prove model
planning or UAT.

### 2026-07-19 — blocker korpusu pokazuje bezpieczny manifest materiałów

`/content-workflow` korzysta teraz z istniejącego metadata-only endpointu
`/api/knowledge/source-materials`. Gdy korpus jest niegotowy, marketer może
rozwinąć listę tytułów i statusów materiałów oczekujących na import/review;
raw treść oraz `source_path` nie są renderowane. Zmieniony kontrakt nie dodaje
drugiego źródła prawdy ani nie odblokowuje generowania bez gotowego korpusu.
Focused proof: `ContentWorkflowSurface` 34 testy oraz dashboard typecheck.
Niezależny checker i disposition dla tego fixed pointu pozostają do wykonania.

Checker retry dla `f60c7f84` przeszedł walidację schematu i zwrócił pustą
tablicę findings. Pięć zgłoszonych `evidence_gaps` wynika z briefu bez
cytowanych linii, nie jest defektem produktu; zostały zachowane w
`disposition.md`. Pierwszy pass zakończył się błędem transportu bez JSON i nie
został użyty jako wynik.

### 2026-07-19 — kontekst decyzji pokazuje źródła i świeżość metryk

Rozwijane `Dlaczego ta decyzja?` w wybranym workflow pokazuje teraz nazwy
źródeł metryk oraz API-owy stan świeżości danych. Nie dodaje własnych obliczeń,
trendów ani technicznych evidence ID do głównego widoku; brak źródeł jest
jawny. Proof: `ContentWorkflowSurface` 34 testy i dashboard typecheck.
Commit oraz niezależny checker dla tego fixed pointu są jeszcze do wykonania.

Checker dla `0a9e53a4` przeszedł walidację schematu. Zwrócił dwa MEDIUM jako
braki dostarczonego źródła (runner przekazał zakresy bez literalnych linii),
więc oba zostały `reject_with_evidence` w disposition; ograniczenia upstreamu
i UAT pozostają jawne.

Szeroki audyt `scripts/dashboard_usefulness_audit.py --api-base
http://127.0.0.1:8000` po zmianie: 14 powierzchni, 11 `demo_ready`, 2
`review_ready`, 1 jawnie zablokowana (Demand Gen), 0 produkcyjnych failures,
minimum usefulness score 7. Raport nadal wskazuje brak private-source review
queue na większości powierzchni jako metadata audytu; nie zmieniam tego w
fałszywy blocker dla bieżącego slice'u.

Read-only cross-source pilot na dwóch exact work itemach użył tego samego
kontraktu `planning-proposals`: BDO wiąże kartę
`ekologus_service_bdo_reporting`, outsourcing wiąże
`ekologus_service_environmental_consulting_outsourcing`; oba mają exact
WordPress/GSC, 7 source-material IDs i ten sam pełny zestaw 10 ocen źródeł.
Brak exact GA4/Ahrefs, Ads i Keyword Planner pozostaje jawnie `missing` lub
`not_applicable` — bez zgadywania. Outsourcing ma istniejący proposal, ale
status `stale`; BDO ma `failed` z istniejącym typed provider blockerem i bez
proposal. To dowodzi wspólnego mapowania i granic dowodu, nie pełnej generacji
tekstu ani UAT.

Ujednolicono też klucz React Query dla gotowości korpusu między głównym
workflow i panelem generowania. Ten sam endpoint ma teraz wspólny cache i nie
tworzy dwóch niezależnych odczytów ani rozjechanych blockerów. Proof:
`ContentPlanningGenerationPanel` 3 testy i dashboard typecheck.

Checker dla `eb0bb331` przeszedł walidację schematu bez findings. Zgłoszone
evidence gaps dotyczyły wyłącznie braku literalnych linii w transporcie; lokalna
disposition potwierdza identyczny klucz w obu deklaracjach. Nie rozszerzamy
tego proofu na poprawność upstream freshness ani wszystkie scenariusze mountu.

Nowy niemutujący provider health probe (`StdioCodexAppServerClient`, 75 s,
minimalny schema-only turn) ponownie zakończył się `codex_turn_failed` po
utworzeniu thread/turn; nie było external tool call ani outputu. Nie zapisano
planu, rewizji ani vendor action. To aktualizuje blocker runtime, ale nie
unieważnia ukończonych kontraktów API/UI.

Naprawiono retry failed planning run: gdy API zachowuje exact
`service_card_id` i `planning_input_digest`, ale nie ma `proposal` po błędzie
Codexa, panel pokazuje ponownie „Wygeneruj plan”. Nie zmienia to bramki
pierwszego uruchomienia — nadal wymaga human-confirmed service selection.
Focused proof: `ContentPlanningGenerationPanel` 4 testy i dashboard typecheck.

Checker dla `e8727eeb` przeszedł walidację i zwrócił trzy LOW confirmations,
bez defektu do naprawy. Disposition zachowuje granice: retry nie dowodzi
akceptacji API ani sukcesu providera; pierwsza generacja nadal wymaga decyzji
człowieka.

### 2026-07-19 — typed failure zachowuje exact input retry

Focused falsifier ujawnił, że błąd submitu do executora zwracał
`planning_input_digest: null`, mimo że request miał exact digest. Pierwsza próba
testu zakończyła się więc poprawnie czerwono. Naprawa obejmuje zarówno
natychmiastowy failure route, jak i wyjątek workera: odpowiedź typed `failed`
odtwarza z bieżącego snapshotu pełny `input_summary` oraz zachowuje
`service_card_id` i digest, a jeśli snapshot nie daje bezpiecznego summary,
nie emituje częściowego digestu. Dzięki temu panel może bezpiecznie retryować
ten sam wybór bez udawania gotowego planu i bez zapisu proposal/revision.
Proof: `uv run pytest -q tests/content/test_dynamic_planning_proposals_api.py
-k executor_submission_failure_is_typed_and_retryable` (1 passed) oraz Ruff
dla zmienionego routera i testu. Provider Codex pozostaje niezależnym blockerem.

Second-opinion checker dla tego fixed pointu nie został przedstawiony jako
PASS: dwa świeże, osobne passy zostały odrzucone przez walidator za cytacje
Claude'a przekraczające 20 linii (F4, następnie F3). Disposition i ścieżki obu
prób są zachowane poza repozytorium; brak retained findings. Szerszy run całego
pliku ujawnił dwa niezwiązane expectation failures (test starego timeoutu 120 s
przy produkcyjnym 180 s oraz fixture quality-gate bez CTA) i został przerwany;
nie przypisuję ich temu slice'owi.

### 2026-07-19 — świeży exact pilot i synchronizacja kontraktu testowego

Z `/api/marketing/brief` pobrano świeży kontekst: 12 connectorów, 9
skonfigurowanych i 2 bez credentials. Oba exact work itemy zostały ponownie
uruchomione przez kanoniczny `planning-proposals` POST na bieżących digestach.
Oba zakończyły się tym samym typed blockerem `runtime_failed/codex_turn_failed`
po utworzeniu thread/turn; `external_call_attempted=false`, proposal/revision
nie powstały i nie było vendor write. To potwierdza aktualny blocker providera,
nie problem mapowania BDO/outsourcing.

Naprawiono dwa ujawnione przez pełniejszy run rozjazdy testowego kontraktu:
domyślny planning timeout testuje obecne 180 sekund, a fixture sprawdzający
hałaśliwe nagłówki zawiera neutralny CTA, więc test nie miesza brakującego CTA z
celem testu. Focused proof obu testów, Ruff i `git diff --check` przechodzą.

### 2026-07-19 — runtime blocker ma operator-facing next step

Znane, bezpieczne kody app-servera są teraz mapowane w planowaniu na konkretny
polski blocker: przerwany `codex_response_stream_disconnected` mówi o zerwanym
strumieniu i sprawdzeniu połączenia, a `codex_timeout` o przekroczeniu
ograniczonego okna. Nie pokazujemy surowego payloadu providera i nie zmieniamy
statusu `failed`, lineage ani zasad retry. Inne kody zachowują dotychczasowy
generic fallback. Focused proof: test mapowania stream failure, timeout
contract i heading-quality fixture (3 passed), Ruff oraz `git diff --check`.

Checker retry dla `0409b4bf` jest schema-valid. Zwrócił cztery LOW/MEDIUM
uwagi będące brakami literalnej ekspozycji kodu dla tool-free reviewera, nie
udowodnionymi defektami; wszystkie zostały `reject_with_evidence` w
disposition. Dwie decyzje — finalne brzmienie po polsku i kompletność przyszłej
allowlisty kodów — pozostają jawnie human-only. Nie claimuję PASS, provider
recovery ani UAT.

Świeży single-case BDO probe po tym slice'ie przeszedł przez aktualny digest,
thread i turn, po czym zakończył się `runtime_failed/codex_turn_failed`.
Odpowiedź zachowała typed blocker, `external_call_attempted=false`, brak
proposal/revision i brak vendor write. Runtime zwrócił kod generic, więc
operator dostał poprawny generic fallback; mapowania stream/timeout pozostają
gotowe dla odpowiadających kodów providera.

W panelu generowania planu techniczny `source_codes` blokera jest teraz ukryty
poniżej w rozwijanym „Dlaczego”, bez zaśmiecania pierwszego widoku marketera.
To daje supportowi dokładny ślad (`codex_*`) przy zachowaniu polskiego labelu i
następnego kroku na wierzchu. Proof: `ContentPlanningGenerationPanel` 4/4 oraz
dashboard `tsc --noEmit`.

### 2026-07-19 — audyt wyboru stron i kontraktu Ads

Sprawdzono aktualny `/content-workflow`: picker nie ma literalnego wyboru BDO,
korzysta z API-owej kolejki kandydatów i pozwala przełączać dostępne work itemy;
strona oraz sekcja są wybierane przez `work_item_id`/`section_heading` w URL.
Nie znaleziono regresji hardkodującej temat ani usuwającej katalog stron, więc
nie wprowadzono pozornej zmiany UI.

Live queue potwierdza 54 kandydatów: 53 `refresh` i 1 jawnie `block`; blokowany
rekord Ahrefs jest widoczny w kolejce z powodem, a BDO i inne istniejące URL-e
mają osobne tytuły, metryki, usługi i tryb odświeżenia.

Na żywym API przeszedł też `wilq-ads-doctor/scripts/smoke_skill_contract.py`.
Wszystkie 21 modułów Ads ma rzeczywiste importy z entrypointu/orchestratora i
chroni odrębne kontrakty; brak bezpiecznej redundancji do kasowania bez
przenoszenia logiki. Zadanie cleanup pozostaje otwarte, ale nie redukujemy
liczby plików kosztem czytelności i ochrony ryzyk.
