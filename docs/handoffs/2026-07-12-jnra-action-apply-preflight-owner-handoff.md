# Handoff: `jnra` action apply preflight owner — 2026-07-12

## Decyzja

Kolejność i treść preflight blockerów apply przeniesiono z `apply_action` do
istniejącego `wilq/actions/action_blockers.py` jako
`action_apply_preflight_blockers`. Owner module obejmuje confirm, preview,
impact, validation, mode, evidence, connector, risk, destructive, payload
readiness i adapter gates. `apply_action` pozostaje orkiestratorem typed
capability → preflight → adapter → audit result.

## Dowody

- `tests/actions/test_action_review_contracts.py`,
  `tests/actions/test_action_object_contracts.py`,
  `tests/actions/test_action_mutation_readiness_api.py` i
  `tests/actions/test_mutation_readiness_contracts.py`: 68 testów przechodzi,
  w tym test kolejności blockerów.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą; service frozen hotspot maleje, bez nowych
  budżetów poza znanym zamrożonym plikiem.
- Live API health `ok`; mutation readiness zachowuje
  `ready_to_request_apply=false`, `vendor_write_possible=false`,
  `publication_allowed=false`.
- Browser proof UI pozostaje aktualny, bo slice nie zmienia React:
  `.local-lab/proof/continuation-2026-07-12/c9h9-14-cache-mobile.png`.
- Brak nowych endpointów, vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; komentarz zaktualizowany.
- `wilq-seo-c9h9.14` pozostaje zamknięty jako external-state false positive.

## Następny slice

Reaudyt `apply_action` po preflight extraction; następny zakres powinien
dotyczyć audit result assembly albo innego większego owner boundary, nie
mechanicznej fasady.

## Otwarte blokery

- Content queue: `not_enough_actionable_candidates` — 1 actionable przy
  wymaganych 3, mimo świeżych źródeł.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
