from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.action_blockers import action_apply_preflight_blockers
from wilq.actions.audit_store import (
    action_mutation_audit_record,
    build_apply_audit_event,
    latest_action_confirmation_event,
    latest_action_impact_check_event,
    latest_preview_event,
)
from wilq.actions.mutation_contract import supported_mutation_adapter
from wilq.actions.payload_readiness import (
    payload_api_mutation_ready,
    payload_apply_allowed,
    payload_preview_items,
)
from wilq.actions.wordpress_mutation_requirements import (
    execute_supported_wordpress_mutation_adapter,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionObject,
    ActionReviewGate,
    ActionStatus,
    AuditEvent,
)


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    wordpress_apply_capability: Callable[..., tuple[Any, list[str]]],
    connector_status: Callable[[str], Any],
    impact_status: Callable[[Any], str | None],
    status_label: Callable[[str], str],
    audit_event_label: Callable[[AuditEvent], AuditEvent],
) -> ActionApplyResult:
    """Run the canonical fail-closed apply lifecycle and preserve mutation audit."""
    errors: list[str] = []

    def action_payload_apply_allowed(payload: dict[str, Any]) -> bool:
        return payload_apply_allowed(payload, payload_preview_items(payload))

    def action_payload_api_mutation_ready(payload: dict[str, Any]) -> bool:
        return payload_api_mutation_ready(payload, payload_preview_items(payload))
    wordpress_capability, capability_errors = wordpress_apply_capability(action, request)
    errors.extend(capability_errors)
    connector = connector_status(action.connector)
    preview = latest_preview_event(action.audit_events)
    confirmation = latest_action_confirmation_event(action.audit_events)
    impact_check = latest_action_impact_check_event(action.audit_events)
    mutation_adapter = supported_mutation_adapter(action)
    errors.extend(
        action_apply_preflight_blockers(
            action=action,
            request=request,
            connector_configured=connector is not None and connector.configured,
            preview_present=preview is not None,
            confirmation_present=confirmation is not None,
            impact_checked=impact_status(impact_check) == "checked",
            mutation_adapter=mutation_adapter,
            wordpress_capability_present=wordpress_capability is not None,
            payload_apply_allowed=action_payload_apply_allowed,
            payload_api_mutation_ready=action_payload_api_mutation_ready,
        )
    )
    adapter_result: dict[str, Any] | None = None
    if not errors and mutation_adapter is not None:
        adapter_result, adapter_errors = execute_supported_wordpress_mutation_adapter(
            action,
            mutation_adapter,
            wordpress_capability,
        )
        errors.extend(adapter_errors)

    actor = request.confirmed_by if request and request.confirmed_by else "wilq_api"
    audit = build_apply_audit_event(
        action=action,
        audit_id=f"audit_{action.id}_{len(action.audit_events) + 1}",
        actor=actor,
        errors=errors,
    )
    mutation_audit = action_mutation_audit_record(
        action=action,
        audit_event=audit,
        actor=actor,
        errors=errors,
        mutation_adapter=mutation_adapter,
        adapter_result=adapter_result,
    )
    action.audit_events.append(audit)
    if errors:
        action.status = ActionStatus.blocked
        action.review_gate = review_gate(action)
        return ActionApplyResult(
            action_id=action.id,
            applied=False,
            status="blocked",
            status_label=status_label("blocked"),
            audit_event=audit_event_label(audit),
            mutation_audit=mutation_audit,
            errors=errors,
            adapter_result=adapter_result,
        )
    action.status = ActionStatus.applied
    action.review_gate = review_gate(action)
    return ActionApplyResult(
        action_id=action.id,
        applied=True,
        status="applied",
        status_label=status_label("applied"),
        audit_event=audit_event_label(audit),
        mutation_audit=mutation_audit,
        adapter_result=adapter_result,
    )
