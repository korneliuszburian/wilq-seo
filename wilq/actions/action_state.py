from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import suppress
from typing import Any

from wilq.schemas import (
    ActionMutationAuditRecord,
    ActionObject,
    ActionReviewGate,
    ActionStatus,
    AuditEvent,
)

AuditEventsByAction = Callable[[set[str]], dict[str, list[AuditEvent]]]
MutationAuditsByAction = Callable[[set[str]], dict[str, list[ActionMutationAuditRecord]]]
ReviewGateHydrator = Callable[
    [ActionObject, list[AuditEvent], list[ActionMutationAuditRecord]], ActionObject
]
ValidationStateLoader = Callable[[str], dict[str, object] | None]
PayloadReviewProjector = Callable[..., dict[str, Any]]
ActionReviewGateBuilder = Callable[..., ActionReviewGate]
ActionLabelProjector = Callable[[ActionObject], ActionObject]


def with_persisted_review_gates(
    actions: Iterable[ActionObject],
    *,
    audit_events_by_action: AuditEventsByAction,
    mutation_audits_by_action: MutationAuditsByAction,
    validation_state: Callable[[ActionObject], ActionObject],
    review_gate: ReviewGateHydrator,
) -> list[ActionObject]:
    action_list = list(actions)
    action_ids = {action.id for action in action_list}
    audit_events = audit_events_by_action(action_ids)
    mutation_audits = mutation_audits_by_action(action_ids)
    return [
        review_gate(
            validation_state(action),
            audit_events.get(action.id, []),
            mutation_audits.get(action.id, []),
        )
        for action in action_list
    ]


def with_persisted_validation_state(
    action: ActionObject,
    *,
    state_loader: ValidationStateLoader,
) -> ActionObject:
    state = state_loader(action.id)
    if state is None:
        return action
    validation_status = state.get("validation_status")
    status = state.get("status")
    if validation_status in {"valid", "invalid", "not_validated"}:
        action.validation_status = validation_status  # type: ignore[assignment]
    if isinstance(status, str):
        with suppress(ValueError):
            action.status = ActionStatus(status)
    return action


def with_review_gate(
    action: ActionObject,
    audit_events: list[AuditEvent] | None = None,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
    *,
    audit_event_has_raw_contract_text: Callable[[AuditEvent], bool],
    content_payload_with_reviewed_previews: PayloadReviewProjector,
    payload_with_operator_labels: PayloadReviewProjector,
    is_raw_content_review_audit_event: Callable[[str, AuditEvent], bool],
    action_review_gate: ActionReviewGateBuilder,
    action_with_operator_labels: ActionLabelProjector,
) -> ActionObject:
    if audit_events is not None:
        action.audit_events = audit_events[:10]
    state_audit_events = [
        event for event in action.audit_events if not audit_event_has_raw_contract_text(event)
    ]
    action.payload = content_payload_with_reviewed_previews(
        action.payload,
        review_event_summaries=(
            event.summary
            for event in state_audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
        review_event_details=(
            event.details
            for event in state_audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
    )
    action.payload = payload_with_operator_labels(action.payload)
    review_gate_events = [
        event
        for event in action.audit_events
        if not is_raw_content_review_audit_event(action.id, event)
    ]
    action.review_gate = action_review_gate(
        action.model_copy(update={"audit_events": review_gate_events}),
        mutation_audits,
    )
    return action_with_operator_labels(action)
