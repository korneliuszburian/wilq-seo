# BDO regulatory pipeline — monotonic semantic deadline repair

**Production fixed point:** `2f0543be`
**Branch:** `feat/regulatory-visible-extraction`
**Scope:** preventing semantic-review resurrection and enforcing one absolute
deadline through preflight, execution and polling.

## Production changes

- `_start_run(run_id=...)` now accepts only the exact active queued run. A
  missing, terminal, mismatched or expired run is rejected; the worker never
  recreates `started` under the same ID.
- The worker uses a deadline-aware client wrapper whose remaining budget is
  calculated immediately before `run_structured_turn()`, after snapshot and
  planning preflight. An expired deadline raises no positive fallback timeout
  and does not invoke Codex.
- Terminal transitions use an SQLite compare-and-set helper. Polling, worker
  completion and worker failure can update only a run still persisted as
  `started`; a concurrent `completed`, `failed` or `blocked` state is preserved.
- Expired preflight/execution returns a typed failed runtime response without
  persisting a review.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_semantic_content_review_api.py tests/content/test_semantic_review_deadline.py tests/content/test_semantic_review_polling_read_path.py` | PASS |
| `uv run ruff check --fix` on changed semantic router/service/state/tests | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q` on changed Python | PASS |
| `git diff --check` | PASS |

The new focused cases cover terminal queued-run resurrection, expired-turn
Codex suppression, and CAS protection against overwriting a completed run.

## Boundary and remaining review

This slice changes only local semantic-review state, the bounded Codex
execution seam and tests. It adds no vendor, WordPress, publication,
deployment, measurement or `ActionObject.apply` write. Human/legal approval
and external cumulative review remain separate gates.
