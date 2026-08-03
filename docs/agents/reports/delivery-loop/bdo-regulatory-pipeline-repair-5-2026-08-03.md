# BDO regulatory pipeline — legacy deadline and timeout lineage repair

**Production fixed point:** `HEAD` after `fix(content): close legacy semantic deadline lineage`
**Branch:** `feat/regulatory-visible-extraction`

## Production changes

- A single `effective_deadline(run, timeout_seconds)` policy now covers
  persisted deadlines and legacy `started` runs with `deadline_at=None`.
  Claiming, GET polling and the deadline-aware Codex client use the same
  fallback calculation.
- A legacy started run older than its fallback budget is atomically marked
  failed and no longer blocks a fresh exact claim. A run still within budget
  remains the single active claim.
- Atomic review commit uses the same conservative fallback when a historical
  run has no persisted deadline, so legacy output cannot commit indefinitely.
- Commit-timeout terminal errors preserve the exact safe source code as
  `runtime_failed:semantic_review_timeout`; later GET reconstruction exposes
  `source_codes=["semantic_review_timeout"]`.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_semantic_review_deadline.py tests/content/test_semantic_content_review_api.py tests/content/test_semantic_review_polling_read_path.py` | PASS — 23 tests |
| `uv run ruff check --fix` on changed semantic modules/tests | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q` on changed Python | PASS |
| `git diff --check` | PASS |

New cases cover legacy claim expiry without a GET, atomic commit expiry, and
preservation of the timeout source code in persisted run state.

## Boundary

Only local semantic-review state, bounded Codex review and tests are changed.
No vendor, WordPress, publication, deployment, measurement or
`ActionObject.apply` write was added. Human/legal approval and cumulative
external re-review remain separate gates.
