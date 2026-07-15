from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.audit_store import (
    build_human_review_audit_event,
    wordpress_draft_audit_details,
)
from wilq.schemas import (
    ActionObject,
    ActionReviewGate,
    ActionReviewRequest,
    ActionReviewResult,
    AuditEvent,
)


def record_action_review(
    action: ActionObject,
    request: ActionReviewRequest,
    *,
    review_summary: Callable[[ActionReviewRequest], str],
    review_details: Callable[[ActionReviewRequest], dict[str, Any]],
    review_gate: Callable[[ActionObject], ActionReviewGate],
    status_label: Callable[[str], str],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
    review_gate_labels: Callable[[ActionReviewGate], ActionReviewGate],
) -> ActionReviewResult:
    """Persist one human review event and recompute the typed review gate."""
    audit = build_human_review_audit_event(
        action=action,
        reviewed_by=request.reviewed_by,
        outcome=request.outcome,
        summary=review_summary(request),
        details=wordpress_draft_audit_details(
            request.wordpress_draft,
            details=review_details(request),
        ),
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = review_gate(action)
    return ActionReviewResult(
        action_id=action.id,
        status="recorded",
        status_label=status_label("recorded"),
        audit_event=audit_event_label(audit),
        review_gate=review_gate_labels(action.review_gate),
    )
