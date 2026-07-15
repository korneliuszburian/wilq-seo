# Current Cleanup State — 2026-07-15

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

`wilq-seo-r564.10` domknął zwarty exact-revision flow człowieka w
`/content-workflow`: podgląd, review, potwierdzenie, kontrola bezpieczeństwa i
draft-only apply używają jednego API-owned bindingu. Tylko aktywny etap jest
rozwinięty. Resume czyta najnowsze uporządkowane eventy tej wersji, a typed
konflikt lub terminalny blocker zatrzymuje przebieg bez retry. Syntetyczny
browser proof przechodzi cały flow bez połączenia z WordPressem.

Następny bounded P0 to server-side handshake WILQ API → Codex app-server
korzystający z istniejącego `codex login` przez ChatGPT. Pierwszy wynik ma być
propozycją child revision dla wybranej usługi i sekcji, ze statusem przebiegu,
lineage dowodów i bez samodzielnego review lub zapisu WordPress. Obecny builder
Structured Outputs tworzy pełny `model_input`, ale wysyła modelowi tylko dwie
instrukcje; `claim_markers`, source facts i sekcje nie docierają do runtime'u.
Nie traktuj tej ścieżki jako grounded generation ani nie utrwalaj jej jako
fallback. Nowy lab musi przenieść cały typed input i przejść quality review.
Browser nie rozmawia z Codex bezpośrednio; Codex nie jest właścicielem workflow,
dowodów, approval ani ActionObject. Nie dodawaj wymogu `OPENAI_API_KEY`,
Agents SDK, Ollamy, fallbacku modelu ani alternatywnego runtime’u.

`c9h9.4` jest zamknięty i nie wolno go powtarzać. Po każdym slice uruchom
`bd ready --json`, zaktualizuj ten handoff, zrób świadomy commit/push i
kontynuuj najwyższy bezpieczny task.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`;
  publiczny `ekologus.pl` pozostaje SEO truth, a Proudsite jest wyłącznie
  draft/dev workspace.
- Snapshot ma jeden kanoniczny journey `scope → section_map → draft → review →
  dev_draft`. Live krok to `draft`; ukończone `scope` i `section_map`
  można tylko przeglądać ponownie bez przesuwania API-owned current step.
- Ocena 8/10 dotyczy wyłącznie bezpieczeństwa exact handoffu. Realna
  użyteczność tworzenia treści jest obecnie około 5/10: marketer-facing
  `Sprawdź tekst szkicu` uruchamia WordPress dry-run, a właściwe quality review
  pozostaje w audycie technicznym. Nie claimuj jakości tekstów przed naprawą
  grounded input i testem paczki na konkretnej usłudze/sekcji.
- Marketer widzi stronę, usługę, decyzję, pięć zadań i jeden aktywny workspace.
  Dziewięć paneli technicznych nie istnieje w marketer-mode DOM i wymaga
  jawnego przejścia do `Audyt techniczny`.
- Read-only refresh `wordpress_sklep` i Ahrefs z 2026-07-14 przywrócił
  freshness. Kolejka pozostaje uczciwie `blocked`: 2 kandydatów, 1 actionable,
  minimum 3. Nie wolno wymyślać trzeciego tematu.
- Service Profile dla wybranego work itemu jest związany z usługą, ale jego
  publiczne karty nadal wymagają review; WILQ nie przedstawia tego jako
  zatwierdzonej polityki twierdzeń.
- Zapisane wersje są append-only i wracają po reloadzie. Niezapisane edycje są
  wyłącznie lokalnym stanem formularza. Review dotyczy dokładnego
  `revision_id`, digestu treści i digestu paczki planu; zmiana kontekstu
  unieważnia review. WordPress handoff/apply jest revision-bound i wysyła body
  immutable rewizji. `dev_draft` prowadzi ten sam binding przez cały inline
  ActionObject chain i po sukcesie odświeża snapshot, readiness i readback.
  Obecny dowód jest syntetyczny; nie wykonano realnego write do WordPressa.
- Nawigacja nie wywołuje write requestów. Preview pozostaje dry-run, a każdy
  przyszły zapis WordPress musi przejść przez exact ActionObject, confirmation i
  audit; publish/update/delete pozostają poza tym journey.
- Bieżąca prawda pozostałych tras jest w `docs/dashboard-state.md`, stan
  bieżącego slice’a w `docs/PROGRESS.md`, a graf pracy w Beads. Nie duplikuj
  tutaj zamkniętych seamów ani historycznych screenshotów.

## Granica bezpieczeństwa

- Content router zawsze przekazuje `create_draft=None` i
  `action_apply_authorized=False`.
- Direct live zwraca `action_apply_required` przed adapterem.
- Readiness: `ready=false`,
  `write_authorization_status=blocked_outside_action_apply`, suggested `null`.
- Central mutation summary: 0 vendor-write possible i 0 attempted.
- React ma wyłącznie builder `mode=dry_run`, `write_authorization=null`; UI nie
  utrwala już niemożliwego direct live contractu.
- Existing draft jest otwierany/podglądany; brak create/duplicate CTA.
- Create/apply akceptuje wyłącznie aktualny approved revision binding i
  najnowszy uporządkowany ślad preview/review/confirm/impact z tym samym
  bindingiem. Atomowy claim serializuje apply z append/re-review; drugi request
  i replay starej zgody kończą się przed adapterem. Legacy eventy są czytelne,
  ale nie autoryzują adaptera. Dashboard przekazuje exact binding we wszystkich
  binding-capable requestach i nie ponawia apply po typed `409`; nowszy binding
  resetuje lokalne akceptacje. Publish, update i delete pozostają poza zakresem.
- Claim zapisuje `action_apply_started` przed vendor call. Outcome, mutation
  audit i execution/post ID są finalizowane w jednej transakcji. Po crashu
  lokalne `wilq wordpress-apply reconcile` czeka 300 sekund, wymaga jawnej
  inspekcji, sprawdza status draft dla `applied` i nie ponawia vendor write.

## Bieżący graf

- `wilq-seo-r564.7` jest zamknięty i wypchnięty w `b23e413a`.
- `wilq-seo-r564.8` jest zamknięty: append-only draft revisions i human
  decisions są związane z dokładną wersją i digestami.
- `wilq-seo-r564.9` jest zweryfikowany: exact revision handoff, ActionObject i
  draft-only adapter używają jednej wersji; legacy/v2/tamper są fail-closed.
- `wilq-seo-r564.10` jest zweryfikowany: inline wizard utrzymuje ten binding od
  preview do apply, wznawia wyłącznie zgodny ordered audit i zatrzymuje typed
  konflikt bez retry. Desktop/mobile proof jest syntetyczny i nie dotyka
  WordPressa.
- Parent `wilq-seo-r564` pozostaje otwarty. Queue density jest zewnętrznie
  niepełna (1 actionable z wymaganych 3), a Service Profile i Wilku UAT nadal
  wymagają ownera. Nie blokuje to ograniczonego lab-testu Codex app-server ani
  evidence-backed propozycji tekstu dla konkretnej usługi i sekcji.
- Nie kopiuj tutaj pełnej listy Beads ani historii zamkniętych seamów. Po każdym
  pushu odczytaj `bd ready --json` i `bd list --status=open --json`.

## Verification checkpoint

- Focused backend/shared/dashboard chronią append-only persistence,
  idempotency, stale-base conflict, exact review, context drift, atomową
  konsumpcję zgody, redakcję bindingu i typed journey.
- Browser proof: save → refetch/reload → exact review → preview → review akcji
  → confirm → impact → syntetyczny apply → draft-only readback, 1440×900 i
  390×844. Endpointy ActionObjectu są przechwycone; zero realnego WordPress
  write. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T11-50-52-058Z/`.
- Focused API/UI przechodzą 32/32, TypeScript i ESLint są zielone, focused
  Playwright przechodzi 1/1, a niezależny Standards+Spec review nie znalazł
  uchybień. Syntetyczny proof nie zastępuje Wilku UAT.
- Szeroki gate potwierdził 977 backend testów (2 skip), 36 shared i 164
  dashboard testy oraz security/API/skill smokes. Pierwszy downstream start
  ujawnił tylko zbyt krótki 15-sekundowy wait; po podniesieniu go do 40 sekund
  pełny Playwright przechodzi 21/21, a dashboard build przechodzi.
- Kanoniczny `local_stack.sh restart` po wyrównaniu cold-start wait do 40 sekund
  kończy się zdrowym API `:8000` i dashboardem `:5173`.
- Pełny verify uruchamiaj przy zatrzymanym managed stacku: dashboard E2E czyta
  aktualny local evidence store, a równoległy API trzyma lock DuckDB.

## Resume

1. Zamknij `r564.10`, zrób świadomy commit/push i ponownie odczytaj roadmapę.
2. Rozpocznij bounded lab-test `codex app-server` po stronie serwera; browser
   nie może rozmawiać z Codex bezpośrednio.
3. Propozycja ma tworzyć child revision dla jawnie wybranej usługi, strony i
   sekcji oraz zachowywać evidence/claim lineage. GSC, GA4, Ahrefs, Ads,
   Keyword Planner i inventory są używane tylko, gdy istnieje aktualny typed
   dowód; brak lub stale źródło jest blockerem, nie wymyśloną metryką.
4. Potem przetestuj wynik na syntetycznym/approved materiale i przygotuj
   review-ready paczkę tekstów; jakości 10/10 nie claimuj przed realnym Wilku
   UAT i owner-reviewed Service Profile.
