"""Typed landing/hub preview and authorization routes."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict

from wilq.content.workflow.decisions.inventory_binding import (
    content_kind_inventory_binding_for_work_item,
)
from wilq.content.workflow.landing_hub import (
    ContentLandingHubAuthorizationBlocker,
    ContentLandingHubAuthorizationPreview,
    ContentLandingHubAuthorizationRecordResult,
    ContentLandingHubAuthorizationRequest,
    build_landing_hub_authorization,
    landing_hub_authorization_blocker,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas.core import utc_now

_PREFIX = "/api/content/work-items"
_INVALID_DETAIL = "landing_hub_authorization_request_invalid"


class _NoEchoLandingHubAuthorizationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def no_echo_route_handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except RequestValidationError:
                return JSONResponse(status_code=422, content={"detail": _INVALID_DETAIL})

        return no_echo_route_handler


class ContentLandingHubAuthorizationValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: Literal["landing_hub_authorization_request_invalid"]


def _preview(
    store: ContentWorkflowStore,
    work_item_id: str,
) -> ContentLandingHubAuthorizationPreview:
    classification = store.load_latest_production_classification()
    row = None if classification is None else classification.for_work_item(work_item_id)
    inventory = content_kind_inventory_binding_for_work_item(work_item_id)
    blocker = landing_hub_authorization_blocker(
        work_item_id=work_item_id,
        classification=classification,
        row=row,
        inventory_binding=inventory,
    )
    if blocker is not None:
        return ContentLandingHubAuthorizationPreview(
            status="blocked",
            work_item_id=work_item_id,
            classification_run_id=None if classification is None else classification.run_id,
            classification_run_digest=None if classification is None else classification.run_digest,
            canonical_path=None if row is None else row.canonical_path,
            public_url=None if row is None else row.public_url,
            blockers=(blocker,),
            safe_next_step=blocker.next_step_pl,
        )
    if classification is None or row is None or inventory is None:
        raise RuntimeError("Landing/hub preview lost its exact context.")
    try:
        authorization = store.load_latest_landing_hub_authorization(work_item_id)
    except ValueError:
        return ContentLandingHubAuthorizationPreview(
            status="blocked",
            work_item_id=work_item_id,
            classification_run_id=classification.run_id,
            classification_run_digest=classification.run_digest,
            canonical_path=row.canonical_path,
            public_url=row.public_url,
            blockers=(
                ContentLandingHubAuthorizationBlocker(
                    seam="authorization",
                    reason="authorization_conflict",
                    evidence_ids=tuple(sorted(inventory.inventory_evidence_ids)),
                    next_step_pl=(
                        "Zweryfikuj albo unieważnij uszkodzony receipt i przygotuj nowy "
                        "landing/hub authorization dla bieżącego exact URL-a."
                    ),
                ),
            ),
            safe_next_step=(
                "Zweryfikuj albo unieważnij uszkodzony receipt i przygotuj nowy "
                "landing/hub authorization dla bieżącego exact URL-a."
            ),
        )
    if authorization is not None:
        return ContentLandingHubAuthorizationPreview(
            status="authorized",
            work_item_id=work_item_id,
            authorization=authorization,
            classification_run_id=classification.run_id,
            classification_run_digest=classification.run_digest,
            canonical_path=row.canonical_path,
            public_url=row.public_url,
            safe_next_step="Authorization landing/hub jest aktualna dla tego exact URL-a.",
        )
    return ContentLandingHubAuthorizationPreview(
        status="ready_to_authorize",
        work_item_id=work_item_id,
        classification_run_id=classification.run_id,
        classification_run_digest=classification.run_digest,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        safe_next_step="Przygotuj intent, approved facts, CTA i zamknij duplicate gate.",
    )


async def read_landing_hub_authorization_preview(
    work_item_id: str = Path(..., min_length=1, max_length=240, pattern=r"^[a-z][a-z0-9_-]*$"),
) -> ContentLandingHubAuthorizationPreview:
    return await asyncio.to_thread(_preview, content_workflow_store(), work_item_id)


async def record_landing_hub_authorization(
    request: ContentLandingHubAuthorizationRequest,
    work_item_id: str = Path(..., min_length=1, max_length=240, pattern=r"^[a-z][a-z0-9_-]*$"),
) -> JSONResponse:
    store = content_workflow_store()
    classification = await asyncio.to_thread(store.load_latest_production_classification)
    row = None if classification is None else classification.for_work_item(work_item_id)
    inventory = await asyncio.to_thread(content_kind_inventory_binding_for_work_item, work_item_id)
    blocker = await asyncio.to_thread(
        landing_hub_authorization_blocker,
        work_item_id=work_item_id,
        classification=classification,
        row=row,
        inventory_binding=inventory,
        request=request,
    )
    if blocker is not None:
        preview = ContentLandingHubAuthorizationPreview(
            status="blocked",
            work_item_id=work_item_id,
            classification_run_id=None if classification is None else classification.run_id,
            classification_run_digest=None if classification is None else classification.run_digest,
            canonical_path=None if row is None else row.canonical_path,
            public_url=None if row is None else row.public_url,
            blockers=(blocker,),
            safe_next_step=blocker.next_step_pl,
        )
        return JSONResponse(status_code=409, content=preview.model_dump(mode="json"))
    if classification is None or row is None or inventory is None:
        raise RuntimeError("Landing/hub authorization lost its exact context.")
    try:
        authorization = await asyncio.to_thread(
            build_landing_hub_authorization,
            work_item_id=work_item_id,
            classification=classification,
            row=row,
            inventory_binding=inventory,
            request=request,
            authorized_at=utc_now(),
        )
        result = await asyncio.to_thread(store.record_landing_hub_authorization, authorization)
    except ValueError:
        preview = await asyncio.to_thread(_preview, store, work_item_id)
        return JSONResponse(status_code=409, content=preview.model_dump(mode="json"))
    status_code = {"created": 201, "idempotent": 200, "conflict": 409}[result.status]
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


async def read_landing_hub_authorization(
    authorization_id: str = Path(
        ..., min_length=1, max_length=280, pattern=r"^[a-z][a-z0-9_-]*$"
    ),
) -> ContentLandingHubAuthorizationRecordResult:
    result = await asyncio.to_thread(
        content_workflow_store().load_landing_hub_authorization,
        authorization_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="content_landing_hub_authorization_not_found")
    return ContentLandingHubAuthorizationRecordResult(status="idempotent", authorization=result)


def register_content_landing_hub_authorization_routes(router: APIRouter) -> None:
    router.add_api_route(
        f"{_PREFIX}/{{work_item_id}}/landing-hub-authorization",
        read_landing_hub_authorization_preview,
        methods=["GET"],
        response_model=ContentLandingHubAuthorizationPreview,
        responses={422: {"model": ContentLandingHubAuthorizationValidationErrorResponse}},
        route_class_override=_NoEchoLandingHubAuthorizationRoute,
        tags=["content"],
    )
    router.add_api_route(
        f"{_PREFIX}/{{work_item_id}}/landing-hub-authorizations",
        record_landing_hub_authorization,
        methods=["POST"],
        status_code=201,
        response_model=ContentLandingHubAuthorizationRecordResult,
        responses={
            409: {"model": ContentLandingHubAuthorizationPreview},
            422: {"model": ContentLandingHubAuthorizationValidationErrorResponse},
        },
        route_class_override=_NoEchoLandingHubAuthorizationRoute,
        tags=["content"],
    )
    router.add_api_route(
        f"{_PREFIX}/landing-hub-authorizations/{{authorization_id}}",
        read_landing_hub_authorization,
        methods=["GET"],
        response_model=ContentLandingHubAuthorizationRecordResult,
        responses={422: {"model": ContentLandingHubAuthorizationValidationErrorResponse}},
        route_class_override=_NoEchoLandingHubAuthorizationRoute,
        tags=["content"],
    )


__all__ = ["register_content_landing_hub_authorization_routes"]
