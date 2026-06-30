from __future__ import annotations

from fastapi import APIRouter

from wilq.briefing.content_diagnostics import build_content_diagnostics
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
    ContentWorkItemSnapshotAuditRequest,
    ContentWorkItemSnapshotHumanReviewRequest,
    ContentWorkItemStructuredDraftGenerationRequest,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemWordPressDraftExecutionRequest,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffRequest,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_draft_package_response,
    build_content_work_item_human_review_response,
    build_content_work_item_measurement_window_response,
    build_content_work_item_preflight_response,
    build_content_work_item_sales_brief_response,
    build_content_work_item_snapshot_audit_response,
    build_content_work_item_snapshot_human_review_response,
    build_content_work_item_structured_draft_generation_response,
    build_content_work_item_wordpress_draft_execution_response,
    build_content_work_item_wordpress_draft_handoff_response,
)
from wilq.content.workflow.store import content_workflow_store

router = APIRouter()


@router.get(
    "/api/content/work-items/snapshot",
    response_model=ContentWorkItemWorkflowSnapshotResponse,
)
def content_work_item_snapshot() -> ContentWorkItemWorkflowSnapshotResponse:
    diagnostics = build_content_diagnostics()
    snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    review = content_workflow_store().latest_human_review(snapshot.preflight.item.id)
    if review is None:
        return snapshot
    audit = content_workflow_store().latest_audit_for_review(review.id)
    return build_content_work_item_diagnostics_snapshot_response(
        diagnostics,
        human_review=review,
        audit=audit,
    )


@router.post(
    "/api/content/work-items/snapshot/human-review",
    response_model=ContentWorkItemHumanReviewResponse,
)
def content_work_item_snapshot_human_review(
    request: ContentWorkItemSnapshotHumanReviewRequest,
) -> ContentWorkItemHumanReviewResponse:
    response = build_content_work_item_snapshot_human_review_response(
        build_content_diagnostics(),
        request,
    )
    if response.wordpress_handoff_allowed and response.review is not None:
        content_workflow_store().save_human_review(response.review)
    return response


@router.post(
    "/api/content/work-items/snapshot/audit",
    response_model=ContentWorkItemWordPressDraftHandoffResponse,
)
def content_work_item_snapshot_audit(
    request: ContentWorkItemSnapshotAuditRequest,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    diagnostics = build_content_diagnostics()
    snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    review = content_workflow_store().latest_human_review(snapshot.preflight.item.id)
    response = build_content_work_item_snapshot_audit_response(
        diagnostics,
        request,
        human_review=review,
    )
    if response.handoff_result.handoff is not None:
        content_workflow_store().save_audit(request.audit)
    return response


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
    "/api/content/work-items/structured-draft-generation",
    response_model=ContentWorkItemStructuredDraftGenerationResponse,
)
def content_work_item_structured_draft_generation(
    request: ContentWorkItemStructuredDraftGenerationRequest,
) -> ContentWorkItemStructuredDraftGenerationResponse:
    return build_content_work_item_structured_draft_generation_response(request)


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
    "/api/content/work-items/wordpress-draft-execution",
    response_model=ContentWorkItemWordPressDraftExecutionResponse,
)
def content_work_item_wordpress_draft_execution(
    request: ContentWorkItemWordPressDraftExecutionRequest,
) -> ContentWorkItemWordPressDraftExecutionResponse:
    return build_content_work_item_wordpress_draft_execution_response(request)


@router.post(
    "/api/content/work-items/measurement-window",
    response_model=ContentWorkItemMeasurementWindowResponse,
)
def content_work_item_measurement_window(
    request: ContentWorkItemMeasurementWindowRequest,
) -> ContentWorkItemMeasurementWindowResponse:
    return build_content_work_item_measurement_window_response(request)
