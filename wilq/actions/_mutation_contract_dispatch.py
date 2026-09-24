"""Pure ActionObject mutation-contract builders and dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from wilq.content.planning.generation_intent import PLANNING_GENERATION_INTENT_ACTION_TYPE
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
)
from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_ACTION_TYPE,
)
from wilq.content.workflow.current_page_disposition_v2 import (
    CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE,
)
from wilq.content.workflow.delivery_identity_authority import (
    DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE,
    DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
)
from wilq.content.workflow.material_review_action_v2 import MATERIAL_REVIEW_ACTION_V2_TYPE
from wilq.content.workflow.research_packet_v2_action import RESEARCH_PACKET_V2_ACTION_TYPE
from wilq.content.workflow.research_packet_v3_action import RESEARCH_PACKET_V3_ACTION_TYPE
from wilq.content.workflow.research_promotion_authority import (
    CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
)
from wilq.content.workflow.source_fact_authority import SOURCE_FACT_AUTHORITY_ACTION_TYPE
from wilq.content.workflow.source_fact_authority_v2 import (
    SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE,
    SOURCE_FACT_AUTHORITY_V2_PREVIEW_CONTRACT,
)
from wilq.content.workflow.target.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE
from wilq.content.workflow.target.dev_draft_discard_action import (
    CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT,
    CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.schemas import ActionMutationApplyContract, ActionObject


@dataclass(frozen=True)
class _LocalContractSpec:
    operation: str
    input_contract: str
    blocked_outputs: tuple[str, ...]
    summary: str


_LOCAL_CONTRACTS = {
    PLANNING_GENERATION_INTENT_ACTION_TYPE: _LocalContractSpec(
        "authorize_one_deferred_planning_generation",
        "wilq_planning_generation_intent_snapshot_v2|approved_research_packet_v2|apply_audit_before_dispatch",
        (
            "vendor_write",
            "wordpress_publish",
            "wordpress_draft",
            "pre_audit_model_enqueue",
            "unbound_content_generation",
        ),
        "Apply zapisuje lokalny zamiar bez modelu; po trwałym audycie wolno raz zlecić "
        "plan dla dokładnego zatwierdzonego pakietu v2. Vendor pozostaje zablokowany.",
    ),
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE: _LocalContractSpec(
        "record_one_v3_planning_generation_intent",
        "wilq_planning_generation_intent_snapshot_v3|approved_research_packet_v3|local_receipt_only",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Apply zapisuje wyłącznie lokalny receipt zamiaru z dokładnego zatwierdzonego "
        "pakietu v3; nie uruchamia modelu ani WordPressa.",
    ),
    DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE: _LocalContractSpec(
        "record_content_delivery_identity_binding",
        f"delivery_identity_authority_snapshot_v1|{DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT}",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny exact identity binding z dwóch receiptów; "
        "nie wywołuje vendora ani nie tworzy treści.",
    ),
    CURRENT_DISPOSITION_ACTION_TYPE: _LocalContractSpec(
        "record_current_disposition_receipt",
        "current_disposition_snapshot_v1",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny receipt bieżącej disposition exact URL-a; "
        "nie wywołuje vendora ani nie tworzy treści.",
    ),
    CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE: _LocalContractSpec(
        "record_current_page_disposition_v2_receipt",
        "wilq_current_page_disposition_snapshot_v2",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny receipt KEEP dla exact bieżącego materiału; "
        "nie wywołuje vendora ani nie tworzy treści.",
    ),
    MATERIAL_REVIEW_ACTION_V2_TYPE: _LocalContractSpec(
        "record_approved_current_material_review",
        "wilq_content_material_review_preview_v1|reviewed_full_material",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny receipt review dokładnego bieżącego materiału; "
        "nie wywołuje vendora ani nie generuje treści.",
    ),
    RESEARCH_PACKET_V2_ACTION_TYPE: _LocalContractSpec(
        "approve_exact_research_packet_v2",
        "wilq_research_packet_v2_preview_record_v1|reviewed_full_packet",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny receipt przeglądu dokładnego pakietu; "
        "nie generuje treści ani nie wywołuje vendora.",
    ),
    RESEARCH_PACKET_V3_ACTION_TYPE: _LocalContractSpec(
        "approve_exact_research_packet_v3",
        "wilq_research_packet_v3_preview_record_v1|reviewed_full_packet",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny receipt dokładnego pakietu v3; "
        "nie generuje treści ani nie wywołuje vendora.",
    ),
    SOURCE_FACT_AUTHORITY_ACTION_TYPE: _LocalContractSpec(
        "record_source_fact_authority_receipt",
        "content_source_fact_authority_preview_v1",
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje wyłącznie lokalny receipt doboru źródeł dla exact "
        "work itemu; nie wywołuje vendora, nie tworzy szkicu ani nie publikuje.",
    ),
    SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE: _LocalContractSpec(
        "record_source_fact_authority_v2_receipt",
        SOURCE_FACT_AUTHORITY_V2_PREVIEW_CONTRACT,
        ("vendor_write", "wordpress_publish", "wordpress_draft", "content_generation"),
        "Ta akcja zapisuje lokalny receipt exact źródeł dla bieżącego v2 KEEP; "
        "nie wywołuje vendora ani nie tworzy treści.",
    ),
    CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE: _LocalContractSpec(
        "record_research_fact_promotion_receipt",
        "content_research_fact_promotion_snapshot_v1",
        ("vendor_write", "content_generation", "draft"),
        "Ta akcja zapisuje wyłącznie lokalny source-fact promotion receipt.",
    ),
}


def _action_type(action: ActionObject) -> str:
    value = action.payload.get("action_type")
    return value if isinstance(value, str) else ""


def _contract(
    action: ActionObject,
    mutation_adapter: str | None,
    *,
    spec: _LocalContractSpec,
) -> ActionMutationApplyContract:
    return ActionMutationApplyContract(
        action_id=action.id,
        action_type=_action_type(action),
        connector=action.connector,
        allowed_operation=spec.operation,
        draft_only=False,
        publication_allowed=False,
        destructive_allowed=False,
        adapter_status="implemented" if mutation_adapter is not None else "not_implemented",
        required_env_flags=[],
        required_input_contracts=spec.input_contract.split("|"),
        required_audit_events=[
            "action_preview_generated",
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        ],
        blocked_outputs=list(spec.blocked_outputs),
        operator_summary=spec.summary,
    )


def _draft_contract(
    action: ActionObject, mutation_adapter: str | None
) -> ActionMutationApplyContract:
    action_type = _action_type(action)
    contract_key = (
        "content_new_page_dev_draft_action_v1"
        if action_type == CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE
        else "content_dev_draft_action_v1"
    )
    return ActionMutationApplyContract(
        action_id=action.id,
        action_type=action_type,
        connector=action.connector,
        allowed_operation="create_wordpress_draft",
        draft_only=True,
        publication_allowed=False,
        destructive_allowed=False,
        adapter_status="implemented" if mutation_adapter is not None else "not_implemented",
        required_env_flags=["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        required_input_contracts=[contract_key],
        required_audit_events=[
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
            "action_impact_check_completed",
        ],
        blocked_outputs=[
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_write",
            "bulk_delivery",
        ],
        operator_summary=(
            "Ta akcja może utworzyć wyłącznie jeden nowy szkic na dev z "
            "potwierdzonej, exact rewizji. Nie publikuje ani nie zmienia istniejącego obiektu."
        ),
    )


def _discard_contract(
    action: ActionObject, mutation_adapter: str | None
) -> ActionMutationApplyContract:
    return ActionMutationApplyContract(
        action_id=action.id,
        action_type=_action_type(action),
        connector=action.connector,
        allowed_operation="trash_wordpress_dev_draft",
        draft_only=True,
        publication_allowed=False,
        destructive_allowed=False,
        adapter_status="implemented" if mutation_adapter is not None else "not_implemented",
        required_env_flags=["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        required_input_contracts=[CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT],
        required_audit_events=[
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
            "action_impact_check_completed",
        ],
        blocked_outputs=[
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_force_delete_post",
            "production_write",
        ],
        operator_summary=(
            "Ta akcja przenosi wyłącznie jeden niezmieniony szkic dev do kosza. "
            "Nie publikuje, nie aktualizuje ani nie usuwa obiektu trwale."
        ),
    )


def _handoff_contract(
    action: ActionObject, mutation_adapter: str | None
) -> ActionMutationApplyContract:
    required = [
        value
        for value in action.payload.get("required_input_contracts", [])
        if isinstance(value, str)
    ]
    action_type = action.payload.get("action_type")
    return ActionMutationApplyContract(
        action_id=action.id,
        action_type=action_type if isinstance(action_type, str) else "wordpress_draft_handoff",
        connector=action.connector,
        allowed_operation="create_wordpress_draft",
        draft_only=True,
        publication_allowed=False,
        destructive_allowed=False,
        adapter_status="implemented" if mutation_adapter is not None else "not_implemented",
        required_env_flags=["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        required_input_contracts=required,
        required_audit_events=[
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
        ],
        blocked_outputs=[
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_publish_ready_claim",
        ],
        operator_summary=(
            "Ten kontrakt może w przyszłości zapisać wyłącznie szkic WordPress. "
            "Nie wolno publikować, aktualizować istniejącego wpisu ani omijać "
            "preview, review, confirm i audytu ActionObject."
        ),
    )


def mutation_apply_contract(
    action: ActionObject,
    mutation_adapter: str | None,
) -> ActionMutationApplyContract | None:
    action_type = action.payload.get("action_type")
    spec = _LOCAL_CONTRACTS.get(action_type) if isinstance(action_type, str) else None
    if spec is not None:
        return _contract(action, mutation_adapter, spec=spec)
    if action_type == CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE:
        return _discard_contract(action, mutation_adapter)
    if action_type in {CONTENT_DEV_DRAFT_ACTION_TYPE, CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE}:
        return _draft_contract(action, mutation_adapter)
    if action.id in {"act_apply_wordpress_draft_handoff", "act_prepare_wordpress_draft_handoff"}:
        return _handoff_contract(action, mutation_adapter)
    return None


__all__ = ["mutation_apply_contract"]
