# BDO regulatory pipeline repair 11

Production repair commit: `5ccefe89372eb932d330701ee684a82954b5390a`.

## Closed runtime risks

- Initial-draft runs now carry a durable context digest covering base revision,
  draft package identity/digest, canonical URL, service identity, proposal,
  planning digest, and planning-input digest.
- Active claims for different refresh contexts cannot share a run. Exact
  repeats of the same context still converge to one claim.
- The worker compares the fresh snapshot context before entering generation;
  a changed package, URL, or service context stops the old claim before a
  writer/repair/assurance turn.
- Final completion canonicalizes and checks the context digest inside the
  atomic append path, so a context change between worker snapshot and append
  cannot create a stale revision.
- GET checks an active matching refresh before returning an older canonical
  revision. A stale-context POST followed by immediate GET therefore remains
  `generating`; once current, the revision-bound completed run wins over later
  retry audit runs.
- Historical runs without `planning_digest` remain supported only through the
  exact immutable revision binding.

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

uv run python -m compileall -q \
  apps/api/wilq_api/routers/content_initial_draft.py \
  wilq/content/drafts/initial_draft_run.py \
  wilq/content/workflow/codex_revision_commit.py \
  wilq/schemas/actions.py
PASS

git diff --check
PASS
```

No WordPress/vendor write, publication, deployment, measurement write, or
ActionObject execution is introduced. Human/legal approval and live connector
freshness remain separate gates.
