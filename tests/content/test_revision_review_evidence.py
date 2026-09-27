from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_workflow as content_workflow_router
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionReviewRequest,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.documents.revision_save_validation import validate_review_evidence
from wilq.content.workflow.documents.revisions import ContentDraftRevision


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

    assert (
        validate_review_evidence(
            request, cast(ContentWorkItemWorkflowSnapshotResponse, snapshot)
        )
        is None
    )


def test_review_rejects_evidence_outside_the_exact_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = SimpleNamespace(
        revision_id="content_revision_exact",
        content_digest="a" * 64,
        sections=[SimpleNamespace(evidence_ids=["ev_exact"])],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    snapshot = SimpleNamespace(
        revision_workspace=SimpleNamespace(
            latest_revision=revision,
            latest_review=None,
            can_review=True,
            status="unreviewed",
            safe_next_step="Zapisz review dokładnej wersji.",
        )
    )
    persisted: list[object] = []

    class _Store:
        def review_draft_revision(self, command: object) -> object:
            persisted.append(command)
            raise AssertionError("foreign evidence must not reach the store")

    monkeypatch.setattr(
        content_workflow_router,
        "semantic_review_snapshot_for_work_item_or_404",
        lambda _work_item_id: snapshot,
    )
    monkeypatch.setattr(
        content_workflow_router, "content_workflow_store", lambda: _Store()
    )

    response = TestClient(app).post(
        "/api/content/work-items/wi_exact/draft-revisions/content_revision_exact/review",
        json={
            "expected_revision_digest": "a" * 64,
            "reviewed_by": "wilku",
            "decision": "approved",
            "notes": "",
            "checked_items": ["pełny dokument"],
            "evidence_ids": ["ev_outside_exact_revision"],
        },
    )

    assert response.status_code == 422
    assert "spoza snapshotu" in response.json()["detail"]
    assert persisted == []
