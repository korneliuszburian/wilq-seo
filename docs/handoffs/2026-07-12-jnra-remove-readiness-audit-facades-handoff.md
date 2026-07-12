# Handoff: `jnra` remove readiness/audit facades — 2026-07-12

## Decyzja

Usunięto lokalne fasady używane wyłącznie wewnątrz `service.py`:
`_wordpress_draft_write_readiness_requirements`,
`_wordpress_draft_write_readiness`, `_wordpress_draft_activation_packet`,
`_apply_audit_event_type` oraz `_action_mutation_audit_record`. Service wywołuje
istniejące owner modules bezpośrednio (`wordpress_mutation_requirements`,
`audit_store`, `mutation_readiness`).

## Dowody

- `rg` nie znajduje usuniętych fasad ani ich call sites w kodzie/testach.
- `tests/actions/test_action_mutation_readiness_api.py`,
  `tests/actions/test_mutation_readiness_contracts.py`,
  `tests/actions/test_audit_store_contracts.py` i
  `tests/content/test_wordpress_execution_api.py`: focused suite przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą.
- Live API: health `ok`; apply readiness zachowuje
  `ready_to_request_apply=false`, `vendor_write_possible=false` i
  `publication_allowed=false`; content queue pozostaje fresh, ale blocked 1/3.
- Brak endpointów, vendor writes, credentiali, publikacji lub zmian UI.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Zatrzymać mechaniczne usuwanie fasad i przejść do świeżej oceny większego
`_execute_supported_mutation_adapter` albo innego seamu z testowalną korzyścią
produktową; nie przenosić orkiestracji ActionObject bez wyraźnego ownera.

## Otwarte blokery

- Content queue: `blocked` przez `not_enough_actionable_candidates` (2
  kandydatów, 1 actionable przy wymaganych 3), mimo świeżych źródeł.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
