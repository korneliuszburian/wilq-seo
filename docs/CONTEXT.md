# WILQ Context Index

Ten plik jest krótkim indeksem recovery po utracie kontekstu. Nie jest
changelogiem ani kopią goalu. Jeżeli potrzebujesz historii, użyj git log,
`docs/progress/archive/` albo dedykowanych ledgerów.

## Start After Context Loss

Przeczytaj w tej kolejności:

1. `AGENTS.md` - stałe reguły pracy, sekrety, lokalne ścieżki i gotchas.
2. `docs/goals/001-goal.md` - jedyny aktywny goal i kolejka następnych zadań.
3. `docs/PROGRESS.md` - krótki aktualny stan, aktywne luki i następny ruch.
4. `docs/evals/skill-coverage-audit.md` - aktualna tabela pokrycia 12 skillów.
5. `docs/evals/skill-eval-ledger.md` - szczegóły manualnych i non-interactive
   przebiegów skillów.
6. `docs/architecture/bdos-class-wilq-operating-system.md` - produktowa
   poprzeczka “lepszy BDOS”.
7. `docs/infra/001.md` i `docs/audits/001-output.md` - pierwotny scope i
   audyt, tylko gdy trzeba sprawdzić źródłowy intent.

## Current Product Direction

WILQ to API-first Marketing Operating System dla Ekologus. WILQ API jest
mózgiem systemu; dashboard, Codex skills, hooks, workflows, expert rules,
opportunities i ActionObjects mają używać tych samych typed contracts.

Marketer jest polski. Widzi decyzje, evidence IDs, source connectors, blocked
claims i bezpieczny następny krok. Nie widzi raw connector dumps jako głównego
produktu.

## Current Recovery State

- Aktywny goal: `docs/goals/001-goal.md`.
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

Strong Ekologus demo is partially built, not done.

Ready or mostly ready surfaces include:

- Google Ads OAuth/customer selection and live campaign/search-term reads.
- GA4 landing/behavior plus key-event/ecommerce/revenue metric reads.
- Merchant aggregate issues and review-only feed queue with payload previews.
- GSC query/page and WordPress inventory matching for current Ekologus URLs.
- Localo aggregate visibility, rankings, GBP visibility, competitor visibility
  and reviews as read-only evidence.
- 12 WILQ skills with baseline non-interactive eval coverage.

Active gaps live in `docs/goals/001-goal.md`, grouped by:

1. source contracts and data acquisition,
2. decision API/view-model quality,
3. ActionObject safety and apply path,
4. Codex skills/prompts/eval quality,
5. knowledge compiler and source condensation,
6. dashboard usefulness/performance/code quality,
7. release/live-test strategy.

## Current Important Boundaries

- No recommendation without evidence IDs and source connectors.
- No write/apply without validated ActionObject, preview, confirmation and
  audit.
- Do not fix product behavior in skill references. Implement typed API/schema/
  view-model/eval first, then make skills consume it.
- Exact live metric values are not release assertions. Exact clicks, costs,
  rankings, reviews and issue counts belong in fixtures or proof notes.
- Live smokes assert contract shape, freshness, nonempty expected facts and
  honest ready/missing/blocked state.
- Keep recovery docs aggressively pruned.

## Prompt For `/new`

Po zapisaniu/commitnięciu aktualnego stanu możesz rozpocząć świeżą sesję:

```text
Kontynuuj aktywny goal z repo:
docs/goals/001-goal.md

Najpierw przeczytaj AGENTS.md, docs/goals/001-goal.md, docs/PROGRESS.md i docs/CONTEXT.md.
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
