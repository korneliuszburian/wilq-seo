# Handoff: `jnra` human review details — 2026-07-12

## Decyzja

Składanie `ActionReviewRequest` do audytowych szczegółów zostało przeniesione z
`wilq/actions/service.py` do istniejącego `wilq/actions/review_gate.py`.
Content-specific URL review i draft-readiness pozostają callbackami, więc
review gate nie przejmuje logiki content ani nie omija human review.

## Dowody

- Zachowano pola `review_outcome`, `reviewed_by`, `checked_items`, `blockers`,
  `content_url_review` i `content_draft_readiness_review`.
- Focused preview/confirmation/review tests: `26 passed`; Ruff, mypy,
  complexity i `git diff --check` przechodzą.
- `service.py` ma 2344 LOC; frozen-file budget violation pozostaje jawny.
- Po managed restart `/api/health` jest `ok`; Ads detail ma evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/review-details-live.png`.
- Commit implementacji: `2789acf` wypchnięty na `origin/main`.
- Brak nowych endpointów, vendor writes, credential changes lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`; nie utworzono duplikatu.

## Następny slice

Świeży odczyt pozostałych helperów review/audit w `service.py` i kolejny seam
tylko przy potwierdzonym module właścicielskim.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
