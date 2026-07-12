# Handoff — kvgd content readiness — 2026-07-13

## Decyzja

Existing-draft update readiness projection została wydzielona do
`wilq/content/workflow/stage_readiness.py`. Publiczny router nadal korzysta z
compatibility exportu; kontrakt pozostaje preview-only i fail-closed.

## Dowody

- Pełne focused content workflow contracts: passed (9 tests).
- Ruff, mypy i `git diff --check`: passed.
- Complexity extraction-only report: `api.py` 1272 → 1201 LOC; residual
  file-budget violation jest jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs GSC/WordPress, 1 handoff blocker.
- Browser `/content-workflow`: public URL, decyzja, blocker i draft-only CTA
  widoczne; istniejący draft update nie jest oferowany jako zapis.

## Następny zakres

`wilq-seo-eieh` obejmuje pozostałe activation/write-readiness orchestration.
Nie włączać write, publish ani nowego endpointu.
