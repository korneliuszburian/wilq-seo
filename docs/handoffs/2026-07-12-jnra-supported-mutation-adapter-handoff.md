# Handoff: `jnra` supported mutation adapter — 2026-07-12

## Decyzja

Rozpoznawanie obsługiwanego mutation adaptera zostało przeniesione z
`wilq/actions/service.py` do istniejącego `wilq/actions/mutation_contract.py`.
Jedyną obsługiwaną capability pozostaje canonical WordPress draft-only:
`act_apply_wordpress_draft_handoff` + `wordpress_ekologus` +
`allowed_operation=create_wordpress_draft` zwraca
`wordpress_draft_execution_boundary`. Publish i arbitralne operacje nadal
zwracają brak adaptera.

## Dowody

- `tests/actions/test_mutation_readiness_contracts.py`: focused contract suite,
  6 testów przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą; raport nie wprowadził nowych naruszeń.
- API pozostaje zdrowe, a ścieżka Ads detail nadal pokazuje evidence i
  `apply=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/adapter-boundary-live.png`.
- Brak nowych endpointów, vendor writes, zmian credentiali lub publikacji.
- Commit implementacji: `2f6ef1c` (`refactor: centralize supported mutation adapter`).

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Wykonać świeży audyt helperów `service.py` i wybrać jeden istniejący seam,
który upraszcza ownership bez zmiany kontraktu API.

## Otwarte blokery

- Content queue pozostaje `blocked` przez `not_enough_actionable_candidates`
  (1 actionable candidate przy wymaganych 3).
- Goal 005 nadal wymaga realnego Wilku UAT albo jawnego owner defer.
