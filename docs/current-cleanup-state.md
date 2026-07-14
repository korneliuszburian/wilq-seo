# Current Cleanup State — 2026-07-14

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

Zacommituj i pushuj zamknięty P0 `wilq-seo-r564.7`. Snapshot ma
kanoniczne pięć API-owned kroków `scope → section_map → draft → review →
dev_draft`; marketer mode pokazuje task mapę, jeden aktywny workspace i
marketer-facing wynik sprawdzenia bez zapisu. Technical wall montuje się
wyłącznie w `Audyt techniczny`. Nie przywracaj usuniętych duplikatów,
parsowania polskiego status copy ani lokalnego numeru wersji.

Po pushu utwórz i rozpocznij P0 child `wilq-seo-r564` dla immutable,
revision-bound persistence: server-owned `revision_id`, digest,
`base_revision_id`, trwałe sekcje, optimistic conflict i human decision
powiązana z dokładną wersją. Ten seam nie może jeszcze wywoływać Codexa,
ActionObjectu ani WordPressa.

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
- Tekst edytora jest nadal lokalnym, niezapisanym szkicem roboczym. Legacy
  package review/audit nie zatwierdza konkretnego tekstu, dlatego `review` i
  `dev_draft` pozostają zamknięte do czasu immutable revision persistence i
  exact-version human acceptance.
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
- Create należy do zamkniętego `c9h9.4`: canonical apply buduje typed capability
  wewnątrz `apply_action` i wiąże exact action, work item, handoff, draft package,
  dev host, operatora i mutation audit. Publish, update i delete pozostają poza
  zakresem.

## Bieżący graf

- `wilq-seo-r564.7` jest zamknięty po pełnym proof i czeka wyłącznie na
  świadomy commit/push.
- Parent `wilq-seo-r564` pozostaje otwarty. Queue density jest zewnętrznie
  niepełna (1 actionable z wymaganych 3), ale nie blokuje repo-local kontraktu
  trwałych rewizji.
- Po zamknięciu `r564.7` utwórz P0 child dla immutable revision persistence;
  aktualne wyszukiwanie Beads nie znalazło istniejącego zadania o tym zakresie.
- Nie kopiuj tutaj pełnej listy Beads ani historii zamkniętych seamów. Po każdym
  pushu odczytaj `bd ready --json` i `bd list --status=open --json`.

## Verification checkpoint

- Focused backend: canonical journey builder/response invariants i snapshot API.
- Focused shared: exact five-step Zod order/current contract.
- Focused dashboard: jeden workspace, pięć zakładek fixture, uczciwa etykieta
  szkicu, typed feedback sprawdzenia bez zapisu i brak mutation requestów.
- Browser: live 1440×900/390×844 current/revisit proof w
  `.local-lab/proof/dashboard-content-workflow/2026-07-14T02-17-53-121Z/`;
  osobny deterministyczny 390px contract proof ma chronić dokładnie pięć
  zakładek przed overflow i jest w
  `.local-lab/proof/dashboard-content-workflow/2026-07-14T02-33-15-013Z/`.
- Finalne `scripts/verify.sh`: 943 backend (2 skip), 158 dashboard, 34 shared
  (10 skip), security/API/skill smoke, 20/20 Playwright i build. Managed stack
  po bramce jest zdrowy na API `:8000` i dashboardzie `:5173`.
- Pełny verify uruchamiaj przy zatrzymanym managed stacku: dashboard E2E czyta
  aktualny local evidence store, a równoległy API trzyma lock DuckDB.

## Resume

1. Sprawdź finalny diff/status, commituj zamknięty `wilq-seo-r564.7` i pushuj
   `origin/main`.
2. Ponownie odczytaj roadmapę. Utwórz/rozpocznij revision-persistence P0 tylko
   jeśli nadal nie istnieje lepszy pokrywający Bead, i kontynuuj bez powtarzania
   ukończonej pracy.
