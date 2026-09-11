"""Read-only classified-refresh preparation and its one local authorization write."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Literal

from fastapi import APIRouter, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict

from apps.api.wilq_api.routers.content_refresh_preparation_authority import (
    content_refresh_preparation_authority,
)
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorizationConflictResponse,
    ContentRefreshPreparationAuthorizationCreatedResponse,
    ContentRefreshPreparationAuthorizationIdempotentResponse,
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationAuthorizationResponse,
    ContentRefreshPreparationPreview,
)

ContentRefreshPreparationAuthorityFactory = Callable[[], ContentRefreshPreparationAuthority]
_AUTHORIZATION_REQUEST_INVALID_DETAIL = "refresh_preparation_authorization_request_invalid"


class _NoEchoRefreshAuthorizationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def no_echo_route_handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={"detail": _AUTHORIZATION_REQUEST_INVALID_DETAIL},
                )

        return no_echo_route_handler


class ContentRefreshPreparationAuthorizationValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: Literal["refresh_preparation_authorization_request_invalid"]


def register_content_refresh_preparation_routes(
    router: APIRouter,
    *,
    authority_factory: ContentRefreshPreparationAuthorityFactory | None = None,
) -> None:
    def authority() -> ContentRefreshPreparationAuthority:
        return authority_factory() if authority_factory is not None else _canonical_authority()

    @router.get(
        "/api/content/work-items/{work_item_id}/refresh-preparation",
        response_model=ContentRefreshPreparationPreview,
    )
    def content_refresh_preparation(
        work_item_id: str,
        service_card_id: str | None = Query(default=None, min_length=1),
    ) -> ContentRefreshPreparationPreview:
        return authority().preview(work_item_id, service_card_id=service_card_id)

    def authorize_content_refresh_preparation(
        work_item_id: str,
        request: ContentRefreshPreparationAuthorizationRequest,
    ) -> ContentRefreshPreparationAuthorizationResponse | JSONResponse:
        result = authority().authorize(work_item_id, request)
        status_code = {"created": 201, "idempotent": 200, "conflict": 409}[result.status]
        return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))

    router.add_api_route(
        "/api/content/work-items/{work_item_id}/refresh-preparation/authorizations",
        authorize_content_refresh_preparation,
        methods=["POST"],
        response_model=ContentRefreshPreparationAuthorizationIdempotentResponse,
        responses={
            201: {"model": ContentRefreshPreparationAuthorizationCreatedResponse},
            409: {"model": ContentRefreshPreparationAuthorizationConflictResponse},
            422: {"model": ContentRefreshPreparationAuthorizationValidationErrorResponse},
        },
        route_class_override=_NoEchoRefreshAuthorizationRoute,
    )


def _canonical_authority() -> ContentRefreshPreparationAuthority:
    return content_refresh_preparation_authority()


__all__ = ["register_content_refresh_preparation_routes"]
