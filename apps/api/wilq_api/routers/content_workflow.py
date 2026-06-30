from __future__ import annotations

from fastapi import APIRouter

from wilq.content.workflow.api import (
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    ContentWorkItemSalesBriefRequest,
    ContentWorkItemSalesBriefResponse,
    build_content_work_item_draft_package_response,
    build_content_work_item_preflight_response,
    build_content_work_item_sales_brief_response,
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


@router.post(
    "/api/content/work-items/sales-brief",
    response_model=ContentWorkItemSalesBriefResponse,
)
def content_work_item_sales_brief(
    request: ContentWorkItemSalesBriefRequest,
) -> ContentWorkItemSalesBriefResponse:
    return build_content_work_item_sales_brief_response(request)


@router.post(
    "/api/content/work-items/draft-package",
    response_model=ContentWorkItemDraftPackageResponse,
)
def content_work_item_draft_package(
    request: ContentWorkItemDraftPackageRequest,
) -> ContentWorkItemDraftPackageResponse:
    return build_content_work_item_draft_package_response(request)
