"""Public ask-only intake seam: one idempotent request, no generation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
    ekologus_source_facts,
)
from wilq.content.workflow.intake import (
    ContentIntakeAskRequest,
    ContentIntakeQueueItem,
    build_content_intake_queue_item,
    demand_connector_freshness,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)
from wilq.schemas.core import utc_now

CatalogLoader = Callable[[], ContentInventoryCatalogResponse]
SourceFactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
FreshnessLoader = Callable[[], Mapping[str, str]]

_ROUTE = "/api/content/intake-requests"


class ContentIntakeErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


def register_content_intake_routes(
    router: APIRouter,
    *,
    store_factory: Callable[[], Any] = content_workflow_store,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    source_facts_loader: SourceFactsLoader = ekologus_source_facts,
    freshness_loader: FreshnessLoader | None = None,
) -> None:
    resolved_freshness_loader = freshness_loader or demand_connector_freshness

    @router.post(
        _ROUTE,
        response_model=ContentIntakeQueueItem,
        responses={
            200: {"model": ContentIntakeQueueItem},
            201: {"model": ContentIntakeQueueItem},
            409: {"model": ContentIntakeErrorResponse},
        },
        tags=["content"],
    )
    def create_content_intake_request(
        request: ContentIntakeAskRequest,
    ) -> JSONResponse:
        item = build_content_intake_queue_item(
            request_id=request.request_id,
            ask=request.ask,
            catalog=catalog_loader(),
            source_facts=source_facts_loader(),
            connector_freshness=resolved_freshness_loader(),
            created_at=utc_now(),
        )
        store = store_factory()
        result, stored = store.create_content_intake_request(item)
        if result == "conflict":
            return JSONResponse(
                status_code=409,
                content=ContentIntakeErrorResponse(
                    detail="intake_request_id_conflict",
                    owner="WILQ content workflow",
                    safe_next_step=(
                        "Użyj nowego request ID dla zmienionej prośby; istniejący "
                        "queue ID pozostaje bez zmian."
                    ),
                ).model_dump(mode="json"),
            )
        return JSONResponse(
            status_code=201 if result == "created" else 200,
            content=stored.model_dump(mode="json"),
        )

    @router.get(
        f"{_ROUTE}/{{queue_id}}",
        response_model=ContentIntakeQueueItem,
        responses={404: {"model": ContentIntakeErrorResponse}},
        tags=["content"],
    )
    def read_content_intake_request(
        queue_id: str,
    ) -> ContentIntakeQueueItem | JSONResponse:
        item = store_factory().load_content_intake_request(queue_id)
        if item is None or not isinstance(item, ContentIntakeQueueItem):
            return JSONResponse(
                status_code=404,
                content=ContentIntakeErrorResponse(
                    detail="intake_queue_item_missing",
                    owner="WILQ content workflow",
                    safe_next_step="Użyj queue ID z odpowiedzi przyjęcia prośby.",
                ).model_dump(mode="json"),
            )
        return item


__all__ = ["ContentIntakeErrorResponse", "register_content_intake_routes"]
