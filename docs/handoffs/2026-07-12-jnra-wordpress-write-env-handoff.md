# Handoff: `jnra` WordPress draft-write env policy — 2026-07-12

## Decyzja

Odczyt `WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES` został przeniesiony z
`wilq/actions/service.py` do istniejącego
`wilq/actions/wordpress_mutation_requirements.py`, obok WordPress readiness
requirements. Service nie duplikuje już tej write policy.

## Dowody

- Env `true` daje `True`, a `false` daje `False`; brak jawnego włączenia
  pozostaje fail-closed.
- Focused WordPress/mutation tests, Ruff, mypy, complexity i
  `git diff --check` przechodzą; frozen API nie zostało zmienione.
- `service.py` ma 2149 LOC; istniejący frozen-file budget violation pozostaje
  jawny.
- Po managed restart API health jest `ok`; live readiness pozostaje bez
  vendor-write capability, Ads detail zachowuje evidence i
  `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/wp-env-live.png`.
- Commit implementacji: `3b47314` wypchnięty na `origin/main`.
- Brak nowych endpointów, vendor writes, credential changes lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`; nie utworzono duplikatu.

## Następny slice

Świeży odczyt pozostałych helperów końcówki `service.py`; kolejny seam tylko
przy istniejącym module właścicielskim i focused behavior test.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
