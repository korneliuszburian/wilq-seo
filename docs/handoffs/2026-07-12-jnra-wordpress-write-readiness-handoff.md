# Handoff: `jnra` WordPress write-readiness requirements — 2026-07-12

## Decyzja

Składanie czterech WordPress draft write-readiness requirements zostało
przeniesione z `wilq/actions/service.py` do istniejącego
`wilq/actions/wordpress_mutation_requirements.py`. Zachowano readiness,
env-gate, REST adapter i write authorization z audytu.

## Dowody

- Typed requirements pozostają w tej samej kolejności i używają tych samych
  blocker codes/evidence: readiness, env, adapter, authorization.
- Focused WordPress/mutation readiness tests przechodzą; Ruff, mypy, complexity
  i `git diff --check` są zielone.
- `service.py` ma 2195 LOC; frozen-file budget violation pozostaje jawny.
- Po managed restart `/api/health` jest `ok`; live readiness raportuje
  `vendor_write_possible=false`, Ads detail ma evidence, blokadę zapisu i
  `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/wp-readiness-live.png`.
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
