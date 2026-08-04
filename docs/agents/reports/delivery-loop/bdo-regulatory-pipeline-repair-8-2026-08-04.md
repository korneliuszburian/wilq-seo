# BDO regulatory pipeline repair 8

Production repair commit: `051909c7ac97998aa0e289ebd40867eabe8f2b9a`.

## Scope

This slice closes the initial-draft boundary between the exact planning
proposal, durable Codex run, evidence lineage, deadline, and immutable draft
append. It does not publish to WordPress, execute an ActionObject, write to a
vendor, deploy, or write measurement data.

## Implemented behavior

- Durable initial-draft claims are exact to proposal, planning digest, input
  digest, hook, and endpoint; a second claim reuses the same run.
- Expired claims are terminalized atomically before a retry can claim the exact
  plan. Polling and worker failure transitions use compare-and-swap semantics.
- A queued worker bounds every Codex turn by the persisted absolute deadline.
  The atomic revision append rejects an initial-draft completion after that
  deadline.
- Completed legacy runs without `planning_digest` are accepted only when the
  immutable revision carries matching planning/input lineage and references
  the exact run ID. Other legacy runs remain invisible to the current proposal.
- Durable run evidence IDs come from the typed proposal, are deduplicated, and
  are checked again when the worker starts.

## Focused proof

```text
uv run --extra dev pytest -q \
  tests/content/test_initial_draft_queue_gate.py \
  tests/content/test_initial_draft_status_read_path.py \
  tests/content/test_initial_draft_scope.py \
  tests/content/test_initial_full_draft_turn.py
41 passed

uv run ruff check --fix \
  apps/api/wilq_api/routers/content_initial_draft.py \
  wilq/content/drafts/initial_draft_run.py \
  wilq/content/workflow/codex_revision_commit.py \
  tests/content/test_initial_draft_queue_gate.py
PASS

uv run python -m compileall -q \
  apps/api/wilq_api/routers/content_initial_draft.py \
  wilq/content/drafts/initial_draft_run.py \
  wilq/content/workflow/codex_revision_commit.py
PASS

uv run python scripts/audit_complexity.py --changed --summary --limit 12
0 changed-code budget violations

git diff --check
PASS
```

## Explicit limits

This packet does not prove live connector freshness, legal approval, factual
correctness of the BDO article, WordPress publication, deployment, or SEO and
lead outcomes. The full repository gate and external human review remain
separate steps.
