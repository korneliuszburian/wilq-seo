from __future__ import annotations

import json
import sqlite3
from typing import cast

from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftExecutionResult
from wilq.content.quality.review import ContentQualityReview
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.store.store_queries import model_json as _model_json
from wilq.security.redaction import redact_mapping


class _EvidenceStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def latest_human_review(self, work_item_id: str) -> ContentHumanReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_human_reviews
                WHERE work_item_id = ?
                ORDER BY updated_at DESC, id DESC
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

    def save_wordpress_draft_execution(
        self,
        work_item_id: str,
        result: ContentWordPressDraftExecutionResult,
    ) -> ContentWordPressDraftExecutionResult:
        redacted = ContentWordPressDraftExecutionResult.model_validate(
            redact_mapping(result.model_dump(mode="json"))
        )
        with self._connect() as connection:
            if redacted.revision_binding is not None:
                binding = redacted.revision_binding
                connection.execute(
                    """
                    INSERT INTO content_wordpress_draft_execution_history
                      (work_item_id, handoff_id, revision_id, revision_digest, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(work_item_id, handoff_id, revision_id, revision_digest)
                    DO UPDATE SET payload_json = excluded.payload_json
                    """,
                    (
                        work_item_id,
                        binding.handoff_id,
                        binding.revision_id,
                        binding.content_digest,
                        _model_json(redacted),
                    ),
                )
            else:
                # Preserve readable v1/history rows that predate exact bindings.
                connection.execute(
                    """
                    INSERT INTO content_wordpress_draft_executions (work_item_id, payload_json)
                    VALUES (?, ?)
                    ON CONFLICT(work_item_id) DO UPDATE SET payload_json = excluded.payload_json
                    """,
                    (work_item_id, _model_json(redacted)),
                )
        return redacted

    def latest_wordpress_draft_execution(
        self,
        work_item_id: str,
        *,
        handoff_id: str | None = None,
        revision_id: str | None = None,
        revision_digest: str | None = None,
    ) -> ContentWordPressDraftExecutionResult | None:
        binding_values = (handoff_id, revision_id, revision_digest)
        # A caller that starts an exact lookup must provide the complete
        # binding. Never fall back to a work-item-wide legacy execution for a
        # partially specified revision, since that could unlock measurement
        # for a different document.
        if any(value is not None for value in binding_values) and not all(
            value for value in binding_values
        ):
            return None
        with self._connect() as connection:
            if handoff_id and revision_id and revision_digest:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_wordpress_draft_execution_history
                    WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
                      AND revision_digest = ?
                    LIMIT 1
                    """,
                    (work_item_id, handoff_id, revision_id, revision_digest),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_wordpress_draft_executions
                    WHERE work_item_id = ?
                    LIMIT 1
                    """,
                    (work_item_id,),
                ).fetchone()
        if row is None:
            return None
        return ContentWordPressDraftExecutionResult.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )
