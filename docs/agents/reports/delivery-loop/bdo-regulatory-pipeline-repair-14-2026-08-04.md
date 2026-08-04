# BDO regulatory pipeline — repair 14

Production repair fixed point: `3f4d7862`

Parent: `35c7e067`

## Scope

This slice closes the two current-context authority races in initial-draft
orchestration. It does not publish content, write WordPress, mutate vendors,
deploy, or execute an ActionObject.

## Changes

- Added a durable SQLite `initial_draft_context_authority` record with digest,
  base revision, monotonic version, and update time.
- Queueing re-reads the snapshot immediately before claim and records the
  exact context token before creating or reusing a run.
- Canonical claim matching now requires the revision's creation context to
  match the request context; a revision from another package, URL, service, or
  planning context is not returned as `created`.
- The append transaction checks the persisted authority in the same
  `BEGIN IMMEDIATE` transaction as completion and revision insertion.
- Context mismatch is surfaced as typed `stale_initial_draft_context`, rather
  than the generic `persistence_failed` blocker.
- Queue reads cannot overwrite an existing authority record; an old request is
  rejected without touching the newer run.
- A fresh canonical revision is returned before creating a shadow retry, and
  canonical context reconstruction uses the revision's own identity consistently.

## Verification

Focused command:

```text
uv run --extra dev pytest -q \
  tests/content/test_initial_draft_queue_gate.py \
  tests/content/test_initial_draft_status_read_path.py \
  tests/content/test_initial_draft_scope.py \
  tests/content/test_initial_full_draft_turn.py
```

Result: `46 passed`.

Additional gates: Ruff passed for all changed Python files, `compileall`
passed, and `git diff --check` passed.

The complexity audit reports pre-existing budget violations in the large
`initial_full_draft.py` and `store.py` modules; this slice did not add a new
frozen growth file. The audit remains a proof limitation, not a runtime
finding.

## Remaining proof limits

The focused suite does not yet contain externally replayable barrier tests for
context mutation while SQLite lock acquisition is pending. The deterministic
old-request/new-request authority reproducer now passes at the helper level.
Live BDO content correctness and human/legal approval remain out of scope.
