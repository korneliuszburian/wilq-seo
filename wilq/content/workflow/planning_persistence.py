from __future__ import annotations

import json
import sqlite3
from typing import Literal, cast
from uuid import uuid4

from wilq.content.workflow.planning import (
    ContentPlanningDecision,
    ContentPlanningReviewRequest,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping


def record_content_planning_review(
    connection: sqlite3.Connection,
    *,
    work_item_id: str,
    request: ContentPlanningReviewRequest,
    planning_digest: str,
    service_card_id: str | None,
    human_override_review_required: bool,
) -> tuple[Literal["created", "idempotent"], ContentPlanningDecision]:
    redacted = ContentPlanningReviewRequest.model_validate(
        redact_mapping(request.model_dump(mode="json"))
    )
    connection.execute("BEGIN IMMEDIATE")
    latest = _latest_planning_decision(connection, work_item_id, redacted.stage)
    if latest is not None and all(
        (
            latest.planning_digest == planning_digest,
            latest.service_card_id == service_card_id,
            latest.human_override_review_required
            == human_override_review_required,
            latest.decision == redacted.decision,
            latest.reviewed_by == redacted.reviewed_by,
            latest.checked_items == redacted.checked_items,
            latest.notes == redacted.notes,
        )
    ):
        return "idempotent", latest
    decision = ContentPlanningDecision(
        decision_id=f"content_planning_review_{uuid4().hex}",
        decision_number=1 if latest is None else latest.decision_number + 1,
        work_item_id=work_item_id,
        stage=redacted.stage,
        planning_digest=planning_digest,
        service_card_id=service_card_id,
        human_override_review_required=human_override_review_required,
        decision=redacted.decision,
        reviewed_by=redacted.reviewed_by,
        checked_items=redacted.checked_items,
        notes=redacted.notes,
        created_at=utc_now(),
    )
    safe = ContentPlanningDecision.model_validate(
        redact_mapping(decision.model_dump(mode="json"))
    )
    connection.execute(
        """
        INSERT INTO content_planning_reviews (
          decision_id, work_item_id, stage, decision_number,
          planning_digest, decision, created_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            safe.decision_id,
            safe.work_item_id,
            safe.stage,
            safe.decision_number,
            safe.planning_digest,
            safe.decision,
            safe.created_at.isoformat(),
            safe.model_dump_json(),
        ),
    )
    return "created", safe


def _latest_planning_decision(
    connection: sqlite3.Connection,
    work_item_id: str,
    stage: str,
) -> ContentPlanningDecision | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM content_planning_reviews
        WHERE work_item_id = ? AND stage = ?
        ORDER BY decision_number DESC
        LIMIT 1
        """,
        (work_item_id, stage),
    ).fetchone()
    if row is None:
        return None
    return ContentPlanningDecision.model_validate(
        json.loads(cast(str, row["payload_json"]))
    )
