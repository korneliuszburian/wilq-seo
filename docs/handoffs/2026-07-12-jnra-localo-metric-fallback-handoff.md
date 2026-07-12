# Handoff: `jnra` Localo metric fallback — 2026-07-12

## Decyzja

Localo-specific filtering of probe-only facts and fallback to the latest
completed vendor read moved from `wilq/actions/service.py` into existing
`wilq/actions/localo/visibility.py`. The module receives storage and refresh-run
access through typed callbacks; service still owns I/O and orchestration.

## Dowód produktu

- Warm `GET /api/actions/act_review_localo_visibility_facts`: HTTP 200,
  10 metric rows, evidence `ev_refresh_refresh_localo_30cd98463f06`,
  preview `zapis zmian zablokowany`, `review_gate=kontrola WILQ poprawna`,
  `apply_allowed=false`.
- Warm `GET /api/actions`: HTTP 200 in 1.496805 s, 21 actions, 0 write-capable.
- Browser first viewport shows Localo decision, blocker and CTA while technical
  details stay behind disclosure:
  `.local-lab/proof/continuation-2026-07-12/localo-metric-fallback-live.png`
  and `localo-metric-fallback-live.txt`.
- First cold Localo detail attempt after managed restart exceeded 60 s; retry
  after warm-up completed in 13.241167 s. This is tracked, not waived, in
  `wilq-seo-zbre`.
- No review/confirm/impact/apply POST or vendor write was executed.

## Weryfikacja

- Focused metric/Localo/action suite: 7 passed.
- Ruff and mypy for `visibility.py`, `service.py` and tests: green.
- Complexity: known frozen `service.py` file budget only; no new function budget
  violation.
- `git diff --check`, API health and managed dashboard: green after warm proof.

## Beads i zależności

- `wilq-seo-jnra` remains `in_progress`; this domain seam is complete.
- New `wilq-seo-zbre` (P1, estimate 1 bounded day) depends on `jnra` and owns
  the confirmed cold Localo detail SLA. It must not duplicate closed `c9h9.11`.
- `wilq-seo-c9h9.4` remains closed; no return to the completed WordPress apply
  path.

## Commit

Implementacja i handoff: `25a7fb13` (`refactor: isolate Localo metric fallback`).
