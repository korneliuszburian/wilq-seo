# BDO regulatory pipeline — one legacy deadline policy

**Production fixed point:** `HEAD` after `fix(content): unify legacy semantic deadlines`
**Branch:** `feat/regulatory-visible-extraction`

## Production changes

- Legacy semantic runs with `deadline_at=None` now use one conservative,
  immutable 180-second fallback through `effective_deadline()`. Claim,
  polling, deadline-aware Codex execution and atomic review commit no longer
  derive different boundaries from env or local constants.
- New runs remain configurable because their exact absolute `deadline_at` is
  persisted when claimed; later environment changes do not alter them.
- A legacy run aged beyond the shared fallback is terminalized and replaced by
  one fresh claim, while all stages make the same active/expired decision.
- Commit-timeout source lineage remains persisted as
  `runtime_failed:semantic_review_timeout`.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_semantic_review_deadline.py tests/content/test_semantic_content_review_api.py tests/content/test_semantic_review_polling_read_path.py` | PASS — 24 tests |
| `uv run ruff check --fix` on changed semantic modules/tests | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q` on changed Python | PASS |
| `git diff --check` | PASS |

The new regression covers a 190-second legacy run while env is configured to
211 seconds: claim and all commit/polling policy use the same conservative
fallback and cannot disagree.

## Boundary

Only local semantic-review deadline policy, persistence, bounded Codex review
and tests are changed. No vendor, WordPress, publication, deployment,
measurement or `ActionObject.apply` write was added. Human/legal approval and
cumulative external re-review remain separate gates.
