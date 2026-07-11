"""Read-only audit history projections used by the action service."""

from __future__ import annotations

from wilq.schemas import ActionMutationAuditRecord, AuditEvent
from wilq.storage.local_state import local_state_store

_MAX_EVENTS_PER_ACTION = 10


def persisted_audit_events_by_action_id(action_ids: set[str]) -> dict[str, list[AuditEvent]]:
    if not action_ids:
        return {}
    events_by_action_id: dict[str, list[AuditEvent]] = {action_id: [] for action_id in action_ids}
    for event in local_state_store().list_audit_events():
        if event.action_id not in action_ids:
            continue
        action_events = events_by_action_id.setdefault(event.action_id, [])
        if len(action_events) < _MAX_EVENTS_PER_ACTION:
            action_events.append(event)
    return events_by_action_id


def persisted_audit_events_for_action(action_id: str) -> list[AuditEvent]:
    return local_state_store().list_audit_events(action_id=action_id)[:_MAX_EVENTS_PER_ACTION]


def persisted_mutation_audits_by_action_id(
    action_ids: set[str],
) -> dict[str, list[ActionMutationAuditRecord]]:
    if not action_ids:
        return {}
    audits_by_action_id: dict[str, list[ActionMutationAuditRecord]] = {
        action_id: [] for action_id in action_ids
    }
    for audit in local_state_store().list_action_mutation_audits():
        if audit.action_id not in action_ids:
            continue
        action_audits = audits_by_action_id.setdefault(audit.action_id, [])
        if len(action_audits) < _MAX_EVENTS_PER_ACTION:
            action_audits.append(audit)
    return audits_by_action_id


def persisted_mutation_audits_for_action(
    action_id: str,
) -> list[ActionMutationAuditRecord]:
    return local_state_store().list_action_mutation_audits(action_id=action_id)[
        :_MAX_EVENTS_PER_ACTION
    ]
