# Handoff: `jnra` WordPress apply capability owner — 2026-07-12

## Decyzja

Typed `WordPressDraftApplyCapability` i builder
`wordpress_draft_apply_capability` zostały przeniesione z `service.py` do
istniejącego `wilq/actions/wordpress_mutation_requirements.py`. Builder wiąże
exact work item, handoff, draft package, public canonical URL i actor z
preview/confirm audit; publish/destructive oraz arbitralny host pozostają
zablokowane. `service.py` zachowuje jedną kompatybilną fasadę, bo istniejące
route tests używają jej jako seamu kontrolowanego adaptera.

## Dowody

- `tests/actions/test_action_mutation_readiness_api.py`,
  `tests/actions/test_mutation_readiness_contracts.py`,
  `tests/actions/test_audit_store_contracts.py` i
  `tests/content/test_wordpress_execution_api.py`: 39 testów przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą. Complexity pokazuje tylko znane wyjątki
  funkcji testowych oraz zamrożony `service.py`; nowy owner module nie ma
  naruszenia budżetu.
- Managed stack po restarcie: API/dashboard `ready`, health `ok`.
- Mutation readiness: `ready_to_request_apply=false`,
  `vendor_write_possible=false`, `publication_allowed=false`.
- Content queue: `fresh`, ale `blocked`, 2 kandydatów / 1 actionable / minimum 3.
- Browser proof po restarcie:
  `.local-lab/proof/continuation-2026-07-12/wordpress-capability-desktop.png`
  i `wordpress-capability-mobile-after-restart.png`.
- Brak nowych endpointów, vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-c9h9.4` pozostaje zamknięty; nie wracamy do wykonanej pracy.
- `wilq-seo-jnra` pozostaje P0 `in_progress`; zaktualizowano komentarz, bez
  duplikatu.

## Następny slice

Reaudyt roadmapy po tym owner seamie. Następny kandydat musi być większym,
testowalnym ownership boundary (np. adapter execution), a nie kolejną
mechaniczną fasadą.

## Otwarte blokery

- Content queue: `not_enough_actionable_candidates` — 1 actionable przy
  wymaganych 3, mimo świeżych źródeł.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
