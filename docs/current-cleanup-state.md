# Current Cleanup State — 2026-07-15

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

`wilq-seo-r564.9` domknął API seam exact revision → WordPress draft:
immutable handoff, ten sam binding w preview/review/confirm/impact/apply,
typed blocker i fail-close legacy review/audit. Syntetyczny adapter dostał
dokładnie zatwierdzony tekst; v2, manipulacje, równoległy apply i replay
zatrzymały się przed adapterem. Jednorazowa zgoda jest atomowo konsumowana, a
sekretopodobne wartości w lineage są redagowane przed audytem. Durable start i
atomowy outcome chronią crash window; przerwany claim ma lokalne, readbackowe
reconciliation bez ponowienia write.
Następny P0 ma udostępnić ten sam kontrakt człowiekowi jako zwarty inline
multi-step w `/content-workflow` zamiast ogólnego linku do akcji bez kontekstu.

Po udowodnieniu rewizji następny bounded research/prototype to server-side
handshake WILQ API → Codex app-server korzystający z istniejącego `codex login`
przez ChatGPT.
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
  immutable rewizji, ale `dev_draft` w UI pozostaje zablokowany, dopóki
  dashboard nie przeprowadzi exact ActionObject chain dla wybranej wersji.
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
  ale nie autoryzują adaptera. Journey nie uruchamia jeszcze `dev_draft`, bo
  dashboard nie przekazuje bindingu do tych kroków. Publish, update i delete
  pozostają poza zakresem.
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
- Parent `wilq-seo-r564` pozostaje otwarty. Queue density jest zewnętrznie
  niepełna (1 actionable z wymaganych 3), a Service Profile i Wilku UAT nadal
  wymagają ownera. Nie blokuje to repo-local inline ActionObject UX ani
  ograniczonego lab-testu Codex app-server.
- Nie kopiuj tutaj pełnej listy Beads ani historii zamkniętych seamów. Po każdym
  pushu odczytaj `bd ready --json` i `bd list --status=open --json`.

## Verification checkpoint

- Focused backend/shared/dashboard chronią append-only persistence,
  idempotency, stale-base conflict, exact review, context drift, atomową
  konsumpcję zgody, redakcję bindingu i typed journey.
- Browser proof: save → refetch/reload → exact review → approved revision →
  fail-closed `dev_draft`, 1440×900 i 390×844; dwa POST-y na viewport, zero
  Codex/ActionObject/WordPress. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-14T05-09-46-343Z/`.
- Szeroki gate potwierdził 977 backend testów (2 skip), 36 shared i 164
  dashboard testy oraz security/API/skill smokes. Pierwszy downstream start
  ujawnił tylko zbyt krótki 15-sekundowy wait; po podniesieniu go do 40 sekund
  pełny Playwright przechodzi 21/21, a dashboard build przechodzi.
- Kanoniczny `local_stack.sh restart` po wyrównaniu cold-start wait do 40 sekund
  kończy się zdrowym API `:8000` i dashboardem `:5173`.
- Pełny verify uruchamiaj przy zatrzymanym managed stacku: dashboard E2E czyta
  aktualny local evidence store, a równoległy API trzyma lock DuckDB.

## Resume

1. Commituj i pushuj zamknięty `r564.9`.
2. Ponownie odczytaj roadmapę i rozpocznij P0 inline ActionObject dla
   `dev_draft` wybranej rewizji.
3. Zweryfikuj desktop/mobile oraz API: exact version, jeden CTA na krok,
   typed blocker i zero zapisu przed finalnym apply.
4. Następnie wykonaj bounded lab-test `codex app-server` po stronie serwera;
   browser nie może rozmawiać z Codex bezpośrednio.
