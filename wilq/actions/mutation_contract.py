from __future__ import annotations

from wilq.actions._mutation_contract_dispatch import (
    mutation_apply_contract as _mutation_apply_contract,
)
from wilq.content.planning.generation_intent import (
    PLANNING_GENERATION_INTENT_ACTION_TYPE,
    PLANNING_GENERATION_INTENT_ADAPTER,
)
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
    PLANNING_GENERATION_INTENT_V3_ADAPTER,
)
from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_ACTION_TYPE,
    CURRENT_DISPOSITION_MUTATION_ADAPTER,
)
from wilq.content.workflow.current_page_disposition_v2 import (
    CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE,
)
from wilq.content.workflow.delivery_identity_authority import (
    DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE,
    DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER,
)
from wilq.content.workflow.delivery_identity_recovery import (
    CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE,
    CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER,
)
from wilq.content.workflow.material_review_action_v2 import (
    MATERIAL_REVIEW_ACTION_V2_ADAPTER,
    MATERIAL_REVIEW_ACTION_V2_TYPE,
)
from wilq.content.workflow.per_url_delivery_identity_authority import (
    PER_URL_DELIVERY_IDENTITY_ACTION_TYPE,
    PER_URL_DELIVERY_IDENTITY_MUTATION_ADAPTER,
)
from wilq.content.workflow.per_url_disposition_authority import (
    PER_URL_DISPOSITION_ACTION_TYPE,
    PER_URL_DISPOSITION_MUTATION_ADAPTER,
)
from wilq.content.workflow.research_packet_v2_action import (
    RESEARCH_PACKET_V2_ACTION_ADAPTER,
    RESEARCH_PACKET_V2_ACTION_TYPE,
)
from wilq.content.workflow.research_packet_v3_action import (
    RESEARCH_PACKET_V3_ACTION_ADAPTER,
    RESEARCH_PACKET_V3_ACTION_TYPE,
)
from wilq.content.workflow.research_promotion_authority import (
    CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
    CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER,
)
from wilq.content.workflow.source_fact_authority import (
    SOURCE_FACT_AUTHORITY_ACTION_TYPE,
    SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER,
)
from wilq.content.workflow.source_fact_authority_v2 import SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE
from wilq.content.workflow.target.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE
from wilq.content.workflow.target.dev_draft_discard_action import (
    CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE,
)
from wilq.content.workflow.target.dev_draft_execution import CONTENT_DEV_DRAFT_MUTATION_ADAPTER
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_draft_executor import (
    CONTENT_NEW_PAGE_DRAFT_MUTATION_ADAPTER,
)
from wilq.schemas import ActionMutationApplyContract, ActionObject

_PLANNING_GENERATION_INTENT_ADAPTERS = {
    PLANNING_GENERATION_INTENT_ACTION_TYPE: PLANNING_GENERATION_INTENT_ADAPTER,
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE: PLANNING_GENERATION_INTENT_V3_ADAPTER,
}
_LOCAL_DISPOSITION_ADAPTERS = {
    CURRENT_DISPOSITION_ACTION_TYPE: CURRENT_DISPOSITION_MUTATION_ADAPTER,
    CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE: CURRENT_DISPOSITION_MUTATION_ADAPTER,
    PER_URL_DISPOSITION_ACTION_TYPE: PER_URL_DISPOSITION_MUTATION_ADAPTER,
    PER_URL_DELIVERY_IDENTITY_ACTION_TYPE: PER_URL_DELIVERY_IDENTITY_MUTATION_ADAPTER,
}


def mutation_apply_contract(
    action: ActionObject,
    mutation_adapter: str | None,
) -> ActionMutationApplyContract | None:
    return _mutation_apply_contract(action, mutation_adapter)


def supported_mutation_adapter(action: ActionObject) -> str | None:
    action_type = action.payload.get("action_type")
    if (
        action_type
        in (PLANNING_GENERATION_INTENT_ACTION_TYPE, PLANNING_GENERATION_INTENT_V3_ACTION_TYPE)
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return _PLANNING_GENERATION_INTENT_ADAPTERS[action_type]
    if (
        action.payload.get("action_type")
        in {RESEARCH_PACKET_V2_ACTION_TYPE, RESEARCH_PACKET_V3_ACTION_TYPE}
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return (
            RESEARCH_PACKET_V2_ACTION_ADAPTER
            if action.payload.get("action_type") == RESEARCH_PACKET_V2_ACTION_TYPE
            else RESEARCH_PACKET_V3_ACTION_ADAPTER
        )
    if (
        action.payload.get("action_type") == CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER
    if (
        action.payload.get("action_type") == MATERIAL_REVIEW_ACTION_V2_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return MATERIAL_REVIEW_ACTION_V2_ADAPTER
    if (
        action.payload.get("action_type") == DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER
    if (
        action_type in _LOCAL_DISPOSITION_ADAPTERS
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return _LOCAL_DISPOSITION_ADAPTERS[action_type]
    if (
        action.payload.get("action_type")
        in {
            SOURCE_FACT_AUTHORITY_ACTION_TYPE,
            SOURCE_FACT_AUTHORITY_V2_ACTION_TYPE,
        }
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER
    if (
        action.payload.get("action_type") == CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER
    if (
        action.payload.get("action_type") == CONTENT_DEV_DRAFT_ACTION_TYPE
        and action.connector == "wordpress_ekologus"
    ):
        return CONTENT_DEV_DRAFT_MUTATION_ADAPTER
    if (
        action.payload.get("action_type") == CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE
        and action.connector == "wordpress_ekologus"
    ):
        return "content_dev_draft_discard_execution_boundary"
    if (
        action.payload.get("action_type") == CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE
        and action.connector == "wordpress_ekologus"
    ):
        return CONTENT_NEW_PAGE_DRAFT_MUTATION_ADAPTER
    if (
        action.id == "act_apply_wordpress_draft_handoff"
        and action.connector == "wordpress_ekologus"
        and action.payload.get("allowed_operation") == "create_wordpress_draft"
    ):
        return "wordpress_draft_execution_boundary"
    return None
