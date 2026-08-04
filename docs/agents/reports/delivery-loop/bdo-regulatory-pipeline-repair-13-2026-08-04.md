# BDO regulatory pipeline repair 13

Production repair commits: `3902cec0ba89a46edeeaa186f329eccc58831cce` and
`01268c50a407ea1a3fcfd3b95bfceaa64a2ecb22`.

## Closed runtime risks

- First-draft runs are visible as `generating` even before a revision exists.
  Refresh runs are matched by their durable base revision ID rather than by
  reconstructing a future context from historical revision fields.
- A stale request cannot treat a newly committed revision as absent: the claim
  re-reads the latest revision inside its transaction and returns the canonical
  run/revision when appropriate.
- Every Codex turn performs a fresh snapshot context check. The worker is
  terminalized before model execution when package, URL, service, or planning
  authority changes.
- The append path performs a fresh context check immediately before delegating
  to the atomic revision store. Context changes after the last model turn are
  therefore rejected rather than persisted as stale revisions.
- Terminal transitions require the expected run to still be `started`; a later
  runtime/preflight path cannot overwrite `stale_initial_draft_context`.

## Focused proof

```text
uv run --extra dev pytest -q \
  tests/content/test_initial_draft_queue_gate.py \
  tests/content/test_initial_draft_status_read_path.py \
  tests/content/test_initial_draft_scope.py \
  tests/content/test_initial_full_draft_turn.py
46 passed

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
