# Handoff: `jnra` content review audit filter — 2026-07-12

## Decyzja

Reguła odfiltrowania raw human-review audit events dla content refresh została
przeniesiona z `wilq/actions/service.py` do istniejącego
`wilq/actions/content_review_details.py`. Zachowano dokładny action ID,
prefix `human_review_` oraz istniejącą redakcję raw contract przez audit store.

## Dowody

- `act_prepare_content_refresh_queue` + `human_review_*` + raw contract nadal
  zwraca `True`; inne action IDs zwracają `False`.
- Focused audit/preview/review tests: `33 passed`; Ruff, mypy, complexity i
  `git diff --check` przechodzą.
- `service.py` ma 2245 LOC; frozen-file budget violation pozostaje jawny.
- Po managed restart `/api/health` jest `ok`; Ads detail HTTP 200 ma evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/content-filter-live.png`.
- Commit implementacji: `e9c2c93` wypchnięty na `origin/main`.
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
