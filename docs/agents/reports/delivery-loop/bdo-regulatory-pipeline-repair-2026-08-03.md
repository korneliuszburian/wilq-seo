# BDO regulatory pipeline — repair proof

**Production fixed point:** `3c950f7aec4320caaabd5e3006b6295645a98424`
**Branch:** `feat/regulatory-visible-extraction`
**Scope:** inventory classification, semantic-review queue terminalization,
exact proposal/revision section binding, and persisted semantic deadline.

## Production changes

- REST and sitemap inventory use one URL classifier. `sorbent*`, `/sklep*`,
  `/shop*`, and `sklep.ekologus.pl` remain audit-only and cannot enter the
  editorial catalog.
- A queued semantic review that resolves to an existing exact review now
  terminalizes its published run as `completed`; it cannot remain a
  `started`/`failed` shadow over the immutable result.
- Semantic context and deterministic guards use only draftable sections and
  bind them by exact `section_id`; missing or ambiguous lineage raises a typed
  runtime blocker before review output is accepted.
- The configured semantic Codex budget is persisted as `deadline_at` on the
  queued `CodexRun`; polling uses that value rather than a second hard-coded
  deadline.

## Focused proof

| command | result |
| --- | --- |
| `uv run --extra dev pytest -q tests/content/test_wordpress_inventory_scope.py tests/content/test_wordpress_sitemap_policy.py tests/content/test_semantic_review_polling_read_path.py tests/content/test_semantic_content_review_api.py -k 'not full_draft_model_envelope'` | PASS — 23 tests |
| `uv run ruff check` on changed Python/tests | PASS |
| `uv run python scripts/audit_complexity.py --changed --summary --limit 12` | PASS — 0 changed-code violations |
| `uv run python -m compileall -q` on changed Python | PASS |
| `git diff --check` | PASS |

## Existing exact BDO artifacts

The read-only delivery artifacts remain in the local runtime artifact store;
they are not copied into prompts or vendor systems. Their SHA-256 values at
this fixed point are:

| artifact | SHA-256 |
| --- | --- |
| `semantic-mutation-suite-final.json` | `5f28e5f918b93f3c32e44613cf7a0be5ca6d91e278de02867c7fa137e28d738d` |
| `semantic-review-final.json` | `ee00e4d52aec81ef8ae0d47f65b5e0f1612f676a8971192758e4457c5fa44131` |
| `planning-response-final.json` | `076a994f14fde7d2c937c30b0862ede0de94c27d33ca549a35ddd648086daccc` |
| `workspace-fresh.json` | `940a90fe2bfef2d4b5fd855d719317263c68eb017d974cd652706cfbde5e0eae` |
| `codex-runs-final.json` | `03987340a9c7a0aebad726209c3e0816a9b8b18ccc2232ad5969fd44ef92f2dd` |

The artifacts bind to revision `content_revision_6b801326be75414186dc4f9f79b05139`,
content digest `d13459d19d50b52e31a9809d8e395b0c25e4275a94db422af56c60d9f191289e`,
planning input digest `bcde37bf6ed6068287a70a6b13847bc5d24d8cffeda0206b8eef29572a78f26b`,
and proposal `content_planning_proposal_2f1047ef9c2c4f7fb00c7191ae5b4436`.

## Runtime boundary

The managed API was restarted with the existing repo-local environment file
selected through `WILQ_ENV_FILE` (secret values were not printed). The API
reported nine configured connectors: Google Ads, GSC, GA4, Merchant Center,
Ahrefs, Localo, both WordPress sites, and Codex. Only LinkedIn and Facebook
remain unconfigured; neither is required for draft generation. No vendor,
WordPress, publication, deployment, measurement, or `ActionObject.apply`
operation was executed by this repair.

Human/legal approval of the BDO draft remains a separate required decision;
`reviewable` is not publication approval.
