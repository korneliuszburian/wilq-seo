# BDO regulatory pipeline repair 9

Production repair commit: `2c9ca27630fa5e172edfd31728df895b8b461b1b`.

## Closed runtime risks

- Initial-draft claim checks the current immutable revision in the same local
  transaction as run claiming. An exact revision-bound completed run is
  returned as canonical; it cannot be hidden by a later retry run.
- Status reads give the exact revision-bound completed run precedence over later
  generating, blocked, or failed audit runs for the same proposal lineage.
- A completed initial-draft run is checked for exact equality before deadline
  enforcement, so replay after the deadline is idempotent. A new
  started-to-completed transition after the deadline remains rejected.
- Worker terminal writes use payload compare-and-swap and cannot overwrite a
  polling timeout or another terminal state.

## Focused proof

```text
uv run --extra dev pytest -q \
  tests/content/test_initial_draft_queue_gate.py \
  tests/content/test_initial_draft_status_read_path.py \
  tests/content/test_initial_draft_scope.py \
  tests/content/test_initial_full_draft_turn.py
44 passed

uv run ruff check --fix \
  apps/api/wilq_api/routers/content_initial_draft.py \
  wilq/content/drafts/initial_draft_run.py \
  wilq/content/workflow/codex_revision_commit.py \
  tests/content/test_initial_draft_queue_gate.py \
  tests/content/test_initial_draft_status_read_path.py
PASS

uv run python scripts/audit_complexity.py --changed --summary --limit 12
0 changed-code budget violations

git diff --check
PASS
```

The slice remains local/read-only with respect to WordPress, vendors,
publication, deployment, measurement, and ActionObject execution. Human/legal
approval and live connector freshness remain separate gates.
