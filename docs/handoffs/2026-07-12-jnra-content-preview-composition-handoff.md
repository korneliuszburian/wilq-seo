# Handoff: `jnra` content-refresh preview composition — 2026-07-12

## Decyzja

Przeniosłem kompozycję kart content-refresh (brief cards oraz opcjonalna karta
reviewed WordPress draft) z `wilq/actions/service.py` do istniejącego wąskiego
`wilq/actions/content_preview.py`. Service pozostaje fasadą i przekazuje
callback do istniejącego WordPress preview adaptera; nie zmieniono endpointu,
payloadu ani safety loop.

## Dowód produktu

- Live API po restarcie: `act_prepare_content_refresh_queue` HTTP 200, `mode=prepare`,
  3 evidence IDs, 3 `content_brief_review` cards i publiczne URL-e.
- `apply_allowed` pozostaje false/blocked na kartach; brak automatycznego zapisu
  lub publikacji.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/content-refresh-composition-live.png`.

## Weryfikacja

- Content/action/API focused tests: passed.
- Ruff i mypy dla `content_preview.py` oraz `service.py`: passed.
- Complexity changed audit: jeden znany frozen `service.py` budget finding; nowy
  moduł mieści się w budżecie.
- `git diff --check`: passed.
- Managed stack po restarcie: API/dashboard ready; health `ok`.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; composition seam jest bounded.
- `wilq-seo-r564` nadal blokuje kolejkę contentu: 1 actionable przy minimum 3.
- Następny turn wybierze kolejny istniejący seam po świeżym runtime/complexity
  checku; nie wraca do content-preview composition.

## Commit

Commit implementacji i docs: `4ddcb34f` (`refactor: extract content preview
composition`), wypchnięty na `origin/main`.
