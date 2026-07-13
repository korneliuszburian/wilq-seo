from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import suppress

from wilq.schemas import ActionMutationAuditRecord, ActionObject, ActionStatus, AuditEvent

AuditEventsByAction = Callable[[set[str]], dict[str, list[AuditEvent]]]
MutationAuditsByAction = Callable[[set[str]], dict[str, list[ActionMutationAuditRecord]]]
ReviewGateHydrator = Callable[
    [ActionObject, list[AuditEvent], list[ActionMutationAuditRecord]], ActionObject
]
ValidationStateLoader = Callable[[str], dict[str, object] | None]


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
