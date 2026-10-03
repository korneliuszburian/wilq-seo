# WILQ — plan domknięcia użytecznego pilota Ekologus

Rola: `decision` o rezultacie, zależnościach i kryteriach pilota. Ten dokument
nie opisuje bieżącego stanu wykonania: **Beads pozostaje jedyną kolejką oraz
właścicielem statusów i WIP**, a kod, Git i wykonane dowody określają stan
produktu. Plan nie zastępuje tych źródeł ani kryteriów `docs/goals/001-goal.md`.

## 1. Meta, nie następny refaktor

Obowiązuje cel z `docs/goals/001-goal.md` oraz kontrakty Q1–Q7. Dowozimy lokalny,
kontrolowany WILQ dla Ekologus: Wilku wykonuje rzeczywistą pracę nad treścią bez
prowadzenia przez developera, a Centrum pracy daje użyteczną decyzję z dowodami.

```text
prośba → exact strona/brief → źródła i materialne decyzje człowieka
→ plan jako wejście serwera → pełny tekst → review i poprawka exact rewizji
→ osobno autoryzowany create-only szkic dev + niezależny readback
→ pomiar związany z rzeczywistym wdrożeniem albo uczciwe oczekiwanie na wdrożenie
```

„Do końca” nie oznacza zamknięcia wszystkich otwartych Beadów, jakości 10/10
nadanej przez model ani gotowości publicznego SaaS. Pierwszy pełny przebieg nie
zastępuje kontraktów existing/new page, service i landing/hub. Przed szerszym
użyciem każda obsługiwana gałąź musi mieć pozytywny dowód albo **rzeczywisty
zewnętrzny** blocker — nie brak implementacji nazwany blockerem.

Nie rozszerzamy mandatu na publish/update/delete, masową generację, publiczny
hosting, multi-client, nowe ścieżki modelowe ani operacje credentials/OAuth.

## 2. Podstawa planu i czego nie powtarzamy

Podstawą są kryteria pilota i kontrakty Q1–Q7. Bieżące dyspozycje wykonania
odczytujemy z Beads i dowodów, nie z dawnych sekcji „aktualna prawda”.

- Kontrakty Q1–Q5 (`79cs`, `rsa5`, `4uux`, `4wxa`, `id3b`) obejmują intake,
  research read, wznowienie/bramki, brief/routing i callerów. Reużywamy ich;
  zamknięcie zadania technicznego samo w sobie nie dowodzi realnego UAT.
- M4/current acceptance (`gg8j`) weryfikujemy na świeżym wersjonowanym inventory,
  nie na historycznych liczbach.
- Integralność planu, autoryzowana generacja i review mają wspólne kontrakty.
  Ich lokalny dowód nie zastępuje realnego runtime, źródeł ani werdyktu tekstu.
- Kontrakt pracy `wilq-seo-9ya2` wiąże ten plan z Beads; WIP i następny slice
  wybiera aktualna dyspozycja zadania. Odziedziczone zmiany rozliczamy przed
  adopcją, bez nadpisywania poprawionych seamów lub nieowned pracy.
- I jest bramą live: managed API/dashboard muszą używać tego samego
  zweryfikowanego kodu. Świeżość źródeł i gotowość operatora wymagają własnego
  odczytu; nie wynikają z dawnych statusów ani samego push.

`1oa` / `1oa.36`, `lt1`, `jst` i `v9ab.13` zachowują własne kryteria wiedzy,
pełnego content loopu, oceny tekstu/UAT i Daily Check. Nie zamykamy rodziców
na podstawie samych zielonych testów dzieci.

## 3. Kolejność dostawy i jednostki pracy

Najpierw pozytywny przebieg **jednej istniejącej strony**. Operat jest
kandydatem pierwszego tracera, nie deklaracją dzisiejszej gotowości jego źródeł.
Chroniona ścieżka BDO nie jest skrótem: `82dx` zachowuje exact source/identity
oraz bramki człowieka. Każda jednostka kończy się własnym wynikiem, focused
falsifierem, dyspozycją review i cohesive commit-em; nie łączymy ich w big-bang.

| Jednostka | Caller → publiczna granica → obserwowalny wynik | Sygnał, który może obalić wynik | Zależność |
|---|---|---|---|
| **I — jeden wiarygodny runtime** | Operator → managed API/dashboard → ten sam zweryfikowany kod i poprawny odczyt istniejących rekordów. Rozliczyć odziedziczone klastry osobno; atomic v3 zapis nie może pomijać receipt/current authority na podstawie samego preview. | Focused dowód każdego przejętego klastra; drift lub brak approval blokuje zapis. Minimalny rzeczywisty structured turn sprawdza seam istniejącego Codex login, nie tylko mock. | Lokalne patche i zachowanie nieowned zmian; publikacja kodu pozostaje osobną zgodą. |
| **C — wspólny exact kontekst pakietu dla draft/review** | Odczyt planu/draft/review → wspólne typed odczyty → jeden zgodny proposal/frozen input/packet/receipt/subject. Current authority jest odrębna od możliwości obejrzenia historii. | Ten sam exact pakiet daje zgodny kontekst odbiorcom; obca strona, zmienione źródło/receipt/identity albo uszkodzony input blokuje. Historyczna reviewed rewizja nadal jest czytelna, lecz nie daje nowej zgody na zapis. | Istniejąca wspólna integralność frozen inputu; I przed dowodem live, nie przed pracą na fixture’ach. |
| **G — autoryzowany pełny tekst istniejącej strony** | Jawne „przygotuj tekst” → exact ActionObject i dispatch → istniejący app-server/pipeline → jedna immutable rewizja z plan/packet/run lineage i status readback. | Zmiana planu/pakietu/autorytetu przed turą lub persystencją: zero niedozwolonych wywołań/zapisów. Replay/równoległy dispatch: jeden efekt. Pozytywny tracer naprawdę zapisuje i odczytuje tekst. | C; reviewed źródła i exact lokalna autoryzacja dla realnego przypadku. |
| **R — review i poprawka tej samej pracy** | Rewizja → semantic review i kontrola źródeł, trzy perspektywy oceny → human decyzja → immutable child revision albo approved exact tekst. | Foreign/stale review nie daje approval; nowy tekst wymaga własnego review; poprawka zachowuje bazę i źródła. Styl-only obserwacja nie wywołuje blokady/automatycznego przepisania; brak dowodu, privacy lub defekt struktury nadal blokuje. | G. |
| **U — jeden zrozumiały journey i szybki odczyt** | `/content-workflow` i content skill → te same API-owned decyzje → przygotowanie, odczyt/reload, review i następny bezpieczny krok bez technicznych formularzy. | Rzeczywisty błąd nie wygląda jak pusty wynik; 409 nie retry ze starym digescie; porównanie pełnej decyzji przed/po optymalizacji. Marketer rozumie decyzję w około 30 s. | G/R; core pola API przed callerami. Profilowanie R8 przed zmianą, bez pomijania kroków zmieniających digest. |
| **K — źródła/wiedza i przypadek usługowy** | Source/Service Profile review → exact local receipt/projection → użyteczna kwalifikacja faktów i ten sam generator dla usługi. | Brak receipt, obcy card/registry digest lub niezatwierdzony claim nie daje eligible/approved. Pozytywny przypadek nie wymaga edycji DB. Wspólny adapter zwraca fakty z lineage albo konkretny powód źródłowy. | C/G; istniejące kontrakty `0mpo`, `lt1`, `s7po`, `87hv` zależnie od przypadku. Brakujący receipt/adapter jest pracą techniczną. |
| **N — nowa strona i landing/hub bez drugiego pipeline’u** | Brief/foundation/overlap i właściwy typed subject → wspólna autoryzowana generacja/review → exact rewizja. Nie tworzymy fikcyjnej tożsamości istniejącego URL-a dla nowej strony. | Brak zatwierdzonego źródła lub niepełne inventory nie daje claimu nowości. Każdy deklarowany typ ma pozytywny przebieg lub realny zewnętrzny blocker, nie unsupported seam. | G/R/K; publiczny kontrakt przed naprawą instrukcji skilla. |
| **D — bezpieczny dev draft i recovery** | Approved rewizja → target proof/mapping → istniejący create-only ActionObject → niezależny exact readback. | Mismatch, drift po review, obcy target: zero vendor write. Timeout po możliwym efekcie nie uprawnia do drugiego create; najpierw reconcile/readback. Readback weryfikuje body/tytuł/status, nie samo istnienie ID. | R, właściwy target i osobne GO dla rzeczywistego vendor write. Existing-page tracer może dojść tu przed N; szersza kohorta dopiero po K/N. |
| **L — jedna bieżąca ścieżka, historia zachowana** | Nowi callerzy → kanoniczny writer/loader; dawne rekordy → historical read → brak dwóch konkurujących decyzji authority. | Faktyczny runtime odrzuca nowe deprecated writes; retained reads/review nadal działają. Brak xfail jako stałej furtki, brak source-string liczenia tras. | C/G/R i caller census; migracja poniżej. |
| **W — realny werdykt i Centrum pracy** | Rzeczywisty exact loop → zapisane SEO/strateg treści/marketer review, czas i uwagi; Wilku UAT albo jawny defer z ryzykiem, osobno realny Daily Check → ocena użyteczności. | Pozytywny wynik nie jest samym screenshotem/testem/modelową samooceną. Każdy materialny finding ma dyspozycję; nie ma „10/10” bez realnego werdyktu. | U/R oraz wymagany wariant D/K/N; `jst`, `1oa.36`, `v9ab.13`. |
| **M — pomiar i zamknięcie wydania** | Exact deployment proof → window/outcome → review-only learning; wcześniej jawne oczekiwanie na wdrożenie. Zintegrowany fixed SHA → final gate/CI → ten sam managed runtime. | Nieopublikowany dev draft nie daje wyniku SEO; brak lub niepełne evidence nie tworzy metryki. Finalne wymagane checks nie mogą być czerwone. | Approved rewizja; realny pomiar wymaga rzeczywistego wdrożenia i okresu danych, a publikacja pozostaje poza tą zgodą. |

Droga pierwszego realnego tekstu: **I → C → G → R**. Potem U i D dają
pierwszy pełny operatorowy tracer. K/N zamykają pozostałe deklarowane gałęzie,
L usuwa konkurujące current writes, a W/M rozstrzygają ukończenie pilota.
Zbieranie źródeł i feedbacku może trwać obok; implementacja pozostaje WIP=1.
Nie podajemy dat ukończenia przed pozytywnym tracerem i pomiarem jego kosztu.

## 4. Wybór kolejnego slice i brama live

Następny wynik wybiera aktywny Bead na podstawie aktualnego kodu, zależności
powyżej i dyspozycji review. Ten plan nie nakazuje ponownej implementacji
wcześniej udowodnionego C/G/R ani pracy w dawnym worktree.

Każdy slice wskazuje caller → publiczną granicę → obserwowalny wynik oraz
focused falsifier przed zmianą. Fixture może dowieść kontraktu, lecz I
pozostaje pierwszą bramą **live**. Cofnięcie dotyczy tylko własnych hunków
lub commitu; nie resetuje dirty drzewa, danych ani nieowned pracy.

## 5. Konsolidacja bez kolejnej generacji obok poprzedniej

L ma kształt **expand → migrate → contract**, bo istnieją historyczne dane,
review i audyt oraz żywi callerzy starszych rodzin.

1. **Expand:** uzgodniony wspólny loader/typed context potrafi odczytać aktualną
   i historyczne wersje, rozróżniając read od uprawnienia do nowego zapisu.
   Nowa granica używa istniejących kontraktów, nie tworzy równoległego v4.
2. **Migrate:** przenieść konkretnego callera i w tym samym slice usunąć jego
   konkurującą decyzję. Dowód pozytywny + drift/retained-history; rollback
   pozostawia stary reader oraz brak nowego write, nie obniża exactness.
3. **Contract:** po dowodzie braku old current-writer callers odrzucić nowe
   deprecated preview/apply i wycofać niepotrzebny kod. Historyczne payloady
   i rewizje pozostają odczytywalne. Zero rekordów nie jest dowodem martwości.

Nie kasujemy tabel ani nie migrujemy realnego storage bez osobnej zgody oraz
backup/restore proof. Źródłem niezmiennika „jedna bieżąca ścieżka” jest
właścicielski typed kontrakt/capability w runtime, nie Markdownowa tabela
lub grep. Nie potrzebujemy do tego ogólnego frameworka rejestrów.

## 6. Jakość i pomiar — bez dodatkowego teatru

Najpierw pełny, grounded tekst i jego rzeczywista ocena. Kolejny dashboard,
score, detektor AI lub Q-SEAL framework nie jest warunkiem startu tracera.
Źródła, dopuszczalne claimy, CTA, privacy i struktura mają konkretne bramki.
Styl to revision-bound informacja advisory i decyzja redaktora, nie lista fraz
ani automatyczne wymuszanie przepisania. Nowe obserwacje wymagają zgodności
producer–consumer, żeby nie zepsuć review nieznanym kodem.

Ewentualna kalibracja używa reviewed, lineage-preserving materiału, holdoutu
oraz etykiet człowieka; nie udajemy gwarancji jakości na podstawie zerowej
liczby trafień w małej próbie. Źródła prywatne i business policy nie trafiają
jako surowy korpus do promptów.

Measurement/learning istnieją jako kontrakty do ponownego użycia. Dla
nieopublikowanej rewizji prawidłowym stanem jest brak rozpoczętego pomiaru.
Public deployment confirmation nie publikuje. Rzeczywisty outcome potrzebuje
zaobserwowanego wdrożenia, poprawnego okna oraz GSC/GA4 evidence. Czas pracy
operatora można mierzyć w UAT wcześniej; nie jest on wynikiem SEO.

## 7. Co robi agent, a czego naprawdę potrzeba od człowieka

**Agent:** architektura i typed seamy, integracja zmian, runtime diagnosis,
publiczne callbacki i parity klientów, tests/review, profile wydajności,
idempotencja/recovery, retained-read migracja, aktualizacja planu i Beads.
Brak validatora, adaptera, mappingu lub ActionObjectu nie jest zadaniem dla
użytkownika ani dopuszczalnym terminalnym blockerem produktu.

**Człowiek/source owner:** review konkretnych faktów/claimów/Service Profile,
materialny wybór usługi/odbiorcy/CTA, przeczytanie exact tekstu i jego werdykt,
realna sesja UAT, osobna zgoda na exact dev write. Credentials, OAuth/consent,
rejestracja vendora lub nowy hosting mają własną authority, jeśli są potrzebne.
Nie prosimy o ogólną akceptację „wszystkiego”, tylko o nazwaną decyzję z dowodami.
Actor pochodzi z trusted request context; prywatny pilot nie jest dowodem
zweryfikowanej tożsamości wszystkich pracowników.

**Publikacja kodu:** commit, push, PR, merge i deploy pozostają osobnymi
przejściami. Plan nie daje na nie dodatkowej zgody. Właściwy reviewer dostaje
fixed diff i dowody; uwagi modelu nie zastępują ludzkiej/content approval.

## 8. Ścisły warunek zakończenia

Pilot można uznać za dowieziony dopiero, gdy łącznie:

1. Przynajmniej jedna exact usługa/strona przechodzi pełny, rzeczywisty
   Content Ops loop; ekran prowadzi do decyzji bez tłumaczenia developera.
   Nie zastępujemy tego fixture’em ani samym browser proofem.
2. Każde źródło **wymagane** przez realny workflow jest aktualne albo ma
   rzeczywisty typed zewnętrzny blocker z właścicielem i warunkiem wznowienia;
   nie wystarczy sprawdzić tylko źródeł, które wybrano do użycia. Brak receipt,
   adaptera lub validatora jest pracą techniczną. Każdy użyty fakt/claim ma
   reviewed authority i evidence/source/freshness; model nie zastępuje źródła.
   Depth audit wiedzy i bramki missing-card są rozliczone; Sales Brief/Claim
   Ledger nie wyciągają mocniejszych wniosków niż pokrycie i jakość sygnałów.
3. Istnieje pełny tekst, exact poprawka/review i trzy wymagane perspektywy:
   **specjalista SEO, strateg treści, marketer/operator**. Kontrola fidelity
   źródeł i zatwierdzenie faktów są bramkami, nie czwartą obowiązkową rolą
   review każdej paczki. Sanitizowana paczka dowodowa zawiera wygenerowane
   sekcje, claim/section lineage, quality findings i dokładne before/after
   dostępnego materiału — bez zgadywania brakujących fragmentów. Jest
   **realny werdykt paczki tekstowej**; samo oczekiwanie na ten werdykt nie
   oznacza ukończenia.
4. Obsługiwane existing/new page i content kinds zachowują właściwe source,
   overlap, revision i target gates; aktualny inventory ma pełne typed
   disposition, bez historycznego/fuzzy pokrycia. Przebieg all-blocked nie
   zastępuje pozytywnego wyniku.
5. Draft delivery ma create-only/exact revision/human authorization/audit
   oraz właściwy readback albo realny external target/source/permission
   blocker. Dla pełnego pozytywnego tracera dev write jest osobno uzgodniony.
6. Realny Wilku UAT ma czas, confusion points i dyspozycję materialnych uwag
   **albo** owner jawnie go odracza z zakresem i residual risk, zgodnie z
   criterion 3 celu. W obu wariantach rzeczywisty loop z pkt 1 ma zmierzony
   czas do wyniku; nie znika wymagany werdykt tekstu z pkt 3. Daily Check
   używa realnego rule packu z evidence/source/freshness, wskazuje użyteczną
   decyzję i ma ocenę realnego outputu albo dozwolony jawny defer.
   Defer w `jst`/`v9ab.13` nie jest wykonanym UAT i **nie zwalnia z werdyktu
   tekstu, dowodu loopu ani własnych kryteriów rodzica `1oa.36`**.
7. Pomiar nie twierdzi sukcesu bez exact deployment/window/data, a learning
   pozostaje review-only. Brak publikacji nie jest zgodą na syntetyczny outcome.
8. Focused proof i `scripts/verify.sh` są zielone na zintegrowanym fixed point;
   wymagane CI i runtime agreement potwierdzono na zatwierdzonej rewizji.
   Po autoryzowanym merge managed API/dashboard używają tego samego SHA.
9. W zakresie tego wyniku nie pozostała potwierdzona bezpieczna praca
   techniczna. Otwarte pozostają wyłącznie jawne rzeczywiste bramki
   człowieka/vendora lub osobno uzgodniony post-pilot scope.

To zachowuje kryteria `docs/goals/001-goal.md` oraz własne acceptance `1oa`,
`1oa.36`, `v9ab` i Q1–Q7; nie ustanawia nowego Goala ani słabszej mety.

## 9. Poza tą metą i zasada wykonania

Publiczne auth/TLS/multi-user/hosting/hardening wymagają odrębnej decyzji z
`docs/architecture/production-target-decision.md`. Nie kończymy ich deklaracją
„pilot działa”. Pełne nowe vendor-write produkty Ads/social, multi-client,
masowa produkcja, optional quality scoring i destrukcyjny cleanup nie są
przemycane jako warunek pierwszego użytecznego pilota.

WIP=1; nie claimujemy nowego Beada, żeby obejść blocker aktywnego. Istniejące
`0mpo`/`s7po`/`lt1` i inne kontrakty są referencjami zależności, nie drugim
równoległym torem implementacji. Konkretny wymagany wspólny fix należy najpierw
powiązać z acceptance aktywnego wyniku i zapisać dyspozycję w Beads.

Publikacja nowych ticketów dla jednostek tego planu: **NOT_REQUESTED**.
Jednostki to zależności/kryteria planu, nie druga kolejka statusów. Następny
wykonawca odczytuje aktywny Bead i aktualny fixed point, zamiast zaczynać
ponownie od C. Nie odtwarza istniejących kontraktów Q1–Q5 ani nie wywodzi
zgody na product/vendor writes z tego dokumentu.
