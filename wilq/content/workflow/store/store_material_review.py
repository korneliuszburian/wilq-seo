"""Append-only persistence for exact current material review previews/receipts."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.material_review import (
    ContentMaterialReviewPreview,
    ContentMaterialReviewPreviewRecordResult,
    ContentMaterialReviewReceipt,
    ContentMaterialReviewRecordResult,
)
from wilq.storage.model_json import model_json


class ContentMaterialReviewStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_material_review_preview(
        self,
        preview: ContentMaterialReviewPreview,
    ) -> ContentMaterialReviewPreviewRecordResult:
        accepted = ContentMaterialReviewPreview.model_validate_json(
            preview.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_material_review_previews "
                "WHERE preview_id = ?",
                (accepted.preview_id,),
            ).fetchone()
            if row is not None:
                stored = ContentMaterialReviewPreview.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return ContentMaterialReviewPreviewRecordResult(
                    status=("idempotent" if stored == accepted else "conflict"),
                    preview=stored,
                )
            connection.execute(
                """
                INSERT INTO content_material_review_previews (
                  preview_id, preview_digest, work_item_id, catalog_id,
                  canonical_path, public_url, catalog_item_digest,
                  catalog_snapshot_digest, prepared_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.preview_id,
                    accepted.preview_digest,
                    accepted.work_item_id,
                    accepted.catalog_id,
                    accepted.canonical_path,
                    accepted.public_url,
                    accepted.catalog_item_digest,
                    accepted.catalog_snapshot_digest,
                    accepted.prepared_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentMaterialReviewPreviewRecordResult(status="created", preview=accepted)

    def load_content_material_review_preview(
        self,
        preview_id: str,
    ) -> ContentMaterialReviewPreview | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_material_review_previews "
                "WHERE preview_id = ?",
                (preview_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentMaterialReviewPreview.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_content_material_review(
        self,
        receipt: ContentMaterialReviewReceipt,
    ) -> ContentMaterialReviewRecordResult:
        accepted = ContentMaterialReviewReceipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            by_preview = connection.execute(
                "SELECT payload_json FROM content_material_review_receipts "
                "WHERE work_item_id = ? AND preview_id = ?",
                (accepted.work_item_id, accepted.preview_id),
            ).fetchone()
            if by_preview is not None:
                stored = ContentMaterialReviewReceipt.model_validate_json(
                    cast(str, by_preview["payload_json"]), strict=True
                )
                same_request = (
                    stored.work_item_id == accepted.work_item_id
                    and stored.preview_id == accepted.preview_id
                    and stored.preview_digest == accepted.preview_digest
                    and stored.decision == accepted.decision
                    and stored.reviewer == accepted.reviewer
                    and stored.reviewed_full_material == accepted.reviewed_full_material
                )
                return ContentMaterialReviewRecordResult(
                    status=("idempotent" if same_request else "conflict"),
                    review=stored,
                )
            by_id = connection.execute(
                "SELECT payload_json FROM content_material_review_receipts "
                "WHERE review_id = ?",
                (accepted.review_id,),
            ).fetchone()
            if by_id is not None:
                stored = ContentMaterialReviewReceipt.model_validate_json(
                    cast(str, by_id["payload_json"]), strict=True
                )
                return ContentMaterialReviewRecordResult(status="conflict", review=stored)
            connection.execute(
                """
                INSERT INTO content_material_review_receipts (
                  review_id, review_digest, work_item_id, preview_id,
                  preview_digest, decision, reviewer, reviewed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.review_id,
                    accepted.review_digest,
                    accepted.work_item_id,
                    accepted.preview_id,
                    accepted.preview_digest,
                    accepted.decision,
                    accepted.reviewer,
                    accepted.reviewed_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentMaterialReviewRecordResult(status="created", review=accepted)

    def load_content_material_review(
        self,
        review_id: str,
    ) -> ContentMaterialReviewReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_material_review_receipts "
                "WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentMaterialReviewReceipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def latest_content_material_review(
        self,
        work_item_id: str,
    ) -> ContentMaterialReviewReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM content_material_review_receipts
                WHERE work_item_id = ?
                ORDER BY reviewed_at DESC, review_id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentMaterialReviewReceipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


__all__ = ["ContentMaterialReviewStoreMixin"]
