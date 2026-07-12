# Handoff — mseb content draft stage — 2026-07-13

## Decyzja

Draft package, structured-generation contract i draft variants zostały
wydzielone do `wilq/content/workflow/stage_drafts.py`. API zachowuje
kompatybilne eksporty dla routera; nie zmieniono endpointów, claim rules ani
ActionObject/write safety.

## Dowody

- 12 focused content workflow tests: passed.
- Ruff i mypy: passed.
- Complexity extraction-only report: `api.py` 1416 → 1352 LOC; pozostały
  file-budget violation jest jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs z GSC/WordPress, 1 handoff blocker.

## Następny zakres

`wilq-seo-frgd` obejmuje human-review i WordPress handoff adapters. Measurement
stage pozostaje osobnym zakresem; nie przenosić go do tego seamu.
