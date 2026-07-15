# WILQ Progress Ledger

Ostatnia aktualizacja: 2026-07-15.

To jest krótki stan bieżący. Historia zmian i proofów pozostaje w git, Beads
i lokalnych katalogach `.local-lab/proof/`; ten plik nie jest kroniką.

## Aktywny kierunek

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

## Bieżący proof

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
- Live snapshot pozostaje uczciwie na `draft`: workspace jest pusty, zapis
  pierwszej wersji jest dostępny, review i `dev_draft` są zamknięte.
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

1. Podłączyć API-owned propozycję do aktywnego kroku `draft`: jawny wybór
   sekcji, jedno CTA generowania, status runu, porównanie z bazą i czytelne
   quality findings. Nie wystawiać browserowi generic runtime ani promptu.
2. Następnie rozwijać najważniejszą wartość treściową: jawny wybór
   strony/usługi/intencji/CTA, bibliotekę/historię treści, typed keyword/Ads
   signals tylko z dowodami i realny Wilku UAT. Nie nadawać oceny 10/10 przed
   tym dowodem.

## Jawne blokery i ograniczenia

- Brakuje owner-reviewed, `approved_current` Service Profile do finalnej pracy
  treściowej.
- Brakuje realnej sesji Wilku UAT albo jawnego owner defer z ryzykiem
  rezydualnym.
- Queue nie ma wymaganych trzech wykonalnych pozycji; WILQ nie tworzy sztucznej
  trzeciej propozycji.
- Obecny marketer CTA `Sprawdź tekst szkicu` nadal uruchamia WordPress dry-run,
  a nowy grounded proposal seam nie jest jeszcze dostępny w dashboardzie.
  Legacy technical Structured Outputs runtime nadal pomija `model_input` i nie
  może być traktowany jako aktywna alternatywa; po sprawdzeniu referencji trzeba
  go usunąć albo wycofać wraz z przepięciem CTA.
- `created_by="wilku"` i `reviewed_by="wilku"` nie są uwierzytelnionym
  tenant/actor contractem. Nie wolno przedstawiać ich jako takiego dowodu.
- Goal 005, produkcyjna gotowość i pełna użyteczność dla marketera nie są
  zakończone.
