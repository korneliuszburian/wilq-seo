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
- Docelowy executor ma działać po stronie serwera przez Codex app-server/SDK
  i istniejący `codex login`. OpenAI API key, Agents SDK, Ollama ani drugi model
  nie są zależnościami produktu.

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

## Bieżący proof

- Focused backend, shared schema, dashboard tests, Ruff, mypy, TypeScript,
  ESLint i diff check przechodzą. Szeroki code gate potwierdził 977 backend
  testów (2 skip), 36 shared i 164 dashboard testy oraz security/API/skill
  smokes.
- Stateful browser proof przechodzi dla 1440×900 i 390×844:
  zapis → refetch → reopen/reload → exact review → zaakceptowana wersja →
  zablokowany `dev_draft`.
- Ten proof wykonuje dokładnie dwa POST-y na viewport: zapis wersji i review.
  Nie wywołuje Codexa, ActionObjectu ani WordPressa.
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

## Następny bezpieczny zakres

Po pushu `r564.9` domknąć brakującą ergonomię człowieka w jednym workspace:

1. `/content-workflow` ma przekazać binding wybranej rewizji do inline kroków
   preview → review → confirm → apply, zamiast wysyłać marketera na ogólną
   stronę akcji bez kontekstu;
2. każdy krok ma pokazać dokładną wersję, blocker i następny bezpieczny ruch;
   apply pozostaje draft-only i wymaga jawnego operatora;
3. potem wykonać ograniczony lab-test server-side `codex app-server` nad
   istniejącym `codex login`: propozycja child revision i stream statusu, bez
   approval oraz bez vendor write.

## Jawne blokery i ograniczenia

- Brakuje owner-reviewed, `approved_current` Service Profile do finalnej pracy
  treściowej.
- Brakuje realnej sesji Wilku UAT albo jawnego owner defer z ryzykiem
  rezydualnym.
- Queue nie ma wymaganych trzech wykonalnych pozycji; WILQ nie tworzy sztucznej
  trzeciej propozycji.
- `created_by="wilku"` i `reviewed_by="wilku"` nie są uwierzytelnionym
  tenant/actor contractem. Nie wolno przedstawiać ich jako takiego dowodu.
- Dashboard nie przekazuje jeszcze revision bindingu do ActionObject, więc
  `dev_draft` pozostaje uczciwie fail-closed mimo gotowego API seam.
- Goal 005, produkcyjna gotowość i pełna użyteczność dla marketera nie są
  zakończone.
