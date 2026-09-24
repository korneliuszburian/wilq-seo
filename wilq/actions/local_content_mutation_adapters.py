"""Dispatch local-only content authority adapters outside the service facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.audit.trusted_local_confirmation import TrustedLocalPrincipalReceipt
from wilq.content.planning.generation_intent import (
    PLANNING_GENERATION_INTENT_ADAPTER,
    execute_planning_generation_intent_action,
)
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ADAPTER,
    execute_planning_generation_intent_v3_action,
)
from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_MUTATION_ADAPTER,
    execute_current_disposition_authority,
)
from wilq.content.workflow.delivery_identity_authority import (
    DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER,
    execute_delivery_identity_authority,
)
from wilq.content.workflow.material_review_action_v2 import (
    MATERIAL_REVIEW_ACTION_V2_ADAPTER,
    execute_current_material_review_action_v2,
)
from wilq.content.workflow.per_url_disposition_authority import (
    PER_URL_DISPOSITION_MUTATION_ADAPTER,
    execute_per_url_disposition_authority,
)
from wilq.content.workflow.research_packet_v2_action import (
    RESEARCH_PACKET_V2_ACTION_ADAPTER,
    execute_research_packet_v2_action,
)
from wilq.content.workflow.research_packet_v3_action import (
    RESEARCH_PACKET_V3_ACTION_ADAPTER,
    execute_research_packet_v3_action,
)
from wilq.content.workflow.research_promotion_authority import (
    CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER,
    ContentResearchFactPromotionExecutionContext,
    execute_research_fact_promotion,
    research_promotion_execution_context_digest,
)
from wilq.content.workflow.source_fact_authority import (
    SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER,
    execute_content_source_fact_authority,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import ActionObject
from wilq.storage.local_state import LocalStateStore

_LOCAL_ADAPTERS = frozenset(
    {
        RESEARCH_PACKET_V2_ACTION_ADAPTER,
        RESEARCH_PACKET_V3_ACTION_ADAPTER,
        MATERIAL_REVIEW_ACTION_V2_ADAPTER,
        SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER,
        CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER,
        CURRENT_DISPOSITION_MUTATION_ADAPTER,
        PER_URL_DISPOSITION_MUTATION_ADAPTER,
        DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER,
        PLANNING_GENERATION_INTENT_ADAPTER,
        PLANNING_GENERATION_INTENT_V3_ADAPTER,
    }
)


def is_local_content_mutation_adapter(adapter: str) -> bool:
    return adapter in _LOCAL_ADAPTERS


def execute_local_content_mutation_adapter(
    action: ActionObject,
    adapter: str,
    *,
    workflow_store: ContentWorkflowStore,
    audit_store_factory: Callable[[], LocalStateStore],
    trusted_principal_receipt: TrustedLocalPrincipalReceipt | None = None,
    content_snapshot_loader: Callable[[str], Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]] | None:
    """Run one local content receipt adapter, or return None for vendor adapters."""
    if adapter == RESEARCH_PACKET_V2_ACTION_ADAPTER:
        return execute_research_packet_v2_action(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
            confirmed_by=_confirmation_actor(action),
        )
    if adapter == RESEARCH_PACKET_V3_ACTION_ADAPTER:
        return execute_research_packet_v3_action(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
            confirmed_by=_confirmation_actor(action),
        )
    if adapter == PLANNING_GENERATION_INTENT_ADAPTER:
        return execute_planning_generation_intent_action(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
            confirmed_by=_confirmation_actor(action),
            current_snapshot_loader=content_snapshot_loader,
        )
    if adapter == PLANNING_GENERATION_INTENT_V3_ADAPTER:
        return execute_planning_generation_intent_v3_action(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
            confirmed_by=_confirmation_actor(action),
        )
    if adapter == MATERIAL_REVIEW_ACTION_V2_ADAPTER:
        return execute_current_material_review_action_v2(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
            confirmed_by=_confirmation_actor(action),
        )
    if adapter == SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER:
        return execute_content_source_fact_authority(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
        )
    if adapter == CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER:
        audit_store = audit_store_factory()
        promotion_store_identity = str(workflow_store.path)
        audit_store_identity = str(audit_store.path)
        return execute_research_fact_promotion(
            action,
            context=ContentResearchFactPromotionExecutionContext(
                promotion_store=workflow_store,
                persisted_audit_events=tuple(audit_store.list_audit_events(action_id=action.id)),
                promotion_store_identity=promotion_store_identity,
                audit_store_identity=audit_store_identity,
                context_digest=research_promotion_execution_context_digest(
                    action.id,
                    promotion_store_identity=promotion_store_identity,
                    audit_store_identity=audit_store_identity,
                ),
                trusted_principal_receipt=trusted_principal_receipt,
            ),
        )
    if adapter == CURRENT_DISPOSITION_MUTATION_ADAPTER:
        return execute_current_disposition_authority(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
        )
    if adapter == PER_URL_DISPOSITION_MUTATION_ADAPTER:
        return execute_per_url_disposition_authority(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
            confirmed_by=_confirmation_actor(action),
        )
    if adapter == DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER:
        return execute_delivery_identity_authority(
            action,
            store=workflow_store,
            audit_events=action.audit_events,
        )
    return None


def _confirmation_actor(action: ActionObject) -> str:
    events = sorted(
        (event for event in action.audit_events if event.event_type == "action_apply_confirmed"),
        key=lambda event: (event.created_at, event.id),
    )
    return events[-1].actor if events else ""


__all__ = ["execute_local_content_mutation_adapter", "is_local_content_mutation_adapter"]
