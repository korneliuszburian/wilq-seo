from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import uuid4

from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftExecutionResult
from wilq.content.quality.review import ContentQualityReview
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionConflict,
    ContentDraftRevisionReview,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionReviewResult,
    ContentDraftRevisionState,
    ContentDraftRevisionWriteResult,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import state_db_path


def content_workflow_store() -> ContentWorkflowStore:
    return ContentWorkflowStore(state_db_path())


class ContentWorkflowStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append_draft_revision(
        self,
        command: ContentDraftRevisionAppendCommand,
    ) -> ContentDraftRevisionWriteResult:
        redacted_command = ContentDraftRevisionAppendCommand.model_validate(
            redact_mapping(command.model_dump(mode="json"))
        )
        content_digest = _draft_revision_content_digest(redacted_command)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = _latest_draft_revision(connection, redacted_command.work_item_id)
            if latest is not None and (
                latest.base_revision_id == redacted_command.base_revision_id
                and latest.content_digest == content_digest
                and latest.created_by == redacted_command.created_by
            ):
                return ContentDraftRevisionWriteResult(
                    status="idempotent",
                    revision=latest,
                )

            current_revision_id = None if latest is None else latest.revision_id
            if redacted_command.base_revision_id != current_revision_id:
                return ContentDraftRevisionWriteResult(
                    status="conflict",
                    conflict=_draft_revision_conflict("stale_base", latest),
                )

            revision = ContentDraftRevision(
                revision_id=f"content_revision_{uuid4().hex}",
                work_item_id=redacted_command.work_item_id,
                revision_number=1 if latest is None else latest.revision_number + 1,
                base_revision_id=redacted_command.base_revision_id,
                content_digest=content_digest,
                draft_package_id=redacted_command.draft_package_id,
                draft_package_digest=redacted_command.draft_package_digest,
                final_canonical_url=redacted_command.final_canonical_url,
                title=redacted_command.title,
                sections=redacted_command.sections,
                created_by=redacted_command.created_by,
                created_at=utc_now(),
            )
            redacted_revision = ContentDraftRevision.model_validate(
                redact_mapping(revision.model_dump(mode="json"))
            )
            connection.execute(
                """
                INSERT INTO content_draft_revisions (
                  revision_id,
                  work_item_id,
                  revision_number,
                  base_revision_id,
                  content_digest,
                  created_at,
                  payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    redacted_revision.revision_id,
                    redacted_revision.work_item_id,
                    redacted_revision.revision_number,
                    redacted_revision.base_revision_id,
                    redacted_revision.content_digest,
                    redacted_revision.created_at.isoformat(),
                    _model_json(redacted_revision),
                ),
            )
        return ContentDraftRevisionWriteResult(
            status="created",
            revision=redacted_revision,
        )

    def review_draft_revision(
        self,
        command: ContentDraftRevisionReviewCommand,
    ) -> ContentDraftRevisionReviewResult:
        redacted_command = ContentDraftRevisionReviewCommand.model_validate(
            redact_mapping(command.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest_revision = _latest_draft_revision(connection, redacted_command.work_item_id)
            requested_revision = _draft_revision_by_id(
                connection,
                work_item_id=redacted_command.work_item_id,
                revision_id=redacted_command.revision_id,
            )
            if requested_revision is None:
                return ContentDraftRevisionReviewResult(
                    status="conflict",
                    conflict=_draft_revision_conflict(
                        "revision_not_found",
                        latest_revision,
                    ),
                )
            if (
                latest_revision is None
                or requested_revision.revision_id != latest_revision.revision_id
            ):
                return ContentDraftRevisionReviewResult(
                    status="conflict",
                    conflict=_draft_revision_conflict(
                        "stale_revision",
                        latest_revision,
                    ),
                )
            if redacted_command.revision_digest != requested_revision.content_digest:
                return ContentDraftRevisionReviewResult(
                    status="conflict",
                    conflict=_draft_revision_conflict(
                        "digest_mismatch",
                        latest_revision,
                    ),
                )

            latest_review = _latest_draft_revision_review(
                connection,
                requested_revision.revision_id,
            )
            if latest_review is not None and _review_matches_command(
                latest_review,
                redacted_command,
            ):
                return ContentDraftRevisionReviewResult(
                    status="idempotent",
                    review=latest_review,
                )
            current_decision_id = None if latest_review is None else latest_review.decision_id
            if redacted_command.base_decision_id != current_decision_id:
                return ContentDraftRevisionReviewResult(
                    status="conflict",
                    conflict=_draft_revision_conflict(
                        "stale_review",
                        latest_revision,
                    ),
                )

            review = ContentDraftRevisionReview(
                decision_id=f"content_revision_review_{uuid4().hex}",
                decision_number=(
                    1 if latest_review is None else latest_review.decision_number + 1
                ),
                work_item_id=redacted_command.work_item_id,
                revision_id=redacted_command.revision_id,
                revision_digest=redacted_command.revision_digest,
                decision=redacted_command.decision,
                reviewed_by=redacted_command.reviewed_by,
                notes=redacted_command.notes,
                checked_items=redacted_command.checked_items,
                evidence_ids=redacted_command.evidence_ids,
                created_at=utc_now(),
            )
            redacted_review = ContentDraftRevisionReview.model_validate(
                redact_mapping(review.model_dump(mode="json"))
            )
            connection.execute(
                """
                INSERT INTO content_draft_revision_reviews (
                  decision_id,
                  work_item_id,
                  revision_id,
                  decision_number,
                  revision_digest,
                  decision,
                  created_at,
                  payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    redacted_review.decision_id,
                    redacted_review.work_item_id,
                    redacted_review.revision_id,
                    redacted_review.decision_number,
                    redacted_review.revision_digest,
                    redacted_review.decision,
                    redacted_review.created_at.isoformat(),
                    _model_json(redacted_review),
                ),
            )
        return ContentDraftRevisionReviewResult(
            status="created",
            review=redacted_review,
        )

    def load_draft_revision_state(self, work_item_id: str) -> ContentDraftRevisionState:
        with self._connect() as connection:
            latest_revision = _latest_draft_revision(connection, work_item_id)
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM content_draft_revisions
                WHERE work_item_id = ?
                """,
                (work_item_id,),
            ).fetchone()
            revision_count = 0 if row is None else cast(int, row["count"])
            latest_review = (
                None
                if latest_revision is None
                else _latest_draft_revision_review(connection, latest_revision.revision_id)
            )
        if latest_revision is None:
            return ContentDraftRevisionState(status="empty", revision_count=0)
        return ContentDraftRevisionState(
            status="unreviewed" if latest_review is None else latest_review.decision,
            latest_revision=latest_revision,
            latest_review=latest_review,
            revision_count=revision_count,
        )

    def list_draft_revisions(self, work_item_id: str) -> list[ContentDraftRevision]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM content_draft_revisions
                WHERE work_item_id = ?
                ORDER BY revision_number ASC
                """,
                (work_item_id,),
            ).fetchall()
        return [
            ContentDraftRevision.model_validate(json.loads(cast(str, row["payload_json"])))
            for row in rows
        ]

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
            connection.execute(
                """
                INSERT INTO content_wordpress_draft_executions (work_item_id, payload_json)
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

    def latest_wordpress_draft_execution(
        self,
        work_item_id: str,
    ) -> ContentWordPressDraftExecutionResult | None:
        with self._connect() as connection:
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
            CREATE TABLE IF NOT EXISTS content_quality_reviews (
              review_id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_wordpress_draft_executions (
              work_item_id TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_draft_revisions (
              revision_id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
              base_revision_id TEXT,
              content_digest TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE (work_item_id, revision_number)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_draft_revision_reviews (
              decision_id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              revision_id TEXT NOT NULL,
              decision_number INTEGER NOT NULL CHECK (decision_number >= 1),
              revision_digest TEXT NOT NULL,
              decision TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE (revision_id, decision_number)
            )
            """
        )


def _model_json(
    model: (
        ContentHumanReview
        | ContentWordPressDraftAuditEnvelope
        | ContentQualityReview
        | ContentWordPressDraftExecutionResult
        | ContentDraftRevision
        | ContentDraftRevisionReview
    ),
) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _latest_draft_revision(
    connection: sqlite3.Connection,
    work_item_id: str,
) -> ContentDraftRevision | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM content_draft_revisions
        WHERE work_item_id = ?
        ORDER BY revision_number DESC
        LIMIT 1
        """,
        (work_item_id,),
    ).fetchone()
    if row is None:
        return None
    return ContentDraftRevision.model_validate(json.loads(cast(str, row["payload_json"])))


def _draft_revision_by_id(
    connection: sqlite3.Connection,
    *,
    work_item_id: str,
    revision_id: str,
) -> ContentDraftRevision | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM content_draft_revisions
        WHERE work_item_id = ? AND revision_id = ?
        LIMIT 1
        """,
        (work_item_id, revision_id),
    ).fetchone()
    if row is None:
        return None
    return ContentDraftRevision.model_validate(json.loads(cast(str, row["payload_json"])))


def _latest_draft_revision_review(
    connection: sqlite3.Connection,
    revision_id: str,
) -> ContentDraftRevisionReview | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM content_draft_revision_reviews
        WHERE revision_id = ?
        ORDER BY decision_number DESC
        LIMIT 1
        """,
        (revision_id,),
    ).fetchone()
    if row is None:
        return None
    return ContentDraftRevisionReview.model_validate(
        json.loads(cast(str, row["payload_json"]))
    )


def _draft_revision_content_digest(command: ContentDraftRevisionAppendCommand) -> str:
    payload = {
        "work_item_id": command.work_item_id,
        "draft_package_id": command.draft_package_id,
        "draft_package_digest": command.draft_package_digest,
        "final_canonical_url": command.final_canonical_url,
        "title": command.title,
        "sections": [section.model_dump(mode="json") for section in command.sections],
        "publish_ready": command.publish_ready,
    }
    canonical_json = json.dumps(
        redact_mapping(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def _draft_revision_conflict(
    code: str,
    latest: ContentDraftRevision | None,
) -> ContentDraftRevisionConflict:
    return ContentDraftRevisionConflict.model_validate(
        {
            "code": code,
            "current_revision_id": None if latest is None else latest.revision_id,
            "current_revision_digest": None if latest is None else latest.content_digest,
        }
    )


def _review_matches_command(
    review: ContentDraftRevisionReview,
    command: ContentDraftRevisionReviewCommand,
) -> bool:
    return (
        review.work_item_id == command.work_item_id
        and review.revision_id == command.revision_id
        and review.revision_digest == command.revision_digest
        and review.decision == command.decision
        and review.reviewed_by == command.reviewed_by
        and review.notes == command.notes
        and review.checked_items == command.checked_items
        and review.evidence_ids == command.evidence_ids
    )
