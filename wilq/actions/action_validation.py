from __future__ import annotations

from collections.abc import Callable

from wilq.actions.payloads import validate_action_payload
from wilq.connectors.registry import get_connector_status
from wilq.content.planning.generation_intent import PLANNING_GENERATION_INTENT_ACTION_TYPE
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
)
from wilq.content.workflow.current_page_disposition_v2 import (
    CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE,
)
from wilq.content.workflow.material_review_action_v2 import MATERIAL_REVIEW_ACTION_V2_TYPE
from wilq.content.workflow.research_packet_v2_action import RESEARCH_PACKET_V2_ACTION_TYPE
from wilq.content.workflow.research_packet_v3_action import RESEARCH_PACKET_V3_ACTION_TYPE
from wilq.content.workflow.research_promotion_authority import (
    CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
)
from wilq.content.workflow.source_fact_authority import SOURCE_FACT_AUTHORITY_ACTION_TYPE
from wilq.content.workflow.source_fact_authority_v2 import SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
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
    elif (
        action.mode == ActionMode.apply
        and not connector.configured
        and not _local_connector_configuration_not_required(action)
    ):
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


def _local_connector_configuration_not_required(action: ActionObject) -> bool:
    action_type = action.payload.get("action_type")
    return action_type in {
        CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
        SOURCE_FACT_AUTHORITY_ACTION_TYPE,
        SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE,
        CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
        MATERIAL_REVIEW_ACTION_V2_TYPE,
        RESEARCH_PACKET_V2_ACTION_TYPE,
        RESEARCH_PACKET_V3_ACTION_TYPE,
        PLANNING_GENERATION_INTENT_ACTION_TYPE,
        PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
    } or (
        action_type == CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    )
