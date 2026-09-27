# WILQ: uniwersalna kolejka treści i evidence-bound dostawa

> Rola: `current state` i długoterminowy plan jednego wyniku. Beads pozostaje
> kolejką wykonawczą i właścicielem WIP; bieżący stan pracy zapisuje kapsuła
> delivery-loop. CSV `docs/content-status-214.csv` opisuje historyczną kohortę,
> nie pełny, aktualny spis sitemap.

## Outcome

Każda uprawniona osoba z Ekologus może opisać potrzebę treści zwykłym językiem.
WILQ tworzy z niej wznowialną kolejkę, zbiera dostępne dowody, składa
propozycję briefu, wskazuje niewiadome i prosi człowieka o decyzję tylko tam,
gdzie jest ona rzeczywiście potrzebna. Kolejka prowadzi do dokładnej,
reviewed rewizji i create-only draftu dev albo do prawdziwego typed blockera.

Wynik jest kompletny, gdy:

- intake działa dla dowolnego uprawnionego operatora, bez hardcodowania Agaty i
  bez wymogu gotowego, sześciopolowego briefu;
- każde zadanie ma trwały identyfikator, idempotentne przyjęcie, krok, stan
  bramek, właściciela następnego kroku, pochodzenie pól i jeden bezpieczny krok;
- każda rekomendacja i proponowany claim mają exact source/evidence lineage,
  zakres autorytetu i freshness; brak lub nieświeżość danych jest blockerem;
- research źródeł oficjalnych, konkurencji, korpusu i popytu korzysta z
  jawnych kontraktów; nie udaje kompletności, gdy dowody lub uprawnienia nie są
  dostępne;
- brief rozdziela dane użytkownika, dowody, wnioski i niewiadome; każda
  materialna decyzja człowieka wstrzymuje i wznawia właściwy etap;
- jakość jest sprawdzana przez lineage faktów/claimów, dopasowanie do intentu,
  odbiorcy i zweryfikowanego profilu Ekologus, wartość dodaną względem korpusu,
  overlap i niezależny review; AI detector ani magic score nie są dowodem;
- istniejące i nowe strony przechodzą przez API-owned workflow, exact revision,
  review, target proof i create-only draft dev albo typed blocker;
- pełny, bieżący inventory sitemap jest uzgodniony przez publiczne źródła WILQ;
  każdy URL ma typed disposition, a każda kwalifikująca się strona — pracę,
  decyzję lub typed blocker;
- nie wykonuje się automatycznej publikacji, update, delete ani masowej
  generacji; write-capable działania zachowują ActionObject i osobne approval.

## Jak utrzymywać ten plan

Goal określa wynik i kryterium jego ukończenia. Ten plik określa kolejność,
zależności i falsyfikatory. Beads przechowuje zadania i pojedynczy aktywny WIP,
a kapsuła delivery-loop — wyłącznie bieżący stan, ownera, blocker i następną
czynność. Nie twórz równoległej listy statusów ani drugiego aktywnego Beada.
Każdy etap poniżej ma własny obserwowalny wynik; claim pozostaje w jednym
Beadzie na raz.

## Źródłowe decyzje projektowe

- Z materiałów OpenAI przyjmujemy rozdział: Goal opisuje outcome, a plan
  rozpisuje milestones z acceptance i walidacją. Nie dodajemy kolejnego pliku
  statusowego; Bead i kapsuła zachowują swoje role.
- Z workflow praktyk przyjmujemy named stages, uprawnienia/ownerów zadań,
  typowany stan, pause/resume i bounded retries. LangGraph ani Temporal nie
  są zależnościami WILQ; wybór frameworka nie rozwiązuje braku typed API,
  dowodów ani ActionObject authority.
- Z Google Search Central przyjmujemy ocenę pod kątem odbiorcy, użyteczności,
  wiarygodności i własnej wartości. AI może wspierać research/strukturę, ale
  nie zastępuje weryfikacji faktów ani nie usprawiedliwia masowego low-value
  contentu.

Źródła: [OpenAI — Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex),
[OpenAI — Run long-horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex),
[Google — Helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content),
[Google — Generative AI content guidance](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content),
[Contentful — Create a workflow](https://www.contentful.com/help/ai-automations/workflows/creating-a-workflow/),
[Contentful — Tasks](https://www.contentful.com/help/content-and-entries/tasks/),
[LangGraph — Thinking in LangGraph](https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph),
[Temporal — Child Workflows](https://docs.temporal.io/child-workflows).

## Authority i źródła prawdy

1. `docs/content-status-214.csv` — historyczny journal kohorty 214 URL-i.
2. WILQ SQLite/API — bieżące evidence, work items, revisions, review,
   ActionObject i audit.
3. Sitemap/public/dev readback — tożsamość URL, canonical i exact target proof.
4. Beads — jedyna kolejka, zależności, WIP, proof i handoff.
5. Ten plan — kolejność, bramy i kryterium zakończenia, nie rejestr URL-i.

Nie wracamy do historycznego JSON journalu ani snapshotu eligibility jako
bieżącej prawdy. Nie regenerujemy dobrej rewizji: `approved` jest reużywane,
a `needs_changes` może utworzyć wyłącznie exact immutable child revision.

## Zweryfikowane seamy do ponownego użycia

Readback kodu, OpenAPI i WILQ API z 2026-09-25. Nowy intake ma łączyć poniższe
kontrakty; nie zastępuje ich drugim research engine, job schedulerem ani
planerem.

| Istniejący seam | Co już robi | Granica względem ask-only kolejki |
| --- | --- | --- |
| `GET /api/content/diagnostics`, `GET /api/content/workflow-entry` | Read-side decision queue, freshness/blockers, wybór existing page albo new page. | Nie przyjmuje i nie utrwala natural-language ask. |
| `GET /api/content/new-page-topics` | Read-only seeds wymagające dokładnych GSC/Ahrefs i braku istniejącej strony. | Nie tworzy briefu ani research runu; obecnie blocked przez niepełny/stale input. |
| `POST /api/content/new-page-briefs` | Trwały brief nowej strony z tytułem, celem, usługą, odbiorcą, search intent i miejscem w serwisie. | Wymaga sześciu pól ręcznie; zapis nie oznacza draftu ani WordPress write. |
| `.../planning-foundation`, `.../planning-proposal` | Sprawdza foundation/overlap i kolejkuje exact-digest proposal; zapisuje claim w SQLite, uruchamia go przez ograniczony in-process `ThreadPoolExecutor` i rewaliduje input przed Codex. | Działa dopiero po ręcznie zapisanym briefie/foundation; nie jest uniwersalnym request/gate runnerem. |
| `/api/content/evidence-acquisition*` | Idempotentny, append-only acquisition oparty o exact identity albo authoring-inventory receipt; wykonuje sanitized exact-page read albo odczyt zarejestrowanego official-primary candidate. | Nie przyjmuje ask bez ustalonego subjectu i nie odkrywa swobodnie konkurentów/źródeł. Kandydat official jest server-owned i musi pasować do exact pathu. |
| `/api/content/evidence-acquisition/{run_id}/research` | Jawnie wywołuje structured Codex app-server proposal z jednego sanitized observation; zapisuje unknowns/contradictions, blokuje niebezpieczny output, wymaga human review. | Nie wykonuje multi-source web search; inne `source_intent` bez implementacji adaptera kończą typed blockerem. Promotion/review pozostają osobnymi kontraktami. |
| Regulatory source candidates/reviews, knowledge cards, Service Profile | Obsługują znane source candidates, snapshot/review/promotion i zatwierdzone fakty/profil. | Istnienie endpointu nie oznacza discovery ani zaakceptowania konkretnego źródła. PPWR pozostaje osobnym źródłowym blockerem. |
| Research packet v2/v3, per-URL identity, ActionObject, exact revision/review/draft seams | Wiążą zatwierdzone fakty, exact identity, packet digest, review i dev delivery. | To downstream authority, nie natural-language intake. Q6 ma je konsumować, nie odtwarzać. |
| `CurrentResearchPacketEntry` + `ResearchPacketV3ActionReview` | Istniejący document canvas może przygotować exact ActionObject v3 i poprowadzić review/confirm/apply. | Entry caller przekazuje tylko `work_item_id`; brak per-URL identity action ID powoduje typed blocker. To M3d caller gap, nie brak V3 preview/action API. |
| `/planning-generation-intent-v3` preview/dispatch | Existing ActionObject binds approved v3 packet to the exact per-URL identity through dispatch; stale/mismatched IDs block before model queue. | Backend and focused tests exist, but no dashboard/skill caller was found. M3c/M3d/Q5 must wire callers, not recreate generation intent or dispatch. |
| `wilq-content-operator` + `POST /api/content/work-items/{id}/planning-proposals` | GET zachowuje bezpieczny planning status/readback. | Skill nadal instruuje POST, ale route jawnie zwraca `409 research_packet_action_required`; ta existing-page ścieżka nie jest generatorem. Przepnij skill po typed identity handoff; nie odblokowuj tego endpointu bokiem. |
| Caller identity | Local pilot exposes fixed `local_operator` / `local_unverified` audit identity. | Nie dowodzi tożsamości konkretnej osoby. Nie wyprowadzaj actor, approval ani ownership z tekstu prośby; zapisuj tylko trusted API actor. Jeżeli assignment/resume musi rozróżniać pracowników, potrzebna jest jawna identity decyzja. |
| `POST /api/workflows/{id}/runs`, `/api/workflow-runs` | Trwale zapisują generyczny `WorkflowRun` ze statusem `queued`; nie uruchamiają jego kroków. | Nie są działającym workerem ani marketer-actionable content queue. Bieżące readbacki to trzy nieaktywne dla marketera `daily_command` runs. |
| APScheduler `wilq/jobs` | Dwa jawne connector jobs: status probe i manual vendor-read refresh. | To nie jest dispatcher kolejki treści; w readbacku `autostart=false`, `running=false`. |

Wąski wniosek implementacyjny: brakującym elementem jest request-owned intake i
orkiestracja między istniejącymi seamami. Zanim dodasz nowy reader, worker albo
provider, najpierw sprawdź, czy istniejący seam można zawołać z tego requestu
z wymaganą lineage i świeżością. Nowy source-discovery capability wymaga osobnej
decyzji dopiero dla wykazanej luki, głównie general web/competitor discovery.

## Live scope readback 2026-09-25

WILQ API odczytano read-only; poniższe liczby opisują różne zbiory i nie wolno
ich sumować ani podmieniać jednego drugim:

- public sitemap: 790/790; wewnętrzny WordPress catalog: 199/199;
- content inventory catalog: 141 pozycji, 134 ready i 7 blocked;
- historyczny journal: 214 rows; 127 mają bieżący catalog match, 87 nie mają
  inventory bindingu; journal readiness jest `incomplete`, bieżąca evidence
  readiness blokuje wszystkie 214 i `generation_allowed=false`;
- latest stored production classification nadal ma 57 `blocked`, 0 `reuse`,
  0 `refresh`, 0 generation allowed;
- per-URL identity, source-pack v3 i intent/dispatch kontrakty istnieją, ale
  live per-URL observation producer i pełny M4 current-acceptance census
  pozostają otwarte; synthetic tests nie są dowodem live readiness/UAT;
- diagnostics wymaga refreshu GSC/Ahrefs/GA4; GSC quality jest `partial`,
  więc nie ma podstaw do aktualnego demand/competitor briefu;
- managed API/dashboard są ready, Codex app-server/login ready; SQLite schema
  14, DuckDB schema 2 bez skonfigurowanej ścieżki metric store; 9/12 connectors
  skonfigurowanych, 2 brakuje credentials, 1 disabled;
- endpoint official-guidance zwraca jeden niezwiązany ISO 37301 candidate;
  regulatory reviews nie zawierają PPWR candidate ID. Bead `87hv` ma wskazane
  EUR-Lex candidates, ale wymagają rejestracji i review przed użyciem.

Te readbacki potwierdzają, że `214`, `141`, `199` i `790` nie są zamiennymi
countami. Końcowy census musi opierać się na aktualnym wersjonowanym publicznym
inventory i typed eligibility, nie na journalu ani liczbie wyników katalogu.

## Historyczna kohorta 2026-09-11 — nie jest aktualnym zakresem sitemap

Poniższe liczby opisują ówczesny snapshot kohorty 214 URL-i. Nie dowodzą
kompletności obecnej sitemap i nie są kryterium końcowego pokrycia. Aktualny
inventory i eligibility wymagają świeżego readbacku WILQ API; bieżące
rozpoznanie wskazuje około 790 URL-i, ale ich pełna kwalifikacja pozostaje
otwarta.

- 214 URL-i: `57 keep / 87 noindex / 46 redirect / 24 remove`.
- `keep`: 18 bieżących approved revisions, 17 semantic zero-findings, 1 semantic
  unavailable (REACH), 7 zweryfikowanych dev draft readbacków, 0 robot-ready.
- frontier S6.3 obejmował 7 legacy śladów dev-readback: 6 ma exact mapping i
  digest-backed readback, a IPPC ma brak exact bieżącego odczytu targetu
  (`target_unavailable`). CSV ma dziś 7 `dev_draft_verified` (tych 6 oraz
  niezależnie odświeżony wpis opakowaniowy); IPPC nie jest w tej liczbie. Brak
  exact odczytu nie jest dowodem nieistnienia obiektu. Pozostałe approved
  revisions nie są regenerowane: czekają na swój exact gate albo typed blocker.
- 45 `keep` to editorial, 7 service, 5 landing/hub. Landing/hub nie ma jeszcze
  pełnej typed authorization path.
- Świeży odczyt GSC `ev_refresh_refresh_google_search_console_5bb0e4041e05`
  obejmuje 548 wierszy `query,page` dla `2026-09-08`, z `partial_possible`;
  bieżący diagnostics queue ma 9 dopasowań page/query. Służy to wyłącznie do
  kolejności, nie do obietnic wyniku.
- GA4 jest settling/unverified i nie page-level. Ahrefs jest manualnym domain
  snapshotem i nie page-level. Oba są kontekstem, nie tie-breakerem URL-i.
- Świeży odczyt WordPress `ev_refresh_refresh_wordpress_ekologus_92c1152daeb8`
  zebrał 176 obiektów, 218 URL-i sitemap targetu i 788 URL-i publicznych;
  pokrycie jest jawnie `partial`, najnowsza modyfikacja to `2026-09-10`.
  Endpointy GSC i WordPress ekologus raportują skonfigurowane credentials w tym
  sprawdzeniu; wartości `.env` nie są ujawniane.
- `delivery_status=blocked_target_unavailable` występuje przy 3 keep (analiza,
  Green Deal i IPPC); kod blokera `target_unavailable` pojawia się przy 4 keep,
  bo REACH ma dodatkowo `blocked_review_and_target_unavailable`. Ten status
  oznacza brak exact bieżącego odczytu targetu, nie dowiedziony brak obiektu.

## Priorytet i dane bieżące

Nie utrwalaj tu rankingu stron ani live metryk. Readback WILQ z 2026-09-25
wykazał stale GSC, GA4 i Ahrefs oraz stale/partial diagnostics. Do czasu
świeżego, page-bound odczytu nie ma podstaw do priorytetu popytowego ani
konkurencyjnego. Następny operator odczytuje dowody przez WILQ API i zapisuje
ich identyfikatory w rekordzie pracy.

## Standard jakości i research

Każdy work item wymagający treści dostaje wersjonowany research packet: exact
intent i query cluster, canonical owner, content kind, odbiorca/problem/trigger,
zweryfikowany profil Ekologus, approved facts, blocked claims, freshness,
legal/source requirements, CTA destination, internal links i source/evidence
IDs. Wymagania pochodzą z aktualnych, bezpośrednich źródeł: Google Search
Central i Search Quality Rater Guidelines, źródeł
urzędowych dla prawa, badań naukowych tam, gdzie rzeczywiście wspierają
mechanizm, oraz jawnie ograniczonych praktyk UX/content. Każde źródło ma URL,
datę odczytu, zakres autorytetu, freshness i decyzję `adopt/reject/lab-test/defer`.
`defer` wymaga nazwanego ownera i warunku ponownego sprawdzenia; nie oznacza
odrzucenia i nie może pozostać bezterminowym stanem domyślnym.
Packet jest typowanym immutable rekordem związanym z current work itemem i
revision-input digest, nie luźnym Markdownem ani promptowym blobem.

Kolejność bram:

1. schema, lineage, blocked-claim i regulatory deterministic checks;
2. readability, struktura, answer directness, repetition, CTA i link safety;
3. corpus-wide duplicate/intent/canonical/link graph na wersjonowanym snapshotcie
   przed revision i ponownie przed readbackiem dostawy;
4. niezależny content/UX judge;
5. niezależny SEO/intent/cannibalization/metadata judge;
6. niezależny factual/regulatory/source-fidelity judge;
7. WILQ semantic review dokładnej revision.

Deterministic gate obejmuje `long_sentence`, `heading_answer_mismatch`,
`heading_exaggeration`, `vague_answer_phrase`, `thin_section`, `wall_of_text`,
`working_note`, `duplicate_paragraph`, weak CTA, język, source/claim oraz
privacy/consent. Byline/author pozostaje `lab-test`.

DeepSeek V4.1 Flash (`opencode-go/deepseek-v4.1-flash`) jest advisory judge. Nie może
nadpisać deterministic failure ani nadać approval. Każdy finding ma lokalną
dyspozycję `accept_and_fix | reject_with_evidence | deferred | human_decision`,
z exact evidence.

Zakazane skróty: magic SEO score, długość tekstu jako jakość, keyword stuffing,
substring coverage jako dowód intencji, current-vs-current uniqueness,
page-level wnioski z domain-level Ahrefs/GA4, samocytowanie Ekologus jako
niezależny proof, syntetyczny PASS i claim o rankingu/konwersji bez pomiaru.

## Plan dostawy

Kolejność to niezależne pionowe slice'y. Q2 wymaga osobnej decyzji źródłowej
przed wyborem providera; ten blocker nie zatrzymuje Q1. Jeden Bead na raz
pozostaje `in_progress`. Publikacja dodatkowych Beadów nie jest częścią tego
planu, dopóki owner jawnie jej nie zleci.

## Dokończenie aktywnej migracji per-URL

Aktywny `gg8j` jest ścieżką rozwoju authority, nie natural-language intake.
Jego status i proof pozostają w Beadzie. Zatwierdzona sekwencja to E1 semantic
per-URL authority → M1 disposition → M2 identity/source-pack → M3a research
packet → M3b generation-intent/dispatch → M3c caller census/V3 boundary
→ M3d selected-workspace identity → M4 current acceptance dla
kwalifikujących się URL-i → C1 usunięcie batch-currentness gates po census
callerów. E1/M1/M2/M3a/M3b mają już readback w tym Beadzie; następny slice to
M3c. M3c i M3d muszą zachować exact per-URL authority oraz typowany blocker
dla brakującego keep/identity/pack. M4 musi zbudować prawdziwą
`current_acceptance` z aktualnych page-specific facts i wydać `keep`, `refresh`
lub typed blocker; all-blocked bootstrap nie zamyka tego wymagania. C1 zachowuje
v1 historical readback i czeka na caller census.

### M3c — caller census i zachowanie istniejących granic

Caller census nie znalazł produkcyjnego dashboardu ani skill callsite dla GET
`/refresh-preparation`; endpoint pozostaje istniejącym batch read contract, a
jego v1 authorization POST nie jest wejściem do V3. Dlatego M3c nie dodaje
query aliasu ani nowej ścieżki readiness. Zachowaj legacy `/refresh-preparation`
bez zmian do C1 caller census.

Istniejący per-URL chain już działa przez osobne publiczne seamy:
KEEP disposition → applied per-URL identity → source-pack v3 → research-packet
v3 preview/ActionObject → planning-generation-intent-v3 ActionObject/dispatch.
Każdy dalszy caller musi przekazać exact bieżące identity; V3 seamy ponownie
sprawdzają page, source, identity i digest. Dla service wymagana jest exact
`approved_current` `service_card_id`; editorial używa exact inventory/receipt.
Nie dobieraj usługi z tytułu.

Właściwy caller gap jest w M3d: `CurrentResearchPacketEntry` dostaje tylko
`work_item_id`, mimo że istniejący V3 ActionObject wymaga exact applied
per-URL identity. M3d przekazuje identity z selected workspace do istniejącego
V3 action call. Skill pozostaje typed 409 aż do tego handoffu i późniejszego
Q5 routing; nie odblokowuj legacy `/planning-proposals` bokiem.

**Falsifier M3c:** caller census pokazuje brak aktywnego callsite dla batch
`/refresh-preparation`; istniejące testy V3 potwierdzają, że missing/stale/
wrong-page identity blokuje przed ActionObject/model queue, a dokładne identity
dochodzi do review i dispatch. Brak nowego endpointu, writer-a ani batch aliasu.

Q1 nie jest drugim aktywnym WIP: wdrażaj ją jako osobny etap dopiero po
domknięciu albo jawnej zmianie kolejności jedynego aktywnego Beada. Nie
przepisuj scope'u `gg8j` na intake i nie odtwarzaj jego ukończonych E1/M1/M2/M3a/M3b.

### Q1 — przyjęcie prośby bez gotowego briefu

API przyjmuje zwykłą prośbę dowolnego uprawnionego operatora, zapisuje ją
idempotentnie i zwraca trwały queue ID, status, pochodzenie pól
(`user_input/evidence/inference/unknown`), typed blockers i jeden
`safe_next_step`. Requester nie musi wypełniać istniejącego sześciopolowego
formularza. Ten slice nie uruchamia researchu, planning proposal, generacji,
ActionObject ani vendor write.

Wymóg „dowolny operator” oznacza brak hardcodowania osoby, nie fikcyjne
uwierzytelnienie: obecny local pilot raportuje stałego, niezweryfikowanego
actor. Nie przyjmuj nazwisk ani uprawnień z samego promptu. Użyj tylko
zweryfikowanego request context; jeśli kolejka ma przypisywać zadania
konkretnym pracownikom, aktor/assignment contract jest osobną bramą.

**Falsifier:** ten sam request/key zwraca to samo ID; inny request z tym samym
key daje conflict; prośba „artykuł o PPWR” zostaje przyjęta i pokazuje brak
fresh demand oraz niezatwierdzone PPWR facts, bez briefu wypełnionego z
domysłów i bez planu/draftu/zapisu.

### Q2 — typowany odczyt researchu

Najpierw użyj już istniejących exact-page/official-primary evidence acquisition,
research proposal, regulatory/public source review, approved Service Profile i
research-packet seams. M3c/M3d muszą przekazać do nich current exact identity;
Q2 nie może skopiować ich transportu, digestów, promotion action ani Codex
app-server runtime. Output dla operatora jest po polsku, zachowuje polskie i
angielskie źródła wraz z linkiem, językiem, datą, zakresem i autorytetem.

Zweryfikowana luka: obecny source acquisition wymaga identity binding albo
authoring receipt, a official primary wymaga server-owned candidate przypiętego
do exact pathu. Nie znalazłem ask-scoped kontraktu, który zbierałby źródła
konkurencji i official discovery dla nowego tematu. Ahrefs gap analysis jest
osobnym read workflow, nie jest obecnie łączony z nowym-page ask i jego dane
są stale/unverified. `credible_external` i podobne acquisition intents nie mają
research adaptera w tym slice'u. Przed dodaniem nowego readera trzeba
zidentyfikować istniejący bezpieczny provider lub podjąć source-to-decision dla
jednej konkretnej luki. Nie podstawiaj tekstu modelu jako dowodu i nie dodawaj
równoległej ścieżki modelowej.

**Falsifier:** każdy zaakceptowany fakt ma source/evidence ID, URL, odczytany
zakres, datę i freshness; niezweryfikowany kandydat pozostaje zablokowany;
stale GSC/Ahrefs nie tworzą popytowego ani konkurencyjnego claimu; stary
research packet/action nie jest tworzony ponownie, gdy exact digest jest
bieżący.

### Q3 — resumowalne kroki i human gates

Request-owned runner zapisuje current step, gate status, ownera,
retry/idempotency i append-only lineage. Deleguje exact reads i planning do
istniejących domain stores/endpoints; nie traktuje `WorkflowRun` ani
APScheduler connector jobs jako workerów treści. Może automatycznie przejść
przez jednoznaczne read-only bramki, ale zatrzymuje się dla niejasnej strony,
service, audience, CTA, claimu lub źródła. Odpowiedź człowieka wznawia
wyłącznie bramki zależne od tej odpowiedzi.

**Falsifier:** przerwane zadanie wznawia się z tym samym ID/evidence; bounded
retry nie duplikuje efektów; zmiana źródła lub świeżości unieważnia zależne
bramki; brak decyzji pozostaje jawny.

### Q4 — propozycja briefu i routing do obecnych API

Składaj reviewable brief z requestu, zweryfikowanych dowodów i jawnie
oznaczonych inferencji. Oznacz unknown zamiast wymyślać brakujące dane. Dopiero
po gotowości briefu nowa strona może użyć istniejącego
`planning-proposal`; istniejąca strona trafia do exact-page workflow.

**Falsifier:** każdy brief field ma provenance; unsupported claim pozostaje
blocked; routing wybiera jedną właściwą gałąź albo zwraca typed ambiguity.

### Q5 — marketer surface i operator routing

Po istnieniu typed API pól podepnij tworzenie, status i wznowienie kolejki do
obecnego `/content-workflow`/document canvas oraz właściwych operator skills.
Najpierw zamknij M3d exact identity handoff dla istniejącego
`CurrentResearchPacketEntry`; potem przepnij skill z obecnego blocked
`/planning-proposals` POST przez v3 packet review oraz
`planning-generation-intent-v3` ActionObject/dispatch. Żaden caller nie
powinien utrzymywać własnej identity/currentness logiki. Zachowaj jedną
API-owned podróż; nie dodawaj osobnego dashboard planera ani logiki domenowej
w React.

**Falsifier:** caller odczytuje ten sam queue ID i status z API; istniejący
manualny flow nadal przechodzi; user widzi decision, evidence, blocker i next
safe step bez czytania raw payload.

### Q6 — dokładna rewizja, review i szkic dev

Przekaż gotowy brief do istniejącego per-URL identity/v3 generation/review
seam. Utrzymaj exact revision, ActionObject, human confirmation, audyt i
create-only dev draft/readback. `the_content` wymaga exact observed target;
ACF wymaga pełnego clone/profile i jawnego potwierdzenia mapowania. Przed
szerszą kohortą przeprowadź ścieżkę editorial, service i landing/hub. Nie
rozszerzaj tego slice'a na publikację ani mass generation.

**Falsifier:** zmiana identity/source/claim/review blokuje dispatch do czasu
ponownej walidacji; exact draft digest zgadza się z readbackiem; żadna
publiczna write nie następuje.

### Q7 — obecny inventory i wszystkie kwalifikujące się URL-e

Pobierz aktualny, wersjonowany sitemap/work-item inventory przez publiczny
WILQ seam. Każdy URL dostaje typed disposition; każda kwalifikująca się strona
wchodzi do bieżącej kolejki jako work item z decyzją lub blockerem. To jest
outcome M4 w aktywnej migracji `gg8j`, a nie drugi census ticket. Uzgodnij
eligibility/current_acceptance z per-URL authority, nie z historycznym
214-row snapshotem.

**Falsifier:** eligible, typed-excluded i blocked dokładnie pokrywają odczytany
inventory; stary lub fuzzy binding nie może dać pozytywnej decyzji. Ten outcome
zależy od current per-URL observation producer oraz M3d selected-workspace
identity handoff w tym samym Beadzie.

## Bieżące zależności Q1–Q7

```text
active gg8j: M3c → M3d → Q7/M4 → C1
                                   │
                              Bead closes
                                   ↓
Q1 intake → Q2 evidence/research → Q3 gates → Q4 brief/routing
                                             ↓
                                Q5 marketer surface → Q6 exact delivery
```

Kolejność Q1 po zamknięciu `gg8j` wynika z repo WIP=1, nie z technicznej
zależności. Q1 nie czeka na wybór providera wymaganego przez Q2. Q2–Q4 są
konieczne, zanim kolejka obieca evidence-backed brief. Q5 zależy od typed API
contractów Q1–Q4. Q6 zależy od briefu, source gates i istniejącego exact
identity/ActionObject path. Q7 jest M4 w `gg8j`: wymaga świeżego inventory,
per-URL observation i current-acceptance seam; nie twórz osobnego Beada ani
drugiej implementacji census dla tego samego acceptance.

## Historyczne zależności planu S0–S12

```text
S0 → S1 → S2 → S3 → corpus preflight → S4 → S5 → S6 → S7 → S8 → S9
                                                    ↓              ↓
                                          cohort QA/readback → S10 final QA
                                                                   ↓
                                                               S11 → S12
runtime credentials ───────────────────────────────→ S6/S7/S9
```

Research może pogłębiać packet następnej strony równolegle jako read-only, ale
nie może pisać stanu. Writer pozostaje jeden. External credential/source blocker
zatrzymuje tylko swój URL; kolejny URL może ruszyć dopiero po zapisaniu blokera
i zakończeniu bieżącego Beada zgodnie z WIP=1.

## Aktualny proof i definicja zakończenia

Cały wynik jest kompletny wyłącznie, gdy:

1. Uprawniona osoba może utworzyć ask-only kolejkę bez briefu; create/readback
   jest idempotentny i każdy stan ma ownera, provenance, blocker oraz jeden
   safe next step.
2. Każdy użyty fakt ma exact source/evidence lineage, freshness i autorytet;
   nierozstrzygnięte albo stale dowody pozostają typed blockerami.
3. Queue runner bezpiecznie wznawia się po pause/retry, nie duplikuje efektów,
   a każda decyzja człowieka wiąże się z exact request/gate.
4. Brief ma provenance przy każdym polu, a overlap, audience, intent, claims i
   konkurencyjne twierdzenia nie są wnioskowane z niewłaściwego poziomu danych.
5. Nowe i istniejące strony trafiają do swoich API-owned ścieżek; dashboard i
   skills używają tych samych typed contracts.
6. Każda dostarczona treść ma exact identity, approved sources, rozwiązane
   critical findings, review, human authorization i exact dev draft readback
   albo prawdziwy typed external blocker.
7. Każdy URL w aktualnym, wersjonowanym inventory ma typed disposition; każda
   kwalifikująca się strona ma decyzję lub typed blocker. Żaden historical
   count ani fuzzy join nie daje zakończenia.
8. Privacy/consent gate chroni dane; nie wykonano public publish/update/delete,
   nie ujawniono credentials i nie przypisano metrykom niepotwierdzonej wartości.
9. Wymagane focused falsifiers, fixed-point review i CI są zielone na
   zatwierdzonym merged SHA; managed API/dashboard odczytują ten sam stan.

Brak świeżego źródła, credentials/consent lub exact targetu może pozostać
terminalnym blockerem konkretnego zadania. Brak seamu, bindingu, klasyfikacji,
review harnessu, mapowania albo walidatora jest pracą do naprawienia, nie
zewnętrznym blockerem.
