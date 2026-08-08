from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import wilq.content.workflow.store.store as workflow_store_module
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.store.store import ContentWorkflowStore


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


def test_human_review_upsert_becomes_latest_without_changing_its_rowid(
    tmp_path: Path,
    monkeypatch,
) -> None:
    moments = iter(
        [
            datetime(2026, 8, 7, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 7, 10, 1, tzinfo=UTC),
            datetime(2026, 8, 7, 10, 2, tzinfo=UTC),
        ]
    )
    monkeypatch.setattr(workflow_store_module, "utc_now", lambda: next(moments))
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    rewritten = ContentHumanReview(
        id="human_review_a_rewritten",
        work_item_id="content_work_item_bdo",
        stage="draft_package",
        reviewed_by="wilku",
        decision="needs_changes",
        checked_items=["tekst"],
        evidence_ids=["ev_gsc_bdo"],
        draft_package_id="draft_package_content_work_item_bdo",
    )
    higher_rowid = rewritten.model_copy(
        update={"id": "human_review_z_older", "decision": "deferred"}
    )
    newest_content = rewritten.model_copy(update={"decision": "approved"})

    store.save_human_review(rewritten)
    store.save_human_review(higher_rowid)
    store.save_human_review(newest_content)

    assert store.latest_human_review("content_work_item_bdo") == newest_content


def test_human_review_schema_migrates_existing_rows_before_ordering(tmp_path: Path) -> None:
    path = tmp_path / "wilq.sqlite3"
    review = ContentHumanReview(
        id="human_review_legacy",
        work_item_id="content_work_item_bdo",
        stage="draft_package",
        reviewed_by="wilku",
        decision="approved",
        checked_items=["tekst"],
        evidence_ids=["ev_gsc_bdo"],
        draft_package_id="draft_package_content_work_item_bdo",
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE content_human_reviews (
              id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO content_human_reviews (id, work_item_id, payload_json) "
            "VALUES (?, ?, ?)",
            (review.id, review.work_item_id, review.model_dump_json()),
        )

    store = ContentWorkflowStore(path)

    assert store.latest_human_review(review.work_item_id) == review
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(content_human_reviews)")}
    assert "updated_at" in columns


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
