from __future__ import annotations

import asyncio
import base64
from binascii import Error as Base64DecodeError
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionClassificationProjectionReadResult,
    ContentProductionClassificationReadResult,
    ContentProductionClassificationRecordResult,
    ContentProductionClassificationRun,
    ContentProductionClassificationValidationError,
    parse_content_production_classification,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.store.store_production_classification import (
    HISTORICAL_PRODUCTION_POLICY_IDS,
)

_MAX_PACKET_BYTES = 1_048_576
_MAX_JUDGE_BYTES = 65_536
_ROUTE_PREFIX = "/api/content/production-classifications"
_REQUEST_INVALID_DETAIL = "production_classification_request_invalid"
_BASE64_INVALID_DETAIL = "production_classification_base64_invalid"
_SIZE_INVALID_DETAIL = "production_classification_size_invalid"
_HISTORICAL_REFERENCE_DETAIL = "production_classification_historical_reference"
_ERROR_CODE_PATTERN = r"^[a-z][a-z0-9_]*$"


class _NoEchoValidationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def no_echo_route_handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={"detail": _REQUEST_INVALID_DETAIL},
                )

        return no_echo_route_handler


class ContentProductionClassificationRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_selector: Literal["wave0-production-classification-v1"]
    packet_base64: str = Field(repr=False)
    judge_base64: str = Field(repr=False)
    recorded_by: str = Field(min_length=1, max_length=160)
    reviewed_by: str = Field(min_length=1, max_length=160)
    recorded_at: datetime


class ContentProductionClassificationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(pattern=_ERROR_CODE_PATTERN)


async def record_content_production_classification(
    request: ContentProductionClassificationRecordRequest,
) -> JSONResponse:
    return await asyncio.to_thread(_record_content_production_classification, request)


def _record_content_production_classification(
    request: ContentProductionClassificationRecordRequest,
) -> JSONResponse:
    packet_bytes = _decode_transport(request.packet_base64, _MAX_PACKET_BYTES)
    judge_bytes = _decode_transport(request.judge_base64, _MAX_JUDGE_BYTES)
    if WAVE0_PRODUCTION_ACCEPTANCE_POLICY.authority_role == "historical_reference":
        raise HTTPException(status_code=409, detail=_HISTORICAL_REFERENCE_DETAIL)
    try:
        run = parse_content_production_classification(
            packet_bytes=packet_bytes,
            judge_bytes=judge_bytes,
            acceptance_policy=WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
            recorded_by=request.recorded_by,
            reviewed_by=request.reviewed_by,
            recorded_at=request.recorded_at,
        )
    except ContentProductionClassificationValidationError as error:
        raise HTTPException(status_code=422, detail=error.code) from error
    result = content_workflow_store().record_production_classification(run)
    status_code = {"created": 201, "idempotent": 200, "conflict": 409}[result.status]
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


async def latest_content_production_classification() -> ContentProductionClassificationReadResult:
    return await asyncio.to_thread(_latest_content_production_classification)


def _latest_content_production_classification() -> ContentProductionClassificationReadResult:
    store = content_workflow_store()
    run = store.load_latest_production_classification()
    if run is None:
        run = store.load_latest_production_classification_reference()
    return ContentProductionClassificationReadResult(
        status=_read_status(run),
        run=run,
    )


async def content_production_classification_for_work_item(
    work_item_id: str,
) -> ContentProductionClassificationProjectionReadResult:
    return await asyncio.to_thread(
        _content_production_classification_for_work_item,
        work_item_id,
    )


def _content_production_classification_for_work_item(
    work_item_id: str,
) -> ContentProductionClassificationProjectionReadResult:
    store = content_workflow_store()
    projection = store.load_production_classification_for_work_item(work_item_id)
    if projection is not None:
        return ContentProductionClassificationProjectionReadResult(
            status="available",
            projection=projection,
        )

    projection = store.load_production_classification_reference_for_work_item(work_item_id)
    if projection is None:
        return ContentProductionClassificationProjectionReadResult(
            status="missing",
            projection=None,
        )

    return ContentProductionClassificationProjectionReadResult(
        status="historical_reference",
        projection=projection,
    )


def _read_status(value: ContentProductionClassificationRun | None) -> Literal[
    "available", "historical_reference", "missing"
]:
    if value is None:
        return "missing"
    if value.input.policy_id in HISTORICAL_PRODUCTION_POLICY_IDS:
        return "historical_reference"
    return "available"


def _decode_transport(value: str, max_bytes: int) -> bytes:
    max_encoded = ((max_bytes + 2) // 3) * 4
    if len(value) > max_encoded:
        raise HTTPException(status_code=422, detail=_SIZE_INVALID_DETAIL)
    try:
        decoded = base64.b64decode(value, validate=True)
    except (Base64DecodeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=_BASE64_INVALID_DETAIL) from error
    if not decoded or len(decoded) > max_bytes:
        raise HTTPException(status_code=422, detail=_SIZE_INVALID_DETAIL)
    return decoded


def register_content_production_classification_routes(router: APIRouter) -> None:
    router.add_api_route(
        _ROUTE_PREFIX,
        record_content_production_classification,
        methods=["POST"],
        response_model=ContentProductionClassificationRecordResult,
        responses={
            201: {"model": ContentProductionClassificationRecordResult},
            409: {
                "model": ContentProductionClassificationRecordResult
                | ContentProductionClassificationErrorResponse
            },
            422: {"model": ContentProductionClassificationErrorResponse},
        },
        tags=["content"],
        route_class_override=_NoEchoValidationRoute,
    )
    router.add_api_route(
        f"{_ROUTE_PREFIX}/latest",
        latest_content_production_classification,
        methods=["GET"],
        response_model=ContentProductionClassificationReadResult,
        tags=["content"],
        route_class_override=_NoEchoValidationRoute,
    )
    router.add_api_route(
        f"{_ROUTE_PREFIX}/work-items/{{work_item_id}}",
        content_production_classification_for_work_item,
        methods=["GET"],
        response_model=ContentProductionClassificationProjectionReadResult,
        tags=["content"],
        route_class_override=_NoEchoValidationRoute,
    )


__all__ = [
    "ContentProductionClassificationErrorResponse",
    "ContentProductionClassificationRecordRequest",
    "register_content_production_classification_routes",
]
