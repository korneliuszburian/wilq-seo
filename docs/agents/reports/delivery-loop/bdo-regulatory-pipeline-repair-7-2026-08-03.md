# BDO regulatory pipeline — initial-draft exact claim repair

**Production fixed point:** `HEAD` after `fix(content): claim initial drafts by exact proposal`
**Branch:** `feat/regulatory-visible-extraction`

## Production changes

- Initial-draft queueing now claims `{work_item_id, proposal_id,
  planning_digest, planning_input_digest, hook, endpoint}` in one SQLite
  `BEGIN IMMEDIATE` transaction.
- The durable queued `CodexRun` is written before executor submission and
  carries the exact proposal/planning lineage plus its persisted deadline.
- A second POST returns the existing exact run and does not submit another
  worker. A run belonging to an older proposal is never returned for the
  current proposal.
- The worker reuses the durable queued run instead of overwriting it, and
  terminal preflight blockers update that existing run instead of leaving it
  permanently `started`.
- Initial-draft read lookup includes the exact planning digest and therefore
  agrees with the POST run identity immediately after queueing.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_initial_draft_scope.py tests/content/test_initial_full_draft_turn.py tests/content/test_initial_draft_queue_gate.py tests/content/test_initial_draft_status_read_path.py` | PASS — 37 tests |
| `uv run ruff check --fix` on initial-draft router/run/schema/tests | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q` on changed initial-draft Python | PASS |
| `git diff --check` | PASS |

The new cases cover durable visibility, same-run repeated POSTs, old-proposal
isolation, and exact proposal/planning lineage on the persisted claim.

## Boundary

Only local queue state, initial-draft workflow orchestration, typed run lineage
and tests are changed. No vendor, WordPress, publication, deployment,
measurement or `ActionObject.apply` write was added. Human/legal approval and
cumulative external re-review remain separate gates.
