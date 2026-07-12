# Handoff: `jnra` review-gate builders — 2026-07-12

## Decyzja

`action_required_checks` i `action_operator_checklist` zostały przeniesione z
`wilq/actions/service.py` do istniejącego `wilq/actions/review_gate.py`.
Buildery otrzymują callbacki do `string_list`, preview parsera i deduplikacji;
service pozostaje właścicielem orkiestracji, apply blockers i ActionObject
safety loop.

## Dowód produktu

- Localo detail HTTP 200 w `0.013067 s`: 5 required checks, 5 operator
  checklist, 1 evidence ID, `kontrola WILQ poprawna`, `apply_allowed=false`.
- Ads strategy detail HTTP 200 w `0.015976 s`: 5 required checks, 5 checklist,
  2 evidence IDs, `apply_allowed=false`, preview `zapis zmian zablokowany`.
- Browser first viewport zachowuje `Ocena strategii Ads do zapisania`,
  `Zapis zablokowany` i technical disclosure:
  `.local-lab/proof/continuation-2026-07-12/review-gate-builders-live.png`
  oraz `review-gate-builders-live.txt`.
- Nie wykonano review/confirm/impact/apply POST ani vendor write.

## Weryfikacja

- Focused review/payload tests: 8 passed.
- Ruff, mypy, complexity i `git diff --check`: zielone; znany frozen-file
  budget `service.py` pozostaje jedynym findingiem.
- Managed API/dashboard i live evidence: zielone.

## Beads

- `wilq-seo-jnra` pozostaje `in_progress`; ten review-gate seam jest domknięty.
- `c9h9.4`, `c9h9.11` i `zbre` pozostają zamknięte.
- Następny wybór wymaga świeżego przeglądu orchestratora, bez powtarzania
  payload/readiness/review-gate boundary.

## Commit

Implementacja i handoff: `ce262ff7` (`refactor: centralize review gate builders`).
