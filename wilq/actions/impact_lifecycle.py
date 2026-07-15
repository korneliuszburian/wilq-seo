from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from wilq.actions.action_blockers import action_impact_check_blockers, action_impact_check_summary
from wilq.actions.audit_store import build_impact_check_audit_event
from wilq.actions.metric_utils import unique_values
from wilq.schemas import (
    ActionImpactCheckRequest,
    ActionImpactCheckResult,
    ActionObject,
    ActionReviewGate,
    AuditEvent,
)


def impact_check_action(
    action: ActionObject,
    request: ActionImpactCheckRequest,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    latest_confirmation: Callable[[list[AuditEvent]], AuditEvent | None],
    status_label: Callable[[str], str],
    connector_labels: Callable[[list[str]], list[str]],
    gate_labels: Callable[[list[str]], list[str]],
    evidence_summary_label: Callable[[list[str]], str],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
    review_gate_labels: Callable[[ActionReviewGate], ActionReviewGate],
) -> ActionImpactCheckResult:
    """Classify the measurement window without implying a success claim or mutation."""
    action.review_gate = review_gate(action)
    confirmation = latest_confirmation(action.audit_events)
    blockers = action_impact_check_blockers(action, confirmation)
    status: Literal["checked", "blocked"] = "blocked" if blockers else "checked"
    evidence_ids = unique_values(
        [*action.evidence_ids, *(fact.evidence_id for fact in action.metrics)]
    )
    source_connectors = unique_values(
        [fact.source_connector for fact in action.metrics if fact.source_connector]
    )
    if not source_connectors:
        source_connectors = [action.connector]
    event_type = (
        "action_impact_check_completed"
        if status == "checked"
        else "action_impact_check_blocked"
    )
    audit = build_impact_check_audit_event(
        action=action,
        actor=request.checked_by,
        event_type=event_type,
        summary=action_impact_check_summary(
            request=request,
            status=status,
            metric_fact_count=len(action.metrics),
            source_connectors=source_connectors,
            blockers=blockers,
            status_label=status_label,
            connector_labels=connector_labels,
            gate_labels=gate_labels,
        ),
        evidence_ids=evidence_ids,
        wordpress_draft_binding=request.wordpress_draft,
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = review_gate(action)
    return ActionImpactCheckResult(
        action_id=action.id,
        status=status,
        status_label=status_label(status),
        pre_window_days=request.pre_window_days,
        post_window_days=request.post_window_days,
        metric_fact_count=len(action.metrics),
        source_connectors=source_connectors,
        source_connector_labels=connector_labels(source_connectors),
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_summary_label(evidence_ids),
        blockers=blockers,
        blocker_labels=gate_labels(blockers),
        audit_event=audit_event_label(audit),
        review_gate=review_gate_labels(action.review_gate),
    )
