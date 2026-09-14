"""Append-only persistence for evidence-scoped authoring inventory receipts."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.authoring_inventory_receipt import (
    ContentAuthoringInventoryReceipt,
    ContentAuthoringInventoryReceiptRecordResult,
)
from wilq.storage.model_json import model_json


class ContentAuthoringInventoryReceiptStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_authoring_inventory_receipt(
        self, receipt: ContentAuthoringInventoryReceipt
    ) -> ContentAuthoringInventoryReceiptRecordResult:
        accepted = ContentAuthoringInventoryReceipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            by_id = connection.execute(
                "SELECT * FROM content_authoring_inventory_receipts WHERE receipt_id = ?",
                (accepted.receipt_id,),
            ).fetchone()
            if by_id is not None:
                existing = _receipt_from_row(by_id)
                return ContentAuthoringInventoryReceiptRecordResult(
                    status=(
                        "idempotent"
                        if existing == accepted
                        else "conflict"
                    ),
                    receipt=existing,
                )
            by_snapshot = connection.execute(
                """
                SELECT * FROM content_authoring_inventory_receipts
                WHERE catalog_id = ? AND catalog_snapshot_digest = ?
                """,
                (accepted.catalog_id, accepted.catalog_snapshot_digest),
            ).fetchone()
            if by_snapshot is not None:
                return ContentAuthoringInventoryReceiptRecordResult(
                    status="conflict", receipt=_receipt_from_row(by_snapshot)
                )
            connection.execute(
                """
                INSERT INTO content_authoring_inventory_receipts (
                  receipt_id, receipt_digest, catalog_id, current_work_item_id,
                  canonical_path, public_url, catalog_snapshot_digest, recorded_by,
                  recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.receipt_id,
                    accepted.receipt_digest,
                    accepted.catalog_id,
                    accepted.current_work_item_id,
                    accepted.canonical_path,
                    accepted.public_url,
                    accepted.catalog_snapshot_digest,
                    accepted.recorded_by,
                    accepted.recorded_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentAuthoringInventoryReceiptRecordResult(status="created", receipt=accepted)

    def load_content_authoring_inventory_receipt(
        self, receipt_id: str
    ) -> ContentAuthoringInventoryReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_authoring_inventory_receipts WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
        return None if row is None else _receipt_from_row(row)

    def list_content_authoring_inventory_receipts(
        self,
    ) -> list[ContentAuthoringInventoryReceipt]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM content_authoring_inventory_receipts "
                "ORDER BY canonical_path, recorded_at, receipt_id"
            ).fetchall()
        return [_receipt_from_row(row) for row in rows]


def _receipt_from_row(row: sqlite3.Row) -> ContentAuthoringInventoryReceipt:
    receipt = ContentAuthoringInventoryReceipt.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    scalars = (
        receipt.receipt_id,
        receipt.receipt_digest,
        receipt.catalog_id,
        receipt.current_work_item_id,
        receipt.canonical_path,
        receipt.public_url,
        receipt.catalog_snapshot_digest,
        receipt.recorded_by,
        receipt.recorded_at.isoformat(),
    )
    stored = tuple(
        row[name]
        for name in (
            "receipt_id",
            "receipt_digest",
            "catalog_id",
            "current_work_item_id",
            "canonical_path",
            "public_url",
            "catalog_snapshot_digest",
            "recorded_by",
            "recorded_at",
        )
    )
    if stored != scalars:
        raise ValueError("Stored authoring inventory receipt scalars do not match payload.")
    return receipt


__all__ = ["ContentAuthoringInventoryReceiptStoreMixin"]
