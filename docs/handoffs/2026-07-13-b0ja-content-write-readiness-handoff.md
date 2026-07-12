# Handoff — b0ja content write-readiness — 2026-07-13

## Decyzja

WordPress draft write-readiness projection została wydzielona do
`wilq/content/workflow/stage_write_readiness.py`. API zachowuje compatibility
wrapper i przekazuje istniejące audit/readiness callbacks; write pozostaje
fail-closed.

## Dowody

- Focused readiness/activation tests: passed.
- Ruff, mypy i `git diff --check`: passed.
- Complexity extraction-only report: `api.py` 1017 → 956 LOC; residual
  file-budget violation jest jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs GSC/WordPress, 1 handoff blocker.
- Browser `/content-workflow`: decyzja, blocker, public URL i draft-only CTA
  pozostają widoczne.

## Następny zakres

`wilq-seo-fc5b` obejmuje pozostałe audit helper orchestration. Nie włączać live
write ani publikacji.
