# Handoff — eieh content activation — 2026-07-13

## Decyzja

Typed WordPress activation packet projection została wydzielona do
`wilq/content/workflow/stage_activation.py`. API zachowuje compatibility
wrapper, który przekazuje istniejące API-owned safety helpers; nie odblokowano
write ani publish.

## Dowody

- Focused activation/readiness tests: passed.
- Ruff, mypy i `git diff --check`: passed.
- Complexity extraction-only report: `api.py` 1201 → 1148 LOC; residual
  file-budget violation jest jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs GSC/WordPress, 1 handoff blocker.
- Browser `/content-workflow`: decyzja, blocker, public URL i draft-only CTA
  pozostają widoczne.

## Następny zakres

`wilq-seo-nlax` obejmuje readback/label helper group. Nie włączać live write,
publikacji ani nowych endpointów.
