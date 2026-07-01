from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import cast

from wilq.content.drafts.structured_generation import StructuredDraftOutput
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.quality.review import ContentQualityReview
from wilq.content.review.human import ContentHumanReview
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import state_db_path


def content_workflow_store() -> ContentWorkflowStore:
    return ContentWorkflowStore(state_db_path())


class ContentWorkflowStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save_human_review(self, review: ContentHumanReview) -> ContentHumanReview:
        redacted = ContentHumanReview.model_validate(redact_mapping(review.model_dump(mode="json")))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_human_reviews (id, work_item_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  work_item_id = excluded.work_item_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.id,
                    redacted.work_item_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_human_review(self, work_item_id: str) -> ContentHumanReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_human_reviews
                WHERE work_item_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentHumanReview.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_audit(
        self,
        audit: ContentWordPressDraftAuditEnvelope,
    ) -> ContentWordPressDraftAuditEnvelope:
        redacted = ContentWordPressDraftAuditEnvelope.model_validate(
            redact_mapping(audit.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_workflow_audits (audit_id, human_review_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(audit_id) DO UPDATE SET
                  human_review_id = excluded.human_review_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.audit_id,
                    redacted.human_review_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_audit_for_review(
        self,
        human_review_id: str,
    ) -> ContentWordPressDraftAuditEnvelope | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_workflow_audits
                WHERE human_review_id = ?
                ORDER BY audit_id DESC
                LIMIT 1
                """,
                (human_review_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentWordPressDraftAuditEnvelope.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )

    def save_structured_output(
        self,
        work_item_id: str,
        output: StructuredDraftOutput,
    ) -> StructuredDraftOutput:
        redacted = StructuredDraftOutput.model_validate(
            redact_mapping(output.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_structured_outputs (work_item_id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  payload_json = excluded.payload_json
                """,
                (
                    work_item_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_structured_output(self, work_item_id: str) -> StructuredDraftOutput | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_structured_outputs
                WHERE work_item_id = ?
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        if row is None:
            return None
        return StructuredDraftOutput.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_quality_review(self, review: ContentQualityReview) -> ContentQualityReview:
        redacted = ContentQualityReview.model_validate(
            redact_mapping(review.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_quality_reviews (review_id, work_item_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                  work_item_id = excluded.work_item_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.review_id,
                    redacted.work_item_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_quality_review(self, work_item_id: str) -> ContentQualityReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_quality_reviews
                WHERE work_item_id = ?
                ORDER BY review_id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentQualityReview.model_validate(json.loads(cast(str, row["payload_json"])))

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        self._ensure_schema(connection)
        return connection

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_human_reviews (
              id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_workflow_audits (
              audit_id TEXT PRIMARY KEY,
              human_review_id TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_structured_outputs (
              work_item_id TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_quality_reviews (
              review_id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )


def _model_json(
    model: (
        ContentHumanReview
        | ContentWordPressDraftAuditEnvelope
        | StructuredDraftOutput
        | ContentQualityReview
    ),
) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
