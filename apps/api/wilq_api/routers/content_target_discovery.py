from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.target_discovery import (
    ContentTargetDiscovery,
    build_content_target_discovery,
)


def register_content_target_discovery_route(router: APIRouter) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/target-discovery",
        response_model=ContentTargetDiscovery,
    )
    def content_target_discovery(work_item_id: str) -> ContentTargetDiscovery:
        discovery = build_content_target_discovery(work_item_id)
        if discovery is None:
            raise HTTPException(
                status_code=404,
                detail="Nie znaleziono strony do sprawdzenia na dev.",
            )
        return discovery


__all__ = ["register_content_target_discovery_route"]
