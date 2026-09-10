"""Public read/record seam for exact source-pack binding receipts."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBindingCommand,
    ContentSourcePackBindingReadResult,
    ContentSourcePackBindingRecordResult,
    ContentSourcePackPrerequisites,
    build_content_source_pack_prerequisites,
)
from wilq.content.workflow.store.store import content_workflow_store

_PREFIX = "/api/content/source-pack-bindings"


async def record_content_source_pack_binding(
    command: ContentSourcePackBindingCommand,
) -> JSONResponse:
    result = await asyncio.to_thread(
        content_workflow_store().record_content_source_pack_binding,
        command,
    )
    status_code = {"created": 201, "idempotent": 200, "conflict": 409}[result.status]
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


async def read_content_source_pack_binding(
    binding_id: str,
) -> ContentSourcePackBindingReadResult:
    result = await asyncio.to_thread(
        content_workflow_store().load_content_source_pack_binding,
        binding_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="content_source_pack_binding_not_found")
    return ContentSourcePackBindingReadResult(binding=result)


async def read_content_source_pack_prerequisites(
    identity_binding_id: str,
) -> ContentSourcePackPrerequisites:
    identity = await asyncio.to_thread(
        content_workflow_store().load_content_delivery_identity,
        identity_binding_id,
    )
    if identity is None:
        raise HTTPException(status_code=404, detail="content_delivery_identity_not_found")
    if identity.status == "blocked":
        raise HTTPException(
            status_code=409,
            detail="content_source_pack_prerequisites_identity_blocked",
        )
    try:
        return build_content_source_pack_prerequisites(identity)
    except ValidationError as exc:
        raise HTTPException(
            status_code=409,
            detail="content_source_pack_prerequisites_unavailable",
        ) from exc


def register_content_source_pack_binding_routes(router: APIRouter) -> None:
    router.add_api_route(
        _PREFIX,
        record_content_source_pack_binding,
        methods=["POST"],
        response_model=ContentSourcePackBindingRecordResult,
        responses={409: {"model": ContentSourcePackBindingRecordResult}},
        tags=["content"],
    )
    router.add_api_route(
        f"{_PREFIX}/prerequisites/{{identity_binding_id}}",
        read_content_source_pack_prerequisites,
        methods=["GET"],
        response_model=ContentSourcePackPrerequisites,
        tags=["content"],
    )
    router.add_api_route(
        f"{_PREFIX}/{{binding_id}}",
        read_content_source_pack_binding,
        methods=["GET"],
        response_model=ContentSourcePackBindingReadResult,
        tags=["content"],
    )


__all__ = ["register_content_source_pack_binding_routes"]
