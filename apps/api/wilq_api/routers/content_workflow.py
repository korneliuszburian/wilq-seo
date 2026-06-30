from __future__ import annotations

from fastapi import APIRouter

from wilq.content.workflow.api import (
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemHumanReviewRequest,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    ContentWorkItemSalesBriefRequest,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemWordPressDraftHandoffRequest,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
    build_content_work_item_control_snapshot_response,
    build_content_work_item_draft_package_response,
    build_content_work_item_human_review_response,
    build_content_work_item_measurement_window_response,
    build_content_work_item_preflight_response,
    build_content_work_item_sales_brief_response,
    build_content_work_item_wordpress_draft_handoff_response,
)

router = APIRouter()


@router.get(
    "/api/content/work-items/control-snapshot",
    response_model=ContentWorkItemWorkflowSnapshotResponse,
)
def content_work_item_control_snapshot() -> ContentWorkItemWorkflowSnapshotResponse:
    return build_content_work_item_control_snapshot_response()


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


@router.post(
    "/api/content/work-items/human-review",
    response_model=ContentWorkItemHumanReviewResponse,
)
def content_work_item_human_review(
    request: ContentWorkItemHumanReviewRequest,
) -> ContentWorkItemHumanReviewResponse:
    return build_content_work_item_human_review_response(request)


@router.post(
    "/api/content/work-items/wordpress-draft-handoff",
    response_model=ContentWorkItemWordPressDraftHandoffResponse,
)
def content_work_item_wordpress_draft_handoff(
    request: ContentWorkItemWordPressDraftHandoffRequest,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    return build_content_work_item_wordpress_draft_handoff_response(request)


@router.post(
    "/api/content/work-items/measurement-window",
    response_model=ContentWorkItemMeasurementWindowResponse,
)
def content_work_item_measurement_window(
    request: ContentWorkItemMeasurementWindowRequest,
) -> ContentWorkItemMeasurementWindowResponse:
    return build_content_work_item_measurement_window_response(request)
