# Current Cleanup State — 2026-07-15

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

`wilq-seo-r564.8` jest zamknięty z kompletnym revision workspace,
exact-review proof oraz pełnym browser/build proof. Następny P0 child
`wilq-seo-r564` ma związać WordPress handoff i ActionObject z dokładnie
zaakceptowaną rewizją oraz fail-close legacy review/audit dla revision-enabled
work itemów.

Dopiero po udowodnieniu rewizji projektuj server-side handshake WILQ API →
Codex app-server/SDK korzystający z istniejącego `codex login` przez ChatGPT.
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
  unieważnia review. `dev_draft` pozostaje zablokowany, bo legacy WordPress
  handoff/apply nie jest jeszcze revision-bound.
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
- Existing create/apply zachowuje ActionObject review/confirm/audit, ale używa
  legacy handoff/package acceptance i nie jest autorytetem dla nowego revision
  workspace. Dlatego journey nie może jeszcze uruchomić `dev_draft`. Publish,
  update i delete pozostają poza zakresem.

## Bieżący graf

- `wilq-seo-r564.7` jest zamknięty i wypchnięty w `b23e413a`.
- `wilq-seo-r564.8` jest zamknięty: append-only draft revisions i human
  decisions są związane z dokładną wersją i digestami.
- Parent `wilq-seo-r564` pozostaje otwarty. Queue density jest zewnętrznie
  niepełna (1 actionable z wymaganych 3), a Service Profile i Wilku UAT nadal
  wymagają ownera. Nie blokuje to repo-local kontraktu revision-bound WordPress
  handoff, który jest następnym P0.
- Nie kopiuj tutaj pełnej listy Beads ani historii zamkniętych seamów. Po każdym
  pushu odczytaj `bd ready --json` i `bd list --status=open --json`.

## Verification checkpoint

- Focused backend/shared/dashboard chronią append-only persistence,
  idempotency, stale-base conflict, exact review, context drift i typed journey.
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

1. Commituj i pushuj zamknięty `r564.8`.
2. Utwórz i uruchom P0 revision-bound WordPress handoff.
3. Przenieś exact revision/digests/decision do handoff i ActionObject oraz
   fail-close legacy authority dla revision-enabled work itemów.
4. Zrób syntetyczny/staging draft-only proof, bez publikacji.
5. Ponownie odczytaj roadmapę; Codex adapter jest kolejnym seamem.
