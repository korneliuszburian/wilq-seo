from __future__ import annotations

from pathlib import Path

from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.store import ContentWorkflowStore


def test_content_workflow_store_persists_human_review(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    review = ContentHumanReview(
        id="human_review_bdo",
        work_item_id="content_work_item_bdo",
        stage="draft_package",
        reviewed_by="wilku",
        decision="approved",
        checked_items=["claimy sprawdzone"],
        evidence_ids=["ev_gsc_bdo"],
        draft_package_id="draft_package_content_work_item_bdo",
    )

    saved = store.save_human_review(review)
    loaded = store.latest_human_review("content_work_item_bdo")

    assert saved == review
    assert loaded == review
    assert store.latest_human_review("content_work_item_other") is None


def test_content_workflow_store_returns_last_recorded_review_not_lexicographic_id(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    first = ContentHumanReview(
        id="human_review_z_first",
        work_item_id="content_work_item_bdo",
        stage="draft_package",
        reviewed_by="wilku",
        decision="needs_changes",
        checked_items=["tekst sprawdzony"],
        evidence_ids=["ev_gsc_bdo"],
        draft_package_id="draft_package_content_work_item_bdo",
    )
    latest = first.model_copy(
        update={
            "id": "human_review_a_latest",
            "decision": "approved",
        }
    )

    store.save_human_review(first)
    store.save_human_review(latest)

    assert store.latest_human_review("content_work_item_bdo") == latest


def test_content_workflow_store_persists_audit_for_human_review(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    audit = ContentWordPressDraftAuditEnvelope(
        audit_id="audit_bdo",
        actor="wilku",
        reason="Zatwierdzony szkic może trafić do WordPress jako draft.",
        evidence_ids=["ev_gsc_bdo"],
        human_review_id="human_review_bdo",
    )

    saved = store.save_audit(audit)
    loaded = store.latest_audit_for_review("human_review_bdo")

    assert saved == audit
    assert loaded == audit
    assert store.latest_audit_for_review("human_review_other") is None
