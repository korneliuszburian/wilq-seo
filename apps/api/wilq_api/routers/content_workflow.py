from __future__ import annotations

from fastapi import APIRouter

from wilq.content.workflow.api import (
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    build_content_work_item_preflight_response,
)

router = APIRouter()


@router.post(
    "/api/content/work-items/preflight",
    response_model=ContentWorkItemPreflightResponse,
)
def content_work_item_preflight(
    request: ContentWorkItemPreflightRequest,
) -> ContentWorkItemPreflightResponse:
    return build_content_work_item_preflight_response(request)
