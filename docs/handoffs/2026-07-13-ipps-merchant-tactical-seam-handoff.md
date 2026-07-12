# Handoff — ipps Merchant tactical seam — 2026-07-13

## Decyzja

Wydzielono Merchant issue/status assembly z `wilq/briefing/tactical_queue.py`
do `wilq/briefing/tactical_merchant.py`. Adapter przekazuje typed fakty i
ActionObject IDs; nie zmieniono reguł grupowania, etykiet, blocked claims ani
write safety.

## Dowody

- Focused tactical, Ahrefs i diagnostics contracts: 17 passed.
- Ruff i mypy dla zmienionych modułów: passed.
- Live po managed restart: `GET /api/marketing/tactical-queue` zwraca 24 items,
  4 Merchant items, 3 action IDs i 9 evidence IDs.
- Complexity extraction-only report: `tactical_queue.py` spadł do 1195 LOC;
  pozostały jeden file-budget violation jest jawny i wymaga kolejnego seama.

## Następny zakres

Nie dodawać kolejnego wrappera w queue. Następny wybór powinien wynikać z
aktualnego `bd ready`, najbliżej jest `wilq-seo-c9h9.16` (typed snapshot
assembly `/content-workflow`) albo nowy dokładny follow-up dla reszty monolitu,
jeśli complexity audit potwierdzi konkretną granicę.
