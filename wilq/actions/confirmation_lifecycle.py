from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import (
    ActionConfirmRequest,
    ActionConfirmResult,
    ActionObject,
    ActionReviewGate,
    AuditEvent,
)


def confirm_action(
    action: ActionObject,
    request: ActionConfirmRequest,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    latest_preview: Callable[[list[AuditEvent]], AuditEvent | None],
    confirmation_blockers: Callable[..., list[str]],
    confirmation_event_type: Callable[[ActionObject, bool], str],
    confirmation_summary: Callable[..., str],
    ads_target_blockers: Callable[[ActionConfirmRequest], list[str]],
    ads_target_summary: Callable[..., str],
    gate_labels: Callable[[list[str]], list[str]],
    money_label: Callable[[Any], str],
    operator_note: Callable[[str], str],
    build_confirmation_audit: Callable[..., AuditEvent],
    status_label: Callable[[str], str],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
    review_gate_labels: Callable[[ActionReviewGate], ActionReviewGate],
) -> ActionConfirmResult:
    """Record confirmation only after preview blockers and audit context are checked."""
    action.review_gate = review_gate(action)
    latest = latest_preview(action.audit_events)
    blockers = confirmation_blockers(
        action,
        request,
        latest,
        ads_target_blockers=ads_target_blockers,
    )
    confirmed = not blockers
    event_type = confirmation_event_type(action, confirmed)
    audit = build_confirmation_audit(
        action=action,
        actor=request.confirmed_by,
        event_type=event_type,
        wordpress_draft_binding=request.wordpress_draft,
        summary=confirmation_summary(
            action,
            request,
            blockers,
            latest,
            ads_target_summary=(
                lambda target_request, target_blockers: ads_target_summary(
                    target_request,
                    target_blockers,
                    gate_labels=gate_labels,
                    micros_money_label=money_label,
                )
            ),
            gate_labels=gate_labels,
            operator_note=operator_note,
        ),
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = review_gate(action)
    return ActionConfirmResult(
        action_id=action.id,
        confirmed=confirmed,
        status="confirmed" if confirmed else "blocked",
        status_label=status_label("confirmed" if confirmed else "blocked"),
        blockers=blockers,
        blocker_labels=gate_labels(blockers),
        audit_event=audit_event_label(audit),
        review_gate=review_gate_labels(action.review_gate),
    )
