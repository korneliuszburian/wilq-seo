"""Public read/record seam for immutable per-URL research packets."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from wilq.content.workflow.research_packet import (
    ContentResearchPacketCommand,
    ContentResearchPacketReadResult,
    ContentResearchPacketRecordResult,
)
from wilq.content.workflow.store.store import content_workflow_store

_PREFIX = "/api/content/research-packets"


async def record_content_research_packet(
    command: ContentResearchPacketCommand,
) -> JSONResponse:
    result = await asyncio.to_thread(
        content_workflow_store().record_content_research_packet,
        command,
    )
    status_code = {"created": 201, "idempotent": 200, "conflict": 409}[result.status]
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


async def read_content_research_packet(packet_id: str) -> ContentResearchPacketReadResult:
    result = await asyncio.to_thread(
        content_workflow_store().load_content_research_packet,
        packet_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="content_research_packet_not_found")
    return ContentResearchPacketReadResult(packet=result)


def register_content_research_packet_routes(router: APIRouter) -> None:
    router.add_api_route(
        _PREFIX,
        record_content_research_packet,
        methods=["POST"],
        status_code=201,
        response_model=ContentResearchPacketRecordResult,
        responses={409: {"model": ContentResearchPacketRecordResult}},
        tags=["content"],
    )
    router.add_api_route(
        f"{_PREFIX}/{{packet_id}}",
        read_content_research_packet,
        methods=["GET"],
        response_model=ContentResearchPacketReadResult,
        tags=["content"],
    )


__all__ = ["register_content_research_packet_routes"]
