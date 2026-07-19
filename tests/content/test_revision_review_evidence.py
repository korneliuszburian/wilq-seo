from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from apps.api.wilq_api.routers.content_workflow import _validate_review_evidence
from wilq.content.workflow.contracts import (
    ContentDraftRevisionReviewRequest,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.revisions import ContentDraftRevision


def test_revision_review_accepts_lineage_from_all_page_assets() -> None:
    revision = ContentDraftRevision.model_construct(
        sections=[SimpleNamespace(evidence_ids=["ev_section"])],
        faq=[SimpleNamespace(evidence_ids=["ev_faq"])],
        cta_blocks=[SimpleNamespace(evidence_ids=["ev_cta"])],
        internal_links=[SimpleNamespace(evidence_ids=["ev_link"])],
    )
    snapshot = SimpleNamespace(
        revision_workspace=SimpleNamespace(latest_revision=revision)
    )
    request = ContentDraftRevisionReviewRequest(
        expected_revision_digest="a" * 64,
        reviewed_by="wilku",
        decision="approved",
        checked_items=["pełny dokument"],
        evidence_ids=["ev_section", "ev_faq", "ev_cta", "ev_link"],
    )

    _validate_review_evidence(
        request, cast(ContentWorkItemWorkflowSnapshotResponse, snapshot)
    )
