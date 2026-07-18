from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from typing import Any, cast

from pydantic import BaseModel

from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftExecutionResult
from wilq.content.measurement.learning import ContentLearningProposal
from wilq.content.measurement.outcome import ContentMeasurementOutcomeInterpretation
from wilq.content.measurement.window import ContentMeasurementWindow
from wilq.content.quality.review import ContentQualityReview
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.planning import ContentPlanningDecision
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionConflict,
    ContentDraftRevisionReview,
    ContentDraftRevisionReviewCommand,
)
from wilq.schemas.actions import ActionMutationAuditRecord, AuditEvent
from wilq.security.redaction import redact_mapping
from wilq.social.reuse import SocialReuseProposal, SocialReuseReview


def model_json(
    model: (
        ContentHumanReview
        | ContentWordPressDraftAuditEnvelope
        | ContentQualityReview
        | ContentWordPressDraftExecutionResult
        | ContentMeasurementWindow
        | ContentMeasurementOutcomeInterpretation
        | ContentLearningProposal
        | ContentDraftRevision
        | ContentDraftRevisionReview
        | ContentPlanningDecision
        | AuditEvent
        | ActionMutationAuditRecord
        | SocialReuseProposal
        | SocialReuseReview
    ),
) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def upsert_audit_event(connection: sqlite3.Connection, event: AuditEvent) -> None:
    redacted = AuditEvent.model_validate(redact_mapping(event.model_dump(mode="json")))
    connection.execute(
        """
        INSERT INTO audit_events (id, action_id, created_at, payload_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          action_id = excluded.action_id,
          created_at = excluded.created_at,
          payload_json = excluded.payload_json
        """,
        (redacted.id, redacted.action_id, redacted.created_at.isoformat(), model_json(redacted)),
    )


def upsert_action_mutation_audit(
    connection: sqlite3.Connection,
    record: ActionMutationAuditRecord,
) -> None:
    redacted = ActionMutationAuditRecord.model_validate(
        redact_mapping(record.model_dump(mode="json"))
    )
    connection.execute(
        """
        INSERT INTO action_mutation_audits (id, action_id, status, created_at, payload_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          action_id = excluded.action_id,
          status = excluded.status,
          created_at = excluded.created_at,
          payload_json = excluded.payload_json
        """,
        (
            redacted.id,
            redacted.action_id,
            redacted.status,
            redacted.created_at.isoformat(),
            model_json(redacted),
        ),
    )


def upsert_wordpress_draft_execution(
    connection: sqlite3.Connection,
    work_item_id: str,
    result: ContentWordPressDraftExecutionResult,
) -> None:
    redacted = ContentWordPressDraftExecutionResult.model_validate(
        redact_mapping(result.model_dump(mode="json"))
    )
    connection.execute(
        """
        INSERT INTO content_wordpress_draft_executions (work_item_id, payload_json)
        VALUES (?, ?)
        ON CONFLICT(work_item_id) DO UPDATE SET payload_json = excluded.payload_json
        """,
        (work_item_id, model_json(redacted)),
    )


def execution_result_from_adapter_result(
    adapter_result: dict[str, Any] | None,
) -> ContentWordPressDraftExecutionResult | None:
    if adapter_result is None:
        return None
    raw_result = adapter_result.get("execution_result")
    if not isinstance(raw_result, dict):
        return None
    return ContentWordPressDraftExecutionResult.model_validate(raw_result)


def latest_draft_revision(
    connection: sqlite3.Connection,
    work_item_id: str,
) -> ContentDraftRevision | None:
    row = connection.execute(
        """
        SELECT payload_json FROM content_draft_revisions
        WHERE work_item_id = ? ORDER BY revision_number DESC LIMIT 1
        """,
        (work_item_id,),
    ).fetchone()
    return _validated_payload(row, ContentDraftRevision)


def draft_revision_by_id(
    connection: sqlite3.Connection,
    *,
    work_item_id: str,
    revision_id: str,
) -> ContentDraftRevision | None:
    row = connection.execute(
        """
        SELECT payload_json FROM content_draft_revisions
        WHERE work_item_id = ? AND revision_id = ? LIMIT 1
        """,
        (work_item_id, revision_id),
    ).fetchone()
    return _validated_payload(row, ContentDraftRevision)


def latest_draft_revision_review(
    connection: sqlite3.Connection,
    revision_id: str,
) -> ContentDraftRevisionReview | None:
    row = connection.execute(
        """
        SELECT payload_json FROM content_draft_revision_reviews
        WHERE revision_id = ? ORDER BY decision_number DESC LIMIT 1
        """,
        (revision_id,),
    ).fetchone()
    return _validated_payload(row, ContentDraftRevisionReview)


def latest_planning_decision(
    connection: sqlite3.Connection,
    work_item_id: str,
    stage: str,
) -> ContentPlanningDecision | None:
    row = connection.execute(
        """
        SELECT payload_json FROM content_planning_reviews
        WHERE work_item_id = ? AND stage = ? ORDER BY decision_number DESC LIMIT 1
        """,
        (work_item_id, stage),
    ).fetchone()
    return _validated_payload(row, ContentPlanningDecision)


def wordpress_revision_apply_claim_key(binding: ContentDraftRevisionBinding) -> str:
    canonical_json = json.dumps(
        binding.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def binding_is_current_and_approved(
    binding: ContentDraftRevisionBinding,
    *,
    latest_revision: ContentDraftRevision | None,
    latest_review: ContentDraftRevisionReview | None,
) -> bool:
    return bool(
        latest_revision is not None
        and latest_review is not None
        and latest_review.decision == "approved"
        and latest_revision.work_item_id == binding.work_item_id
        and latest_revision.revision_id == binding.revision_id
        and binding.handoff_id
        == f"wordpress_draft_handoff_{latest_revision.work_item_id}_{latest_revision.revision_id}"
        and latest_revision.content_digest == binding.content_digest
        and latest_revision.draft_package_id == binding.draft_package_id
        and latest_revision.draft_package_digest == binding.draft_package_digest
        and latest_revision.planning_digest == binding.planning_digest
        and latest_revision.final_canonical_url == binding.final_canonical_url
        and latest_review.work_item_id == binding.work_item_id
        and latest_review.revision_id == binding.revision_id
        and latest_review.revision_digest == binding.content_digest
        and latest_review.decision_id == binding.approval_decision_id
    )


def wordpress_revision_apply_in_progress(
    connection: sqlite3.Connection,
    work_item_id: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1 FROM content_wordpress_revision_apply_claims
        WHERE work_item_id = ? AND status = 'claimed' LIMIT 1
        """,
        (work_item_id,),
    ).fetchone()
    return row is not None


def draft_revision_conflict(
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


def review_matches_command(
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


def _validated_payload[ModelT: BaseModel](
    row: sqlite3.Row | None,
    model: type[ModelT],
) -> ModelT | None:
    if row is None:
        return None
    return model.model_validate(json.loads(cast(str, row["payload_json"])))
