from __future__ import annotations

from collections.abc import Callable

from wilq.actions.payloads import validate_action_payload
from wilq.connectors.registry import get_connector_status
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionReviewGate,
    ActionRisk,
    ActionStatus,
    ActionValidationResult,
)
from wilq.storage.local_state import local_state_store


def validate_action(
    action: ActionObject,
    *,
    review_gate: Callable[[ActionObject], ActionReviewGate],
    status_label: Callable[[str], str],
) -> ActionValidationResult:
    """Validate evidence, connector readiness and payload before lifecycle review."""
    errors: list[str] = []
    warnings: list[str] = []
    connector = get_connector_status(action.connector)
    if not action.evidence_ids:
        errors.append("Akcja wymaga co najmniej jednego dowodu źródłowego.")
    if connector is None:
        errors.append(f"Nieznany łącznik danych: {action.connector}")
    elif action.mode == ActionMode.apply and not connector.configured:
        errors.append(f"Łącznik danych {action.connector} nie jest skonfigurowany.")
    errors.extend(validate_action_payload(action.connector, action.payload))
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        warnings.append("Akcje o wysokim i krytycznym ryzyku wymagają osobnego wsparcia produktu.")
    valid = not errors
    action.validation_status = "valid" if valid else "invalid"
    if not valid:
        action.status = ActionStatus.validation_failed
    elif action.mode == ActionMode.apply:
        action.status = ActionStatus.ready_to_apply
    else:
        action.status = ActionStatus.ready
    action.review_gate = review_gate(action)
    local_state_store().save_action_validation_state(
        action_id=action.id,
        status=action.status.value,
        validation_status=action.validation_status,
    )
    return ActionValidationResult(
        action_id=action.id,
        valid=valid,
        status="valid" if valid else "invalid",
        status_label=status_label("valid" if valid else "invalid"),
        errors=errors,
        warnings=warnings,
    )
