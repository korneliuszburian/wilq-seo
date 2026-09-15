"""Append-only persistence for exact per-URL research packets."""

from __future__ import annotations

import json
import sqlite3
from typing import cast

from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.research_packet import (
    ContentResearchPacket,
    ContentResearchPacketCommand,
    ContentResearchPacketRecordResult,
    reconcile_content_research_packet,
)
from wilq.content.workflow.research_packet_preparation_receipt import (
    ContentResearchPacketPreparationReceipt,
    ContentResearchPacketPreparationReceiptRecordResult,
)
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding
from wilq.content.workflow.store.store_delivery_identity import binding_from_row
from wilq.content.workflow.store.store_source_pack_binding import (
    _binding_from_source_pack_row,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json


class ContentResearchPacketStoreMixin:
    """Persist only validated, redacted packet receipts."""

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def _record_content_research_packet_preparation_receipt(
        self,
        receipt: ContentResearchPacketPreparationReceipt,
    ) -> ContentResearchPacketPreparationReceiptRecordResult:
        accepted = ContentResearchPacketPreparationReceipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute(
                "SELECT * FROM content_research_packet_preparation_receipts "
                "WHERE receipt_id = ? OR receipt_digest = ?",
                (accepted.receipt_id, accepted.receipt_digest),
            ).fetchone()
            if existing_row is not None:
                existing = _preparation_receipt_from_row(existing_row)
                return ContentResearchPacketPreparationReceiptRecordResult(
                    status=(
                        "idempotent"
                        if existing.receipt_digest == accepted.receipt_digest
                        else "conflict"
                    ),
                    receipt=existing,
                )
            connection.execute(
                """
                INSERT INTO content_research_packet_preparation_receipts (
                  receipt_id, receipt_digest, identity_binding_id,
                  identity_binding_digest, source_pack_binding_id,
                  source_pack_binding_digest, current_work_item_id,
                  input_digest, recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.receipt_id,
                    accepted.receipt_digest,
                    accepted.identity_binding_id,
                    accepted.identity_binding_digest,
                    accepted.source_pack_binding_id,
                    accepted.source_pack_binding_digest,
                    accepted.current_work_item_id,
                    accepted.input_digest,
                    accepted.recorded_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentResearchPacketPreparationReceiptRecordResult(
            status="created", receipt=accepted
        )

    def _load_content_research_packet_preparation_receipt(
        self,
        receipt_id: str,
    ) -> ContentResearchPacketPreparationReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_research_packet_preparation_receipts "
                "WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
        return None if row is None else _preparation_receipt_from_row(row)

    def record_content_research_packet(
        self,
        command: ContentResearchPacketCommand,
    ) -> ContentResearchPacketRecordResult:
        redacted_input = redact_mapping(command.model_dump(mode="json"))
        accepted = ContentResearchPacketCommand.model_validate_json(
            json.dumps(redacted_input, ensure_ascii=False), strict=True
        )
        accepted = accepted.model_copy(update={"recorded_at": utc_now()})
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            identity = _load_identity(connection, accepted.identity_binding_id)
            source_pack = _load_source_pack(connection, accepted.source_pack_binding_id)
            preparation_receipt = _load_preparation_receipt(
                connection, accepted.preparation_receipt_id
            )
            packet = reconcile_content_research_packet(
                accepted,
                identity,
                source_pack,
                preparation_receipt=preparation_receipt,
                now=accepted.recorded_at,
            )
            if packet.blocker is not None and packet.blocker.seam == "preparation_receipt":
                return ContentResearchPacketRecordResult(status="blocked", packet=packet)
            existing_row = connection.execute(
                "SELECT * FROM content_research_packets WHERE packet_id = ?",
                (packet.packet_id,),
            ).fetchone()
            if existing_row is not None:
                existing = _packet_from_row(existing_row)
                return ContentResearchPacketRecordResult(
                    status=(
                        "idempotent"
                        if existing.packet_digest == packet.packet_digest
                        else "conflict"
                    ),
                    packet=existing,
                )
            digest_row = connection.execute(
                "SELECT * FROM content_research_packets WHERE packet_digest = ?",
                (packet.packet_digest,),
            ).fetchone()
            if digest_row is not None:
                return ContentResearchPacketRecordResult(
                    status="conflict",
                    packet=_packet_from_row(digest_row),
                )
            redacted = ContentResearchPacket.model_validate_json(
                packet.model_dump_json(), strict=True
            )
            connection.execute(
                """
                INSERT INTO content_research_packets (
                  packet_id, packet_digest, identity_binding_id,
                  identity_binding_digest, source_pack_binding_id,
                  source_pack_binding_digest, current_work_item_id,
                  canonical_path, public_url, content_kind, input_digest,
                  status, recorded_by, recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    redacted.packet_id,
                    redacted.packet_digest,
                    redacted.identity_binding_id,
                    redacted.identity_binding_digest,
                    redacted.source_pack_binding_id,
                    redacted.source_pack_binding_digest,
                    redacted.current_work_item_id,
                    redacted.canonical_path,
                    redacted.public_url,
                    redacted.content_kind,
                    redacted.input_digest,
                    redacted.status,
                    redacted.recorded_by,
                    redacted.recorded_at.isoformat(),
                    model_json(redacted),
                ),
            )
        return ContentResearchPacketRecordResult(status="created", packet=redacted)

    def load_content_research_packet(self, packet_id: str) -> ContentResearchPacket | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_research_packets WHERE packet_id = ?",
                (packet_id,),
            ).fetchone()
        return None if row is None else _packet_from_row(row)


def _load_identity(
    connection: sqlite3.Connection,
    binding_id: str,
) -> ContentDeliveryIdentityBinding | None:
    row = connection.execute(
        "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?",
        (binding_id,),
    ).fetchone()
    return None if row is None else binding_from_row(row)


def _load_source_pack(
    connection: sqlite3.Connection,
    binding_id: str,
) -> ContentSourcePackBinding | None:
    row = connection.execute(
        "SELECT * FROM content_source_pack_bindings WHERE binding_id = ?",
        (binding_id,),
    ).fetchone()
    return None if row is None else _binding_from_source_pack_row(row)


def _load_preparation_receipt(
    connection: sqlite3.Connection,
    receipt_id: str | None,
) -> ContentResearchPacketPreparationReceipt | None:
    if receipt_id is None:
        return None
    row = connection.execute(
        "SELECT * FROM content_research_packet_preparation_receipts WHERE receipt_id = ?",
        (receipt_id,),
    ).fetchone()
    return None if row is None else _preparation_receipt_from_row(row)


def _preparation_receipt_from_row(
    row: sqlite3.Row,
) -> ContentResearchPacketPreparationReceipt:
    receipt = ContentResearchPacketPreparationReceipt.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    expected = (
        receipt.receipt_id,
        receipt.receipt_digest,
        receipt.identity_binding_id,
        receipt.identity_binding_digest,
        receipt.source_pack_binding_id,
        receipt.source_pack_binding_digest,
        receipt.current_work_item_id,
        receipt.input_digest,
        receipt.recorded_at.isoformat(),
    )
    stored = tuple(
        row[name]
        for name in (
            "receipt_id",
            "receipt_digest",
            "identity_binding_id",
            "identity_binding_digest",
            "source_pack_binding_id",
            "source_pack_binding_digest",
            "current_work_item_id",
            "input_digest",
            "recorded_at",
        )
    )
    if stored != expected:
        raise ValueError("Stored preparation receipt scalars do not match payload.")
    return receipt


def _packet_from_row(row: sqlite3.Row) -> ContentResearchPacket:
    packet = ContentResearchPacket.model_validate_json(cast(str, row["payload_json"]), strict=True)
    expected = (
        packet.packet_id,
        packet.packet_digest,
        packet.identity_binding_id,
        packet.identity_binding_digest,
        packet.source_pack_binding_id,
        packet.source_pack_binding_digest,
        packet.current_work_item_id,
        packet.canonical_path,
        packet.public_url,
        packet.content_kind,
        packet.input_digest,
        packet.status,
        packet.recorded_by,
        packet.recorded_at.isoformat(),
    )
    stored = tuple(
        row[name]
        for name in (
            "packet_id",
            "packet_digest",
            "identity_binding_id",
            "identity_binding_digest",
            "source_pack_binding_id",
            "source_pack_binding_digest",
            "current_work_item_id",
            "canonical_path",
            "public_url",
            "content_kind",
            "input_digest",
            "status",
            "recorded_by",
            "recorded_at",
        )
    )
    if stored != expected:
        raise ValueError("Stored research packet scalars do not match payload.")
    return packet


__all__ = ["ContentResearchPacketStoreMixin"]
