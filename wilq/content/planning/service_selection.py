"""Exact service-card selection shared by planning input rebuilds."""

from __future__ import annotations

from wilq.content.knowledge.cards import (
    match_content_knowledge_cards,
    select_content_knowledge_service_card,
)
from wilq.content.knowledge.work_item_service_profile import (
    build_content_work_item_service_profile_context,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse


def with_explicit_content_service_selection(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    service_card_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Bind one exact service choice without writing a planning decision."""

    item = snapshot.preflight.item
    match = select_content_knowledge_service_card(
        match_content_knowledge_cards(item), service_card_id
    )
    context = build_content_work_item_service_profile_context(
        item,
        knowledge_match=match,
        service_selection_confirmed=True,
    )
    return snapshot.model_copy(update={"service_profile_context": context})


__all__ = ["with_explicit_content_service_selection"]
