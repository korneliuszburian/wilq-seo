"""Public exact read-only seam for current content verification receipts."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.current_verification import (
    ContentCurrentVerification,
)
from wilq.content.workflow.store.store import content_workflow_store

_PREFIX = "/api/content/current-verifications"


async def read_current_verification(verification_id: str) -> ContentCurrentVerification:
    result = await asyncio.to_thread(
        content_workflow_store().load_current_verification,
        verification_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="content_current_verification_not_found")
    return result


def register_content_current_verification_routes(router: APIRouter) -> None:
    router.add_api_route(
        f"{_PREFIX}/{{verification_id}}",
        read_current_verification,
        methods=["GET"],
        response_model=ContentCurrentVerification,
        tags=["content"],
    )


__all__ = ["register_content_current_verification_routes"]
