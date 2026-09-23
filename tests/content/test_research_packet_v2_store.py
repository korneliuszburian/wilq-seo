from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.content.test_research_packet_v2_preview import _ready_inputs
from wilq.content.workflow.research_packet_v2_preview import (
    build_research_packet_v2_preview,
)
from wilq.content.workflow.research_packet_v2_receipt import (
    ResearchPacketV2ApprovalReceipt,
    ResearchPacketV2PreviewRecord,
    research_packet_v2_receipt_digest,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def _preview_record() -> ResearchPacketV2PreviewRecord:
    source_pack, planning_input = _ready_inputs()
    preview = build_research_packet_v2_preview(
        "wi_exact", source_pack=source_pack, planning_input=planning_input
    )
    return ResearchPacketV2PreviewRecord.from_preview(preview)


def _receipt(record: ResearchPacketV2PreviewRecord) -> ResearchPacketV2ApprovalReceipt:
    payload = {
        "schema_version": "wilq_research_packet_v2_approval_receipt_v1",
        "packet_id": f"content_research_packet_v2_{record.preview_hash[:24]}",
        "packet_digest": record.preview_hash,
        "action_id": f"act_content_research_packet_v2_{record.preview_hash}",
        "action_payload_digest": "a" * 64,
        "preview_audit_event_id": "audit_preview_exact",
        "review_audit_event_id": "audit_review_exact",
        "confirmation_audit_event_id": "audit_confirm_exact",
        "impact_audit_event_id": "audit_impact_exact",
        "review_actor": "codex_server",
        "approved_at": "2026-09-24T10:00:00Z",
    }
    digest = research_packet_v2_receipt_digest(payload)
    return ResearchPacketV2ApprovalReceipt.model_validate(payload | {"receipt_digest": digest})


def test_packet_receipt_rejects_a_foreign_action_even_with_recomputed_digest() -> None:
    receipt = _receipt(_preview_record())
    foreign = receipt.model_dump(mode="json") | {"action_id": "act_foreign"}
    foreign["receipt_digest"] = research_packet_v2_receipt_digest(foreign)

    with pytest.raises(ValueError, match="action identity"):
        ResearchPacketV2ApprovalReceipt.model_validate(foreign)


def test_approval_cannot_use_a_tampered_stored_preview(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    record = _preview_record()
    store.record_research_packet_v2_preview(record)
    with sqlite3.connect(store.path) as connection:
        connection.execute("DROP TRIGGER content_research_packet_v2_previews_no_update")
        connection.execute(
            "UPDATE content_research_packet_v2_previews SET payload_json = '{}' "
            "WHERE preview_hash = ?",
            (record.preview_hash,),
        )

    with pytest.raises(ValueError, match="Stored research packet v2 preview"):
        store._record_research_packet_v2_approval_receipt(_receipt(record))


def test_incomplete_v2_table_cannot_be_treated_as_current_schema(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE content_research_packet_v2_previews "
            "(preview_hash TEXT PRIMARY KEY)"
        )

    with pytest.raises(RuntimeError, match="v2 preview schema is incomplete"):
        ContentWorkflowStore(path).load_research_packet_v2_preview("0" * 64)


def test_v2_table_with_columns_but_without_constraints_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "weak-schema.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE content_research_packet_v2_previews "
            "(preview_hash TEXT, work_item_id TEXT, payload_json TEXT)"
        )

    with pytest.raises(RuntimeError, match="v2 preview schema is incomplete"):
        ContentWorkflowStore(path).load_research_packet_v2_preview("0" * 64)


def test_stored_packet_preview_snapshot_has_immutable_nested_links() -> None:
    record = _preview_record()
    assert record.snapshot.internal_links
    link = record.snapshot.internal_links[0]

    with pytest.raises(ValueError, match="frozen"):
        link.anchor_hint = "Podmieniony link"


def test_preview_and_approval_receipt_are_exact_idempotent_and_append_only(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    record = _preview_record()

    assert store.record_research_packet_v2_preview(record) == "created"
    assert store.record_research_packet_v2_preview(record) == "idempotent"
    receipt = _receipt(record)
    assert store._record_research_packet_v2_approval_receipt(receipt) == "created"
    assert store._record_research_packet_v2_approval_receipt(receipt) == "idempotent"
    assert store.load_research_packet_v2_preview(record.preview_hash) == record
    assert store.load_research_packet_v2_approval_receipt(receipt.packet_id) == receipt

    changed = receipt.model_copy(update={"review_actor": "different_server"})
    changed = changed.model_copy(
        update={
            "receipt_digest": research_packet_v2_receipt_digest(changed.model_dump(mode="json"))
        }
    )
    assert store._record_research_packet_v2_approval_receipt(changed) == "conflict"

    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE content_research_packet_v2_previews SET payload_json = '{}'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM content_research_packet_v2_approval_receipts")
        connection.execute("DROP TRIGGER content_research_packet_v2_approval_receipts_no_update")
        connection.execute(
            "UPDATE content_research_packet_v2_approval_receipts "
            "SET payload_json = '{}' WHERE packet_id = ?",
            (receipt.packet_id,),
        )

    with pytest.raises(ValueError, match="stored approval receipt does not match"):
        store.load_research_packet_v2_approval_receipt(receipt.packet_id)
