# WILQ Progress Ledger

Ostatnia aktualizacja: 2026-07-19.

To jest krótki stan bieżący. Historia zmian i proofów pozostaje w git, Beads
i lokalnych katalogach `.local-lab/proof/`; ten plik nie jest kroniką.

## Aktywny kierunek

- 2026-07-20: dynamiczny planner przestał streszczać zatwierdzony profil usługi
  generycznym komunikatem. Gdy karta wskazuje zatwierdzony `source_fact_id`,
  input bierze rzeczywisty approved `extracted_fact`, connector, evidence i
  lineage z rejestru WILQ; fallback pozostaje tylko dla starszych/syntetycznych
  identyfikatorów. BDO/outsourcing używają tego samego mechanizmu, bez wyjątku
  URL. Focused source-fact planning proof 2/2 i Ruff przechodzą.

- 2026-07-20: Sales Brief nie przypina już do enrichmentu lineage
  `source_fact_ids` z faktów innych niż `approved`. To chroni dynamiczny input
  przed oznaczeniem materiału `review_required` jako użytego tylko dlatego, że
  dzieli evidence z zatwierdzonym faktem. Publiczny falsifier briefu przechodzi;
  nie zmienia to treści ani statusu owner-review materiałów.

- 2026-07-20: panel planowania pokazuje teraz ograniczone, lineage-preserving
  użytych faktów źródłowych, wraz z connectorem oraz licznikami materiałów i
  evidence. Dane pochodzą z tego samego `ContentPlanningInput` i digestu co
  plan; nie są to surowe prywatne materiały ani wymyślone tezy. Dla starszych
  odpowiedzi pole jest opcjonalne, więc readback pozostaje kompatybilny.
  Focused dashboard test 7/7, typecheck, shared-schema test i Python input
  proof przechodzą.

- 2026-07-19: exact reviewed-service Ads read/review pilot został zamknięty.
  Świeży odczyt ma 21 bounded rows/30 dni i 200 rows/90 dni; 9 wierszy wiąże
  kartę `ekologus_service_environmental_consulting_outsourcing` przez exact
  inventory binding. Decyzja ma evidence i action IDs, a marketer ma
  review-only handoff do natywnego Google Ads przez campaign/ad-group/search
  term identifiers. Mixed safety queue pozostaje `blocked` do czasu pełnego
  90-dniowego pokrycia; Keyword Planner i realne UAT nie są zamknięte.
  Bead `wilq-seo-v9ab.17.7` zamknięty bez vendor write.

- 2026-07-19: zamknięto dwa cross-source seamy po audycie fixed pointu.
  Wspólny `LandingPageIdentity` rozróżnia exact, tracking-only, host-alias,
  functional-query, ambiguous, missing i no-match; metric store filtruje tę
  tożsamość przed limitem i historią. Planning source assessments przenoszą
  match tier/status, a Ads hash-only landing join i oba piloty używają tego
  samego kontraktu. Publication-bound aggregate przyjmuje tylko exact URL +
  exact period GSC/GA4; wrong period, query/detail, ambiguous lineage i
  insufficient quality zostają wykluczone z typed reason/evidence. Focused
  cross-source suites: 24 testy; Beads `wilq-seo-v9ab.18.2` i
  `wilq-seo-1oa.36.20` zamknięte. To nie jest dowód publikacji, outcome ani UAT.

- 2026-07-19: live Ads smoke ujawnił niespójność w mixed negative-keyword
  queue. Kontrakt miał `status=ready`, mimo że część z 12 kandydatów nie miała
  dokładnego 90-dniowego wiersza bezpieczeństwa, więc nie było bezpiecznego
  `payload_preview` ani akcji do review. API teraz fail-closed oznacza całą
  kolejkę jako `blocked`, zostawia kandydaty i ich statusy do diagnozy, ale
  usuwa preview/akcje oraz dodaje `90_day_safety_check`. Focused testy
  negative-keyword 3/3, Ruff, mypy i live Ads smoke przechodzą.

- 2026-07-19: świeży Ads pilot ma exact reviewed service binding. Read-only
  refresh `refresh_google_ads_51d766262b25` jest świeży i zwraca
  `live_data_available=true`. Kanoniczna kolejka `ads_review_search_terms` ma
  21 wierszy w bounded oknie 30 dni oraz 200 wierszy bezpieczeństwa z 90 dni;
  9 wierszy ma status `approved_current` dla karty
  `ekologus_service_environmental_consulting_outsourcing` i inventory work
  itemu `content_work_item_inventory_6caeaa2acb57bd46d278ca73`. Ta sama
  decyzja ma akcje `act_prepare_custom_segments_from_search_terms` i
  `act_prepare_negative_keyword_review_queue`; obie walidacje zwróciły
  `valid`. Nie ma żadnego vendor write. Keyword Planner pozostaje typowanym
  blockerem `DEVELOPER_TOKEN_NOT_APPROVED`, a native Google Ads handoff i
  realne UAT nadal czekają na człowieka. Bead `wilq-seo-v9ab.17.7` pozostaje
  otwarty.

- 2026-07-19: dynamiczna mapa briefu odrzuca teraz datowane testimonial/case
  rows (np. nazwa klienta z `[2013 r.]`) przed wyznaczeniem kierunków H2. Reguła
  działa po wzorcu roku, nie po nazwie klienta; live 0454 nie pokazuje już SERTOP
  jako sekcji do napisania. Fixed point `19e5fe05` ma 5 focused testów, Ruff i
  diff-check; checker został odrzucony przez cytację ponad 20 linii i zapisany
  jako evidence gap.
- 2026-07-19: usunięto fałszywy blocker productowy w briefie: słowa z
  zapytań/faktów GSC nie są już traktowane jako CTA zakupowe. Produktowy guard
  patrzy wyłącznie na temat, URL i deklarowany CTA; jawne „kup sorbent” nadal
  wymaga Merchant/sklepu. Live inventory `0454...` (edukacyjny artykuł o
  opakowaniach) ma teraz pustą listę blockerów Sales Brief i zatrzymuje się
  dopiero na decyzji zakresu. Fixed point `b830ec5a` przeszedł 4 focused testy,
  Ruff, mypy, diff-check i live snapshot. Checker został odrzucony przez
  nielegalną cytację ponad 20 linii; nie traktuję go jako PASS.
- 2026-07-19: naprawiono realny błąd wyboru strony: inventory ID
  `content_work_item_inventory_*` mogło otworzyć snapshot, ale następne
  zapytanie enrichment szukało wyłącznie canonicalnego
  `content_decision_*` i zwracało `missing_work_item`. API rozwiązuje teraz
  alias przez ten sam evidence-bound inventory binding, a queue przekazuje
  selected ID do enrichment. Live URL `0454c020b0ddbad0062b3d08` zwrócił
  enrichment z `inventory_0454...`, bez blokera, w 2,29 s. Fixed point
  `2b9ed1a6` przeszedł 6 focused testów, Ruff, mypy i diff-check; bounded
  second-opinion ma ważny schema output, ale jego trzy findingi sklasyfikowano
  jako evidence gap/follow-up. To naprawia przepływ wyboru strony, nie odblokowuje
  automatycznie usługi ani generowania tekstu.
- 2026-07-19: realny re-run planowania dla aliasu inventory
  `content_work_item_inventory_0454c020b0ddbad0062b3d08` przeszedł do `ready`
  po dynamicznej normalizacji mapy. Planner użył digestu
  `f06c4b2aff00adc8f9e5c8d5af6812a0268a09fc66ef03c24e001d008de82577`;
  wszystkie 12 wierszy inventory ma jawny wynik, a ogon po sekcji „Może Cię
  również zainteresować” jest deterministycznie traktowany jako
  `navigation_or_promotional_inventory`, nawet gdy model próbuje go ponownie
  przypisać. Zmiana polityki mapowania unieważnia poprzedni proposal (`stale`),
  a świadomy re-run utworzył
  `content_planning_proposal_b271ade8deff47f6980fb9cbb11b0c62`. Live API zwraca
  `ready`, `blockers=[]`, `publish_ready=false`; nadal nie jest to zgoda
  człowieka ani draft WordPress.
- Niezależny checker tego fixed pointu został uruchomiony w pass
  `2026-07-19-dynamic-footer-mapping-pbUJxT`, ale runner odrzucił wynik przez
  cytację F1 ponad limit 20 linii. Pass ma `evidence_gap`; nie przedstawiam go
  jako PASS ani approval i nie zmieniam kodu na podstawie niewalidowanego
  findingu.
- 2026-07-19: dynamiczny odczyt WordPress rozróżnia teraz strukturę ACF od
  `the_content` także wtedy, gdy materiał przychodzi przez REST. Parser zapisuje
  H2/H3 z REST-owego HTML, a binding preferuje sekcje ACF i dopiero potem
  nagłówki treści głównej. Dzięki temu mapa sekcji nie zależy od ręcznego
  wpisywania nagłówków ani od jednego typu szablonu. Fixed point `8fed2b67`
  przeszedł 4 focused testy inventory, Ruff, mypy i diff-check; drugi-opinion
  checker został odrzucony lokalnie, bo dwukrotnie zwrócił cytację ponad limit
  20 linii. To naprawa mechanizmu odczytu, nie dowód UAT ani jakości generowanego
  tekstu.
- 2026-07-19: cross-source planning snapshot zachowuje dokładne fakty GA4 i
  inne nie-GSC/Ads fakty po projekcji exact-demand oraz przy scalaniu selected
  inventory. Live URL `/szkolenie/gospodarka-odpadami-i-opakowaniami-
  kompendium-wiedzy-dla-przedsiebiorcow/` ma 11 exact Ads rows, świeży wspólny
  evidence i metryki kliknięć/kosztu, ale pozostaje `review_required`, bo
  dopasowana karta usługi nie ma `approved_current`. Landing outsourcingu ma
  GSC exact, lecz Ads `not_exactly_mapped` i brak exact GA4; WILQ nie dopisuje
  tych źródeł przez podobieństwo tekstu. Focused proof fixed pointów
  `772b262d`/`251f215f` przeszedł Ruff, mypy, diff-check i live snapshot;
  second-opinion findings zostały sklasyfikowane z lokalnym dowodem. To jest
  postęp exact landing-alignment, nie UAT ani gotowość do draftu.
- 2026-07-19: Ads source assessment pokazuje teraz marketerowi właściwy
  blocker zamiast ogólnego błędu: exact landing z `review_required` mówi o
  owner review karty, a `unbound`/`ambiguous` o nierozstrzygniętym powiązaniu
  inventory/service. Wszystkie trzy stany pozostają fail-closed. Focused
  3-case proof przeszedł; checker retry zwrócił `findings=[]`. To poprawa
  decyzji i następnego kroku, nie automatyczna akceptacja usługi.
- 2026-07-19: brak exact term→landing→service dla Ads ma teraz status
  `missing`, a nie `not_applicable`; źródła naprawdę nieadekwatne do strony
  (Merchant/Localo/Social) zachowują `not_applicable`. Live outsourcing
  zwraca `missing` bez evidence IDs. To rozróżnia „oceniono, ale brak dowodu”
  od „źródło nie dotyczy” bez zmiany fail-closed policy.
- 2026-07-19: read-only Ads pilot pobrany przez kanoniczne
  `/api/ads/diagnostics`: świeży odczyt (`live_data_available=true`), 18 kampanii,
  23 wiersze zapytań, 12 kandydatów wykluczeń z 90-dniowym kontekstem, 9 akcji
  review-only i 1 blocker. API jawnie blokuje ocenę opłacalności, CPA/ROAS,
  skalowanie i zapis zmian bez brakujących kontraktów/człowieka. To jest dowód
  konektora i kolejki decyzji, nie ukończony exact-service pilot ani UAT.
- 2026-07-19: świeży read-only GA4 cross-source odczyt ma status `fresh` (28,7 h
  przy progu 48 h), 8 dowodów źródłowych i 1 akcję review. API rozdziela 1
  problem pomiaru `(not set)`, 2 brakujące strony WordPress i 2 czytelne wiersze
  ruchu; konwersje, przychód, ROAS, atrybucja i naprawa pomiaru pozostają
  `review_required`. To dowód jakości kontraktu, nie wynik biznesowy ani UAT.
- 2026-07-19: `/api/content/diagnostics` potwierdza 53 istniejące URL-e
  WordPress i 54 decyzje contentowe z 15 dowodami; BDO jest typem
  `refresh_or_merge` (266 wyświetleń, 1 kliknięcie, CTR 0,38%, średnia pozycja
  8,50), a nie nowym tematem. API wymaga sprawdzenia aktualnych sekcji i CTA
  przed rewrite/scaleniem; Ahrefs ma 7 pasujących rekordów, 42 do ręcznej oceny
  i 68 poza zakresem. To jest realny content queue, nie automatyczna decyzja
  publikacyjna.
- 2026-07-19: kanoniczny `/api/marketing/daily-check` po zakończeniu prewarmu
  scala 7 źródeł marketingowych, 18 evidence IDs i 8 reguł eksperckich. Zwraca
  3 bezpieczne kolejki review (Merchant, content/GSC/WordPress/Ahrefs/GA4,
  Ads) oraz 1 typed blocker jakości pomiaru GA4; `do_not_touch` jawnie blokuje
  write/publish bez preview → review → confirm → audit. Pierwszy odczyt w trakcie
  prewarmu zwracał `daily_check_runtime_prewarm`, a retry przechodzi do pełnego
  kontraktu — to ważny stan przejściowy, nie błąd maskowany jako gotowość.
- 2026-07-19: `POST /api/codex/context-pack` dla `wilq-content-operator`
  zwraca API-owned context: 12 konektorów, 9 statusów, 24 evidence summaries,
  8 knowledge-card summaries, 8 expert-rule summaries, 29 capability entries,
  18 aktywnych ActionObjects i brief z 19 evidence IDs. Strict instruction
  wymusza odczyt metryk z WILQ API; kompaktowanie oznacza pominięcie historii,
  nie utratę kontraktu. To dowód seam-u Codex → API, nie dowód jakości tekstu.
- 2026-07-19: pierwszy content-operator context-pack trwał 5,926 s przy
  pięciosekundowym cache, więc domyślny TTL API-owned skill context został
  wydłużony do 300 s. Env override, freshness connectorów i invalidacja po
  refresh/write pozostają bez zmian. Focused kontrakt cache + Ruff przechodzą;
  to nie jest dowód produkcyjnej wydajności.
- 2026-07-19: po `scripts/local_stack.sh restart` i 5 s startupu pierwszy
  content-operator context-pack trwał 1,873 s, a kolejny 0,081 s; oba zachowały
  24 evidence summaries, 19 brief evidence IDs i strict instruction o metrykach
  z WILQ API. API i dashboard pozostały `ready`. To lokalny runtime proof,
  nie produkcyjny SLA ani UAT.
- 2026-07-19: live inventory material potwierdza dynamiczny fallback WordPress:
  BDO i news w `the_content` mają status `ready`, odpowiednio 812 i 826 słów,
  tytuł, nagłówki, evidence `ev_refresh_refresh_wordpress_ekologus_ff4e784ddded`
  oraz lineage `public_html.main_or_article`; ACF pozostaje puste, bez
  zgadywania sekcji. To realny dowód `the_content` path, nie dowód każdego
  wariantu ACF ani UAT.
- 2026-07-19: read-only piloty Merchant/Localo są gotowe do review. Merchant
  ma świeżość 21,6 h/48 h, 1351 zgłoszonych wystąpień problemów, 6 decyzji,
  11 klastrów, 4 evidence IDs i 1 akcję; API jawnie odróżnia wystąpienia od
  unikalnych SKU i nie obiecuje naprawy/przychodu. Localo ma 31 faktów, 2
  evidence IDs, 1 akcję i gotowe agregaty miejsc, rankingów, GBP, konkurencji i
  opinii; `local_tasks` pozostaje brakującym kontraktem, a write/publish GBP i
  wzrost widoczności są zablokowane.
- 2026-07-19: szeroki `scripts/verify.sh` nie jest zielony: Ruff zgłosił 29
  istniejących błędów (głównie E501/UP017/I001) w testach inventory/Ads oraz
  modułach `wilq/connectors/wordpress/client.py`,
  `wilq/content/handoff/wordpress_authoring.py` i
  `wilq/content/workflow/store_measurement.py`. Żaden z tych plików nie był
  częścią ostatniego cache/runtime slice; nie poprawiam masowo niezwiązanej
  powierzchni. Release gate pozostaje otwarty i nie claimujemy PASS.
- 2026-07-19: po mechanicznym formatowaniu wyłącznie trzech śledzonych modułów
  produkcyjnych (`wordpress/client.py`, `wordpress_authoring.py`,
  `store_measurement.py`) ich Ruff jest zielony, a `scripts/verify.sh` spadł do
  21 błędów — pozostały w testach i niezwiązanych plikach. Bezpośrednie testy
  WordPress inventory/handoff/measurement przeszły; release gate nadal otwarty.
- 2026-07-19: po wyczyszczeniu Ruffa i shared-schema regexów `scripts/verify.sh`
  przechodzi Python/Ruff, ESLint, shared-schemas, dashboard, skill hygiene i
  marketer-language guard. Zatrzymuje się na mypy: 102 błędy w 20 plikach
  (typowanie kontraktów/API/measurement). To osobny release blocker; nie
  redukuję go masowym `Any` ani przypadkowym castowaniem.

- 2026-07-19: zmierzony cold-start briefu po wygaśnięciu 30-sekundowego cache
  wynosił 4,056 s, a kolejki 2,820 s. Domyślny TTL read-only agregatów daily
  runtime został wydłużony do 300 s, nadal z env override i bez zmiany
  connector freshness/invalidacji. Focused proof kontraktu cache i Ruff są
  zielone; nie jest to dowód produkcyjnej wydajności ani świeżości danych poza
  jawnym TTL.

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

### 2026-07-19 — stale detection dla pełnego draftu

Live BDO ujawnił rozjazd: zatwierdzony plan i istniejąca rewizja miały digest
`550ba271…`, ale późniejszy planning job zakończył się błędem dla digestu
`0ffb4109…`. `GET /initial-draft` zwracał wcześniej `created` starej rewizji,
co mogło pokazać marketerowi nieaktualny tekst jako bieżący.

Naprawiono read path: bez ciężkiego snapshotu odczytuje najnowszy queued/failed
planning job, porównuje jego `planning_input_digest` z zatwierdzoną propozycją i
zwraca typed `blocked/stale_planning_input` z bezpiecznym retry. Historia rewizji
pozostaje niezmienna; GET nie uruchamia modelu ani vendor write. Focused proof:
`tests/content/test_initial_draft_status_read_path.py` 5 passed, Ruff passed,
live BDO GET zwraca blocker zamiast `created`.

Second-opinion checker dla fixed pointu: pierwsza próba została odrzucona przez
walidator (Claude przekroczył limit 20 linii cytacji), bez retained outputu.
Świeża próba jest schema-valid i nie ma findings; pozostawia wyłącznie jawne
evidence gaps wynikające z tool-free transportu oraz human-only decyzję o
akceptacji planu/draftu. Nie claimuję UAT, jakości tekstu ani gotowości publikacji.

### 2026-07-19 — compact measurement exclusions

Świeży readback przez WILQ API dla exact BDO URL-u zwrócił 35 użytecznych faktów
GSC/WP, ale 544 powtórzone row-level exclusions dla historycznych
`connector_refresh`. Agregator zachowuje teraz jeden wpis na kombinację
`code/source/metric/period` i scala wszystkie `evidence_ids`, więc nie gubi
lineage, a wynik nie zalewa marketera technicznym szumem. Live readback po
zmianie: 35 faktów, 4 typowane exclusions (`wrong_period`). Focused aggregate
and evidence proof: 9 testów, Ruff passed. Nie zmienia to zasad wykluczania,
nie dopuszcza historycznych okresów do measurement loopu i nie tworzy
synthetic metrics.

### 2026-07-19 — wspólny deadline planowania i stale joba

W storage stale job był ustawiony na 120 sekund, podczas gdy bounded Codex
planning turn miał 180 sekund. To tworzyło ryzyko ponownego enqueue i drugiego
turnu, gdy pierwszy nadal pracował. Router i store korzystają teraz z jednego
env-backed `runtime_contract`: domyślnie 180 sekund, a stale detection używa
tej samej wartości. Jawna grace wynosi `0.0`, ponieważ istniejący publiczny
kontrakt traktuje dokładnie trzy minuty jako retryable; zmiana tej granicy
wymagałaby osobnej decyzji właściciela.

Focused proof: timeout/default/shared-config 3 passed, stale queued-generation
falsifier passed, Ruff i diff-check passed. Claude checker został przygotowany
z fingerprintem fixed pointu, ale okno wykonania było zamknięte (przed 12:00
Europe/Warsaw); nie claimuję review PASS. Human-only pozostaje decyzja, czy
przyszły maintenance window może przyjąć dodatnią grace.

### 2026-07-19 — service-scoped stale detection

Po wcześniejszym stale hardeningu wykryto drugi edge case: lookup najnowszego
planning joba był tylko po `work_item_id`. Przy kilku kartach usług job innej
usługi mógłby fałszywie unieważnić aktualny plan. Store przyjmuje teraz
opcjonalny `service_card_id`, a initial-draft GET przekazuje kartę zatwierdzonej
propozycji. Focused status suite: 6 passed; Ruff, diff-check i live BDO GET
przeszły. Dodany checker ma osobny fingerprint i prompt; wynik Claude’a jest
jeszcze pending przez zamknięte okno wykonania.

### 2026-07-19 — klasyfikacja provider stream disconnect ze stderr

Minimalny repro izolowanego structured turnu kończył się po 20 sekundach bez
outputu, z `codex_timeout`, mimo że lokalny Codex wypisywał bezpieczny sygnał
`responseStreamDisconnected` na stderr. Transport odrzucał cały stderr przez
`DEVNULL`, więc operator dostawał zbyt ogólny blocker i nie dało się odróżnić
przerwania strumienia od zwykłego timeoutu.

Adapter czyta teraz stderr do krótkotrwałego, nieutrwalającego obserwatora i
zapamiętuje wyłącznie boolean dla rozpoznanego disconnectu. Nie zapisuje ani nie
ujawnia payloadu providera, nie dodaje fallbacku ani drugiej ścieżki modelowej.
Focused falsifier w `tests/content/test_codex_app_server_transport.py` dowodzi,
że stderr-only disconnect kończy się typed `codex_response_stream_disconnected`;
transport suite, Ruff i diff-check przechodzą. Realny probe po zmianie również
zwrócił ten kod, nadal bez outputu, zapisu, vendor write i `external_call_attempted`.
To poprawia diagnozę, ale nie dowodzi dostępności providera ani gotowości
pełnego planowania; provider/runtime pozostaje blockerem.

### 2026-07-19 — exact digest w kolejce planowania

Live POST planning dla outsourcingu zwrócił `generating` natychmiast, ale
wcześniej queued payload tracił `expected_planning_input_digest`, bo kontrakt
odrzucał digest bez pełnego `input_summary`. Przy wolnym workerze GET pokazywał
więc próbę bez identyfikacji exact fixed pointu. Generating response może teraz
przechowywać digest bez summary (summary dołącza worker po snapshot/readback), a
router zapisuje requestowy digest od razu. Focused store proof zachowuje digest
w queued readback; Ruff i diff-check przechodzą. Live POST+GET outsourcingu
potwierdził digest `f695aed7…`, service card i run ID bez czekania na model.
Nie zmienia to zasad stale detection ani nie udaje sukcesu providera; oba realne
turny nadal mogą zakończyć się typed runtime blockerem.

Live terminal proof po tej zmianie zakończył outsourcingowy run jako `failed`,
z zachowanym digestem `f695aed7…`, service card, thread/turn IDs i
`source_codes=[codex_response_stream_disconnected]`. Nie zapisano propozycji,
rewizji ani vendor write; `external_call_attempted=false`. To jest dowód
bezpiecznego zakończenia i readbacku kolejki, nie dowód dostępności providera,
pełnego tekstu ani gotowości pilota.

### 2026-07-19 — run ID w terminalnym planning trace

W terminalnym readbacku provider failure miał thread/turn, ale `runtime.run_id`
był pusty, mimo że worker utworzył i zakończył `CodexRun`. Trace planowania
wiąże teraz failed/persistence-failed/success response z rzeczywistym
`codex_content_planning_*` ID; queued `planning_generation_*` pozostaje tylko
identyfikatorem oczekującej próby przed startem workera. Helper-level proof
potwierdza zachowanie statusu i thread ID. Live BDO terminal readback
potwierdził `run_id=codex_content_planning_7ac5982747154662aadc0d9c957eed80`
razem z thread/turn oraz `codex_response_stream_disconnected`; plan nie został
zapisany. Nie claimuję pełnego planu.

### 2026-07-19 — persisted planning readback zachowuje CodexRun ID

Po naprawie terminalnego trace znaleziono drugi, niezależny read path: GET
istniejącej propozycji odbudowywał status z lokalnego `CodexRun`, ale pomijał
jego `id`. `_persisted_runtime_trace` zwraca teraz `run_id` również po reloadzie;
focused readback test, Ruff i diff-check przechodzą. To spina historię zapisanego
planu z tym samym runem, bez ujawniania provider payloadu. Nie dowodzi jakości
tekstu ani sukcesu nowej generacji.

### 2026-07-19 — exact planning digest w CodexRun

`CodexRun` miał już pole `planning_input_digest`, ale planningowy `_start_run`
go nie ustawiał. Run ID można było więc odnaleźć, lecz nie dało się z samego
persisted runu udowodnić, któremu exact input odpowiadał. Start runu zapisuje
teraz digest razem z evidence IDs; focused suite ma 2 testy, Ruff i diff-check
przechodzą. To domyka identyfikację run → input, bez zmiany providerowego
blockera i bez tworzenia planu.

### 2026-07-19 — świeży API context i timing startu workflow

Bezpośredni odczyt WILQ API: 12 konektorów, 9 skonfigurowanych, 2 bez credentials;
brief ma 1 blocker, 3 rekomendacje i 17 evidence IDs. Kolejka treści ma 54
kandydatów, 53 actionable i status `ready`; nie jest ograniczona do dwóch
pilotów. Pomiar lokalnego seamu dla obu exact pilotów wykazał odpowiedź wybranej
kolejki w 0,26–0,67 s oraz pierwszy pełny snapshot w 3,9–7,7 s. Kolejne odczyty
z ciepłego cache trwały 1,2–1,4 s. To dowodzi, że API nie wisi przez 10 minut,
ale pierwszy snapshot nadal jest mierzalnym hotspotem do redukcji; nie claimuję
jeszcze docelowego UX ani realnego UAT. Claude checker pozostaje przygotowany na
świeżym fixed poincie, lecz wykonanie jest niedostępne przed 12:00 Europe/Warsaw.

### 2026-07-19 — snapshot nie buduje diagnostics drugi raz

Wybrany browser snapshot przechodzi przez warstwę „czy to nie jest blocker”, a
następnie ponownie wołał pełne `diagnostics_with_exact_gsc_demand` i odczyty stanu
store. Ten sam request budował więc ciężki exact diagnostics path dwukrotnie.
Route zachowuje teraz pierwszy wynik diagnostics, revision state i planning
decisions przy przejściu do pełnego snapshotu. Publiczny kontrakt inventory
test suite: 5 passed; Ruff i diff-check przechodzą. Kontrolny odczyt outsourcing
po reloadzie miał 4,955 s, potem 1,573 s; wcześniejszy cold baseline w tym samym
stacku wynosił 7,543 s. To jest dowód usunięcia powtórnego odczytu, nie obietnica
docelowego czasu ani dowód UAT.

### 2026-07-19 — snapshot blocker probe bez drugiej pełnej assembly

Po reuse diagnostics pozostał jeszcze drugi koszt: endpoint budował pełny
snapshot tylko po to, by sprawdzić, czy element nie jest zablokowany, a potem
budował go ponownie z proposal/review state. Probe używa teraz bezpośrednio
blocked projection; pełną assembly wykonuje tylko dla elementu przechodzącego
do workflow. Publiczny kontrakt inventory suite: 5 passed; Ruff i diff-check
przechodzą. Ten sam cold outsourcing snapshot po reloadzie zmierzono na 3,134 s,
a warm na 1,053 s. To redukuje powtórną pracę, ale nie jest jeszcze docelowym
SLO ani dowodem realnego UAT.

Kontrolny odczyt blocked itemu `content_work_item_content_decision_ahrefs_gap_records_review`
zwrócił poprawnie `recommended_mode=block` i powód, bez próby przypisania usługi
ani uruchomienia planera. To zachowuje bezpieczną gałąź po usunięciu pełnej
assembly dla elementów nieblokowanych.

### 2026-07-19 — audit lineage source facts

Focused audit rzeczywistego rejestru wiedzy wykazał 21 faktów: 9 `approved` i 12
`review_required`; żaden fakt niezatwierdzony nie ma `evidence_ids`. To ogranicza
ryzyko, że review-required kandydat trafi do planera jako evidence-bound claim.
Nie oznacza to kompletności korpusu: 8 z 15 zatwierdzonych materiałów nadal ma
`import_pending`, a realne owner review pozostaje wymagane.

### 2026-07-19 — exact input readback dla dwóch pilotów

Live GET planning proposal dla BDO i doradztwa/outsourcingu zwraca dwa różne
`service_card_id` i dwa różne planning digests, ale ten sam dynamiczny zestaw
ocen źródeł: WordPress, Service Profile i GSC `used`; GA4, Ahrefs i Keyword
Planner `missing`; Ads, Merchant, Localo i Social `not_applicable`. Oba inputy
mają 2 source facts, 7 source-material IDs i 3 evidence IDs. Wszystkie 7
material IDs są faktycznie `imported`. Oba runy kończą się jednak typed
`codex_response_stream_disconnected`, bez proposal/revision/vendor write. To
potwierdza parity wejścia i lineage dwóch pilotów, nie sukces providera ani
gotowy tekst.

### 2026-07-19 — aggregate coverage dla Ahrefs gap contract

Kontrakt `AhrefsGapReadContract` eksponuje teraz również zbiorczy, API-owned
`coverage_summary`, złożony z zakresów zapisanych przy poszczególnych rekordach
luk. Panel pokazuje ten zakres nad listą rekordów, a rekordy nadal zachowują
`derived_method`, własny `coverage_summary` i status mapowania. Live readback
zwrócił 8 rekordów oraz mieszany zakres: próbka domeny docelowej 100, limit
porównania 1000 i rekordy bez podanego zakresu. To poprawia widoczność
ograniczenia próby; nie jest dowodem kompletności całego Ahrefs ani nie odblokowuje
automatycznego mapowania strony/usługi.

### 2026-07-19 — wyszukiwanie kolejki obejmuje realne sekcje strony

Wybór strony w `/content-workflow` przeszukuje teraz także `content_summary` oraz
nagłówki `acf_section_headings` z inventory WordPressa. Dzięki temu marketer może
znaleźć istniejącą podstronę po sekcji, a nie tylko po URL, tytule lub query.
To jest wyłącznie filtr prezentacyjny nad pełną kolejką API; nie zmienia
rekomendacji, mapowania usługi, digestów ani żadnej decyzji generacyjnej.

### 2026-07-19 — karta kolejki pokazuje pozycję i status porównania

Karta kandydata w kolejce pokazuje teraz, gdy API je dostarcza, najlepszą
średnią pozycję, liczbę zapytań oraz jawny status porównania okresów. Brak
porównywalnego okresu i niejednoznaczne porównanie są komunikowane wprost,
zamiast znikać za samym CTR. To nadal read-only prezentacja istniejących
metryk GSC; nie wyprowadza przyczyny ani prognozy efektu.

### 2026-07-19 — social reuse zachowuje evidence historii duplikacji

`SocialHistoryImportAudit` i `SocialHistoryInventory` przenoszą teraz
zweryfikowane `source_evidence_ids` z metadata-only spisu do immutable
`SocialReuseProposal` jako `duplicate_risk_evidence_ids`. Builder blokuje nową
propozycję, jeśli historia nie ma evidence; dashboard pokazuje osobno liczbę
źródeł rewizji treści i dowodów historii. Digest historii nadal unieważnia
readback po zmianie, a publikacja pozostaje wyłączona. Live inventory nadal ma
status `missing`, więc ten slice nie odblokowuje social reuse dla Ekologusa.

### 2026-07-19 — świeży context WILQ API po kolejnym fixed poincie

Bezpośredni odczyt API o `2026-07-19T07:51:54Z` potwierdził 12 konektorów,
9 skonfigurowanych i 2 brakujące credentials; brief ma 1 blocker i 3
rekomendacje. Kolejka treści pozostaje `ready`: 54 kandydatów, 53 actionable,
świeżość `fresh` (`checked_at=2026-07-19T07:51:56Z`). Baza materiałów Ekologusa
ma 15 pozycji, z czego 7 zaimportowanych i 8 `import_pending`; generation
pozostaje jawnie zablokowane do kontrolowanego importu i owner review. Pomiar
bezpośredniego endpointu wybranego snapshotu BDO wyniósł 3,36 s w ciepłym
stacku, a osobny odczyt briefu i kolejki odpowiednio 0,002 s i 0,039 s. To
potwierdza, że API jest dostępne i kolejka nie jest źródłem 10-minutowego
spinnera; snapshot pozostaje osobnym hotspotem do dalszej optymalizacji i
browser proof, bez claimu docelowego SLO ani UAT.

### 2026-07-19 — Ads landing/service binding domknięty jako kontrakt review-only

Hash-only join Ads → WordPress inventory → Service Profile ma teraz zamknięty
focused proof: test dopasowanego landingu z kartą `review_required`, test BDO
bez dopasowania oraz powierzchnia Ads przechodzą 3/3, Ruff i diff-check. Live
`/api/ads/diagnostics` jest świeży i ma `live_data_available=true`; 23 wiersze
search-term dzielą się na 12 `resolved → unbound` i 11
`resolved → review_required`. Żaden nie jest udawany jako `approved_current`, a
raw landing URL nie wraca z kontraktu Ads. P1 `wilq-seo-wgaq` zamknięty; P0 Ads
pilot pozostaje otwarty, bo realne dane nie dostarczają jeszcze zatwierdzonego
service bindingu ani native-UI handoffu. Szerszy Ads contract suite ma nadal
znaną, niezwiązaną awarię fixture/query dla Demand Gen; nie jest ona
przedstawiana jako zielony wynik.

### 2026-07-19 — realny Ads read/review pilot ma dowód, ale nie ma jeszcze service handoffu

Live smoke `smoke_skill_contract.py --api-base http://127.0.0.1:8000` zakończył
się kodem 0. Odczyt Ads jest dostępny; WILQ ma evidence
`ev_connector_google_ads_status` i `ev_refresh_refresh_google_ads_1b4938f44dd1`,
23 wiersze search-term, 32 kliknięcia, 503 wyświetlenia, koszt 163 PLN i 0
konwersji. Sześć review actions przechodzi walidację. Apply/write pozostaje
wyłączone, a twierdzenia CPA/ROAS, zmarnowanego budżetu, wykluczeń i zmian
budżetu są jawnie zablokowane. P0 `wilq-seo-v9ab.17.7` pozostaje otwarty:
realne landing rows są `unbound` albo `review_required`, więc nie ma jeszcze
zatwierdzonej usługi ani native-UI handoffu. To jest dowód read/review, nie
gotowości do wykonania ani UAT.

### 2026-07-19 — Ads contract fixture rozdziela auxiliary final-URL od Demand Gen

Pełny `tests/api_contracts/test_ads_contracts.py` był czerwony nie przez
produkcyjne GAQL, ale przez MockTransport: szerokie `FROM ad_group_ad` łapało
auxiliary `AD_FINAL_URL_INVENTORY_QUERY` jako zapytanie Demand Gen i wymuszało
niepasujący filtr. Fixture rozdziela teraz final-URL inventory od
`DEMAND_GEN_AD_GROUP_AD_QUERY`; produkcja pozostała bez zmian. Pełny Ads
contract suite przechodzi, a `py_compile`, Ruff `E9/F` i diff-check są zielone.
To usuwa fałszywy czerwony sygnał w review, nie jest dowodem vendor write ani
native-UI handoffu.

### 2026-07-19 — runner planowania: jawne odroczenie migracji

Lab durable store potwierdził readback queued run identity po odtworzeniu
store, stale re-enqueue, idempotent identical enqueue i izolację usług (3/3).
APScheduler pozostaje connector-only z `autostart=false`; brak crash-injection
i no-duplicate model proofu oraz brak autoryzacji do migracji produkcyjnej.
Bead `wilq-seo-1dke` zamknięty decyzją **DEFER**: utrzymujemy obecny
ThreadPoolExecutor, durable queued rows i typed stale retry. To decyzja
operacyjna, nie claim pełnej recovery ani sukcesu providera.

### 2026-07-19 — planowanie nie duplikuje turnów i nie ściga żywego workera

Planowanie używa jednego kontraktu czasu: router Codex i store stale detection
czytają `WILQ_PLANNING_CODEX_TIMEOUT_SECONDS` (domyślnie 180 s), a istniejąca
granica 3 minut pozostaje zachowana przez jawne `grace=0`. Osobna transakcja
`BEGIN IMMEDIATE` blokuje nowy digest dla tego samego `work_item_id` +
`service_card_id`, gdy rodzeństwo jest queued/running; API zwraca typed
`in_flight`, aktywny run i retry-after zamiast drugiego turnu. Focused dynamic
planning suite i falsifiers timeout/stale/concurrency przechodzą, a Beads
`wilq-seo-v1um` i `wilq-seo-tcd7` są zamknięte. Nie oznacza to sukcesu providera,
wygenerowanego tekstu ani approval; wcześniejsze checker dispositions z
evidence gaps pozostają jawne.

### 2026-07-19 — browser proof `/content-workflow` wrócił do aktualnego kontraktu UI

Pełny `apps/dashboard/e2e/content-workflow-layout.spec.ts` przechodzi 6/6 w
jednym przebiegu (desktop/mobile, inventory, planning, pięć zakładek, Codex
section rewrite oraz save → reload → exact review → WordPress draft-only wizard).
Naprawa dotyczyła wyłącznie rozjechanych oczekiwań testu: aktualny API-owned
payload wybiera sekcję przez `selected_section_headings`, review używa etykiety
`Zapisz decyzję dla aktualnego draftu`, a wizard ma nagłówek `Szkic aktualnego
tekstu → dev`. Produkcja nie została zmieniona. To świeży synthetic browser
proof, nie realny Wilku UAT ani zgoda na vendor write; nadal obowiązują blokery
importu materiałów, owner review i storage maintenance window.

Świeży checker fixed pointu został przygotowany poza repo w
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-content-browser-contract-v2-TfOhjc`.
Runner został poprawnie zatrzymany o `10:24 CEST` przez ograniczenie okna i nie
ma jeszcze outputu Claude; po `12:00` można uruchomić wyłącznie ten pass, jeśli
fingerprint repo pozostanie niezmieniony. Brak outputu nie jest ani PASS, ani
findingiem.

### 2026-07-19 — oba exact piloty przechodzą ten sam selected-work-item seam

Read-only API odczytał oba kanoniczne work itemy jako `workflow_snapshot`:
BDO w 2,527 s z kartą `ekologus_service_bdo_reporting` oraz doradztwo i
outsourcing w 1,378 s z kartą
`ekologus_service_environmental_consulting_outsourcing`. Oba mają `scope`,
planning digest, trzy konektory źródłowe i trzy evidence IDs. Unfiltered queue
nie musi zawierać inventory-bound URL; jawne
`GET /api/content/work-items/queue?work_item_id=...` zwraca dla outsourcingu
`candidate_count=1`, `actionable=1`, a dashboard używa właśnie tej ścieżki po
wyborze adresu. To dowód wspólnego API seamu, nie owner approval, pełny draft,
UAT ani vendor write.

Odczyt proposal workspace obu pilotów pozostaje uczciwie przed generowaniem:
`generation_status=baseline`, `proposal_id=null` i brak `planning_input_digest`.
BDO ma zapisaną usługę, ale `scope_current=false` i `section_map_current=false`
po zmianie digestu; outsourcing dodatkowo ma
`service_selection_confirmed=false`. To nie jest gotowy plan ani zgoda na
initial draft — dashboard ma pozostać na etapie zakresu i wymagać aktualnego
review, zamiast przedstawiać baseline jako wygenerowany dokument.

### 2026-07-19 — picker rozróżnia baseline strony od wygenerowanego planu

W `/content-workflow` sekcja z baseline’owego inventory nie jest już opisana
marketerowi jako „Poprawiana sekcja”. Picker używa teraz API-owned
`generation_status`: dla `baseline` pokazuje „Sekcja z aktualnej strony”, a dla
`codex_generated` „Sekcja z planu”. Nie zmienia to wyboru, digestu ani zapisów;
usuwa tylko sugestię, że plan lub rewrite został już wygenerowany. Focused
ContentWorkflowSurface: 34/34, dashboard typecheck i diff-check przechodzą.

Panel review używa tego samego rozróżnienia: baseline mówi „Zakres opiera się
na…”, a wygenerowany plan „Plan opiera się na…”. Focused
`ContentPlanningReviewPanel`: 7/7 i dashboard typecheck przechodzą; źródła,
digesty i decyzje pozostają bez zmian.

### 2026-07-19 — marketing brief dostaje istniejący startup prewarm

Cold read `/api/marketing/brief` po managed restart był wcześniej obciążony
buildem około 3,6 s, mimo że kolejka była już prewarmed. Lifespan wywołuje teraz
`build_daily_marketing_brief()` w tym samym nieblokującym prewarmie co
daily-check i GA4. Po restarcie pierwszy pomiar wyniósł 1,096 s, następne
0,010–0,011 s; kolejka 0,063 s. Focused `tests/test_daily_runtime_prewarm.py`:
4/4, Ruff i diff-check przechodzą. To poprawa cold-startu, nie deklaracja SLO
ani kompletności danych.

### 2026-07-19 — raport aktywacji semantic review odzyskuje dokładny typ proofu

Mypy wskazał dwa błędy w `wilq/storage/semantic_review_activation.py`: raport
deklarował `dict[str, int]`, choć `storage_proof()` zwraca kontraktowy
`StorageProof` TypedDict. Raport używa teraz tego samego typu publicznego bez
zmiany runtime ani serializacji. Focused
`tests/storage/test_semantic_review_activation.py` przechodzi 1/1, a
`uv run mypy wilq/storage/semantic_review_activation.py` jest czyste. Pełny
repozytoryjny mypy nadal ma szeroki, niezależny klaster 100+ błędów w wielu
modułach; nie przedstawiam tego slice'a jako zamknięcia całej bramki.

### 2026-07-19 — pełna bramka po slice'ie typowania: jakość tekstowa zielona, mypy jawnie czerwone

Po commitcie `a0f1c8f1` i pushu `scripts/verify.sh` ponownie przechodzi lint
shared schemas oraz dashboard, skill hygiene i marketer language guard. Mypy
zatrzymuje bramkę na 100 błędach w 19 plikach, głównie w istniejących kontraktach
Literal/TypedDict, optional payloadach i niezaanotowanych seamach Ads, GA4,
WordPress inventory, planning, semantic review oraz routerach draftu. To nie
jest awaria jednego flow ani dowód na brak działania runtime; jest to osobny
repozytoryjny dług typowania, który pozostaje kolejnym zadaniem. Nie claimuję
pełnego `verify.sh` PASS.

### 2026-07-19 — świeży checker Claude i pierwszy następny slice po jego findingu

Po otwarciu dozwolonego okna uruchomiono dokładnie jeden bounded checker Claude
dla fixed pointu `6d779c9b` (tree `c63791a3`, dirty state SHA
`cf44bf12…`). Output został zwalidowany jako `valid evidence-bounded review`;
pełny JSON i disposition są poza repo w katalogu
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-content-ops-final-typing-gate-oK9lL7/`.
Checker zwrócił 6 findings: dwa HIGH wokół bramki mypy i typu głównego
snapshotu, MEDIUM dla section mapping, freshness oraz TS/Python contract
drift, LOW dla szerszego proofu storage. Żaden finding nie został przedstawiony
jako approval; UAT, provider execution, knowledge approval i vendor write nadal
są jawnie nieudowodnione.

F2 został od razu zamieniony w produkcyjny slice: helper
`_latest_exact_wordpress_execution` przyjmuje oba istniejące typy snapshotu, a
carryover v2 wymaga nie-null planning digestu. `uv run mypy
apps/api/wilq_api/routers/content_workflow.py` jest czyste,
`tests/content/test_revision_lineage_contract.py -k editor_save_v2` przechodzi
1/1, a `git diff --check` jest zielony. Szerszy selector activation-packet ma
3 istniejące fixture failures (`KeyError: preflight`) poza zakresem tej zmiany;
nie maskujemy ich zmianą testów.

### 2026-07-19 — section mapping ma teraz typowany publiczny seam

Finding F3 ze świeżego checkera został zamieniony w produkcyjny slice bez
zmiany heurystyki dopasowania. `build_inventory_mapping` przyjmuje teraz
konkretny `ContentPlanningModelOutput`, a kandydaci i `_mapped_status` używają
`ContentPlanningModelSection` zamiast `object`; lokalny status został nazwany
`mapping_status`, więc znika także realny `no-redef`. Proof:
`uv run mypy wilq/content/planning/section_mapping.py` clean,
`tests/content/test_planning_section_mapping.py` 7/7, `git diff --check` clean.
To nie zamyka jeszcze freshness seam, TS/Python contract drift ani całego
repozytoryjnego mypy.

Po tym slice pełny odczyt `uv run mypy wilq apps/api --no-incremental` spadł z
100 błędów w 19 plikach do 90 błędów w 17 plikach. To jest licznik długu, nie
claim gotowości; pozostałe klastry obejmują freshness diagnostics, initial draft,
Ads, GA4, WordPress inventory i shared-contract seams.

### 2026-07-19 — measurement evidence zachowuje typ świeżości i settlementu

Następny klaster długu został zamknięty w
`wilq/content/measurement/evidence.py`: `_quality_metadata` przyjmuje teraz
typed `ConnectorRefreshRun` i zwraca jawny tuple stanów jakości, settlementu i
caveats. To nie zmienia decyzji pomiarowych, ale usuwa niezaanotowany seam
odpowiedzialny za interpretację świeżości. Proof: modułowy mypy clean,
`tests/content/test_publication_bound_measurement.py` oraz
`tests/content/test_measurement_aggregates.py` razem 13/13, diff-check clean.

Po tym slice pełny odczyt mypy wynosił 87 błędów w 16 plikach. Literalny status
waluty Ads został następnie domknięty; aktualny odczyt wynosi 86 błędów w 15
plikach. To nadal nie jest pełna bramka ani dowód poprawności raportów Ads.

Ahrefs gap diagnostics ma teraz jawny fallback dla nieufnych wartości
`gap_method`: `_gap_derived_method` zwraca wyłącznie `str` i nie przepuszcza
`None` z zewnętrznego payloadu. Proof: modułowy mypy clean,
`tests/content/test_ahrefs_planning.py` 4/4, diff-check clean.

Po naprawie Ahrefs pełny mypy wynosił 85 błędów w 14 plikach. Domknięty został
także `compact_capabilities` w API context compaction: ma jawny
`dict[str, Any]`, bez zmiany redakcji payloadu. Proof: modułowy mypy clean,
`tests/api_contracts/test_metric_context_contracts.py` i
`tests/api_contracts/test_security_connector_contracts.py` razem 17/17,
diff-check clean. Aktualny pełny odczyt po tej serii wynosi 84 błędy w 13
plikach; kolejny klaster dotyczy helpera initial-draft.

### 2026-07-19 — drugi checker potwierdza lukę bramki, a mapping zachowuje oba kontrakty

Drugi checker dla fixed pointu `be409222` został zwalidowany po jednej
odrzuconej próbie (Claude podał zakres cytacji ponad 20 linii; runner nie
zapisał JSON-a). Retry zwrócił 5 findings MEDIUM/LOW: brak aktualnego pełnego
verify na fixed poincie, brak per-file listy 84 błędów, jawnego inwentarza
dirty artefaktów i liczbowych proofów dla części seamów. Żaden finding nie jest
approval; disposition pozostaje advisory.

W trakcie weryfikacji wykryto i naprawiono regresję kontraktu: po utwardzeniu
`build_inventory_mapping` przyjmował tylko modelowy output, choć istniejący
generator przekazuje także `ContentPlanningProposal`. Funkcja obsługuje teraz
oba typy przez jawny union/cast, bez zmiany mapowania. Proof:
`tests/content/test_planning_section_mapping.py` i
`tests/content/test_generated_proposal_store.py` razem 10/10,
`uv run mypy wilq/content/planning/section_mapping.py` clean,
`uv run ruff check wilq/content/planning/section_mapping.py` clean. Pełny
odczyt po tej korekcie wynosi 83 błędy w 13 plikach.

### 2026-07-19 — initial-draft router ma typowany planning/status seam

Naprawiono klaster routera initial draft bez zmiany odpowiedzi workflow:
planning workspace jest jawnie zawężany przed kolejką, statusy runtime są
mapowane na kontrakt `generating/created/blocked/failed/conflict`, blocker code
ma właściwy Literal, a proposal store i proposal mają konkretne typy. Proof:
`uv run mypy apps/api/wilq_api/routers/content_initial_draft.py` clean,
Ruff clean, `tests/content/test_initial_draft_status_read_path.py` oraz
`tests/content/test_initial_draft_queue_gate.py` razem 9/9, diff-check clean.

Semantic-review router ma teraz jawny `ContentSemanticBlockerCode`, typ klienta
Codex i status terminalny; modułowy mypy oraz Ruff są czyste. Istniejący
`tests/content/test_semantic_content_review_api.py` został uruchomiony, ale
zawisł w `threading` bez wyniku i został przerwany. Nie jest to PASS; pozostaje
osobnym blockerem runtime/test harnessu.

Freshness diagnostics ma teraz typed `TypedDict` dla wszystkich pól jakości,
covered windows, settlementu i caveats; wcześniejsze `**dict[str, object]`
nie przechodziły bezpiecznie do `ContentFreshnessAssessment`. Proof:
`uv run mypy wilq/briefing/content_diagnostics.py` clean, Ruff clean,
`tests/test_content_diagnostics.py` 7/7, diff-check clean.

Freshness slice zmniejszył pełny mypy z 72 do 47 błędów; następnie
`_persisted_runtime_trace` mapuje teraz stan CodexRun `started` do bezpiecznego
runtime statusu zamiast przekazywać niedozwolony Literal. Proof: modułowy mypy
clean, dynamic planning runtime/stale tests 5/5.

Po normalizacji runtime trace pełny odczyt `uv run mypy wilq apps/api
--no-incremental` wynosi 46 błędów w 9 plikach. To aktualny licznik długu na
fixed poincie `9d6fc711`; nie jest to jeszcze pełna bramka.

### 2026-07-19 — checker 46-error fixed point: baseline i reprodukowalność są jawne

Świeży checker dla `d7f537b0` został zwalidowany jako
`valid evidence-bounded review`; disposition jest poza repo w katalogu
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-content-ops-46-mypy-fixed-point-qAfBDN/`.
Retained findings dotyczą obserwowalności bramki, dirty fixed pointu i baseline
per-file; human-only pozostają UAT, copy/knowledge approval i decyzja o
baseline-tolerant verify mode.

Aktualny per-file mypy baseline (46/9):

- `wilq/connectors/google_ads/ad_landing_pages.py`: 14
- `wilq/content/workflow/catalog.py`: 14
- `wilq/content/measurement/aggregates.py`: 7
- `wilq/connectors/wordpress/inventory.py`: 3
- `wilq/briefing/ads_landing_service_binding.py`: 2
- `wilq/content/planning/input_sources.py`: 2
- `wilq/content/quality/semantic_review_service.py`: 2
- `wilq/content/workflow/exact_demand_decision.py`: 1
- `wilq/content/workflow/planning.py`: 1

Stan `dirty` jest intencjonalny: nieśledzone paczki marketera, nagrania,
research oraz task-owned test/code artifacts pozostają własnością użytkownika i
nie są stage'owane. `state_sha256` second-opinion obejmuje porcelain status,
staged/unstaged binary diffs oraz mode i pełny hash każdej ścieżki cached albo
untracked; to pozwala odtworzyć, dlaczego commit sam nie opisuje całego fixed
pointu.

Domknięto dwa najmniejsze remaining clusters: baseline inventory disposition
ma jawnie typowaną mapę, a exact-demand title używa bezpiecznego fallbacku dla
opcjonalnego `page`. Proof: oba moduły mypy/Ruff clean,
`tests/content/test_planning_decisions.py` 7/7, diff-check clean.

Pełny mypy po tych dwóch singletonach wynosi 44 błędy w 7 plikach; następne
klastry są już większe i wymagają osobnych publicznych proofów.

### 2026-07-19 — quality-max goal i świeży checker z realnym connector context

Ustawiono jeden aktywny quality-max goal: WILQ API jest jedynym źródłem
kontekstu/metryk, Codex ma pobierać aktualny context pack, a brak/stalenie
źródła ma być typed blockerem. Checker dla fixed pointu `bbd3e076` został
zwalidowany jako `valid evidence-bounded review`; disposition jest poza repo w
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-wilq-quality-max-fixed-point-EpCxsO/`.
Operator-provided connector summary mówi: 12 total, 9 configured, 2 missing
credentials. Checker retained: verify zatrzymuje się przed testami po mypy,
draft/model/UAT nie mają realnego proofu, wpływ dwóch brakujących connectorów na
consumerów nie jest jeszcze zmapowany, a metryki potrzebują realnego API fetchu
z exact lineage. Nie ma approval, publish ani vendor write.

### 2026-07-19 — context pack jawnie mapuje gotowość źródła na consumerów

Dodano `connector_consumer_readiness_v1` do pełnego, daily i skill-scoped
context packu. Każdy rozważany connector ma jawny status `ready` albo
`blocked`, kod blokady (`missing_credentials`, `read_unavailable`,
`stale_or_unknown_source`), freshness, dostęp do odczytu i efekt dla decyzji.
Blokada mówi wprost, że nie wolno zasilać nią metryk, rekomendacji ani claimów;
nie zmienia to istniejącego statusu connectora i nie udaje brakujących danych.

Proof produkcyjny: `tests/api_contracts/test_context_safety_contracts.py`
(2/2), content strategist context contract (1/1), Ruff i modułowy mypy dla
czterech context modules clean. Read-only runtime przez
`POST /api/codex/context-pack` potwierdził dla content strategist 5/5 źródeł
gotowych; pełny pack pokazał 12 connectorów, 8 gotowych i 4 zablokowane
(`google_sheets`, `linkedin`, `facebook`, `openai_codex`). To jest jawny
consumer impact, nie dowód gotowości draft/model/UAT.

### 2026-07-19 — runtime i źródła marketingowe nie są tym samym

Read-only porównanie `/api/system/status` i pełnego context packu wykazało
ważny rozjazd prezentacyjny: `openai_codex` jest skonfigurowanym runtime'em
operatora, ale nie źródłem marketingowym, więc nie powinien liczyć się jako
zablokowany connector danych. Readiness projection rozróżnia teraz
`not_applicable` dla runtime/wyłączonych opcjonalnych connectorów od
`blocked` dla realnych źródeł. Aktualny runtime: 12 total, 8 ready,
2 blocked (`linkedin`, `facebook`) i 2 not applicable (`google_sheets`,
`openai_codex`); system summary pozostaje 12 total, 9 configured,
2 missing credentials. Proof: focused context safety 3/3, Ruff i modułowy
mypy clean, managed API runtime zgodny z tym rozdziałem.

Selection seam ma teraz jawny alias typu `BusinessMetricFacts`, więc jego
kontrakt jest nazwany także statycznie, nie tylko przez nazwę funkcji. To nie
zmienia zachowania ani nie udaje pełnej ochrony przed przyszłym bypass'em;
stanowi mały, czytelny punkt rozszerzeń dla kolejnych brief projections.

Wydzielono nazwany seam `select_business_metric_facts`: jedna selekcja po
freshness/readiness, potem wyłącznie jej wynik zasila `what_we_know`,
`recommended_focus` i `top_metric_facts`. `rg` po module pokazuje pojedyncze
wywołanie selekcji przed trzema projekcjami; comparative GSC proof obejmuje
również brak zablokowanego źródła w representative facts. Focused brief tests
pozostają 8/8, command-center marketing tests 6/6, Ruff+mypy clean.

### 2026-07-19 — marketing brief fail-closed dla zablokowanych źródeł

Marketing brief jest teraz rzeczywistym consumerem freshness/readiness: przed
budową sekcji `Co wiemy` odrzuca metric facts z connectorów
`missing/stale/unknown`, z błędem odczytu oraz z ostatnim refresh'em
`blocked/failed`. Zablokowane źródło nie trafia do metryk ani rekomendacji, ale
jego osobny blocker nadal jest widoczny operatorowi.

Proof: Localo z auth error/stale refresh i metric factem — metric item znika,
blocker pozostaje; `tests/api_contracts/test_localo_marketing_language_contracts.py`
3/3, marketing brief contract 6/6, Ruff i mypy clean. Managed API nadal
pokazuje realny summary 12/9/2, a obecny brief nie pokazuje LinkedIn/Facebook
jako danych marketingowych. To nie jest jeszcze dowód pełnego downstream
omission dla wszystkich consumerów.

Dodano freshness matrix dla tego samego GSC factu: tylko `fresh` dopuszcza
metric item do `what_we_know` i `recommended_focus`; `stale`, `missing` oraz
`unknown` są fail-closed. Proof obejmuje cztery stany na publicznym builderze,
bez zmiany kontraktu blockera. Local marketing-brief focused proof wzrósł do
8/8, a modułowy Ruff/mypy pozostaje clean.

Fresh checker dla `d7dcf0b9` potwierdził gate i wskazał brak asercji sekcji
rekomendacji. Falsifier rozszerzono: zablokowany Localo nie może pojawić się
ani w `what_we_know`, ani w `recommended_focus`, podczas gdy `what_blocks_us`
pozostaje widoczne. Marketing brief/localo focused proof wynosi teraz 9/9;
pozostałe źródła i consumerzy wymagają osobnych kontraktów.

Domknięto causal proof przez porównanie tego samego GSC metric factu w dwóch
stanach: świeży connector tworzy wpis `what_we_know` i `recommended_focus`, a
identyczny fact przy `auth_error`/stale/blocked refresh znika z obu sekcji i
pojawia się wyłącznie jako blocker. To odróżnia prawdziwe filtrowanie od testu,
który przechodziłby przez pusty fixture. Brief/command-center focused proof:
10/10, Ruff i mypy clean.

### 2026-07-19 — readiness test korzysta z realnego `/api/connectors`

Domknięto pierwszy follow-up z checker'a: focused falsifier pobiera listę
connectorów z publicznego `GET /api/connectors` i dopiero ją przekazuje do
readiness projection. Nie testujemy już wyłącznie ręcznie zbudowanych statusów:
runtime `openai_codex` i disabled `google_sheets` są `not_applicable`, a
eksperymentalne LinkedIn/Facebook bez dostępu pozostają `blocked`.
Proof: context readiness 4/4, security connector scope 2/2, Ruff, mypy i
diff-check clean. Downstream omission (czy rekomendacje faktycznie odrzucają
blocked source) pozostaje kolejnym osobnym seamem.

Checker production-descriptor fixed pointu `b755b123` został zwalidowany;
zwrócił evidence gap dotyczący kompletności payloadu registry. Falsifier
rozszerzono o `len == 12` oraz obecność runtime/optional/experimental IDs przed
projekcją readiness. To utrzymuje test na publicznym API seamie i nie pozwala
przejść pustej albo niepełnej odpowiedzi. Pozostaje osobny downstream omission
proof; nie jest on udawany przez ten test.

Checker dla fixed pointu `b056f6ef` został zwalidowany jako evidence-bounded;
jedyny praktyczny follow-up dotyczył jawnego testu `optional_disabled`. Dodano
ten falsifier: readiness nie blokuje wyłączonego Google Sheets i zachowuje
`not_applicable`. Focused context safety wynosi teraz 4/4; pozostałe granice
(downstream consumer enforcement, freshness policy, realne UAT i model/draft)
pozostają otwarte.

### 2026-07-19 — jawny kontrakt statusu Ads→landing

Usunięto kolejny mały klaster długu typów w `resolve_ads_landing_service_binding`:
status wyniku i lista lifecycle są teraz jawnie zawężone do kontraktu publicznego,
bez zmiany zachowania dopasowania landingu ani polityki review. Proof:
`uv run mypy wilq/briefing/ads_landing_service_binding.py --no-incremental` oraz
`uv run pytest -q tests/test_ads_landing_service_binding.py` (2/2).

### 2026-07-19 — typowane źródła wejścia planowania

W `wilq/content/planning/input_sources.py` doprecyzowano dwa istniejące
kontrakty literalne: confidence materiału WordPress oraz akceptowane tiers
dopasowania landingu. To zmiana type-only, bez luzowania match policy ani
review gating. Proof: modułowy mypy clean oraz
`uv run pytest -q tests/content/test_dynamic_planning_input_sources.py` (10/10).

### 2026-07-19 — kontrakt blockerów semantic review

Helpery blockerów w `semantic_review_service.py` przyjmują teraz
`Sequence[str]` i materializują wartości do listy kontraktu Pydantic. Usuwa to
invariance debt bez zmiany kodów blockerów ani ścieżki fail-closed. Proof:
modułowy mypy clean oraz `tests/content/test_semantic_review_polling_read_path.py`
(3/3).

### 2026-07-19 — bezpieczne zawężenie Ads search-term payload

Na granicy Google Ads search-termów zawężono nested objects przed przekazaniem
do helperów metryk i jawnie opisano słownik wymiarów jako `dict[str, str]`.
Nie zmienia to kryteriów admission (kompletny rekord, kliknięcia > 0,
nieujemne metryki), ale usuwa ryzyko obsługi `None` jako obiektu oraz błędną
inferencję wartości statusowych. Proof: modułowy mypy clean i testy
`tests/connectors/test_google_ads_ad_landing_pages.py`
oraz `tests/connectors/test_google_ads_landing_page_read.py` (16/16).

### 2026-07-19 — fail-closed obliczenia porównań GSC/GA4

Agregaty pomiarowe mają jawny alias dozwolonych connectorów GSC/GA4, a CTR,
engagement rate i weighted average sprawdzają `None` oraz zero przed dzieleniem.
Nie zmienia to admission danych; usuwa tylko niebezpieczne ścieżki typu
`float / None` i utrzymuje brak wyniku przy niepełnym denominatorze. Proof:
`uv run mypy wilq/content/measurement/aggregates.py --no-incremental` oraz
`tests/content/test_measurement_aggregates.py` (8/8).

### 2026-07-19 — typowana granica WordPress inventory

REST inventory odrzuca teraz nie-stringowy lub pusty `link` przed normalizacją,
ACF enrichment buduje jawny `dict[str, str]`, a paginowane requesty przekazują
query params przez właściwy typ HTTPX. Zachowane zostają te same pola inventory,
ACF i limity odczytu; zmiana wzmacnia mapowanie strony/sekcji. Proof: modułowy
mypy clean oraz inventory/catalog tests (15/15).

### 2026-07-19 — content diagnostics pokazuje jedną właściwą akcję

Usunięto przeciek akcji z innych workflowów do kolejki Treści i SEO. Content
diagnostics filtruje teraz registry do `act_prepare_content_refresh_queue`;
draft handoff i Service Profile promotion pozostają dostępne wyłącznie w swoich
osobnych, review-bound seamach. Dzięki temu marketer widzi jedną bezpieczną
decyzję zamiast zawyżonego „2 akcje do sprawdzenia”. Proof: reproducer API
wrócił z `2` do `1`, zmienione moduły mypy clean, view-model/planning tests
14/14.

### 2026-07-19 — headings z `the_content` trafiają do mapowania sekcji

Naprawiono utratę zwykłych nagłówków WordPress: katalog czyta teraz
`section_headings_json` obok ACF, binding używa ich jako źródła sekcji, a
queue/snapshot wystawia `page_inventory.section_headings`. Runtime proof na
obu dokładnych case'ach pokazuje 12 nagłówków z publicznego HTML, ACF pozostaje
jawnie `missing`, a `content_word_count` i evidence pozostają zachowane.
Focused proof: inventory catalog + queue `9/9`, mypy trzech modułów clean.

### 2026-07-19 — marketer wybiera sekcję przed wygenerowaniem planu

Shared queue schema wystawia teraz `page_inventory.section_headings`, a
`/content-workflow` używa tych nagłówków jako źródła wyboru sekcji, gdy plan
Codexa jeszcze nie istnieje. Po wygenerowaniu planu picker przełącza się na
stabilne nagłówki propozycji; stary `planning_digest` nie może zanieczyścić
wyboru z bieżącej strony. To jest tylko fokus sesji — nie tworzy planu ani nie
udaje akceptacji. Proof: dashboard route testy 35/35 oraz shared-schema i
dashboard typecheck clean.

### 2026-07-19 — wyszukiwanie kolejki obejmuje sekcje `the_content`

Wyszukiwanie strony w kolejce Treści i SEO uwzględnia teraz zarówno zwykłe
nagłówki z `the_content`, jak i istniejące nagłówki ACF. Dzięki temu marketer
może znaleźć adres po konkretnym fragmencie strony, zanim wybierze sesję i plan.
Nie zmienia to kolejki ani rankingu kandydatów. Proof: `ContentCandidateQueuePanel`
2/2 oraz dashboard typecheck clean.

### 2026-07-19 — bounded proof wyboru usługi bez skanowania całej kolejki

Test API wyboru usługi nie miał deadlocka: skanował 54 kandydatów i wykonywał
ciężkie snapshoty po około 2 sekundy każdy. Harness używa teraz istniejącego
syntetycznego BDO work item z aktualnym kontraktem planowania, więc sprawdza
ten sam publiczny route bez zależności od całego runtime queue. Proof:
`test_content_service_selection_api.py` 2/2 (35,7 s), Ruff clean. Nie jest to
dowód szybkości produkcyjnego snapshotu; ten pozostaje osobnym ryzykiem.

### 2026-07-19 — baseline latencji snapshotu produkcyjnego

Read-only timing na managed API: pierwszy `/api/content/work-items/queue`
3,64 s, kolejne 0,05 s; pierwszy snapshot BDO 3,87 s, kolejne około 0,8 s;
pierwszy snapshot outsourcingu 6,12 s, kolejne około 0,9 s. To nie jest
10-minutowy hang, ale pierwszy odczyt outsourcingu jest za ciężki dla
30-sekundowego doświadczenia marketera i wymaga osobnego profilowania. Nie
zmieniano cache ani polityki freshness bez dowodu przyczyny.

### 2026-07-19 — Ahrefs nie przepuszcza luk z niepełnym zakresem

Kontrakt luk Ahrefs ma teraz osobny `ahrefs_gap_coverage`: gdy rekordy
porównania deklarują domenę docelową, każdy rekord musi nieść próbkę i limit
porównania. Mieszany lub niepełny zakres przechodzi w `blocked`, usuwa akcje
z kolejki i blokuje twierdzenie o kompletności zakresu; proste syntetyczne
agregaty bez deklarowanego scope pozostają kompatybilne. Live API potwierdza
obecnie `blocked`, brak akcji i rekordy organiczne bez zakresu jako realny
external/data-quality blocker. Proof: test kontraktu Ahrefs 2/2 oraz Ruff.

### 2026-07-19 — reprodukcja awarii runtime planowania bez częściowego zapisu

Aktualny context pack WILQ potwierdza 8 gotowych źródeł marketingowych z 9
aktywnych w tym consumerze; brakujące materiały wiedzy nadal są osobnym
blockerem. Kontrolowana próba BDO przez API zwróciła `generating` natychmiast,
a po około 65 sekundach `failed` z `runtime_failed` /
`codex_response_stream_disconnected`, `external_call_attempted=false`, bez
proposal. Bezpośredni minimalny structured turn app-servera reprodukuje ten
sam błąd; obserwowany przebieg to `thread/started → turn/started →
item/userMessage → error`. To jest realny provider/runtime blocker, nie zgoda
na fallback ani dowód gotowości planów. Dashboard-state zaktualizowany do tego
fixed pointu; następny slice dotyczy recovery UX i diagnostyki tego runtime’u.

### 2026-07-19 — system status pokazuje ostatni istotny run Codexa

`/api/system/status` nie udawał wcześniej diagnostyki runtime’u: zawsze
zwracał `last_codex_run=null`, a częste hooki `Stop` zasłaniały właściwy run
workflowu. API filtruje teraz hook-only wpisy i wystawia ostatni typed run
marketera wraz ze statusem, czasem, skill/hook oraz bezpiecznym błędem. Live
status pokazuje `codex_content_planning_e5967...` jako `failed` z
`runtime_failed:codex_response_stream_disconnected`. Proof: system-status
contract 2/2, mypy i Ruff clean. Nie są ujawniane surowe payloady provider’a.
Ponieważ login/CLI pozostają dostępne, `readiness_status` nadal opisuje
gotowość lokalnej sesji, ale nowy `operational_status=degraded` i
`operational_blocker_code` nie pozwalają pomylić jej z działającym providerem.
Status sanitizuje też niezgodny z typed-code format błędu do
`codex_run_error_unclassified`, więc system status nie staje się kanałem dla
surowego payloadu provider’a. Proof: system-status contract 3/3, mypy i Ruff.

### 2026-07-19 — Ads pilot ma świeże dane, ale brak exact service binding

Live `/api/ads/diagnostics` ma `live_data_available=true` i świeży ostatni
odczyt. Search terms zwracają 23/50 w bounded sample z caveat prywatności, a
90-dniowy odczyt bezpieczeństwa obejmuje 200 wierszy. Nie da się jednak
uczciwie wskazać jednej usługi: 11 landingów ma exact inventory, lecz
`review_required` i zero typed service candidates, a 12 jest `unbound`.
Pilot single-service pozostaje więc właścicielsko zablokowany do review/karty
Service Profile; nie wykonujemy leksykalnego przypisania ani Ads write.

### 2026-07-19 — app-server blocker odseparowany od loginu Codexa

Kontrolowany direct `codex exec --ephemeral --sandbox read-only -m
gpt-5.6-sol --json` zwrócił poprawne `agent_message` i `turn.completed`. Ten
sam izolowany auth/env uruchomiony przez `codex app-server --stdio` przechodzi
initialize/thread/turn startup, ale dostaje `responseStreamDisconnected` i
reconnecty 1/5…5/5; zachowanie pozostaje takie samo po usunięciu
`features.remote_models=false`. Diagnoza zawęża blocker do bieżącego
app-server/provider protocol path. Nie wprowadzamy obejścia przez CLI, drugi
model ani fallback; wynik zapisany w Bead recovery.

### 2026-07-19 — naprawa app-server: nie wymuszamy niestandardowego providera

Oficjalny kontrakt app-servera potwierdza zgodność naszego handshake’u i pól
`input`/`threadId`/`model`/`outputSchema`. Dodatkowy probe `codex debug
app-server send-message-v2` zakończył się poprawnie na `gpt-5.6-sol`, podczas
gdy adapter WILQ kończył się reconnectami. Fixed-point probe wykazał przyczynę:
po usunięciu przekazywania `model_provider`/`model_providers` z lokalnego
`config.toml` ten sam adapter zwrócił `completed` i `{"ok":true}`. App-server
ma wybierać provider z własnego uwierzytelnionego katalogu; niestandardowy
override był kompatybilny z `codex exec`, ale nie z tą ścieżką strumieniową.
Usunięto martwy helper provider override, zachowując model scalar, izolację,
read-only i brak fallbacku. Proof: transport test 1/1, Ruff, mypy oraz live
structured-turn `completed` bez blockera. Nie jest to druga ścieżka modelowa —
to naprawa jedynego istniejącego app-server seamu.

Kontrolowany POST pełnego `/api/content/work-items/{id}/planning-proposals`
przeszedł po reloadzie API: status `ready`, proposal v15, `generation_status`
`codex_generated`, runtime `completed`, bez blockerów i bez częściowego stanu.
Plan zachował 7 identyfikatorów materiałów źródłowych, exact GSC evidence,
service-card binding, query→section assignments oraz measurement plan bez
wymyślonych targetów. To jest pierwszy live proof całego API→app-server→store
seamu po naprawie; nadal wymaga human review przed draftem/publikacją.

Drugi exact case przeszedł tym samym kontraktem po ponowieniu z aktualnym
digestem: outsourcing ma własną propozycję `content_planning_proposal_80090cb7…`,
kartę `ekologus_service_environmental_consulting_outsourcing`, canonical URL
`/oferta/doradztwo-i-outsourcing-ekologiczny/`, 12 własnych sekcji i 24 query
assignments. Serializowany plan nie zawiera literalnego `bdo` (0 wystąpień),
ma 3 evidence IDs i 4 claim IDs. To potwierdza, że naprawiony app-server i
planner obsługują oba case’y dynamicznie, bez kopiowania BDO.

### 2026-07-19 — initial-draft GET nie pokazuje starej rewizji jako aktualnej

Po wygenerowaniu nowego planu BDO stary zatwierdzony plan nadal prowadził
`GET /initial-draft` do historycznej rewizji `created`. Read seam sprawdza teraz
najnowszą trwałą propozycję dla tej samej karty usługi, także gdy jej generacja
już zakończyła się sukcesem (a nie tylko gdy job jest `queued`/`failed`). Jeśli
digest wejścia lub proposal ID się zmieniły, marketer dostaje typed
`stale_planning_input` i musi zatwierdzić aktualny plan. Proof live: BDO zwraca
`blocked`, `stale_planning_input`, bez budowania snapshotu; focused status suite
7/7, Ruff i mypy clean. To chroni pełny dokument przed cichym użyciem starego
tekstu.

### 2026-07-19 — mapa sekcji jest generowana, nie zatwierdzana ręcznie

Usunięto błędną bramkę, która wymagała osobnej decyzji `section_map` mimo że
aktualna propozycja planu już zawierała stabilne sekcje, inventory disposition,
query assignments i evidence lineage. `section_map_current` wynika teraz z
aktualnej propozycji z niepustą mapą; marketer zatwierdza zakres, a następnie
ocenia wygenerowany tekst. Journey, pełny draft i zapis rewizji korzystają z
tej samej zasady. Focused proof: operator journey 18/18, w tym jawny przypadek
z `section_map_review_current=false`, który przechodzi bez ręcznego review mapy;
Ruff i mypy clean.

### 2026-07-19 — content context pack pokazuje realną wiedzę Ekologusa

Context pack dla `wilq-content-operator`, `wilq-content-strategist` i
`wilq-gsc-content-doctor` nie używa już ogólnych kart playbooków jako głównej
wiedzy treściowej. Zwraca skompilowane source-fact cards Ekologusa z realnym
tytułem i streszczeniem, `source_fact_ids`, `source_material_ids`, evidence,
lineage, lifecycle, freshness, dozwolonymi i zablokowanymi claimami. Karty
Ads/playbook pozostają bez zmian dla operatorów kampanii. Live proof po reloadzie
API: context pack zawiera m.in. `ekologus_service_bdo_reporting`,
`ekologus_service_environmental_consulting_outsourcing` oraz zatwierdzone karty
KB z material IDs; focused test przechodzi.

### 2026-07-19 — readiness nie rozjeżdża się już z journey

Browser snapshot nie pokazuje `structured_generation_readiness=ready`, gdy
kanoniczny operator journey nadal jest na `scope` albo `section_map`. Readiness
dziedziczy typed blocker aktualnego kroku, więc marketer widzi jeden prawdziwy
następny krok zamiast równoczesnego „gotowe” i „zablokowane”. Live proof dla
outsourcingu: `current_step_id=scope`, readiness `blocked`, blocker
`scope_review_required`; focused snapshot test, Ruff i mypy clean.

### 2026-07-19 — pełny draft zachowuje lineage na poziomie dokumentu i sekcji

Focused proof obu pilotów przechodzi ponownie po rozszerzeniu falsyfikatora:
rewizja v2 ma globalne `source_material_ids` i `knowledge_card_ids`, a każda
sekcja zachowuje własne `evidence_ids` oraz `knowledge_card_ids`. Nie wymuszamy
fałszywego `source_material_id` przy sekcjach opartych wyłącznie na aktualnym
live evidence; materiał źródłowy pozostaje jednak trwały na poziomie dokumentu.
Proof: `test_initial_full_draft_uses_the_same_atomic_contract_for_both_services`
pass dla BDO i outsourcingu, bez częściowej rewizji i bez publish-ready.

### 2026-07-19 — dashboard nie prosi już o drugi approval mapy

Panel ukończonego kroku `section_map` jest teraz read-only. Pokazuje automatycznie
wyliczoną mapę, inventory disposition, query i evidence, ale nie renderuje pola
decyzji ani przycisku zapisu. Jedyna planistyczna decyzja marketera dotyczy
scope/usługi; mapa jest wynikiem kontraktu API. Focused dashboard proof:
11 testów workflow przechodzi, typecheck dashboardu przechodzi.

### 2026-07-19 — marketer widzi page assets już na etapie planu

Po wygenerowaniu propozycji planu dashboard pokazuje read-only podgląd tytułu
WordPress, H1, leadu, meta title i meta description. Dane pochodzą wyłącznie z
`proposal.page_assets`; panel jasno oznacza brak zapisu do WordPress. To skraca
decyzję przed pełnym draftem i nie tworzy drugiej ścieżki autorstwa. Focused
panel proof: 5/5, dashboard typecheck przechodzi.

### 2026-07-19 — provenance `the_content` jest decyzją zakresu, nie fikcyjną akceptacją mapy

Po przejściu mapy sekcji na tryb automatyczny usunięto pozostałą bramkę, która
wymagała `existing_content_provenance` na nieistniejącym już approvalu
`section_map`. Dla materiału `review_required` marketer potwierdza teraz w
jedynym realnym formularzu — zatwierdzeniu scope — dokładny zakres odczytanego
publicznego materiału. API wiąże ten checked item z `scope_decision`, a initial
full draft nie omija już blokera materiału tylko dlatego, że HTML ma poprawną
ekstrakcję. Mapa sekcji pozostaje automatyczna; REST/ACF, `the_content` i inne
warianty nadal są wybierane dynamicznie przez inventory seam. Focused dynamic
input 10/10, API runtime falsifier pass, dashboard proof 8/8, Ruff/mypy i
typecheck przechodzą.

### 2026-07-19 — pasek źródeł pokazuje tylko lineage wybranej strony

`ContentSourceStatusBar` nie ma już stałego zestawu GSC/Ahrefs. Z API-owned
`source_connectors` buduje chipy dla faktycznie powiązanych źródeł (GSC, GA4,
Ads, Ahrefs), a freshness assessment oznacza źródło jako `w dowodach`,
`wymaga odświeżenia` albo `zablokowane`. Dzięki temu BDO pokaże Ads, gdy Ads
jest w jego lineage, ale nie będzie udawać GA4/Merchant/Localo bez exact
powiązania. Focused test 1/1 i dashboard typecheck przechodzą.

### 2026-07-19 — legacy landing identity jest rozstrzygane przed bounded LIMIT

`list_metric_facts_for_content_url` używa teraz istniejącego, tymczasowego
resolvera legacy URL do wyliczenia prywatnego landing identity przed SQL
LIMIT. Funkcjonalne query na tej samej ścieżce nie mogą już zająć limitu i
wpłynąć na wynik exact page; publiczny limit nadal jest nakładany dopiero po
identity filtering i enrichment history. Zachowano poprzednią wartość/delta,
więc measurement nie traci historii. Falsyfikator wymusza LIMIT=1 z nowszym
interloperem i nadal zwraca właściwy exact evidence oraz poprzednią wartość;
2 testy metric-store, Ruff, mypy i diff-check przechodzą.

### 2026-07-19 — selected workflow zachowuje realne agregaty GSC

Typed `ContentWorkItem` i shared schema przenoszą teraz istniejące agregaty
GSC do snapshotu: kliknięcia, wyświetlenia, CTR, pozycję, liczbę zapytań i
primary query. Pasek źródeł pokazuje te liczby przy GSC, ale tylko gdy GSC jest
w lineage wybranej strony; stale/zablokowane źródło nadal ma pierwszeństwo nad
liczbą. Live BDO snapshot: 266 wyświetleń, 1 kliknięcie, CTR 0,3759%, pozycja
8,5, 18 zapytań, `bdo co to`. Focused chip test, dashboard typecheck,
dynamic-input test, Ruff, mypy i diff-check przechodzą.

### 2026-07-19 — realny initial draft przeszedł do trwałej rewizji v2

Po dynamicznym odczycie kanonicznego WordPress REST i wygenerowaniu propozycji
planowania dla `ekologus_service_environmental_consulting_outsourcing` powstała
trwała rewizja v2 `content_revision_62c7467f39b74033b399e8ad166674c5`.
Zawiera page assets, 4 sekcje, 3 FAQ, 2 CTA i link wewnętrzny; jej digest to
`57f4c6b00d288787bc9bd9b0facc6953bec6d5c8022fef33be7831cfbada0edc`, a
`publish_ready=false`. Initial draft jest realnym readbackiem dokumentu,
nie tylko podglądem modelu.

Quality review nie blokuje już wersji v2 wyłącznie dlatego, że publication-bound
measurement window nie może istnieć przed publikacją. Przed handoffem pokazuje
informację `measurement_window_pending_publication`; stary blocker pozostaje dla
payloadów bez exact revision. Semantic review nadal ma osobny, uczciwy blocker
`storage_activation_required` do maintenance window.

### 2026-07-19 — review exact revision zna lineage całego dokumentu

Walidacja decyzji człowieka nie ogranicza się już do evidence sekcji. Dopuszcza
lineage z sekcji, FAQ, CTA i linków wewnętrznych zapisanych w tej samej rewizji
v2, nadal odrzucając dowody spoza snapshotu. Falsyfikator
`test_revision_review_accepts_lineage_from_all_page_assets` przechodzi razem z
Ruff i mypy dla routera oraz testu.

### 2026-07-19 — exact digest nie dominuje pierwszego widoku review

Panel rewizji pokazuje marketerowi najpierw tytuł, liczbę sekcji i źródeł;
pełny digest exact wersji pozostaje dostępny w rozwijanych szczegółach
technicznych. Zachowano trace dla supportu bez wypychania identyfikatora nad
tekst i decyzję. Focused dashboard review tests: 5 passed; typecheck przechodzi.
Po advisory second opinion dodano też fallback licznika źródeł, więc niepełny
snapshot nie może wyświetlić `undefined źródeł`. Po poprawce focused review tests
ponownie: 5 passed; typecheck przechodzi.

Pełny review surface pokazuje teraz również liczbę FAQ, CTA i linków wewnętrznych,
a licznik evidence obejmuje lineage wszystkich tych assetów, nie tylko sekcji.
To odpowiada backendowej walidacji exact revision i nie zmienia żadnej władzy
approval. Focused dashboard review tests: 5 passed; typecheck przechodzi.
Po drugim checkerze dodano opcjonalny dostęp i fallbacki dla liczników oraz
lineage kolekcji assetów, więc częściowy payload nie wywraca review surface.
Focused dashboard review tests: 5 passed; typecheck przechodzi.
Status badge kroku `draft` również nie pokazuje już skróconego digestu; mówi
po prostu, że zapisana wersja jest aktualna, a exact trace pozostaje w
szczegółach technicznych.

Rozwijane źródła review renderują teraz również pełne lineage FAQ, CTA i linków
wewnętrznych, nie tylko sekcji. Marketer może sprawdzić cały dokument w jednym
read-only miejscu przed decyzją człowieka. Focused dashboard review tests:
5 passed; typecheck przechodzi.
Hardening dopina też spread fallbacków `?? []`, więc brak którejkolwiek
kolekcji assetów nie wywołuje wyjątku podczas liczenia evidence.

### 2026-07-19 — świeży odczyt nie może wywrócić wybranego workflow

Po celowanym, read-only odczycie GA4 dla strony
`/informacja-o-opakowaniach-i-odpadach-opakowaniowych-oraz-o-oplacie-produktowej/`
oraz GSC z tego samego adresu zapisany wcześniej wybór usługi outsourcingowej
przestał być aktualną kandydaturą. Snapshot wcześniej kończył się 500 przez
`ValueError`; teraz dynamiczny matcher zwraca typed blocker
`stale_service_selection`, pokazuje aktualną listę kandydatów i bezpieczny krok
ponownego wyboru. Nie ma automatycznego przepisywania usługi ani zgadywania.
Focused falsifier przechodzi, Ruff przechodzi, a live snapshot zwraca `blocked`
z jawnym powodem zamiast błędu serwera.

Ten sam świeży odczyt dostarczył GA4 evidence
`ev_refresh_refresh_google_analytics_4_adb22a10fd9a`: okno 2026-06-21—2026-07-18,
1 exact target row, 3 aktywnych użytkowników z `google / organic`; key events i
konwersje pozostają niezweryfikowane. GSC evidence
`ev_refresh_refresh_google_search_console_7a17272e2612` ma okno 2026-07-17,
495 wierszy query/page i `partial_possible`; nie używamy go do trendu ani
przyczynowości.

### 2026-07-19 — dynamiczne dopasowanie obsługuje odmiany polskich zapytań

Po usunięciu stale selection okazało się, że świeży temat `Gospodarka
opakowaniami` nadal nie odzyskiwał karty usługi: matcher porównywał literalne
tokeny, mimo że karta używa celowego stema `opakowani`. Wydzielony, mały seam
`wilq/content/knowledge/text_matching.py` zachowuje exact match i dodaje
ograniczone dopasowanie prefiksu dla tokenów o długości co najmniej 5 znaków;
body strony nadal jest używane tylko przy exact service lineage, więc nawigacja
nie może przypisać obcej usługi.

Focused service matching/profile tests: 9 passed; Ruff, mypy i complexity audit
przechodzą bez naruszeń. Live snapshot strony opakowaniowej zwraca teraz
`bound/ready`, kartę `ekologus_service_environmental_consulting_outsourcing`
oraz drugiego kandydata `ekologus_service_waste_packaging_obligations`, oba z
matched term `opakowani`; ranking nadal pozostaje jawny i reviewable.

### 2026-07-19 — artykuł o pozwoleniu dostaje jawny kandydat review-required

Exact snapshot `analiza-pozwolen-zintegrowanych` wcześniej pozostawał `unbound`,
mimo że materiał WordPress zawierał realny kontekst dokumentacji. Matcher
otrzymuje teraz ograniczoną fleksję: exact prefiks pozostaje bez zmian, a
odmieniony token jest dopuszczany tylko przy wspólnym rdzeniu ≥5 znaków i
75% długości krótszego tokenu, z wyłączeniem krótkich/broad stemów typu
`odpady`. Materiał `wordpress_rest.content` jest traktowany jako zaufany,
wydzielony body input; test na nawigacji artykułu nadal blokuje przypadkowe
przypisanie outsourcingu.

Focused matching/profile tests: 10 passed; Ruff, mypy i complexity audit
przechodzą. Live snapshot: GSC 2 wyświetlenia, 0 kliknięć, pozycja 9, 2 query,
service `ekologus_service_environmental_compliance_audit`, status
`review_required`; brak twierdzenia o skuteczności lub trendzie.

### 2026-07-19 — panel nie sugeruje marketerowi ukrytego wyboru strony

Katalog `/content-workflow` już zawiera pełny read-only inventory WordPressa
(808 adresów, 73 z materiałem), ale copy aktywnej sesji mówiło wcześniej, że
„WILQ wybrał stronę”. Zmieniono je na neutralne „Strona do pracy” i wskazanie,
że marketer może przełączyć się na dowolny adres z inventory. Nie zmieniono
mechanizmu ani API: nie ma automatycznego wyboru ani publikacji, a kliknięcie
„Rozpocznij workflow” nadal otwiera dokładnie wybrany `work_item_id`.
Focused dashboard test i typecheck przechodzą.

### 2026-07-19 — realny BDO proposal zapisany przez API-owned Codex seam

Z dokładnego snapshotu BDO zbudowano `ContentPlanningInput` v6 z digestem
`71f98e22c830430f6126dfb3b3f654b5692c89f4a5616a6f93e432a4864f1ee4`:
7 sekcji inventory, 2 source facts i wszystkie 10 ocen źródeł. Brakujące GA4,
Ads, Ahrefs i Keyword Planner pozostały `missing`; Merchant, Localo i Social
pozostały `not_applicable`.

POST przez `/api/content/work-items/{id}/planning-proposals` uruchomił realny
server-side Codex run `codex_content_planning_e3ccc6ace99f47b7bdf5b85b82336a7d`
i trwale zapisał proposal
`content_planning_proposal_2e21360b96f44c609811490d6d1aec74`, version 16,
status `ready`. Readback po reloadzie zwraca ten sam proposal i digest bez
ponownego model call. Proposal ma 7 stabilnych sekcji, 8 exact GSC query, 3 FAQ
i pełne title/H1/lead/meta assets. Pozostaje niezatwierdzony: marketer/owner
muszą ocenić zakres i kartę usługi; mapa sekcji nie jest osobnym głosowaniem.

Próba przejścia dalej przez `POST /initial-draft` została uczciwie zatrzymana
typed blockerem `planning_not_approved`; nie uruchomiła modelu i nie zapisała
częściowej rewizji. To jest właściwa granica człowieka: zatwierdza zakres i
usługę, nie ręcznie mapuje sekcji.

### 2026-07-19 — outsourcing proposal odtworzony po zmianie exact inventory

Po dynamicznym matcherze i świeżym odczycie `the_content` poprzedni outsourcing
proposal stał się `stale`; nie został ponownie użyty. Zbudowano nowy input digest
`736572b57edfb9d1604ede254369e4d8d4946fbcdd4c0e24bec791e623633728` z 1
rzeczywistą sekcją, 2 source facts, exact GSC i exact GA4 oraz brakującymi
Ads/Ahrefs/Keyword Planner.

Nowy run `codex_content_planning_7085fbc5d5ab4d25b65d0ce7ac94c522` zapisał
proposal `content_planning_proposal_d77cf0828c3849518726aaee8e18ef94`, version
6, status `ready`: 3 sekcje, 2 FAQ, 2 query i komplet page assets. Stara wersja
nie jest traktowana jako aktualna. Nowy proposal nadal wymaga scope/service
review przed initial draft.

### 2026-07-19 — panel uczciwie oznacza rewizję z nieaktualnym kontekstem

Dashboard nie pokazuje już każdej zapisanej rewizji jako bieżącego draftu. Gdy
API zwraca `revision_workspace.context_current=false`, status brzmi teraz
„Zapisana wersja · wymaga odświeżenia”; historia rewizji pozostaje zachowana, a
istniejące bramki `revision_context_changed` nadal decydują o dalszej pracy.

Focused regression (1 test) i dashboard typecheck przechodzą. Zmiana została
niezależnie sprawdzona przez advisory checker; wynik jest evidence-bounded i nie
jest akceptacją produktu ani gotowości do publikacji.

### 2026-07-19 — placement CTA nie może wskazywać sekcji usuniętej po review

Planowanie odrzuca teraz CTA albo link, którego placement wskazuje sekcję z
`remove_review_required`. Guard działa zarówno na świeżym modelowym outputcie,
jak i przy readbacku już zapisanej propozycji; rozpoznaje heading oraz stabilne
`section_id`/`inventory_section_id`. Nie przenosimy elementu automatycznie.

Realny readback WILQ po restarcie potwierdził guard: BDO proposal
`content_planning_proposal_2e21360b96f44c609811490d6d1aec74` zwraca typed
`quality_gate_failed` z `orphaned_placement`; outsourcing pozostaje `ready`.
Focused falsifier, Ruff i diff-check przechodzą. To nie jest jeszcze zgoda na
scope, pełny draft ani publikację.

### 2026-07-19 — brak dopasowanej usługi nie udaje wyboru

Zakres workflow ma teraz jawny stan pustego dopasowania: gdy API nie zwraca
żadnej karty usługi, select jest wyłączony, pokazuje „Brak dopasowanej usługi”,
a panel prowadzi do Service Profile zamiast pozwalać wybierać usługę z samego
tematu. Przy istniejących kandydatach zachowanie pozostaje bez zmian — marketer
widzi lifecycle, powody dopasowania i może potwierdzić właściwą kartę.

Focused panel suite: 9 testów; dashboard typecheck i diff-check przechodzą.
Follow-up advisory checker zaakceptował mechanikę; pozostałą uwagę o wiring
zaklasyfikowano jako lukę cytowania i zamknięto lokalną inspekcją. Nie jest to
dowód kompletności matcherów ani owner review kart.
### 2026-07-19 — dynamiczny placement planu respektuje sekcje wymagające usunięcia

W instrukcji planowania CTA i linki są teraz jawnie wiązane z dynamiczną mapą inventory: placement może wskazywać tylko `after_lead`, `after_content` albo konkretną sekcję, która pozostaje użyteczną odpowiedzią dla czytelnika. Sekcja oznaczona `remove_review_required` nie może być miejscem CTA/linku; istniejący model/odczyt nadal fail-closed przez `quality_gate_failed/orphaned_placement`. To nie wymaga ręcznego zatwierdzania każdej sekcji — mapę wyznacza inventory ACF/the_content, a człowiek zatwierdza zakres i usługę.

Focused proof: Ruff oraz `tests/content/test_planning_output_contract_limits.py -k 'compactness or removed_section'` (2 passed). Live BDO rerun z tym samym digestem ponownie zakończył się `blocked/orphaned_placement`; outsourcing pozostaje `ready`. Nie twierdzę, że BDO ma gotowy plan ani draft; wymaga nowego poprawnego fixed pointu.

### 2026-07-19 — kryteria v5 odblokowały świeży dynamiczny BDO fixed point

Ponieważ zmiana bramki jakości musi unieważnić starszy plan, `ContentPlanningInput.criteria_version` i wspólny schemat przeszły z `wilq_people_first_planning_v4` na v5. Live GET oznaczył poprzedni BDO proposal jako `stale` (digest `71f98e22…`), a świadomy POST z nowym exact digestem `81a39f23…` wygenerował przez API-owned Codex seam proposal `content_planning_proposal_d67afa3376b046d8bdab27c9e582ef4e` (`ready`, criteria v5).

Nowy plan ma 7 sekcji z dynamicznego inventory, 2 CTA (`after_lead`, `after_content`) i 1 link osadzony w zachowanej sekcji. Dated training material dostał `remove_review_required`; żadna CTA ani link nie wskazuje usuniętej sekcji. To dowodzi świeżego planu i kontraktu placementu, nie akceptacji, pełnego draftu, semantic review ani publikacji.

Focused proof: Ruff, 3 testy dynamic input, 2 testy contract limits i shared-schema TypeScript `tsc --noEmit` passed. No vendor write.

### 2026-07-19 — oba exact piloty przeszły ten sam dynamiczny planner v5

Po tym samym bumpie kryteriów wygenerowano drugi case: `ekologus_service_environmental_consulting_outsourcing`, digest `43fbabec…`, proposal `content_planning_proposal_1b298307e78d453ab5d2ff2e069d64e7`, `ready`, criteria v5. Jego inventory ma jedną istniejącą sekcję, poprawnie zmapowaną po `inventory_section_id`; cztery kolejne sekcje zostały utworzone dynamicznie, bez `unmapped` ani `ambiguous`. Plan ma 2 CTA i link `after_content`.

Wraz z BDO (`content_planning_proposal_d67afa3376b046d8bdab27c9e582ef4e`) daje to dwa różne adresy, karty usług i kształty inventory obsłużone przez ten sam API-owned kontrakt. Oba plany pozostają niezatwierdzone; semantic storage, pełne rewizje, human acceptance i draft-only handoff są nadal otwarte.

### 2026-07-19 — granica plan → pełny draft jest jawna i nie wymaga review sekcji

Live `GET /initial-draft` dla obu świeżych proposalów zwraca typed `stale_planning_input`, ponieważ istniejące scope decisions należą do poprzednich digestów v4. To jest poprawny blocker: nie zapisuję fałszywej akceptacji w imieniu Wilku. API ma `section_map_current=true` na podstawie wygenerowanych sekcji; marketer zatwierdza tylko aktualny zakres/usługę, a mapa ACF/the_content pozostaje automatyczna.

Świeży katalog ma 808 adresów publicznego sitemapu, pełne pokrycie tego odczytu i jawne rozróżnienie `content_and_structure` / `url_only`; nie oznacza to kompletności ACF. Korpus wiedzy Ekologusa pozostaje częściowy: 7/15 materiałów ma kontrolowany redacted import, 8 czeka na owner-governed ingest. Nie uruchamiam pełnego draftu ani semantic storage bez odpowiedniej decyzji/maintenance window.

### 2026-07-19 — snapshot performance: cache exact inventory metric batch

Profilowanie selected snapshot wykazało, że `inventory_metric_facts()` odbudowywał legacy landing index przy powtarzanych odczytach GSC/GA4. Dodałem 15-sekundowy, read-only cache związany z URL/path oraz ID i evidence IDs najnowszego vendor-read refreshu. Zmiana nie może przenieść danych między batchami; istniejąca filtracja latest evidence pozostaje aktywna.

Focused proof: Ruff i 2 testy `test_inventory_catalog.py -k 'metric_facts'` passed. Po restarcie live snapshot warm: BDO ~1,94 s (wcześniej ~3,3 s), outsourcing ~1,21 s (wcześniej ~2,0 s); cold BDO ~9,43 s pozostaje osobnym klastrem import/diagnostics. Claude checker nie wyemitował JSON, więc nie przedstawiam review jako PASS.

Kolejny micro-slice performance: content diagnostics korzysta teraz z istniejącego `list_actions_cached()` zamiast odbudowywać registry akcji przy każdym cold snapshot. `tests/test_content_diagnostics.py` (7) i Ruff passed. Cold start pozostaje osobnym problemem; nie deklaruję pełnego rozwiązania latency.

### 2026-07-19 — measurement evidence nie skanuje ponownie tego samego refresh snapshotu

`load_content_measurement_evidence()` ma teraz krótki, read-only cache związany z konkretnym store, URL/path oraz najnowszymi run IDs, statusami i evidence IDs dla WordPress, GSC i GA4. Cache wygasa po 15 sekundach, a nowy refresh identity wymusza ponowny odczyt; exact URL/path filtering i agregacja pozostają bez zmian.

Focused proof: `tests/content/test_measurement_aggregates.py` 9/9, Ruff i `git diff --check` passed. Live selected BDO snapshot readback: 4269 ms cold, 1880 ms i 1937 ms warm. To jest kierunkowy pomiar jednej ścieżki, nie obietnica uniwersalnego SLA. Bounded Claude checker zakończył się przed schema output; disposition pozostaje `evidence_gap`, bez PASS ani approval: `/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-measurement-evidence-cache-GxSrWB/disposition.md`.

### 2026-07-19 — cache diagnostyki unieważnia się po nowym refreshu

Główny cache `content_diagnostics` nie opiera się już wyłącznie na TTL. Przechowuje
ID, status i evidence IDs najnowszego refreshu każdego content connectora; nowy
refresh wymusza rebuild, a `content_diagnostics_cache_ready` również odrzuca stary
identity. To chroni decyzje marketera przed chwilowym pokazaniem danych sprzed
odświeżenia, zachowując reuse podczas startup waterfall.

Focused proof: `tests/test_content_diagnostics.py` 8/8, Ruff, mypy i diff-check
passed. Live BDO snapshot: 5206 ms cold, 2756 ms i 2455 ms warm; freshness `fresh`
z jawnymi connector refresh run IDs. Checker Claude odrzucił niewalidowany output
przez cytację ponad 20 linii (`F-3`); nie traktuję go jako PASS:
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-diagnostics-refresh-identity-final-6sTMAN/disposition.md`.
### 2026-07-19 — produkcyjny lint i typowanie są domknięte

Jednorazowy cross-surface verify potwierdził: marketer-language guard, skill
hygiene, Ruff produkcyjny, `uv run mypy wilq apps/api --no-incremental` (382
plików) oraz oba dashboard/shared typechecki przechodzą. Usunięto trzy ostatnie
produkcyjne Ruff findings w WordPress inventory, measurement aggregates i
semantic-review service (`0100be4d`). Focused inventory/measurement/semantic
read-path proof: 30 testów.

Verify nadal zatrzymuje się na kolekcji dwóch historycznych testów, które
importują usunięte helpery i legacy revision-plan routes (404). Nie przywracam
usuniętych powierzchni tylko dla zielonego testu; pozostaje to jawny dług
testów/retired API. Bounded checker dla fixed pointu jest schema-valid, ale ma
wyłącznie evidence gaps (brak bezpośrednich diff/AST excerpts); disposition:
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-19-production-ruff-cleanup-final-DccFi8/disposition.md`.

### 2026-07-19 — verify nie ładuje już usuniętych legacy testów

Usunięto wyłącznie testy, które wywoływały skasowane endpointy
`revision-plan`/`revision-apply` albo dawny ręczny payload measurement window.
Aktualny łańcuch preflight → brief → draft → human review → WordPress draft-only
pozostał, a focused quality/brief suite przechodzi 16/16. `pytest --collect-only`
przechodzi bez import errors.

Jednorazowy szeroki verify doszedł do 438 passed, ale ujawnił 9 niezależnych
starych oczekiwań kontraktowych w action mockach, context cards, daily-check,
Ahrefs, Localo i Ads snapshot; został przerwany po 491 s, bez claimu PASS. To
następny cluster migracji testów do aktualnych typed seamów, nie powód do
przywracania usuniętego API.

### 2026-07-19 — context-pack dynamicznie domyka lineage kart wiedzy

Content diagnostics i kompilator source-facts są osobnymi właścicielami danych,
więc context-pack nie zakłada już, że ich listy kart przypadkiem się pokrywają.
Dla content skills API dynamicznie zbiera `knowledge_card_ids` z bieżącej
`decision_queue`, dołącza wyłącznie wskazane playbook cards oraz zachowuje
source-backed karty Ekologusa jako główny materiał dla operatora. Ten sam
mechanizm działa dla scoped i `full_context` requestu; nie ma ręcznego mapowania
sekcji ani wyjątku dla pilota.

Focused proof: content contract PASS, Ruff i mypy dla trzech modułów PASS. Live
context-pack po restarcie: 15 kart (12 kart Ekologusa + 3 dokładnie
referencjonowane playbooki), 0 brakujących ID lineage, 1000 evidence summaries i
12 connector statuses. To naprawia spójność wejścia do planowania; nie jest
jeszcze dowodem pełnego draftu ani publikacji.

W tym samym seamie operator content dostał również `content_diagnostics` i
`content_preflight` w scoped context-packu. Wcześniej operator widział karty i
akcje review, ale nie kolejkę decyzji; teraz strategist i operator korzystają z
jednego diagnostyku API, bez osobnej ścieżki modelowej.

Focused proof: `test_content_operator_context_pack_exposes_service_profile_review_actions`
oraz Ruff PASS.

### 2026-07-20 — content context nie ucina już katalogu kart Ekologusa

Usunięto sztuczny limit `[:12]` z `content_knowledge_cards_for_skill`. Katalog
kart jest już kompaktowany dopiero na granicy context-packu, więc wybór dowolnej
aktualnie dostępnej usługi lub reguły Ekologusa nie traci swojej karty tylko
dlatego, że sortowanie umieściło ją dalej na liście. To jest mechanizm ogólny,
nie wyjątek dla BDO ani outsourcingu.

Focused proof: test równości katalogu source-backed cards, Ruff i mypy PASS.
Live operator context po reloadzie: 22 karty `ekologus_*`, 51 decyzji
diagnostycznych i 36 evidence summaries. Nie oznacza to jeszcze owner review
wszystkich kart ani gotowości pełnego draftu.

### 2026-07-20 — outsourcing odzyskał aktualny, reviewable planning fixed point

Krótki test lokalnego Codex app-server zakończył się poprawnym structured
JSON-em bez próby tool call, więc odświeżyłem wyłącznie przeterminowany plan
outsourcingu przez istniejący API-owned endpoint. POST zwrócił `generating`, a
GET po zakończeniu odczytał proposal
`content_planning_proposal_e3dcd3dfc621403dbc57760cd673b992`, run
`codex_content_planning_7dc6a18992904db69bd2ba10330d81f9` i digest wejścia
`23d20cacf8026625bec3d6f246082e2a66d3fb51215c534e6e07cd4f8131f697`.

Plan ma 12 sekcji, 3 FAQ, 2 CTA, 1 link i pełną lineage evidence dla sekcji;
6 sekcji ma `rewrite`, 1 `merge`, a 5 pozostaje
`remove_review_required`. Źródła zostały ocenione jawnie: WordPress,
Service Profile i GSC `used`; GA4, Ads, Ahrefs i Keyword Planner `missing`;
Merchant, Localo i Social `not_applicable`. Snapshot poprawnie pokazuje
`scope_current=false`, więc nie uruchamiam draftu ani nie udaję approval.

### 2026-07-20 — blocker pełnego draftu nie żąda już review sekcji

Typed `planning_not_approved` i snapshot workspace prowadzą teraz marketera do
jednej decyzji: aktualny zakres i usługa. Komunikat jawnie mówi, że mapa sekcji
jest wyliczana automatycznie z inventory, zamiast sugerować osobne zatwierdzanie
nagłówków. To porządkuje UX bez zmiany bramki bezpieczeństwa: bez aktualnego
scope review pełny draft nadal nie startuje.

Focused proof: 9 testów initial-draft/status, Ruff i mypy; live outsourcing GET
zwraca `blocked/planning_not_approved` z nowym następnym krokiem.

### 2026-07-20 — query mapping używa tego samego dynamicznego inventory co plan sekcji

Naprawiono rozjazd w budowie planning input: po odczycie snapshotu portfolio
zapytań nie bierze już surowej listy `wordpress_section_headings`. Korzysta z
tego samego rozstrzygniętego inventory, które wybiera dostępne nagłówki ACF albo
publiczny `the_content`. Dzięki temu mapowanie metryk → sekcji pozostaje
dynamiczne także dla stron, których układ jest wystawiony przez ACF.

Focused proof: test ACF-vs-`the_content` inventory mapping 15/15, Ruff i
`git diff --check` PASS.

### 2026-07-20 — wybrana strona nie zastępuje już całej kolejki

Endpoint lekkiej kandydatury dla jawnie wskazanego `work_item_id` zwraca jedną
stronę, żeby pierwszy ekran nie czekał na ciężki diagnostyk. Dashboard błędnie
traktował tę odpowiedź jako całą kolejkę, przez co po wejściu bezpośrednim
picker pokazywał jedną stronę zamiast wszystkich dostępnych adresów. Hook teraz
ładuje lekką kandydaturę natychmiast i scala ją z pełnym katalogiem w tle; strony
nie giną, a nieznany w katalogu wybrany adres pozostaje widoczny z własnym
blockerem.

Focused proof: typecheck dashboard PASS; dedykowany merge test 2/2 PASS. Pełny
`ContentWorkflowSurface` ma jeden niezależny, wcześniejszy kontraktowy fail
(`getByText` znajduje dwa już renderowane statusy GA4); nie zmieniałem testu ani
nie udawałem PASS całego pakietu.

### 2026-07-20 — statusy źródeł nie dublują się w panelu planu

Usunięto rzeczywiste powtórzenie statusu źródła w `ContentPlanningGenerationPanel`:
widoczny chip nadal pokazuje krótką decyzję, a rozwijane „Dlaczego ten stan?”
pokazuje teraz techniczny format `Źródło · status` wraz z powodem. Nie znika
żadna informacja o GA4/Ads ani lineage, ale marketer nie czyta dwa razy tego
samego komunikatu.

Focused proof: ContentWorkflowSurface + ContentPlanningGenerationPanel 41/41,
dashboard typecheck PASS, `git diff --check` PASS.

### 2026-07-20 — ranking usługi respektuje intencję strony przed szumem treści

Dopasowanie kart usług zachowuje teraz osobny sygnał priorytetowy z tematu,
tytułu, adresu i zapytań. Najpierw wygrywa dokładna lineage URL, następnie
termin występujący w tym sygnale, dopiero później długość frazy i lifecycle
karty. Dzięki temu artykuł o operacie wodnoprawnym nie jest rekomendowany jako
Eko-Opieka tylko dlatego, że pełny `the_content` zawiera ogólne słowa „terminy”
albo „decyzje”. Mechanizm jest wspólny dla wszystkich usług; nie ma wyjątku dla
operatu, BDO ani outsourcingu.

Focused proof: `tests/content/test_service_matching_surface.py` oraz
`tests/content/test_work_item_service_profile.py` — 11/11, Ruff PASS.

### 2026-07-20 — selected-page snapshot nie skanuje legacy indeksu przy każdej ścieżce

Pomiar selected-page snapshotu wykazał, że `inventory_metric_facts` tracił
większość czasu na budowanie tymczasowego indeksu legacy URL-i z całej tabeli
DuckDB. Dla zwykłych adresów bez funkcjonalnego query stringu odczyt filtruje
legacy wprost w SQL i nie uruchamia tego indeksu. Funkcjonalne adresy zachowują
stary indeks, bo musi on rozstrzygać query identity przed bounded limit.

Focused proof: istniejące testy bounded landing identity, GA4 relative path i
inventory catalog — 3/3; Ruff PASS. Na realnym selected work item czas
`inventory_decision_for_work_item` spadł z 6,753 s do 2,262 s, a HTTP snapshot
z timeoutu >10 s do 4,119 s; odpowiedź nadal zawiera usługę
`ekologus_service_operat_wodnoprawny` i pełne candidate lineage.

### 2026-07-20 — dashboard nie odświeża bez potrzeby read-only kontraktów

Read-only query hooks `/content-workflow` dostały jawne okna freshness: katalog
i profile 30 sekund, snapshot/enrichment 10 sekund, a status planu 5 sekund
z zachowaniem szybszego pollingu tylko podczas `generating`. Mutacje nadal
unieważniają właściwe query keys, więc nie opóźnia to decyzji po zapisaniu scope,
rewizji ani draftu. Zmiana redukuje powtarzane odczyty przy refocusie i remoncie
komponentów, bez zmiany API, metryk ani blockerów.

Focused proof: `ContentPlanningGenerationPanel.test.tsx` 5/5 oraz dashboard
typecheck PASS; pełny pakiet ujawnił wcześniejszy, niezależny fail architektury
(`ContentWorkflowArchitecture`: zakaz `<details>` niezgodny z obecnym
knowledge-readiness disclosure), którego nie przypisuję tej zmianie.

### 2026-07-20 — knowledge readiness ma własnego właściciela prezentacji

Przeniesiono disclosure gotowości korpusu źródłowego do
`ContentKnowledgeReadinessNotice`. Route `ContentWorkflowSurface` pozostaje
orkiestratorem typed state i nie zawiera już własnego `<details>` ani logiki
renderowania listy materiałów. Tekst, stany loading/error/blocked i identyfikatory
testowe pozostały bez zmian.

Focused proof: architektura dashboardu 4/4, knowledge-readiness cases 4/4,
typecheck PASS.

Pełna regresja dashboardu po refaktorze: 51 plików, 212 testów PASS oraz
typecheck PASS. To jest proof zachowania powierzchni po przeniesieniu notice,
nie dowód jakości finalnego tekstu ani realnego Wilku UAT.

### 2026-07-20 — knowledge surface pokazuje realną liczbę zatwierdzonych faktów

Usunięto stałe `0` z kafla „zatwierdzonych”. Wartość jest teraz liczona z
API-owego rejestru source facts i obejmuje wyłącznie rekordy
`generation_status=eligible`; fakty `blocked_review_required` nie są mylone z
wiedzą produkcyjną. Etykieta mówi wprost o „zatwierdzonych faktach”, a nie o
zatwierdzonych kartach lub skuteczności treści.

Focused proof: `KnowledgeSurface.test.tsx` 3/3, dashboard typecheck i
`git diff --check` PASS.

### 2026-07-20 — panel planu pokazuje realne zmiany GSC/GA4

Planning input już wylicza exact page-scoped porównania GSC/GA4, ale poprzedni
shared response wystawiał tylko liczbę nazw metryk. Dodałem kompatybilne pole
`metric_comparisons` do `ContentPlanningInputSummary` oraz kompaktowy blok w
panelu strategii: connector, okres bazowy i porównawczy, rzeczywiste wartości,
status porównania i liczba evidence. Brak porównania pozostaje jawny jako
`brak porównania`/`niejednoznaczne`; UI nie tworzy targetów ani score'ów.

Focused proof: shared-schema round-trip z 12 → 19 kliknięć, panel 6/6,
dashboard typecheck i `git diff --check` PASS. Starsze odpowiedzi bez pola są
czytelne dzięki opcjonalności pola.

### 2026-07-20 — świeży BDO plan po read-only refreshu

Ten sam endpoint planning-proposals wygenerował nowy BDO fixed point po
odświeżeniu GSC/GA4: proposal `content_planning_proposal_a81059f558b5473197839c8d10639d5a`,
7 sekcji, 4 FAQ, 2 CTA, 1 link, 7 source-material IDs i 4 evidence IDs.
WordPress, Service Profile, GSC i GA4 są użyte; Ads, Ahrefs i Keyword Planner
pozostają `missing`, a Merchant/Localo/Social są `not_applicable`. GSC i GA4
mają match `exact`, ale porównania okresów pozostają `not_available`, bo
pojedynczy snapshot nie jest trendem. `publish_ready=false`.

Initial draft nadal zwraca `stale_planning_input`, ponieważ istniejąca decyzja
scope jest związana ze starszym digestem. To poprawny blocker — nie wykonano
auto-approval ani vendor write.

Bounded second-opinion dla tego fixed pointu zwrócił jeden HIGH dotyczący
braku artefaktu w izolowanej sesji review oraz trzy evidence gaps. Nie jest to
finding produktu ani PASS; lokalny zapis znajduje się w katalogu review.

### 2026-07-20 — API nie przyjmuje już ręcznej decyzji mapy sekcji

Usunięto drugą władzę nad mapą sekcji: POST `planning-review` z
`stage=section_map` zwraca teraz typed `409`, a historyczne decyzje pozostają
czytelne w workspace. Jedynym źródłem mapy jest wygenerowana propozycja z
aktualnego inventory/usługi/evidence; człowiek zatwierdza scope i później exact
revision, nie nagłówki. Draft gate nie został poluzowany.

Focused proof: route/revision planning tests, planning-review gate,
contract inventory 5/5, Ruff, dashboard typecheck i `git diff --check` PASS.
