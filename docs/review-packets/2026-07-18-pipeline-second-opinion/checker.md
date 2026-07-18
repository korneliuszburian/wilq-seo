# Second-opinion review: full content pipeline lineage slice

## Claim

The current WILQ content pipeline safely carries approved source-material and knowledge-card lineage from dynamic planning into the durable full-document revision, without breaking legacy revisions or changing the draft-only approval boundary.

## Acceptance and scope

- Request or tracker: active WILQ content-pipeline goal; durable full-document slice.
- Fixed ref or artifact: current Git checkout supplied to the runner.
- Evidence root and identity: the exact Git identity supplied by `fingerprint-git`.
- In-scope paths: `wilq/content/workflow/revisions.py`, `wilq/content/drafts/initial_full_draft_document.py`, `wilq/content/workflow/revision_persistence.py`, `packages/shared-schemas/src/contentWorkflow.ts`, and focused tests.
- Explicitly out of scope: owner approval, real Wilku UAT, vendor publishing, connector freshness beyond existing API evidence, and unrelated dirty worktree changes.

## Local verification

- `uv run pytest -q tests/content/test_full_document_revision_v2.py tests/content/test_content_workflow_revisions.py` — 25 passed.
- `uv run pytest -q tests/content/test_dynamic_planning_proposals_api.py -k 'two_case_and_idempotent'` — passed.
- `pnpm --dir packages/shared-schemas exec vitest run src/index.test.ts -t 'ContentDraftRevision'` — 1 passed.
- `uv run pytest -q tests/content/test_dynamic_planning_proposals_api.py -k 'initial_full_draft_uses_the_same_atomic_contract_for_both_services'` — passed after fixing source-fact lineage extraction; process teardown required interruption after the test result.

## Proof boundaries

- Proves: the typed models, builder, digest payload, and shared schema expose the lineage fields; v1 construction remains compatible; v2 builder derives material IDs from source facts and card IDs from planning input; focused API generation reaches persistence.
- Does not prove: that all pending source materials are approved, that every real connector is fresh, that a human accepted a revision, that WordPress received a draft, or that the dashboard is useful to a real marketer.
- Human-only decisions: owner approval of knowledge/material scope, exact revision acceptance, marketer/UAT score, and any vendor write.

## Current evidence

- `wilq/content/workflow/revisions.py` defines lineage on section, proposal metadata, stored revision, and append command while retaining defaults for v1 compatibility.
- `wilq/content/drafts/initial_full_draft_document.py` maps section lineage and derives top-level material IDs from `planning_input.source_facts`.
- `wilq/content/workflow/revision_persistence.py` includes source/card IDs in the v2 digest payload.
- `packages/shared-schemas/src/contentWorkflow.ts` mirrors section, metadata, and revision lineage fields for browser/API consumers.
- The API currently reports eight pending source materials and does not permit an initial draft until the plan is approved; those are intentional typed blockers, not silently bypassed.

Return only schema-compatible findings. Be strict: identify missing lineage, compatibility, digest, API, or safety proof; do not praise or declare the claim complete.
