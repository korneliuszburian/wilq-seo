"""Public ask-scoped research read over existing per-URL evidence seams."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ekologus_content_knowledge_cards,
)
from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
    ekologus_source_facts,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.intake import demand_connector_freshness
from wilq.content.workflow.research_read import (
    ContentResearchReadResponse,
    resolve_content_research_read,
)
from wilq.content.workflow.store.store import content_workflow_store

EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]
SourceFactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
CardsLoader = Callable[[], tuple[ContentKnowledgeCard, ...]]
FreshnessLoader = Callable[[], Mapping[str, str]]
_ROUTE = "/api/content/intake-requests/{queue_id}/research"


class ContentResearchReadErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


def register_content_research_read_routes(
    router: APIRouter,
    *,
    store_factory: Callable[[], Any] = content_workflow_store,
    evidence_loader: EvidenceLoader | None = None,
    source_facts_loader: SourceFactsLoader = ekologus_source_facts,
    cards_loader: CardsLoader = ekologus_content_knowledge_cards,
    freshness_loader: FreshnessLoader = demand_connector_freshness,
) -> None:
    load_evidence = evidence_loader or (
        lambda work_item_id: content_current_page_evidence.read_current_page_evidence(
            work_item_id=work_item_id
        )
    )

    @router.get(
        _ROUTE,
        response_model=ContentResearchReadResponse,
        responses={404: {"model": ContentResearchReadErrorResponse}},
        tags=["content"],
    )
    def read_content_research(
        queue_id: str,
    ) -> ContentResearchReadResponse | JSONResponse:
        result = resolve_content_research_read(
            store_factory(),
            queue_id,
            evidence_loader=load_evidence,
            source_facts_loader=source_facts_loader,
            cards_loader=cards_loader,
            connector_freshness=freshness_loader(),
        )
        if result is None:
            return JSONResponse(
                status_code=404,
                content=ContentResearchReadErrorResponse(
                    detail="intake_queue_item_missing",
                    owner="WILQ content workflow",
                    safe_next_step="Użyj queue ID z odpowiedzi przyjęcia prośby.",
                ).model_dump(mode="json"),
            )
        return result


__all__ = ["ContentResearchReadErrorResponse", "register_content_research_read_routes"]
