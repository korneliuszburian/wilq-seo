# BDO regulatory pipeline — semantic review queue repair

**Production fixed point:** `92f5fc8d`
**Branch:** `feat/regulatory-visible-extraction`
**Scope:** absolute semantic-review deadlines and immutable-review authority.

## Production changes

- A queued semantic `CodexRun` is reused by the worker instead of being
  replaced. Its `started_at`, `deadline_at`, `planning_input_digest`, endpoint
  and evidence lineage therefore remain intact in local state.
- The worker derives the app-server timeout from the persisted absolute
  deadline, capped by the client budget. Polling and runtime now share one
  published deadline; a later environment change cannot extend the run.
- POST checks for an exact immutable review before queueing or expensive
  planning/context preflight. A duplicate returns the persisted review and
  cannot create a shadow run.
- GET gives the exact immutable review precedence over later started, blocked,
  or failed retry runs for the same revision and digest. Retry attempts remain
  audit state and cannot hide the canonical advisory result.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_semantic_content_review_api.py tests/content/test_semantic_review_polling_read_path.py` | PASS |
| `uv run ruff check apps/api/wilq_api/routers/content_semantic_review.py wilq/content/quality/semantic_review_service.py wilq/content/quality/semantic_review_guards.py tests/content/test_semantic_content_review_api.py tests/content/test_semantic_review_polling_read_path.py` | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q apps/api/wilq_api/routers/content_semantic_review.py wilq/content/quality/semantic_review_service.py wilq/content/quality/semantic_review_guards.py` | PASS |
| `git diff --check` | PASS |

The focused tests cover queued-run persistence, remaining-budget derivation,
duplicate review short-circuiting, canonical GET precedence, polling deadline
handling, and queued result terminalization.

## Runtime and boundary

The managed WILQ API was verified against the existing repo-local environment
without printing secret values: 9 of 12 connector configurations are present
(Google Ads, GSC, GA4, Merchant Center, Ahrefs, Localo, both WordPress sites,
and Codex). LinkedIn and Facebook remain unconfigured and are not required for
this content-draft slice.

No vendor, WordPress, publication, deployment, measurement, or
`ActionObject.apply` write was executed. Human/legal approval and external
cumulative review remain separate gates; this report records implementation
proof, not publication approval.
