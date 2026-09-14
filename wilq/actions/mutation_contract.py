from __future__ import annotations

from wilq.actions._mutation_contract_dispatch import (
    mutation_apply_contract as _mutation_apply_contract,
)
from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_ACTION_TYPE,
    CURRENT_DISPOSITION_MUTATION_ADAPTER,
)
from wilq.content.workflow.delivery_identity_authority import (
    DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE,
    DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER,
)
from wilq.content.workflow.source_fact_authority import (
    SOURCE_FACT_AUTHORITY_ACTION_TYPE,
    SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER,
)
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


def mutation_apply_contract(
    action: ActionObject,
    mutation_adapter: str | None,
) -> ActionMutationApplyContract | None:
    return _mutation_apply_contract(action, mutation_adapter)


def supported_mutation_adapter(action: ActionObject) -> str | None:
    if (
        action.payload.get("action_type") == DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER
    if (
        action.payload.get("action_type") == CURRENT_DISPOSITION_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return CURRENT_DISPOSITION_MUTATION_ADAPTER
    if (
        action.payload.get("action_type") == SOURCE_FACT_AUTHORITY_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
        and action.connector == "wordpress_ekologus"
    ):
        return SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER
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
