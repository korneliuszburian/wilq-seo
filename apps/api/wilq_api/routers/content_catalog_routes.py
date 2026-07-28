from __future__ import annotations

from fastapi import APIRouter, Query

from wilq.content.knowledge.cards import (
    ContentKnowledgeCardsResponse,
    content_knowledge_cards_response,
)
from wilq.content.knowledge.service_profile import (
    ContentServiceProfileResponse,
    content_service_profile_response,
)
from wilq.content.workflow.catalog import (
    ContentInventoryBindingRequest,
    ContentInventoryBindingResponse,
    ContentInventoryCatalogResponse,
    ContentInventoryMaterialResponse,
    bind_content_inventory_item,
    build_content_inventory_catalog_cached,
    read_content_inventory_material,
)
from wilq.content.workflow.operator import ContentOperatorContext, content_operator_context


def register_content_catalog_routes(router: APIRouter) -> None:
    """Read/write inventory binding and catalogue facts, outside document workflow routing."""

    @router.get("/api/content/operator-context", response_model=ContentOperatorContext)
    def content_operator_context_route() -> ContentOperatorContext:
        return content_operator_context()

    @router.get("/api/content/inventory/catalog", response_model=ContentInventoryCatalogResponse)
    def content_inventory_catalog() -> ContentInventoryCatalogResponse:
        return build_content_inventory_catalog_cached()

    @router.get("/api/content/inventory/material", response_model=ContentInventoryMaterialResponse)
    def content_inventory_material(
        url: str = Query(min_length=1),
    ) -> ContentInventoryMaterialResponse:
        return read_content_inventory_material(url)

    @router.post("/api/content/inventory/bind", response_model=ContentInventoryBindingResponse)
    def content_inventory_bind(
        request: ContentInventoryBindingRequest,
    ) -> ContentInventoryBindingResponse:
        return bind_content_inventory_item(request.url)

    @router.get("/api/content/knowledge-cards", response_model=ContentKnowledgeCardsResponse)
    def content_knowledge_cards() -> ContentKnowledgeCardsResponse:
        return content_knowledge_cards_response()

    @router.get("/api/content/service-profile", response_model=ContentServiceProfileResponse)
    def content_service_profile() -> ContentServiceProfileResponse:
        return content_service_profile_response()


__all__ = ["register_content_catalog_routes"]
