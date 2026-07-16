from __future__ import annotations

import sqlite3
from uuid import uuid4

from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionReviewResult,
)
from wilq.content.workflow.store_queries import (
    draft_revision_by_id,
    draft_revision_conflict,
    latest_draft_revision,
    latest_draft_revision_review,
    model_json,
    review_matches_command,
    wordpress_revision_apply_in_progress,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping


def record_draft_revision_review(
    connection: sqlite3.Connection,
    command: ContentDraftRevisionReviewCommand,
) -> ContentDraftRevisionReviewResult:
    latest_revision, requested_revision, conflict = _review_target(connection, command)
    if conflict is not None or requested_revision is None:
        if conflict is None:
            raise RuntimeError("Draft revision review preflight lost its typed conflict.")
        return conflict
    latest_review = latest_draft_revision_review(connection, requested_revision.revision_id)
    if latest_review is not None and review_matches_command(latest_review, command):
        return ContentDraftRevisionReviewResult(status="idempotent", review=latest_review)
    current_decision_id = None if latest_review is None else latest_review.decision_id
    if command.base_decision_id != current_decision_id:
        return _conflict("stale_review", latest_revision)
    review = _new_review(command, latest_review)
    _insert_review(connection, review)
    return ContentDraftRevisionReviewResult(status="created", review=review)


def _review_target(
    connection: sqlite3.Connection,
    command: ContentDraftRevisionReviewCommand,
) -> tuple[
    ContentDraftRevision | None,
    ContentDraftRevision | None,
    ContentDraftRevisionReviewResult | None,
]:
    latest_revision = latest_draft_revision(connection, command.work_item_id)
    if wordpress_revision_apply_in_progress(connection, command.work_item_id):
        return latest_revision, None, _conflict("apply_in_progress", latest_revision)
    requested_revision = draft_revision_by_id(
        connection,
        work_item_id=command.work_item_id,
        revision_id=command.revision_id,
    )
    if requested_revision is None:
        return latest_revision, None, _conflict("revision_not_found", latest_revision)
    if latest_revision is None or requested_revision.revision_id != latest_revision.revision_id:
        return latest_revision, requested_revision, _conflict("stale_revision", latest_revision)
    if command.revision_digest != requested_revision.content_digest:
        return latest_revision, requested_revision, _conflict("digest_mismatch", latest_revision)
    return latest_revision, requested_revision, None


def _new_review(
    command: ContentDraftRevisionReviewCommand,
    latest_review: ContentDraftRevisionReview | None,
) -> ContentDraftRevisionReview:
    review = ContentDraftRevisionReview(
        decision_id=f"content_revision_review_{uuid4().hex}",
        decision_number=1 if latest_review is None else latest_review.decision_number + 1,
        work_item_id=command.work_item_id,
        revision_id=command.revision_id,
        revision_digest=command.revision_digest,
        decision=command.decision,
        reviewed_by=command.reviewed_by,
        notes=command.notes,
        checked_items=command.checked_items,
        evidence_ids=command.evidence_ids,
        created_at=utc_now(),
    )
    return ContentDraftRevisionReview.model_validate(redact_mapping(review.model_dump(mode="json")))


def _insert_review(connection: sqlite3.Connection, review: ContentDraftRevisionReview) -> None:
    connection.execute(
        """
        INSERT INTO content_draft_revision_reviews (
          decision_id, work_item_id, revision_id, decision_number,
          revision_digest, decision, created_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review.decision_id,
            review.work_item_id,
            review.revision_id,
            review.decision_number,
            review.revision_digest,
            review.decision,
            review.created_at.isoformat(),
            model_json(review),
        ),
    )


def _conflict(
    code: str,
    latest_revision: ContentDraftRevision | None,
) -> ContentDraftRevisionReviewResult:
    return ContentDraftRevisionReviewResult(
        status="conflict",
        conflict=draft_revision_conflict(code, latest_revision),
    )
