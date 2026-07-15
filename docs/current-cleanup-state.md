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

`wilq-seo-r564.11` domknął server-side handshake WILQ API → Codex app-server
przez istniejący `codex login`. API pobiera pełny typed model input oraz exact
base/review, a dynamiczne pola trafiają wyłącznie do `untrusted` context.
App-server działa ephemeral/read-only na izolowanym profilu, wyłącza znane
capabilities i unieważnia wynik po zaobserwowanej próbie tool/server request;
stockowy protokół nie daje jednak twardej gwarancji `tool-free`. Wynik może
  utworzyć tylko `unreviewed` child revision, a rewizja i terminalny run zapisują
  się atomowo z trwałym evidence/claim lineage. Quality dotyczy wyłącznie
  utrwalanych wybranych sekcji; obcy identifier, literalny known blocked claim i
  wąski high-risk promise guard są fail-closed, lecz pełna semantyka nadal wymaga
  człowieka. Finalny proof po hardeningu
utworzył 38-słowną poprawkę sekcji na dwóch dowodach GSC/WP bez zaobserwowanej
próby tool call, ale quality uczciwie zwróciło
`needs_changes`; nie jest to dowód finalnej jakości tekstu. Browser nadal nie
rozmawia z Codex bezpośrednio, a Codex nie jest właścicielem workflow, approval
ani ActionObject.

`wilq-seo-r564.13` podłączył proposal do aktywnego kroku `draft`: Wilku wybiera
API-approved sekcje exact reviewed revision, widzi pending, diff baza/child,
lineage, findings i semantyczną bramkę review. Browser-safe snapshot nie zawiera
promptu ani model inputu. Marketerowy WordPress dry-run udający content review i
osierocone panele zostały usunięte. Desktop/mobile proof nie dotyka Codexa ani
WordPressa; exact proposal POST jest syntetycznie przechwycony.

Następny bounded P0 to `wilq-seo-r564.14`: po migracji skilla i testów usunąć
cztery publiczne Structured Outputs generation/runtime/preview routes oraz ich
API-key runtime. Zachowaj wewnętrzny structured contract/output i preview
blockers używane przez kanoniczny Codex proposal. Nie dodawaj `OPENAI_API_KEY`,
Agents SDK, Ollamy ani alternatywnej ścieżki modelu.

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
- Ocena 8/10 dotyczy wyłącznie bezpieczeństwa exact handoffu. Operator workflow
  ma obecnie około 6/10, ale jakość realnego tekstu pozostaje około 5/10:
  sekcję można już poprawić przez grounded Codex proposal i porównać wynik,
  lecz realny proof był generyczny i `needs_changes`. Nie claimuj jakości przed
  owner-reviewed Service Profile i testem paczki na konkretnej usłudze/sekcji.
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
- `wilq-seo-r564.11` jest zamknięty i zweryfikowany: full grounded input przechodzi przez
  lokalny app-server, obcy lineage jest fail-closed, a poprawny wynik tworzy
  niezatwierdzoną child revision z run/evidence/claim trace. Realny output ma
  verdict `needs_changes`, więc usefulness tworzenia treści pozostaje 5/10.
- `wilq-seo-r564.12` jest zamknięty: zwalidowany
  `normalized_page_path` zachowuje exact publiczną ścieżkę w context-packu,
  natomiast tokenowe, sekretowe i malformed ścieżki pozostają redagowane.
- `wilq-seo-r564.13` jest zweryfikowany: marketer wybiera exact sekcje i widzi
  pending/diff/findings bez promptu w browserze, approval ani WordPress write.
  Cross-work-item result i brak wybranej sekcji są fail-closed. Proof 1440×900 i
  390×844: `.local-lab/proof/dashboard-content-workflow/2026-07-15T19-06-55-670Z/`.
- `wilq-seo-r564.14` jest otwartym P0 dla usunięcia publicznego alternatywnego
  OpenAI Structured Outputs runtime. Internal generation contract pozostaje
  wymagany przez kanoniczny proposal i nie jest martwym artefaktem.
- Parent `wilq-seo-r564` pozostaje otwarty. Queue density jest zewnętrznie
  niepełna (1 actionable z wymaganych 3), a Service Profile i Wilku UAT nadal
  wymagają ownera. Nie blokuje to podłączenia zweryfikowanego proposal seam do
  aktywnego kroku dashboardu ani evidence-backed propozycji konkretnej sekcji.
- Nie kopiuj tutaj pełnej listy Beads ani historii zamkniętych seamów. Po każdym
  pushu odczytaj `bd ready --json` i `bd list --status=open --json`.

## Verification checkpoint

- Focused proposal/store/preview chronią pełny grounded input, body-only claim
  leakage, brak quality credit z model-only delivery fields, atomowość child
  revision z CodexRun i fail-closed tool attempt; 29/29 przechodzi. Focused
  redaction przechodzi 5/5, a pierwotny context-pack repro 1/1.
- Browser proof proposal: exact needs-changes base → wybór sekcji → pending →
  baza/child → findings → semantic review, 1440×900 i 390×844, bez overflow i
  bez requestu WordPress. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T19-06-55-670Z/`.
- Osobny browser proof handoff: save → refetch/reload → exact review → preview → review akcji
  → confirm → impact → syntetyczny apply → draft-only readback, 1440×900 i
  390×844. Endpointy ActionObjectu są przechwycone; zero realnego WordPress
  write. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T11-50-52-058Z/`.
- Focused API/UI przechodzą 32/32, TypeScript i ESLint są zielone, focused
  Playwright przechodzi 1/1, a niezależny Standards+Spec review nie znalazł
  uchybień. Syntetyczny proof nie zastępuje Wilku UAT.
- Aktualny szeroki `scripts/verify.sh` doszedł do 986 backend testów (2 skip) i
  ujawnił jeden błąd redakcji; po naprawie jego pierwotny publiczny repro jest
  zielony. Umbrella nie był powtarzany dla już zielonych testów. Aktualne
  `security.sh`, Ruff, mypy, oba content skill smokes oraz niezależny
  Standards/Spec/security review są zielone.
- Kanoniczny `local_stack.sh restart` kończy się zdrowym API `:8000` i
  dashboardem `:5173`; health, metrics, content queue i `/content-workflow`
  zwracają 200.
- Pełny verify uruchamiaj przy zatrzymanym managed stacku: dashboard E2E czyta
  aktualny local evidence store, a równoległy API trzyma lock DuckDB.

## Resume

1. Wykonaj `wilq-seo-r564.14`: przez `$skill-creator` przepnij content operatora
   na readiness/exact proposal, usuń cztery alternate public routes i API-key
   runtime, lecz zachowaj internal generation contract używany przez proposal.
2. GSC, GA4, Ahrefs, Ads, Keyword Planner i inventory używaj tylko, gdy istnieje
   aktualny typed dowód; brak lub stale źródło jest blockerem, nie wymyśloną
   metryką ani wolumenem słowa kluczowego.
3. Potem przygotuj review-ready paczkę tekstów; jakości 10/10 nie claimuj przed realnym Wilku
   UAT i owner-reviewed Service Profile.
