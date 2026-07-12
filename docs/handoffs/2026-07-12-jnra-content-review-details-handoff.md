# Handoff: `jnra` content review details parsers — 2026-07-12

## Decyzja

Przeniosłem parsery `checked_items` dla content URL review i draft-readiness
z `wilq/actions/service.py` do nowego wąskiego
`wilq/actions/content_review_details.py`. Parsery zachowują wyłącznie
dozwolone klucze, ignorują nieznane pola i nie zmieniają ActionObject safety loop.

## Dowód produktu

- Live API: `act_prepare_content_refresh_queue` HTTP 200, `mode=prepare`,
  3 evidence IDs, 3 typed `content_brief_review` cards i blokada zapisu.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/content-review-details-live.png`.
- Nie wykonano POST review ani vendor write; parser ma izolowany test kontraktu.

## Weryfikacja

- Action review, WordPress readiness/handoff i content URL tests: passed.
- Ruff i mypy dla `content_review_details.py`, `service.py` i testu: passed.
- Complexity changed audit: jeden znany frozen `service.py` budget finding;
  nowy moduł mieści się w budżecie.
- `git diff --check`: passed.
- Managed stack po restarcie: API/dashboard ready; health `ok`.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; parser seam jest bounded.
- `wilq-seo-r564` nadal blokuje kolejkę contentu: 1 actionable przy minimum 3.
- Następny turn wybierze kolejny potwierdzony seam po świeżym runtime/complexity
  checku; nie wraca do ukończonych review parserów.

## Commit

Commit implementacji i docs: `4a605fa0` (`refactor: extract content review
details`), wypchnięty na `origin/main`.
