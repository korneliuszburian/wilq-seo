"""Public read seam for immutable per-URL research packets."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from wilq.content.workflow.research_packet import (
    ContentResearchPacketReadResult,
)
from wilq.content.workflow.research_packet_current import (
    CurrentSnapshotLoader,
    revalidate_content_research_packet,
)
from wilq.content.workflow.store.store import content_workflow_store

_PREFIX = "/api/content/research-packets"


async def read_content_research_packet(
    packet_id: str,
    *,
    snapshot_loader: CurrentSnapshotLoader | None = None,
) -> ContentResearchPacketReadResult:
    workflow_store = content_workflow_store()
    result = await asyncio.to_thread(
        workflow_store.load_content_research_packet,
        packet_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="content_research_packet_not_found")
    loader = snapshot_loader or snapshot_for_work_item_or_404
    current = await asyncio.to_thread(
        revalidate_content_research_packet,
        store=workflow_store,
        packet=result,
        snapshot_loader=loader,
    )
    return ContentResearchPacketReadResult(packet=result, current=current)


def register_content_research_packet_routes(
    router: APIRouter,
    *,
    snapshot_loader: CurrentSnapshotLoader | None = None,
) -> None:
    async def read_packet(packet_id: str) -> ContentResearchPacketReadResult:
        return await read_content_research_packet(
            packet_id,
            snapshot_loader=snapshot_loader,
        )

    router.add_api_route(
        f"{_PREFIX}/{{packet_id}}",
        read_packet,
        methods=["GET"],
        response_model=ContentResearchPacketReadResult,
        tags=["content"],
    )


__all__ = ["read_content_research_packet", "register_content_research_packet_routes"]
