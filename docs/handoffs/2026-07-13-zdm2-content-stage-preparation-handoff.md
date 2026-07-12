# Handoff — zdm2 content stage preparation — 2026-07-13

## Decyzja

Preflight i Sales Brief adapters zostały wydzielone do
`wilq/content/workflow/stage_preparation.py`. API zachowuje istniejące nazwy
publicznych funkcji przez import adapterów; nie zmieniono endpointów ani reguł
claim/write.

## Dowody

- 12 focused content contract tests: passed.
- Ruff i mypy: passed.
- Complexity extraction-only report: `api.py` 1470 → 1416 LOC; pozostałe
  naruszenie file budget jest jawne.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs z GSC/WordPress, Service Profile review-required, 1 handoff blocker.

## Następny zakres

`wilq-seo-mseb` obejmuje draft/review/handoff stage adapters. Nie rozszerzać
tego handoffu na nowe endpointy, vendor writes ani zmiany decyzji contentowych.
