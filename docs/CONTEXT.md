# WILQ Context Index

Ten plik jest krótkim indeksem recovery po utracie kontekstu. Nie jest
changelogiem ani kopią goalu. Jeżeli potrzebujesz historii, użyj git log,
`docs/progress/archive/` albo dedykowanych ledgerów.

## Start After Context Loss

Przeczytaj w tej kolejności:

1. `AGENTS.md` - stałe reguły pracy, sekrety, lokalne ścieżki i gotchas.
2. `docs/goals/archive/005-goal.md` - aktywny goal i granice aktualnego etapu.
3. `docs/PROGRESS.md` - krótki aktualny stan, aktywne luki i następny ruch.
4. `bd prime` and `bd ready --json` - operational issue graph for the current
   cleanup queue.
5. `docs/evals/skill-coverage-audit.md` - aktualna tabela pokrycia 12 skillów.
6. `docs/evals/skill-eval-ledger.md` - szczegóły manualnych i non-interactive
   przebiegów skillów.
7. `docs/architecture/bdos-class-wilq-operating-system.md` - produktowa
   poprzeczka “lepszy BDOS”.
8. `docs/infra/001.md` i `docs/audits/001-output.md` - pierwotny scope i
   audyt, tylko gdy trzeba sprawdzić źródłowy intent.

## Current Product Direction

WILQ to API-first Marketing Operating System dla Ekologus. WILQ API jest
mózgiem systemu; dashboard, Codex skills, hooks, workflows, expert rules,
szanse i akcje do sprawdzenia mają używać tych samych typed contracts.

Marketer jest polski. Widzi decyzje, źródła danych, dowody opisane po polsku,
blokady i bezpieczny następny krok. Techniczne ID, connector IDs, raw trace i
surowe payloady trafiają tylko do technicznego szczegółu albo audytu.

## Current Recovery State

- Aktywny goal: `docs/goals/archive/005-goal.md`.
- Completed baseline: `docs/goals/archive/004-goal.md`.
- Historical cleanup contract: `docs/goals/001-goal.md`.
- Aktualny ledger: `docs/PROGRESS.md`.
- Historyczne wpisy przeniesione lub pozostawione w git history i
  `docs/progress/archive/`.
- Nie dopisuj tu długich logów. Jeżeli ten plik zacznie puchnąć, usuń albo
  zastąp outdated/done rzeczy zamiast dopisywać nowe sekcje.

## Runtime

Canonical local stack:

```bash
scripts/local_stack.sh start
scripts/local_stack.sh status
```

Canonical URLs:

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:5173/command-center`

Python/API commands must use `uv run ...`.

## Current High-Level Status

Goal 004 completed the safe content operations mechanics. Goal 005 is active
because mechanics are not the same as Wilku usefulness. Do not infer daily
content-operations readiness from route/API availability, test count or the
UAT harness alone.

Available evidence surfaces for current proof include:

- Google Ads OAuth/customer selection and live campaign/search-term reads.
- GA4 landing/behavior plus key-event/ecommerce/revenue metric reads.
- Merchant aggregate issues and review-only feed queue with marketer-readable
  change previews.
- GSC query/page and WordPress inventory matching for current Ekologus URLs.
- Localo aggregate visibility, rankings, GBP visibility, competitor visibility
  and reviews as read-only evidence.
- 12 WILQ skills with baseline non-interactive eval coverage.

Active gaps live in:

- `docs/goals/archive/005-goal.md` - current goal contract and next execution
  boundaries.
- `docs/PROGRESS.md` - short current readout, latest proof and active gaps.
- `PLAN.md` - canonical cleanup/product-semantics plan.
- `PLANS.md` - active long-running Goal 005 ExecPlan.
- `bd ready --json` - current operational work graph. Do not duplicate this as
  markdown TODOs.

## Current Important Boundaries

- Brak dowodu w WILQ i źródła danych oznacza brak rekomendacji.
- Brak akcji do sprawdzenia, podglądu, potwierdzenia i audytu oznacza brak zapisu
  zmian.
- Nie naprawiaj zachowania produktu w opisach skilli. Najpierw popraw typowany
  kontrakt API, schemat, view-model albo eval, a dopiero potem każ skillowi
  używać nowego pola.
- Exact live metric values are not release assertions. Exact clicks, costs,
  rankings, reviews and issue counts belong in fixtures or proof notes.
- Live smokes assert contract shape, freshness, nonempty expected facts and
  honest ready/missing/blocked state.
- Keep recovery docs aggressively pruned.

## Prompt For `/new`

Po zapisaniu/commitnięciu aktualnego stanu możesz rozpocząć świeżą sesję:

```text
Kontynuuj aktywny goal z repo:
docs/goals/archive/005-goal.md

Najpierw przeczytaj AGENTS.md, docs/goals/archive/005-goal.md, PLANS.md, docs/PROGRESS.md i docs/CONTEXT.md.
Użyj aktualnego worktree i live WILQ API jako źródła prawdy.
Nie rozbudowuj recovery docs; usuwaj outdated rzeczy zamiast dopisywać log.
Kontynuuj następny najlepszy slice z goalu i używaj focused verification.
```

## When In Doubt

1. Sprawdź `git status --branch --short`.
2. Sprawdź `scripts/local_stack.sh status`.
3. Pobierz live API dla dotykanego obszaru.
4. Dodaj najmniejszy focused test dla zmiany zachowania.
5. Zrób minimalny slice.
6. Zapisz tylko aktualny stan i aktywne luki, nie historię wykonania.
