# Second-opinion review: editor save and child revision seam

## Claim

The canonical editor-save path cannot silently downgrade an existing full-document v2 revision: a child save preserves exact planning bindings, page assets, source-material and knowledge-card lineage, and remains reviewable/draft-only.

## Acceptance and scope

- Request or tracker: active WILQ content-pipeline goal; exact revision hardening.
- Fixed ref or artifact: current Git checkout supplied to the runner.
- Evidence root and identity: the exact Git identity supplied by `fingerprint-git`.
- In-scope paths: `apps/api/wilq_api/routers/content_workflow.py`, `wilq/content/workflow/revision_children.py`, `wilq/content/drafts/codex_section_proposal.py`, `wilq/content/workflow/revisions.py`, and focused revision tests.
- Explicitly out of scope: human approval, real WordPress writes, storage maintenance activation, legacy test fixtures that do not generate a current plan, and unrelated dirty worktree edits.

## Local verification

- `uv run ruff check apps/api/wilq_api/routers/content_workflow.py wilq/content/workflow/revision_children.py wilq/content/drafts/codex_section_proposal.py` — passed.
- `python3 -m py_compile apps/api/wilq_api/routers/content_workflow.py` — passed.
- `uv run pytest -q tests/content/test_revision_lineage_contract.py tests/content/test_content_revision_proposal_atomicity.py tests/content/test_full_document_revision_v2.py` — 22 passed.
- `uv run pytest -q tests/content/test_planning_review_gate.py` — passed.

## Proof boundaries

- Proves: v2 editor save construction carries exact bindings and page assets; child proposal persistence carries top-level and section lineage; v1 remains readable; no vendor write is introduced by the seam.
- Does not prove: real owner approval, approved material import, semantic-review maintenance activation, dashboard UAT, or a WordPress vendor mutation.
- Human-only decisions: acceptance of revised text, semantic review, and any draft handoff confirmation.

## Current evidence

- `apps/api/wilq_api/routers/content_workflow.py` branches existing v2 editor saves into a v2 append command and preserves full-document fields.
- `wilq/content/workflow/revision_children.py` copies source/card IDs and exact v2 bindings into child commands.
- `wilq/content/drafts/codex_section_proposal.py` copies source/card lineage into selected-section proposal metadata.
- `wilq/content/workflow/revisions.py` keeps `publish_ready=false` and exact v2 validation.
- Focused tests assert lineage round-trip, legacy readback and deterministic digest behavior.

Return only schema-compatible findings. Be strict: find downgrade, stale-binding, lineage-loss, review-bypass, or vendor-write risks; do not approve or declare readiness.
