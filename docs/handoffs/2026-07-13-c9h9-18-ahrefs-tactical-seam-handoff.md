# Handoff — c9h9.18 Ahrefs tactical seam — 2026-07-13

## Decyzja

Wydzielono Ahrefs-specific assembly z `wilq/briefing/tactical_queue.py` do
`wilq/briefing/tactical_ahrefs.py`. Nowy moduł przyjmuje typed `MetricFact`
inputs, zwraca `list[TacticalQueueItem]` i tworzy `AhrefsCrossSourceMatcher`
raz dla całego batcha. Nie zmieniano reguł exact/weak/missing ani write path.

## Dowody

- Focused tests: `tests/test_tactical_queue.py` i
  `tests/content/test_ahrefs_cross_source_overlap.py`: 8 passed.
- Ruff i mypy dla zmienionych modułów: passed.
- Live `GET /api/marketing/tactical-queue`: 24 items, 19 compact groups,
  3 action IDs, 9 evidence IDs; Ahrefs cross-check records remain present.
- Complexity: explicit extraction-only allow-budget run passes, while normal
  report still exposes `tactical_queue.py` 1311 LOC and `_merchant_feed_items`
  115 LOC. This is an existing blocker, not waived as green.

## Pozostały zakres

Nie przenoszono Merchant/WordPress helpers. Kolejny seam musi redukować monolit
albo zamknąć dokładny follow-up z mierzalnym LOC reduction; nie dodawać kolejnej
logiki biznesowej do `tactical_queue.py`.
