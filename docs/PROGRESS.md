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

## Następny bezpieczny zakres

Po pushu slice'a `r564.8` utworzyć i rozpocząć P0 child `r564` dla
revision-bound WordPress handoff:

1. handoff i ActionObject muszą zawierać dokładne `revision_id`, digest treści,
   digest paczki planu i zaakceptowaną decyzję;
2. legacy human-review/audit nie może być alternatywną zgodą dla work itemu,
   który ma revision workspace;
3. podgląd pozostaje draft-only, a realny zapis wymaga osobnego review,
   potwierdzenia i audytu;
4. dopiero po tym seamie projektować adapter Codex app-server/SDK, który może
   zaproponować child revision, ale nie może zatwierdzić jej ani zapisać
   WordPress bez człowieka.

## Jawne blokery i ograniczenia

- Brakuje owner-reviewed, `approved_current` Service Profile do finalnej pracy
  treściowej.
- Brakuje realnej sesji Wilku UAT albo jawnego owner defer z ryzykiem
  rezydualnym.
- Queue nie ma wymaganych trzech wykonalnych pozycji; WILQ nie tworzy sztucznej
  trzeciej propozycji.
- `created_by="wilku"` i `reviewed_by="wilku"` nie są uwierzytelnionym
  tenant/actor contractem. Nie wolno przedstawiać ich jako takiego dowodu.
- Revision-bound WordPress handoff jest nadal pracą techniczną, nie blockerem
  właściciela. Do jego domknięcia `dev_draft` pozostaje fail-closed.
- Goal 005, produkcyjna gotowość i pełna użyteczność dla marketera nie są
  zakończone.
