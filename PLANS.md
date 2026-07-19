# WILQ — kanoniczny plan doprowadzenia do używalności

Status: aktywny, długotrwały plan wykonawczy. Właścicielem zadań i zależności
pozostaje Beads (`wilq-seo-1oa`); ten plik definiuje produkt, standard i kolejność.
Nie jest historią commitów ani listą zastępczą dla Beads.

### Checkpoint 2026-07-19 — fixed point po browser-proof `/content-workflow`

Ostatni utrwalony stan obejmuje serię runtime i lineage hardening slices. `GET /initial-draft` nie
pokazuje już starej rewizji jako aktualnej po nowszym planning jobie z innym
digestem; zwraca typed `stale_planning_input` bez model call. Measurement
aggregator scala powtórzone exclusions per `code/source/metric/period`,
zachowując pełną union evidence IDs. Świeży WILQ API context: 12 konektorów,
9 skonfigurowanych, 2 brakujące credentials; brief ma 1 blocker, 3
rekomendacje i 17 evidence IDs; kolejka ma 54 kandydatów, z czego 53 są
actionable. Exact BDO readback ma 35 faktów i 4 wykluczenia `wrong_period`.
Oba piloty planowania nadal kończą się typed `runtime_failed` z
`codex_response_stream_disconnected`; queued digest, terminalny `CodexRun.id`
i persisted readback są zachowane;
pełna generacja, semantic storage, jakość tekstu i UAT pozostają nieudowodnione.

Ostatni wypchnięty commit: `e615205d` (`perf(runtime): keep daily brief warm for marketer sessions`).
Po zmierzonym cold-starcie `/api/marketing/brief` (4,056 s) i kolejki (2,820 s)
po wygaśnięciu 30-sekundowego cache domyślny TTL read-only daily runtime wynosi
300 s. Env override i jawne connector freshness pozostają bez zmian; focused
cache contract i Ruff przechodzą. To nie jest dowód produkcyjnej wydajności ani
UAT.
Pełny `apps/dashboard/e2e/content-workflow-layout.spec.ts` przechodzi 6/6 w
jednym przebiegu; obejmuje desktop/mobile, inventory-bound workflow, planning,
Codex section rewrite oraz save → reload → exact review → draft-only wizard.
To synthetic proof, nie UAT ani zgoda na vendor write. Selektory testu zostały
związane z aktualnymi etykietami UI i payloadem `selected_section_headings`;
produkcja nie została zmieniona w tym slice.

Poprzedni wypchnięty commit: `c4780e8b` (`docs(plan): refresh long-running fixed point`).
Po tym punkcie social reuse zachowuje osobne `source_evidence_ids` historii
duplikacji w immutable proposal i blokuje reuse bez zatwierdzonego inventory;
live social history nadal jest `missing`. Audyt Ads obejrzał wszystkie 21
skryptów: każdy ma realnego callera i odrębne ryzyko kontraktowe, więc nie ma
udowodnionej bezpiecznej kasacji ani mechanicznego merge'u. Deterministyczny
Ads smoke nadal przechodzi na żywym API (6 walidacji akcji, 16 sekcji, 14
decyzji, 7 kart wiedzy). Bead pozostaje jawnie `in_progress`, dopóki nie
pojawi się konkretny caller diff uzasadniający redukcję powierzchni.

Poprzedni stan po `b266f65b` (`chore(beads): record run input binding`) został
zachowany w historii git; nie nadpisujemy go ani nie udajemy, że transport
Codexa, pełna generacja, semantic storage lub UAT są zamknięte.
Po poprzednim pomiarze doszły wspólny kontrakt deadline/stale job oraz izolacja
starych planning jobs po `service_card_id`: nowszy run innej usługi nie może już
unieważnić aktualnego proposal/draft statusu. Transport Codexa klasyfikuje
bezpiecznie stream disconnect ze stderr bez utrwalania payloadu. Niezależne review passy i dispositions
znajdują się poza repo w katalogu second-opinion-review; findings bez źródła
są klasyfikowane jako evidence gaps/reject, nigdy jako PASS.

## 1. Cel i granica produktu

WILQ jest API-first Marketing Operating System dla Ekologus. Ma pomagać
marketerowi analizować dane, wybierać decyzję, tworzyć i poprawiać treści,
przygotowywać kampanie oraz bezpiecznie przekazywać działania do sprawdzenia.
Dashboard i umiejętności Codexa są klientami jednego WILQ API. Nie tworzymy
konkurencyjnych plannerów, drugiego magazynu prawdy ani browser-to-model.

Główny rezultat dla marketera: z realnych danych i zatwierdzonych materiałów
powstaje zrozumiała decyzja, plan, tekst/page assets, review i bezpieczny
WordPress draft. Wartość jest ważniejsza niż liczba ekranów, score'ów i testów.

## 2. Standardy niepodlegające negocjacji

- Każdy fakt, query, claim, CTA, link i metryka ma źródło, identyfikator,
  freshness i lineage. Brak lub starość dowodu daje jawny blocker.
- Nie zgadujemy wolumenu, intencji, wyników, przewagi konkurencji, konwersji
  ani jakości. GSC nie jest kompletnym zbiorem zapytań.
- Surowe prywatne materiały, tokeny, dumpy vendorów i teksty z credentials nie
  trafiają do promptów, logów, paczek ani repo. Do modelu trafiają tylko
  zatwierdzone, zredagowane fakty z lineage.
- Człowiek zatwierdza service scope, claims, exact revision i ActionObject.
  Codex proponuje; nie zatwierdza, nie publikuje i nie wykonuje vendor write.
- WordPress pozostaje draft-only. Każdy write przechodzi przez exact revision,
  preview, human confirmation, safety checks i audit. Brak replayu starej zgody.
- Używamy istniejącego serwerowego Codex app-server i lokalnego logowania.
  Nie dodajemy API keya, Agents/SDK drugiej ścieżki, Ollamy ani bezpośredniego
  wywołania modelu z przeglądarki.
- Nie pokazujemy marketerowi technicznych etykiet jako treści produktu:
  `operator_local_dashboard`, „audyt”, „evidence” i digesty są szczegółem
  „Dlaczego”, a nie nagłówkiem. UI jest po polsku i używa języka decyzji.
- Nie używamy magicznego SEO/content score jako KPI. Deterministyczne bramki,
  advisory review i realna ocena SEO/content/marketera są rozdzielone.
- Zachowujemy istniejące dirty work i historię. Destrukcyjne czyszczenie,
  publikacja, credentials, deploy i push są osobną autoryzacją.

## 3. Doświadczenie marketera (docelowe 10/10)

Pierwszy ekran w około 30 sekund odpowiada: co widzimy, dlaczego teraz, jaki
jest wpływ, czego brakuje i jaki jest jeden następny krok. Marketer może
wybrać każdą dostępną stronę, usługę, artykuł i sekcję — nic nie jest
preselected BDO ani ograniczone do dwóch pilotów.

Kanoniczne kroki:

1. **Wybór** — strona/usługa/sekcja, cel, zakres i jawne potwierdzenie.
2. **Sygnały** — realne metryki, zapytania, źródła, świeżość i decyzja.
3. **Plan** — mapa sekcji, pytania czytelnika, claims, CTA, linkowanie i
   przypisania query/evidence.
4. **Tekst** — pełny page-like dokument: title, H1, lead, body, FAQ, CTA,
   meta i linki; można poprawić wybrane sekcje.
5. **Review i przekazanie** — findings, diff, exact revision, WP dry-run,
   human acceptance i dopiero potem ActionObject draft-only.

Na każdym kroku widoczne są: nazwa strony/usługi, etap, status, decyzja,
metryki i następny krok. Szczegóły lineage są rozwijane w „Dlaczego”. Reload
nie gubi stanu; mobile i desktop mają osobny browser proof.

## 4. Wydajność i zachowanie startu workflow

„Run workflow” nie może wyglądać jak zawieszona strona. Po wyborze dowolnego
elementu:

- pierwszy użyteczny widok (nazwa, decyzja, podstawowe metryki i blocker)
  pojawia się w maksymalnie kilku sekundach na ciepłym lokalnym stacku;
- queue i minimalny snapshot są priorytetem; katalog, authoring profile,
  activation packet, enrichment i ciężkie readbacki ładują się niezależnie,
  lazy albo po otwarciu właściwego kroku;
- żaden GET nie uruchamia Codexa, nie zapisuje propozycji i nie wykonuje
  vendora; błędy pobocznych odczytów nie blokują pierwszego ekranu;
- POST generowania planu zapisuje exact queued job i zwraca `generating`, a
  ciężki snapshot/Codex działa w tle po stronie API; GET tylko odczytuje stan
  i odpytuje go bez ponownego wywołania modelu;
- identyczny digest jest idempotentny, a znany konflikt digestu wraca jako
  `409 stale_input` przed uruchomieniem modelu;
- loading ma mieć osobne stany per panel, timeout i bezpieczny retry, bez
  10-minutowego spinnera. Mierzymy czas każdego endpointu w browser proof.
  Generowanie planu ma osobny bounded Codex deadline (domyślnie 120 s), niezależny
  od draftu i semantic review; przekroczenie zapisuje typed failure bez
  częściowego planu i zostawia retry.
- inventory WordPress może mieć wyłącznie krótki, read-only cache z jawnym TTL;
  daty odczytu, evidence IDs i status freshness pozostają widoczne, a materiał
  i propozycje nie są ukrywane za tym cache.
- optymalizujemy istniejące API seams (cache z poprawną freshness, selektywny
  payload, równoległe read-only calls), nie dodajemy drugiej ścieżki danych.

Wybrany adres jest interakcją priorytetową: queue może użyć katalogu i zwrócić
„materiał wymaga odczytu” bez synchronicznego pobierania pełnego HTML/ACF. Pełny
odczyt pozostaje API-owned, lineage-bound i blokuje plan/draft, jeśli nie da się
go potwierdzić. Katalog jest prewarmowany po gotowości API w tle; prewarm nie
zmienia freshness ani nie jest dowodem kompletności inventory.

Focused falsifier: Playwright wybiera losowy inventory item, klika Run
workflow i sprawdza widoczny decision panel przed zakończeniem secondary
requests; zapisuje czasy i endpointy.

## 5. Dane, źródła i treść

`ContentPlanningInput` jest wersjonowanym, jedynym wejściem planera i zawiera:
work item/canonical URL, kandydatury service cards i powody dopasowania,
potwierdzoną usługę, WordPress inventory, dokładne fakty, freshness,
evidence/knowledge IDs, status każdego konektora (`used`, `not_applicable`,
`missing`, `stale`, `blocked`) oraz digest inputu.

Transport do modelu jest osobną, niemutującą reprezentacją tego kontraktu:
pełny `ContentPlanningInput` pozostaje używany do digestu, walidacji, stale
detection i zapisu; model dostaje wszystkie query rows, ale bez pól `null` i
z ograniczoną powtarzalnością row-level evidence/heading arrays. Top-level
evidence IDs i output schema nadal obejmują pełny dozwolony zbiór.
Kompaktowanie nie może usuwać faktów z API ani zmieniać planning input digestu.
Wersja kryteriów `wilq_people_first_planning_v3` obejmuje także deterministyczną
bramkę odrzucającą nagłówki nawigacyjne, related-content, promocyjne i datowane;
zmiana kryteriów musi unieważnić starsze propozycje przez digest.

Każdy planning fact zachowuje osobno `source_fact_ids` i
`source_material_ids`; samo `evidence_id` lub `knowledge_card_id` nie jest
dowodem pochodzenia wypowiedzi Ekologusa. Materiał bez zaimportowanego,
zredagowanego i zatwierdzonego fragmentu pozostaje review-required i nie może
zasilać publish-ready draftu.
Matcher usług najpierw respektuje exact canonical URL powiązany z lineage
źródłowej karty, dopiero potem szerokie frazy z copy strony; wzmianka o BDO na
stronie outsourcingowej nie może zmienić jej usługi.

Źródła dobieramy kontekstowo: WordPress (realny `the_content`, ACF i struktura),
Service Profile, GSC, GA4, Ads, Ahrefs, Keyword Planner po tokenie, Merchant
tylko produkty, Localo tylko lokalne strony, Social tylko reuse zatwierdzonego
tekstu. Wszystkie dostępne konektory są oceniane, ale do planu trafiają tylko
dokładnie pasujące fakty.

Measurement nie może udawać, że query/detail fact jest już page aggregate.
GSC i GA4 mogą zasilać publication-bound loop dopiero przez server-owned,
exact-URL + exact-period aggregate z zachowaną listą źródeł, refresh runów i
jakością/kompletnością. Wrong period, query variant, ambiguous URL,
capped/insufficient source albo settling data pozostają wykluczone z
allowed/observed metrics z typowanym powodem — bez synthetic targetów i bez
drugiego learning loopu.
Każdy refresh przechowuje dodatkowo typed `covered_window`,
`settlement_state` i `quality_state` wraz z caveatami kompletności/capu.
Semantyka jest własnością konektora: brak sygnału settling oznacza `unknown`,
a nie automatycznie „świeże”; `partial`/`unverified` nie może zasilać
publish-ready ani review-bound obserwacji bez jawnej decyzji kontraktu.

„Knowledge” oznacza prawdziwą bazę materiałów Ekologus: zatwierdzone artykuły,
transkrypcje, dokumenty, wcześniejsze sformułowania i wnioski. Karty i
playbooki są wtórnym, lineage-preserving indeksem; nie zastępują źródeł i nie
mogą zawierać zmyślonych stwierdzeń. Import surowych materiałów jest osobnym,
kontrolowanym krokiem z redakcją, owner review i audytem.

## 6. WordPress/ACF i pełny dokument

Inventory musi dynamicznie wykrywać dla każdej strony: post type, canonical URL,
`the_content`, dostępne ACF, zwykłe pola, sekcje i status odczytu. Brak ACF nie
jest błędem — news/article może być w całości w `the_content`. Renderer i
dry-run zachowują wszystkie page assets, a nie tylko tytuł i nagłówki. Meta
mapujemy automatycznie wyłącznie przy potwierdzonym profilu; inaczej pokazujemy
typed blocker, niczego nie gubiąc.

`ContentDraftRevision` v2 przechowuje title/H1/lead/meta, stabilne section IDs,
body, query/evidence/claim IDs, FAQ, CTA, linki, planning/service/inventory
digests i digest całego dokumentu. Starsze v1 pozostają czytelne. Każda zmiana
assetu unieważnia review i handoff.

## 7. Jakość i review

Trzy niezależne poziomy:

1. deterministyczne gates (lineage, freshness, claims, duplikacja,
   kompletność, długości, linki, CTA, bezpieczeństwo);
2. persistowany advisory semantic review związany z exact revision digest,
   criteria version i Codex run ID;
3. człowiek (SEO reviewer, content editor, marketer), który jako jedyny może
   dać 10/10 i zaakceptować revision.

Review nie poprawia automatycznie własnego tekstu i nie wykonuje vendor write.
Finding wybiera marketer, a Codex zapisuje nową immutable child revision.
Nie przedstawiamy syntetycznego browser proof jako realnego UAT.

### Jeden wynik kanoniczny, nie galeria wersji

Planer i generator mają zwracać jeden rekomendowany wynik dla jednego
`planning_input_digest`. Idempotentne ponowienie tego samego wejścia odczytuje
ten sam proposal albo jego stan generowania; nie tworzy v2, v3 i v10 tylko
dlatego, że marketer ponownie otworzył ekran.

Numery wersji dotyczą wyłącznie trwałości kontraktu i historii rewizji:
`ContentDraftRevision` v1/v2 oznacza schemat odczytu, a numer rewizji oznacza
niezmienny punkt dokumentu. Nie są to alternatywne teksty do wyboru.

Warianty mogą powstać tylko jako mały, wewnętrzny eksperyment jakościowy dla
konkretnego pola lub sekcji (np. dwa leady po findingu dotyczącym bezpośredniości).
Każdy wariant musi mieć te same query/evidence/claim IDs, a marketer dostaje
jedną rekomendację z krótkim uzasadnieniem. Alternatywy nie są zapisywane jako
konkurencyjne propozycje, nie trafiają do głównego UI i nie mogą omijać review.
Domyślna ścieżka nie generuje wariantów. Testy A/B po publikacji należą do
istniejącego publication-bound measurement loopu, nie do planera.

### Standard dla całego Marketing OS

Każdy moduł (treści, GSC, GA4, Ads, Ahrefs, Merchant, Localo, Social i
kampanie) ma ten sam minimalny wynik: decyzja, realne fakty, okres i freshness,
identyfikatory evidence/source, jawne braki, bezpieczny następny krok oraz
granica człowieka. Moduł może pokazywać tylko pola, które ma typed kontrakt;
brak kontraktu jest blokadą, nie miejscem na brainstorm modelu.

Campaign Builder jest obecnie review-only dla istniejących kampanii: może
zwrócić campaign candidates, derived KPIs, landing/context, budget preview,
human gates, missing contracts, blocked claims i ActionObject. Nie udaje
generatora keywords, ad groups, assets, sitelinks, copy, targetowania,
budżetów docelowych ani prognoz. Odczyt wielu walut blokuje sumowanie i
etykietowanie kosztu jedną walutą do czasu potwierdzenia spójności konta.

## 8. Kolejność pracy i dowody

### Natychmiast

1. Zdiagnozować i naprawić opóźnienie Run workflow; focused timing + browser
   falsifier, bez testowania w kółko zielonych ścieżek.
2. Dokończyć marketer-first UI: wszystkie inventory entries, brak preselection,
   mięso nad technicznymi panelami, per-panel loading i czytelne błędy.
3. Zweryfikować aktualny operator context pod istniejącym API; techniczne
   request labels pozostają pod spodem, nie na głównym ekranie.

### Pipeline treści

4. Kontrolowany import zatwierdzonych materiałów: manifest → redakcja →
   owner review → lineage facts → planning input. Bez kopiowania prywatnych
   dumpów.
5. Dokończyć trwały plan i pełny dokument v2, readback, stale detection,
   semantic review, section improvements i draft-only handoff.
6. Użyć dwóch exact pilotów (BDO i doradztwo/outsourcing) jako dowodu jednego
   dynamicznego kontraktu, nie jako hardcoded wyjątków.
7. Zbudować paczkę: decyzja/źródła, baseline, plan, query→section, pełny tekst,
   page preview, meta/FAQ/CTA/linking, findings, dry-run, formularze i realne
   nagranie.

### Cały Marketing OS

8. Po treściach dopiąć jednolite decision views dla Ads, GA4, GSC, Ahrefs,
   Merchant, Localo, Social i campaign buildera; każdy przez istniejący API,
   evidence/freshness i ActionObject safety. Nie powielać measurement loopu.
9. Przygotować non-interactive second-opinion review obejmujący API, dane,
   UX, performance, prompts, security, source lineage, content quality i
   handoff. Każdy finding staje się Beadem lub jest uzasadnionym odrzuconym
   ryzykiem — nie zostaje w raporcie jako dekoracja.

### Przekazanie marketerowi — obowiązujący standard

Robocza paczka przekazania znajduje się w
`docs/review-packets/2026-07-17-wilku-live/`, a jej archiwum w
`docs/review-packets/WILQ-PACZKA-DLA-MICHALA-WILCZKA-2026-07-17-v4.zip`.
Paczka musi rozdzielać dowód live od synthetic/browser proof, podawać datę
odczytu i freshness, identyfikatory evidence/work itemów, jawne blokery,
formularz oceny i instrukcję realnego nagrania. Stare metryki,
`approved_current` bez aktualnego API albo fixture jako „UAT” są
niedopuszczalne. Jeżeli nie ma prawdziwego nagrania, mówimy wprost „nagranie
do wykonania”, nie tworzymy domniemania działania.

## 9. Proof i akceptacja

Każdy slice: claim Beada → najmniejsza zmiana produkcyjna → focused falsifier →
state record/Bead → niezależny review fixed point → świadomy commit/push, jeśli
autoryzowany. Dla zmian TS uruchamiamy wąski typecheck; dla API wąski pytest;
cross-surface `scripts/verify.sh` tylko raz przy szerokim claimie.

Pilot nie jest ukończony, dopóki: obie karty mają owner review; oba case'y
przechodzą ten sam dynamiczny workflow; pełne teksty i assets są trwałe;
brak critical/high findings; SEO reviewer, editor i marketer dają 10/10;
WordPress exact dry-run i human-confirmed ActionObject przechodzą; Wilku UAT
potwierdza czas do decyzji i użyteczność.

## 10. Aktualny stan i jawne blokery

Stan referencyjny odczytujemy z `docs/CONTEXT.md`, `docs/PROGRESS.md`,
`docs/dashboard-state.md`, `docs/current-cleanup-state.md` i Beads — nie z tego
pliku. Znane fakty robocze: inventory ma 601 obiektów (113 ready, 7 partial,
481 blocked); metryki mają ponad 124k facts; 15 zatwierdzonych materiałów ma
manifest metadata-only i `import_pending`. Techniczne exact binding,
measurement history i direct-live guard są domknięte; jakość realnego tekstu,
knowledge import, pełny v2 document, semantic review i UAT nie są domknięte.

Blokery wymagające właściciela: review Service Profiles i materiałów,
credentials/token Keyword Planner, produkcyjny actor/tenant, maintenance window
storage oraz zgoda na realny WordPress draft. Żaden blocker nie może być
przedstawiony jako ukończony bez dowodu.

## 11. Definition of done celu

Cel można zamknąć dopiero, gdy marketer sam wybiera dowolną stronę/usługę,
widzi w kilka sekund realne sygnały, uruchamia pełny pipeline, rozumie źródła,
otrzymuje użyteczny tekst bez slopu, może poprawić sekcję, review jest związane
z exact digest, a WordPress otrzymuje wyłącznie potwierdzony draft-only
ActionObject. Dodatkowo istnieje sanitizowana paczka z prawdziwym nagraniem,
wynikami reviewerów i formularzem Wilku UAT. Do tego czasu goal pozostaje
aktywny, a status komunikujemy jako częściowo gotowy z konkretną listą braków.

## 12. Bramka wykonawcza — wymagania, których nie omijamy

Każda kolejna zmiana musi przejść przez ten sam łańcuch: **wybór → API-owned
snapshot → źródła i świeżość → decyzja → plan → tekst → review → exact
revision → draft-only ActionObject**. Nie uznajemy za gotowe samego ekranu,
zielonych testów, syntetycznego fixture ani odpowiedzi modelu.

Minimalny standard obserwowalnego zachowania:

- kliknięcie dowolnego adresu z inventory musi otworzyć jego realną kartę albo
  zwrócić opisany blocker; nie może wrócić jako fałszywy `block` tylko dlatego,
  że materiał został odczytany w poprzednim kroku;
- pierwszy widok musi pokazać decyzję, metryki, źródło, świeżość i następny krok,
  a ciężkie odczyty nie mogą zasłaniać pracy nieskończonym spinnerem;
- każda zmiana źródła, okresu, jakości, materiału, usługi, inventory lub
  kryteriów zmienia digest i unieważnia zależny plan/review;
- brak porównywalnych okresów nie daje diagnozy spadku, wzrostu, kanibalizacji
  ani przyczynowości — wyświetlamy typowany brak danych;
- model może tylko zaproponować niezatwierdzony artefakt przez serwerowy seam;
  człowiek zatwierdza scope, claims, exact revision i akcję WordPress;
- każdy focused proof ma wskazywać konkretny caller, publiczny seam i wynik
  widoczny dla marketera; pełne `scripts/verify.sh` uruchamiamy dopiero po
  domknięciu wszystkich zależnych slice'ów.

## 13. Protokół long-running task — obowiązuje od nowego goalu

Ten protokół opisuje sposób realizacji długiego celu, nie nową warstwę produktu.
Jest inspirowany oficjalnym wzorcem trwałego celu Codexa dla long-running work
oraz wzorcami OpenAI Cookbook dotyczącymi resilient workflows, eval flywheel i
pracy w tle. W repo pozostajemy przy istniejącym serwerowym Codex app-server;
nie dodajemy drugiego klienta modelowego.

### 13.1 Jeden aktywny goal i wykonywalny plan

- Aktywny goal ma jeden opis rezultatu, granice, Definition of Done i jawne
  blokery. Nie zakładamy nowego goalu dla każdej drobnej czynności.
- `update_plan` pokazuje najwyżej kilka aktualnych kroków; każdy krok ma
  `pending`, `in_progress` albo `completed`. Plan jest kompasem, a nie dowodem.
- Beads jest grafem właścicieli, zależności i handoffów. `PLANS.md` nie jest
  równoległą kolejką TODO i nie kopiuje statusów Beads.
- Na początku każdego odcinka czytamy właściwy `docs/CONTEXT.md`, stan route'u,
  aktywny Bead i tylko wymagane źródła. Nie odzyskujemy stanu z pamięci modelu.

### 13.2 Checkpoint zamiast pozornej ciągłości

Każda iteracja zostawia krótki checkpoint zawierający: fixed commit, zakres,
zmienione seamy, obserwowany wynik, uruchomione proofy, niezakończone ryzyka,
następny krok i właściciela blokera. Po przerwaniu można wznowić pracę z tego
rekordu bez ponownego wymyślania planu.

Procesy trwające długo działają przez managed stack albo jawny background job:

- start zapisuje `run_id`, wejściowy digest, wersję kontraktu i czas;
- GET odczytuje stan, nigdy nie uruchamia modelu ani vendora;
- wynik pośredni nie jest publikowany jako gotowy artefakt;
- retry tworzy nową próbę, a stary run pozostaje czytelny;
- timeout, crash i brak wyniku kończą się typed blockerem bez częściowego zapisu;
- pollujemy krótkimi odcinkami i komunikujemy postęp, zamiast blokować shell lub
  UI nieskończonym spinnerem;
- restart procesu nie może zgubić faktu, że próba się rozpoczęła albo zakończyła.

Nie uruchamiamy tego samego kosztownego modelowego zadania równolegle tylko po
to, żeby „przyspieszyć”. Najpierw sprawdzamy istniejący run, digest i idempotencję.

### 13.3 Najmniejszy kompletny slice i dowód

Kolejność każdego slice'u jest stała:

`claim Beada → caller/public seam → najmniejsza zmiana produkcyjna → focused
falsifier → state/Bead checkpoint → review fixed point → semantic commit → push`.

Proof dobieramy do ryzyka, nie do rozmiaru diffu:

- 0 nowych testów dla dokumentacji, copy i zmian mechanicznych już objętych
  publicznym seamem;
- 1 focused falsifier dla jednego zmienionego kontraktu lub reprodukcji błędu;
- kilka falsyfikatorów tylko wtedy, gdy wymagania mają niezależne failure modes;
- szerokie `scripts/verify.sh` raz przy końcowym cross-surface claimie, nie po
  każdym zielonym teście;
- nigdy nie przedstawiamy testu fixture, screenshotu ani synthetic browser proof
  jako realnego UAT lub dowodu jakości treści.

Każde twierdzenie w handoffie ma bezpośredni artefakt dowodowy: command output,
live API response, test result, rendered browser result albo human decision.
Brak dowodu jest stanem `unknown`/blockerem, nie zaproszeniem do zgadywania.

### 13.4 Model, prompt i review

Model dostaje jeden jasno określony kontrakt i niemutowalny input digest. Nie
prosimy jednej sesji o research, implementację i zatwierdzenie naraz. Model może
proponować; API, człowiek i ActionObject zachowują władzę nad stanem.

Każdy istotny fixed point może mieć najwyżej jeden bounded second-opinion pass
na rolę: `researcher`, `rewrite-maker` albo `checker`. Pass musi mieć własny
katalog poza repo, fingerprint, zakres ścieżek, expected deliverable, lokalny
proof i `disposition.md`. Wynik Claude jest hipotezą klasyfikowaną jako
`accept_and_fix`, `evidence_gap`, `reject_with_evidence`, `follow_up` albo
`human_decision`; nie jest approvalem. Nie retryujemy w tym samym katalogu po
odrzuconym outputcie.

### 13.5 Commit i publikacja

Każdy nowy commit używa semantic headera egzekwowanego przez
`.githooks/commit-msg`. Commit zawiera tylko task-owned paths, a push następuje
po focused proofie i świadomym sprawdzeniu dirty worktree. Stare nagłówki są
historycznym debt, którego nie przepisujemy bez osobnej zgody na rewrite historii.

Commit nie oznacza ukończenia celu. Ukończenie wymaga spełnienia Definition of
Done, świeżego audytu wymagań i dowodów oraz braku nierozwiązanych blockerów
produktowych. Gdy nie można iść dalej przez trzy kolejne goal turns z tym samym
zewnętrznym blockerem, oznaczamy blocker jawnie; nie udajemy postępu i nie
zmieniamy kryteriów sukcesu na łatwiejsze.
