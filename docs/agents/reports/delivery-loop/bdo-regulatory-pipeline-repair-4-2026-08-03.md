# BDO regulatory pipeline — semantic commit and claim repair

**Production fixed point:** `HEAD` after `fix(content): make semantic commit and claim atomic`
**Branch:** `feat/regulatory-visible-extraction`
**Scope:** post-turn deadline enforcement and cross-process exact queue claims.

## Production changes

- `ContentSemanticReviewStore.save_generated()` checks the persisted run's
  exact lineage and absolute `deadline_at` inside the same `BEGIN IMMEDIATE`
  transaction as the immutable review insert and Codex completion. An output
  that finishes after the deadline is rejected before any review row is added.
- The service maps that rejection to typed `runtime_failed` timeout state and
  terminalizes the run monotonically; polling is not required to make the
  outcome safe.
- Queue creation now uses one SQLite transaction that checks exact immutable
  review, active exact run and then inserts one queued run. Only the process
  that receives `newly_claimed=True` submits an executor worker. Existing
  active claims are returned to both callers; a current exact review wins the
  race without a new worker.
- Expired active claims are terminalized within the claim transaction before a
  controlled retry can obtain a fresh claim.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_semantic_review_deadline.py tests/content/test_semantic_content_review_api.py tests/content/test_semantic_review_polling_read_path.py` | PASS — 21 tests |
| `uv run ruff check --fix` on changed semantic store/service/router/tests | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q` on changed Python | PASS |
| `git diff --check` | PASS |

The focused suite includes expired started-run commit rejection, monotonic CAS
against overwriting a completed run, and two-thread exact claim convergence to
one active Codex run.

## Boundary and remaining review

This repair changes only local semantic-review persistence, queue ownership,
bounded Codex execution and tests. No vendor, WordPress, publication,
deployment, measurement or `ActionObject.apply` write was added. Human/legal
approval and cumulative external re-review remain separate gates.
