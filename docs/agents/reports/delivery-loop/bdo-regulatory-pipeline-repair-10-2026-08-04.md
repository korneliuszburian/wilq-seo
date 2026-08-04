# BDO regulatory pipeline repair 10

Production repair commit: `58e774bf2a4186a32edc061d2777fc2bf80c1e8f`.

## Closed runtime risks

- Canonical revision/run matching accepts the historical `planning_digest=None`
  shape only through the exact immutable revision binding. The same rule is
  used by claim and GET, so later blocked or failed retries cannot hide the
  completed legacy BDO draft.
- A revision is canonical for a new claim only while the loaded snapshot says
  its context is current. A stale package, URL, or service context therefore
  creates an exact refresh claim instead of returning the old revision as
  `created`.

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

No WordPress/vendor write, publication, deployment, measurement write, or
ActionObject execution is introduced. Human/legal approval and live connector
freshness remain separate gates.
