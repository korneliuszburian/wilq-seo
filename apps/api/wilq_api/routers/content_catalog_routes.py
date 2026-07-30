from __future__ import annotations

from fastapi import APIRouter

from wilq.content.knowledge.cards import (
    ContentKnowledgeCardsResponse,
    content_knowledge_cards_response,
)
from wilq.content.knowledge.service_profile import (
    ContentServiceProfileResponse,
    content_service_profile_response,
)
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)
from wilq.content.workflow.operator import ContentOperatorContext, content_operator_context


def register_content_catalog_routes(router: APIRouter) -> None:
    """Shared catalogue and knowledge reads outside the exact document workflow."""

    @router.get("/api/content/operator-context", response_model=ContentOperatorContext)
    def content_operator_context_route() -> ContentOperatorContext:
        return content_operator_context()

    @router.get("/api/content/inventory/catalog", response_model=ContentInventoryCatalogResponse)
    def content_inventory_catalog() -> ContentInventoryCatalogResponse:
        return build_content_inventory_catalog_cached()

    @router.get("/api/content/knowledge-cards", response_model=ContentKnowledgeCardsResponse)
    def content_knowledge_cards() -> ContentKnowledgeCardsResponse:
        return content_knowledge_cards_response()

    @router.get("/api/content/service-profile", response_model=ContentServiceProfileResponse)
    def content_service_profile() -> ContentServiceProfileResponse:
        return content_service_profile_response()


__all__ = ["register_content_catalog_routes"]
