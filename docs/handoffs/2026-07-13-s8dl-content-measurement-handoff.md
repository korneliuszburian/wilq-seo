# Handoff — s8dl content measurement — 2026-07-13

## Decyzja

Measurement window i outcome adapters zostały wydzielone do
`wilq/content/workflow/stage_measurement.py`. Zachowano baseline/observation
periods, allowed metrics/connectors, blocker semantics i brak automatycznych
success claims.

## Dowody

- 19 focused content/adversarial tests: passed.
- Ruff, mypy i `git diff --check`: passed.
- Complexity extraction-only report: `api.py` 1313 → 1272 LOC; pozostały
  file-budget violation jest jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs GSC/WordPress, 1 measurement blocker, 1 handoff blocker.
- Browser `/content-workflow`: public URL, decision, blocker i draft-only CTA
  nadal widoczne.

## Następny zakres

`wilq-seo-kvgd` obejmuje jeden kolejny readiness helper seam. Nie dodawać
nowych metryk, publikacji ani vendor writes.
