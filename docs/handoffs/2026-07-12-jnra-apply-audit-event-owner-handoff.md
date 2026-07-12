# Handoff: `jnra` apply audit event owner — 2026-07-12

## Decyzja

Budowanie apply `AuditEvent` przeniesiono z `apply_action` do istniejącego
`wilq/actions/audit_store.py` jako `build_apply_audit_event`. Owner mapuje
canonical event type, operator label, summary, actor, action ID, audit ID i
evidence IDs; service pozostaje orkiestratorem capability/preflight/adapter/audit.

## Dowody

- `tests/actions/test_audit_store_contracts.py`,
  `tests/actions/test_action_review_contracts.py`,
  `tests/actions/test_action_mutation_readiness_api.py` i
  `tests/actions/test_action_object_contracts.py`: 55 testów przechodzi,
  w tym nowy test event type/summary/evidence.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą; service frozen hotspot maleje.
- Live API health `ok`; readiness pozostaje
  `ready_to_request_apply=false`, `vendor_write_possible=false`,
  `publication_allowed=false`.
- Aktualny browser proof UI pozostaje ważny, bo slice nie zmienia dashboardu:
  `.local-lab/proof/continuation-2026-07-12/c9h9-14-cache-mobile.png`.
- Brak nowych endpointów, vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; komentarz zaktualizowany.
- `wilq-seo-c9h9.14` pozostaje zamknięty jako external-state false positive.

## Następny slice

Reaudyt pozostałego `apply_action`; wybór kolejnego większego owner boundary,
jeśli istnieje, bez mechanicznego rozdrabniania orkiestracji.

## Otwarte blokery

- Content queue: `not_enough_actionable_candidates` — 1 actionable przy
  wymaganych 3, mimo świeżych źródeł.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
