from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.knowledge.cards import (
    ContentKnowledgeCardsResponse,
    content_knowledge_cards_response,
    ekologus_content_knowledge_cards,
)
from wilq.content.knowledge.private_source_reviews import (
    ContentPrivateSourceReviewCommand,
    ContentPrivateSourceReviewResponse,
    private_source_review_store,
)
from wilq.content.knowledge.public_source_reviews import (
    ContentPublicSourceReviewCommand,
    ContentPublicSourceReviewResponse,
    public_source_review_store,
)
from wilq.content.knowledge.service_profile import (
    ContentServiceProfileResponse,
    content_service_profile_response,
)
from wilq.content.knowledge.source_facts import ekologus_seed_source_facts
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)
from wilq.content.workflow.pipeline_steps.operator import ContentOperatorContext, content_operator_context


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

    @router.post(
        "/api/content/private-source-reviews",
        response_model=ContentPrivateSourceReviewResponse,
        responses={409: {"description": "Private source candidate changed or conflicts."}},
    )
    def record_private_source_review(
        request: ContentPrivateSourceReviewCommand,
    ) -> ContentPrivateSourceReviewResponse:
        try:
            response = private_source_review_store().record(
                request,
                candidates=ekologus_seed_source_facts(),
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        ekologus_content_knowledge_cards.cache_clear()
        return response

    @router.post(
        "/api/content/public-source-reviews",
        response_model=ContentPublicSourceReviewResponse,
        responses={409: {"description": "Public source candidate changed or conflicts."}},
    )
    def record_public_source_review(
        request: ContentPublicSourceReviewCommand,
    ) -> ContentPublicSourceReviewResponse:
        try:
            response = public_source_review_store().record(
                request,
                candidates=ekologus_seed_source_facts(),
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        ekologus_content_knowledge_cards.cache_clear()
        return response


__all__ = ["register_content_catalog_routes"]
