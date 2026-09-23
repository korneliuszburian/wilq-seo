"""Append-only storage for exact v2 research packet previews and approvals."""

from __future__ import annotations

import re
import sqlite3
from typing import cast

from pydantic import ValidationError

from wilq.content.workflow.research_packet_v2_receipt import (
    ResearchPacketV2ApprovalReceipt,
    ResearchPacketV2PreviewRecord,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json
from wilq.storage.schema_versions import reject_newer_sqlite_schema

_RESEARCH_PACKET_V2_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS content_research_packet_v2_previews (
      preview_hash TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_content_research_packet_v2_previews_work_item
    ON content_research_packet_v2_previews (work_item_id)
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_v2_previews_no_update
    BEFORE UPDATE ON content_research_packet_v2_previews
    BEGIN SELECT RAISE(ABORT, 'research packet v2 previews are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_v2_previews_no_replace
    BEFORE INSERT ON content_research_packet_v2_previews
    WHEN EXISTS (SELECT 1 FROM content_research_packet_v2_previews
                 WHERE preview_hash = NEW.preview_hash)
    BEGIN SELECT RAISE(ABORT, 'research packet v2 previews are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_v2_previews_no_delete
    BEFORE DELETE ON content_research_packet_v2_previews
    BEGIN SELECT RAISE(ABORT, 'research packet v2 previews are append-only'); END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_research_packet_v2_approval_receipts (
      packet_id TEXT PRIMARY KEY,
      packet_digest TEXT NOT NULL UNIQUE,
      action_id TEXT NOT NULL UNIQUE,
      work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_content_research_packet_v2_receipts_work_item
    ON content_research_packet_v2_approval_receipts (work_item_id)
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_v2_approval_receipts_no_update
    BEFORE UPDATE ON content_research_packet_v2_approval_receipts
    BEGIN SELECT RAISE(ABORT, 'research packet v2 approval receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_v2_approval_receipts_no_replace
    BEFORE INSERT ON content_research_packet_v2_approval_receipts
    WHEN EXISTS (SELECT 1 FROM content_research_packet_v2_approval_receipts
                 WHERE packet_id = NEW.packet_id OR packet_digest = NEW.packet_digest
                    OR action_id = NEW.action_id)
    BEGIN SELECT RAISE(ABORT, 'research packet v2 approval receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_v2_approval_receipts_no_delete
    BEFORE DELETE ON content_research_packet_v2_approval_receipts
    BEGIN SELECT RAISE(ABORT, 'research packet v2 approval receipts are append-only'); END
    """,
)

_DDL_HEADER = re.compile(
    r"CREATE (TABLE|INDEX|TRIGGER) IF NOT EXISTS ([a-z0-9_]+)", re.IGNORECASE
)


def ensure_research_packet_v2_schema(connection: sqlite3.Connection) -> None:
    """Create v2 proposal and receipt tables on supported local stores."""
    reject_newer_sqlite_schema(connection)
    for statement in _RESEARCH_PACKET_V2_SCHEMA:
        match = _DDL_HEADER.match(statement.lstrip())
        if match is None:
            raise RuntimeError("Research packet v2 schema statement is invalid.")
        object_type, name = match.groups()
        connection.execute(statement)
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = ? AND name = ?",
            (object_type.lower(), name),
        ).fetchone()
        if row is None or _normalized_ddl(str(row[0])) != _normalized_ddl(statement):
            kind = "preview" if "_previews" in name else "approval"
            raise RuntimeError(f"Research packet v2 {kind} schema is incomplete.")


def _normalized_ddl(sql: str) -> str:
    without_guard = re.sub(r"\bIF NOT EXISTS\b", "", sql, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", without_guard).strip().casefold()


class ResearchPacketV2StoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_research_packet_v2_preview(self, record: ResearchPacketV2PreviewRecord) -> str:
        accepted = _accepted_preview_record(record)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_research_packet_v2_previews "
                "WHERE preview_hash = ?",
                (accepted.preview_hash,),
            ).fetchone()
            if row is not None:
                stored = _preview_from_payload(row["payload_json"])
                return "idempotent" if stored == accepted else "conflict"
            connection.execute(
                "INSERT INTO content_research_packet_v2_previews "
                "(preview_hash, work_item_id, payload_json) VALUES (?, ?, ?)",
                (accepted.preview_hash, accepted.work_item_id, model_json(accepted)),
            )
        return "created"

    def load_research_packet_v2_preview(
        self, preview_hash: str
    ) -> ResearchPacketV2PreviewRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT preview_hash, work_item_id, payload_json "
                "FROM content_research_packet_v2_previews WHERE preview_hash = ?",
                (preview_hash,),
            ).fetchone()
        if row is None:
            return None
        stored = _preview_from_payload(row["payload_json"])
        if (row["preview_hash"], row["work_item_id"]) != (
            stored.preview_hash,
            stored.work_item_id,
        ):
            raise ValueError("Stored research packet v2 preview does not match its index.")
        return stored

    def _record_research_packet_v2_approval_receipt(
        self, receipt: ResearchPacketV2ApprovalReceipt
    ) -> str:
        accepted = _accepted_receipt(receipt)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            proposal = connection.execute(
                "SELECT work_item_id, payload_json FROM content_research_packet_v2_previews "
                "WHERE preview_hash = ?",
                (accepted.packet_digest,),
            ).fetchone()
            if proposal is None:
                raise ValueError("Approval receipt requires its stored exact preview.")
            stored_preview = _preview_from_payload(proposal["payload_json"])
            if (
                stored_preview.preview_hash != accepted.packet_digest
                or stored_preview.work_item_id != proposal["work_item_id"]
            ):
                raise ValueError("Stored research packet v2 preview index does not match.")
            existing = connection.execute(
                "SELECT work_item_id, payload_json "
                "FROM content_research_packet_v2_approval_receipts "
                "WHERE packet_id = ? OR packet_digest = ? OR action_id = ?",
                (accepted.packet_id, accepted.packet_digest, accepted.action_id),
            ).fetchone()
            if existing is not None:
                stored = _receipt_from_payload(existing["payload_json"])
                return (
                    "idempotent"
                    if stored == accepted and existing["work_item_id"] == proposal["work_item_id"]
                    else "conflict"
                )
            connection.execute(
                "INSERT INTO content_research_packet_v2_approval_receipts "
                "(packet_id, packet_digest, action_id, work_item_id, payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    accepted.packet_id,
                    accepted.packet_digest,
                    accepted.action_id,
                    cast(str, proposal["work_item_id"]),
                    model_json(accepted),
                ),
            )
        return "created"

    def load_research_packet_v2_approval_receipt(
        self, packet_id: str
    ) -> ResearchPacketV2ApprovalReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT receipt.packet_id, receipt.packet_digest, receipt.action_id, "
                "receipt.work_item_id AS receipt_work_item_id, receipt.payload_json, "
                "preview.work_item_id AS preview_work_item_id "
                "FROM content_research_packet_v2_approval_receipts AS receipt "
                "LEFT JOIN content_research_packet_v2_previews AS preview "
                "ON preview.preview_hash = receipt.packet_digest "
                "WHERE receipt.packet_id = ?",
                (packet_id,),
            ).fetchone()
        if row is None:
            return None
        stored = _receipt_from_payload(row["payload_json"])
        if (row["packet_id"], row["packet_digest"], row["action_id"]) != (
            stored.packet_id,
            stored.packet_digest,
            stored.action_id,
        ) or row["receipt_work_item_id"] != row["preview_work_item_id"]:
            raise ValueError("Stored approval receipt does not match its index.")
        return stored


def _accepted_preview_record(
    record: ResearchPacketV2PreviewRecord,
) -> ResearchPacketV2PreviewRecord:
    accepted = ResearchPacketV2PreviewRecord.model_validate_json(
        record.model_dump_json(), strict=True
    )
    preview = accepted.snapshot
    visible = {
        "selected_facts": [
            {"text": fact.text, "source_reference": fact.source_reference}
            for fact in preview.selected_facts
        ],
        "planning_context": (
            None
            if preview.planning_context is None
            else preview.planning_context.model_dump(mode="json")
        ),
        "cta_direction": preview.cta_direction,
        "required_cta_patterns": list(preview.required_cta_patterns),
        "internal_links": [
            {"target_url": link.target_url, "anchor_hint": link.anchor_hint}
            for link in preview.internal_links
        ],
        "legal_requirements": [
            {"label": requirement.label} for requirement in preview.legal_requirements
        ],
    }
    if redact_mapping(visible) != visible:
        raise ValueError("Research packet v2 preview contains redaction-required text.")
    return accepted


def _accepted_receipt(
    receipt: ResearchPacketV2ApprovalReceipt,
) -> ResearchPacketV2ApprovalReceipt:
    accepted = ResearchPacketV2ApprovalReceipt.model_validate_json(
        receipt.model_dump_json(), strict=True
    )
    visible = {
        "action_id": accepted.action_id,
        "preview_audit_event_id": accepted.preview_audit_event_id,
        "review_audit_event_id": accepted.review_audit_event_id,
        "confirmation_audit_event_id": accepted.confirmation_audit_event_id,
        "impact_audit_event_id": accepted.impact_audit_event_id,
        "review_actor": accepted.review_actor,
    }
    if redact_mapping(visible) != visible:
        raise ValueError("Research packet v2 receipt contains redaction-required identity.")
    return accepted


def _preview_from_payload(payload: str) -> ResearchPacketV2PreviewRecord:
    try:
        return ResearchPacketV2PreviewRecord.model_validate_json(payload, strict=True)
    except (ValidationError, ValueError) as exc:
        raise ValueError("Stored research packet v2 preview is invalid.") from exc


def _receipt_from_payload(payload: str) -> ResearchPacketV2ApprovalReceipt:
    try:
        return ResearchPacketV2ApprovalReceipt.model_validate_json(payload, strict=True)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "stored approval receipt does not match its authenticated payload."
        ) from exc


__all__ = ["ResearchPacketV2StoreMixin", "ensure_research_packet_v2_schema"]
