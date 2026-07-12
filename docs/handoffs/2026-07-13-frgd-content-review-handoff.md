# Handoff — frgd content review/handoff — 2026-07-13

## Decyzja

Human review i WordPress draft handoff adapters zostały wydzielone do
`wilq/content/workflow/stage_review.py`. API zachowuje compatibility exports dla
routera; ActionObject safety, audit blockers i draft-only semantics pozostały
bez zmian.

## Dowody

- 17 focused content/adversarial tests: passed.
- Ruff i mypy: passed.
- Complexity extraction-only report: `api.py` 1352 → 1313 LOC; residual
  file-budget violation pozostaje jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs z GSC/WordPress, 0 human-review blockers, 1 handoff blocker,
  `publish_allowed` nieaktywne.
- Browser `/content-workflow`: public URL, decision, blocker i draft-only CTA
  pozostają widoczne w pierwszym viewport.

## Następny zakres

`wilq-seo-s8dl` obejmuje wyłącznie measurement adapter. Nie rozszerzać go na
publikację, nowe metryki ani vendor writes.
