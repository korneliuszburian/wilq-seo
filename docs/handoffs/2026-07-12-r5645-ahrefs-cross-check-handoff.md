# r564.5 — Ahrefs cross-check handoff

## Domknięty zakres

`wilq-seo-r564.5` usuwał potwierdzony false positive: Ahrefs mógł oznaczyć
niezwiązany rekord jako obecny w GSC lub WordPress wyłącznie przez wspólny token.
Wspólny pure seam `wilq/content/planning/ahrefs_overlap.py` klasyfikuje teraz
każdy source-specific wynik jako `exact`, `weak` albo `missing`.

- `exact`: tylko keyword phrase w GSC albo publiczny URL/phrase w typed
  inventory WordPress;
- `weak`: zachowuje source connectors/evidence i wymaga ręcznej oceny;
- `missing`: nie ma lineage.

Planner, Ahrefs diagnostics, tactical queue, context-pack, enrichment i
preflight używają tego samego znaczenia. Tylko `exact` może dać legacy
`present`, punkty relevance, ActionObject kolejki lub podobny URL w duplicate
preflight. Dev Proudsite nie jest publicznym URL-em dla tego seamu.
Rekord WordPress bez publicznego URL jest odrzucany przed porównaniem frazy, więc
nawet identyczny tytuł dev draftu nie potwierdza publicznego inventory.

## Aktualny proof

- Managed API restart: health i metrics status OK (`104362` facts, `4580`
  refresh runs).
- Live `GET /api/ahrefs/diagnostics`: `manual_required`, 6 candidates, 0
  action IDs; live tactical queue: 10 Ahrefs items, 0 attached actions.
- Final desktop proof after managed restart: `.local-lab/proof/bdos-wilq-2026-07-12/r5645-final-desktop.png`.
- Final mobile layout proof after managed restart: `.local-lab/proof/bdos-wilq-2026-07-12/r5645-final-mobile.png`.
- Focused backend contracts, shared-schema Vitest, dashboard Vitest/lint/typecheck/build,
  Ruff and mypy pass. `audit_complexity --changed` has only pre-existing large
  files/functions touched by necessary compatibility assertions; the new overlap
  seam and dedicated API regression test are within local budgets.

## Resume

Do not reopen this matcher for generic semantic similarity. If a richer
cross-source rule is needed, extend the same typed module with explicit source
lineage and regression fixtures first. Next product slice is `r564.6`: project
typed Service Profile context into the existing content work-item snapshot; no
new endpoint and no inferred service binding from free text.
