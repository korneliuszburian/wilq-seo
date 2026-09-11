"""SQLite persistence and exact-row guards for editorial content-kind receipts."""

from __future__ import annotations

import json
import sqlite3
from typing import cast

from wilq.content.workflow.content_kind_receipt import (
    ContentKindReceipt,
    ContentKindReceiptRecordResult,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
)
from wilq.content.workflow.store.store_production_classification import (
    load_latest_production_classification_from_connection,
)
from wilq.storage.model_json import model_json


class ContentKindReceiptStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_kind_receipt(
        self,
        receipt: ContentKindReceipt,
    ) -> ContentKindReceiptRecordResult:
        accepted = ContentKindReceipt.model_validate_json(receipt.model_dump_json(), strict=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _assert_current_content_kind_receipt(connection, accepted)
            existing_row = connection.execute(
                """
                SELECT *
                FROM content_kind_receipts
                WHERE work_item_id = ?
                  AND classification_run_digest = ?
                  AND decision_set_digest = ?
                  AND source_packet_row_digest = ?
                  AND canonical_path = ?
                  AND public_url = ?
                  AND planning_input_digest = ?
                  AND content_kind = ?
                LIMIT 1
                """,
                _content_kind_receipt_context(accepted),
            ).fetchone()
            if existing_row is not None:
                existing = _content_kind_receipt_from_row(existing_row)
                return ContentKindReceiptRecordResult(
                    status=(
                        "idempotent"
                        if existing.receipt_digest == accepted.receipt_digest
                        else "conflict"
                    ),
                    receipt=existing,
                )
            connection.execute(
                """
                INSERT INTO content_kind_receipts (
                  receipt_id, receipt_digest, work_item_id,
                  classification_run_id, classification_run_digest, decision_set_digest,
                  source_packet_row_digest, canonical_path, public_url,
                  planning_input_digest, content_kind, wordpress_content_type,
                  inventory_evidence_digest, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.receipt_id,
                    accepted.receipt_digest,
                    accepted.work_item_id,
                    accepted.classification_run_id,
                    accepted.classification_run_digest,
                    accepted.decision_set_digest,
                    accepted.source_packet_row_digest,
                    accepted.canonical_path,
                    accepted.public_url,
                    accepted.planning_input_digest,
                    accepted.content_kind,
                    accepted.wordpress_content_type,
                    accepted.inventory_evidence_digest,
                    model_json(accepted),
                ),
            )
        return ContentKindReceiptRecordResult(status="created", receipt=accepted)

    def load_content_kind_receipt(self, receipt_id: str) -> ContentKindReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM content_kind_receipts
                WHERE receipt_id = ?
                LIMIT 1
                """,
                (receipt_id,),
            ).fetchone()
        return None if row is None else _content_kind_receipt_from_row(row)


def assert_persisted_editorial_content_kind_receipt(
    connection: sqlite3.Connection,
    authorization: ContentRefreshPreparationAuthorization,
) -> ContentKindReceipt:
    """Require the exact durable editorial receipt before an authorization can persist."""

    if authorization.content_kind != "editorial":
        raise ValueError("Editorial content-kind receipt guard received a service authorization.")
    row = connection.execute(
        """
        SELECT *
        FROM content_kind_receipts
        WHERE work_item_id = ?
          AND classification_run_digest = ?
          AND decision_set_digest = ?
          AND source_packet_row_digest = ?
          AND canonical_path = ?
          AND public_url = ?
          AND planning_input_digest = ?
          AND content_kind = ?
        LIMIT 1
        """,
        _content_kind_receipt_context(authorization),
    ).fetchone()
    if row is None:
        raise ValueError(
            "Editorial refresh authorization requires a persisted content-kind receipt."
        )
    receipt = _content_kind_receipt_from_row(row)
    if (
        receipt.work_item_id != authorization.work_item_id
        or receipt.classification_run_id != authorization.classification_run_id
        or receipt.classification_run_digest != authorization.classification_run_digest
        or receipt.decision_set_digest != authorization.decision_set_digest
        or receipt.source_packet_row_digest != authorization.source_packet_row_digest
        or receipt.canonical_path != authorization.canonical_path
        or receipt.public_url != authorization.public_url
        or receipt.planning_input_digest != authorization.planning_input_digest
        or receipt.content_kind != authorization.content_kind
    ):
        raise ValueError("Editorial content-kind receipt does not match refresh authorization.")
    return receipt


def _assert_current_content_kind_receipt(
    connection: sqlite3.Connection,
    receipt: ContentKindReceipt,
) -> None:
    run = load_latest_production_classification_from_connection(connection)
    if run is None:
        raise ValueError("Content-kind receipt requires a current classification.")
    row = run.for_work_item(receipt.work_item_id)
    if (
        row is None
        or row.current_work_item_id != receipt.work_item_id
        or row.decision != "refresh"
        or run.freshness.requires_refresh
        or run.run_id != receipt.classification_run_id
        or run.run_digest != receipt.classification_run_digest
        or run.input.decision_set_digest != receipt.decision_set_digest
        or row.source_packet_row_digest != receipt.source_packet_row_digest
        or row.canonical_path != receipt.canonical_path
        or row.public_url != receipt.public_url
    ):
        raise ValueError("Content-kind receipt does not bind the current classified row.")


def _content_kind_receipt_from_row(row: sqlite3.Row) -> ContentKindReceipt:
    receipt = ContentKindReceipt.model_validate(json.loads(cast(str, row["payload_json"])))
    expected_scalars = (
        receipt.receipt_id,
        receipt.receipt_digest,
        receipt.work_item_id,
        receipt.classification_run_id,
        receipt.classification_run_digest,
        receipt.decision_set_digest,
        receipt.source_packet_row_digest,
        receipt.canonical_path,
        receipt.public_url,
        receipt.planning_input_digest,
        receipt.content_kind,
        receipt.wordpress_content_type,
        receipt.inventory_evidence_digest,
    )
    stored_scalars = tuple(
        row[name]
        for name in (
            "receipt_id",
            "receipt_digest",
            "work_item_id",
            "classification_run_id",
            "classification_run_digest",
            "decision_set_digest",
            "source_packet_row_digest",
            "canonical_path",
            "public_url",
            "planning_input_digest",
            "content_kind",
            "wordpress_content_type",
            "inventory_evidence_digest",
        )
    )
    if stored_scalars != expected_scalars:
        raise ValueError("Stored content-kind receipt scalars do not match receipt.")
    return receipt


def _content_kind_receipt_context(
    value: ContentKindReceipt | ContentRefreshPreparationAuthorization,
) -> tuple[str, str, str, str, str, str, str, str]:
    return (
        value.work_item_id,
        value.classification_run_digest,
        value.decision_set_digest,
        value.source_packet_row_digest,
        value.canonical_path,
        value.public_url,
        value.planning_input_digest,
        value.content_kind,
    )


__all__ = [
    "ContentKindReceiptStoreMixin",
    "assert_persisted_editorial_content_kind_receipt",
]
