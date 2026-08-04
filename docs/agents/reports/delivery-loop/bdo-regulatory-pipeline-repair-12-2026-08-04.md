# BDO regulatory pipeline repair 12

Production repair commit: `3902cec0ba89a46edeeaa186f329eccc58831cce`.

## Closed runtime risks

- Every queued Codex turn re-loads the workflow snapshot and compares its
  context digest before invoking the model. A package, URL, service, or
  planning-context change terminalizes the old run as
  `stale_initial_draft_context`.
- A context change is also terminalized when a newer exact claim is created,
  so older workers cannot continue alongside the new context.
- Claiming against an old request snapshot cannot create a shadow run after a
  newer immutable revision has committed: the transaction re-reads the latest
  revision and returns its canonical run.
- GET exposes an active run before a canonical revision only when that run's
  durable context token matches the revision context; an unrelated stale run
  cannot hide the current immutable revision.
- Atomic completion compares the persisted run context token with the command
  context token, preventing a stale package from being appended after a
  context change between the last turn and SQLite commit.

## Focused proof

```text
uv run --extra dev pytest -q \
  tests/content/test_initial_draft_queue_gate.py \
  tests/content/test_initial_draft_status_read_path.py \
  tests/content/test_initial_draft_scope.py \
  tests/content/test_initial_full_draft_turn.py
45 passed

uv run ruff check --fix \
  wilq/schemas/actions.py \
  wilq/content/drafts/initial_draft_run.py \
  apps/api/wilq_api/routers/content_initial_draft.py \
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
