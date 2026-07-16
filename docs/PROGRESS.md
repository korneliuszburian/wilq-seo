# WILQ Progress Ledger

Ostatnia aktualizacja: 2026-07-16.

To jest krótki stan bieżący. Historia zmian i proofów pozostaje w git, Beads
i lokalnych katalogach `.local-lab/proof/`; ten plik nie jest kroniką.

## Aktywny kierunek

- Kanoniczny bieżący cel jest w `docs/goals/001-goal.md`; archiwalny Goal 005
  nie jest już aktywnym recovery entrypointem. Operacyjna kolejka pozostaje
  wyłącznie w Beads pod `wilq-seo-1oa` i review-only `wilq-seo-v9ab`.
- Priorytetem jest jeden użyteczny workspace `/content-workflow`, a nie nowe
  ekrany ani kolejne warstwy ceremonii.
- Kanoniczny przebieg marketera ma pięć kroków:
  `scope → section_map → draft → review → dev_draft`.
- WILQ API jest właścicielem stanu, dowodów, wersji, decyzji, ActionObjectów
  i audytu. React renderuje typed view-model i przechowuje tylko niezapisane
  edycje formularza.
- Ograniczony executor działa po stronie serwera przez Codex app-server i
  istniejący `codex login`. OpenAI API key, Agents SDK, Ollama ani drugi model
  nie są zależnościami produktu. Browser nie łączy się z Codex bezpośrednio.

## Ostatnie domknięte zakresy

- Live homepage UAT ujawnił, że dwa query GSC dziedziczyły wszystkie trzy
  sekcje tylko dlatego, że facts i sekcje współdzieliły refresh-level evidence
  ID. Demand evidence zachowuje oba query jako page-level proof, ale sekcję
  przypisuje wyłącznie po konserwatywnym dopasowaniu tokenu do jej nagłówka lub
  celu. Typed `section_mapping_status` rozróżnia `lexical_relevance` i
  `page_only`. Focused BDO case mapuje relewantny term i pozostawia niepowiązany
  term z pustą mapą; live homepage snapshot ma 2 świeże query i 0 fałszywych
  przypisań do sekcji. Browser opisuje oba jako sygnał strony bez potwierdzonej
  sekcji. Scope nadal wymaga decyzji Wilka, a Service Profile review ownera.
- Epiki `wilq-seo-c9h9` (43/43 dzieci), `wilq-seo-3bst` (28/28) i
  `wilq-seo-amj2` (10/10) są zamknięte po ponownym odczycie grafu. Nie zamyka to
  Goal 005: `lt1` nadal wymaga reviewed knowledge, `jst` realnego Wilku UAT, a
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
- `wilq-seo-r564.14` usuwa pięć publicznych ścieżek ujawniających full generation
  contract: legacy generation/runtime/dwa preview oraz `draft-variants`. Usunięto
  OpenAI SDK/API-key runtime, dependency, env flags i browser schemas. OpenAPI
  ma jeden content-model entrypoint: exact `codex-proposal`; internal contract,
  output i preview blockers pozostają częścią jego serwerowego działania.
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
