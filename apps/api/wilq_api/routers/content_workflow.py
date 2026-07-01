from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichmentResponse,
    build_content_opportunity_enrichment_response,
)
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.knowledge.cards import (
    ContentKnowledgeCardsResponse,
    content_knowledge_cards_response,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.api import (
    build_content_work_item_blocked_snapshot_response_for_work_item,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_diagnostics_snapshot_response_for_work_item,
    build_content_work_item_draft_package_response,
    build_content_work_item_draft_variants_response,
    build_content_work_item_human_review_response,
    build_content_work_item_measurement_outcome_response,
    build_content_work_item_measurement_window_response,
    build_content_work_item_preflight_response,
    build_content_work_item_quality_review_response,
    build_content_work_item_revision_apply_response,
    build_content_work_item_revision_plan_response,
    build_content_work_item_sales_brief_response,
    build_content_work_item_snapshot_audit_response,
    build_content_work_item_snapshot_human_review_response,
    build_content_work_item_structured_draft_generation_response,
    build_content_work_item_structured_draft_preview_response,
    build_content_work_item_structured_draft_runtime_response,
    build_content_work_item_wordpress_draft_execution_response,
    build_content_work_item_wordpress_draft_handoff_response,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemDraftVariantsRequest,
    ContentWorkItemDraftVariantsResponse,
    ContentWorkItemHumanReviewRequest,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    ContentWorkItemQualityReviewRequest,
    ContentWorkItemQualityReviewResponse,
    ContentWorkItemRevisionApplyRequest,
    ContentWorkItemRevisionApplyResponse,
    ContentWorkItemRevisionPlanRequest,
    ContentWorkItemRevisionPlanResponse,
    ContentWorkItemSalesBriefRequest,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemSnapshotAuditRequest,
    ContentWorkItemSnapshotHumanReviewRequest,
    ContentWorkItemSnapshotResponse,
    ContentWorkItemStructuredDraftGenerationRequest,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemStructuredDraftPreviewRequest,
    ContentWorkItemStructuredDraftPreviewResponse,
    ContentWorkItemStructuredDraftRuntimeRequest,
    ContentWorkItemStructuredDraftRuntimeResponse,
    ContentWorkItemWordPressDraftExecutionRequest,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffRequest,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.queue import (
    ContentWorkItemQueueResponse,
    build_content_work_item_queue_response,
)
from wilq.content.workflow.store import content_workflow_store

router = APIRouter()


@router.get(
    "/api/content/knowledge-cards",
    response_model=ContentKnowledgeCardsResponse,
)
def content_knowledge_cards() -> ContentKnowledgeCardsResponse:
    return content_knowledge_cards_response()


@router.get(
    "/api/content/work-items/queue",
    response_model=ContentWorkItemQueueResponse,
)
def content_work_item_queue() -> ContentWorkItemQueueResponse:
    return build_content_work_item_queue_response(build_content_diagnostics())


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


@router.get(
    "/api/content/work-items/{work_item_id}/snapshot",
    response_model=ContentWorkItemSnapshotResponse,
)
def content_work_item_snapshot_for_selected_item(
    work_item_id: str,
) -> ContentWorkItemSnapshotResponse:
    return _snapshot_for_work_item_or_blocked_or_404(work_item_id)


@router.get(
    "/api/content/work-items/{work_item_id}/enrichment",
    response_model=ContentOpportunityEnrichmentResponse,
)
def content_work_item_enrichment(
    work_item_id: str,
) -> ContentOpportunityEnrichmentResponse:
    diagnostics = build_content_diagnostics()
    return build_content_opportunity_enrichment_response(
        diagnostics,
        work_item_id,
        queue=build_content_work_item_queue_response(diagnostics),
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
    "/api/content/work-items/{work_item_id}/human-review",
    response_model=ContentWorkItemHumanReviewResponse,
)
def content_work_item_human_review_for_selected_item(
    work_item_id: str,
    request: ContentWorkItemSnapshotHumanReviewRequest,
) -> ContentWorkItemHumanReviewResponse:
    response = _snapshot_for_work_item_or_404(
        work_item_id,
        human_review=request.review,
    ).human_review
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
    "/api/content/work-items/{work_item_id}/audit",
    response_model=ContentWorkItemWordPressDraftHandoffResponse,
)
def content_work_item_audit_for_selected_item(
    work_item_id: str,
    request: ContentWorkItemSnapshotAuditRequest,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    review = content_workflow_store().latest_human_review(work_item_id)
    response = _snapshot_for_work_item_or_404(
        work_item_id,
        human_review=review,
        audit=request.audit,
    ).wordpress_handoff
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
    "/api/content/work-items/draft-variants",
    response_model=ContentWorkItemDraftVariantsResponse,
)
def content_work_item_draft_variants(
    request: ContentWorkItemDraftVariantsRequest,
) -> ContentWorkItemDraftVariantsResponse:
    return build_content_work_item_draft_variants_response(request)


@router.post(
    "/api/content/work-items/structured-draft-runtime",
    response_model=ContentWorkItemStructuredDraftRuntimeResponse,
)
def content_work_item_structured_draft_runtime(
    request: ContentWorkItemStructuredDraftRuntimeRequest,
) -> ContentWorkItemStructuredDraftRuntimeResponse:
    return build_content_work_item_structured_draft_runtime_response(request)


@router.post(
    "/api/content/work-items/structured-draft-preview",
    response_model=ContentWorkItemStructuredDraftPreviewResponse,
)
def content_work_item_structured_draft_preview(
    request: ContentWorkItemStructuredDraftPreviewRequest,
) -> ContentWorkItemStructuredDraftPreviewResponse:
    return build_content_work_item_structured_draft_preview_response(request)


@router.post(
    "/api/content/work-items/{work_item_id}/structured-draft-preview",
    response_model=ContentWorkItemStructuredDraftPreviewResponse,
)
def content_work_item_structured_draft_preview_for_selected_item(
    work_item_id: str,
    request: ContentWorkItemStructuredDraftPreviewRequest,
) -> ContentWorkItemStructuredDraftPreviewResponse:
    _snapshot_for_work_item_or_404(work_item_id)
    _ensure_contract_matches_work_item(work_item_id, request)
    response = build_content_work_item_structured_draft_preview_response(request)
    if response.preview_result.preview is not None and request.output is not None:
        content_workflow_store().save_structured_output(work_item_id, request.output)
    return response


@router.post(
    "/api/content/work-items/quality-review",
    response_model=ContentWorkItemQualityReviewResponse,
)
def content_work_item_quality_review(
    request: ContentWorkItemQualityReviewRequest,
) -> ContentWorkItemQualityReviewResponse:
    return build_content_work_item_quality_review_response(request)


@router.post(
    "/api/content/work-items/{work_item_id}/quality-review",
    response_model=ContentWorkItemQualityReviewResponse,
)
def content_work_item_quality_review_for_selected_item(
    work_item_id: str,
    request: ContentWorkItemQualityReviewRequest,
) -> ContentWorkItemQualityReviewResponse:
    _snapshot_for_work_item_or_404(work_item_id)
    if request.item.id != work_item_id:
        raise HTTPException(
            status_code=400,
            detail="Content quality review item does not match the selected work item.",
        )
    response = build_content_work_item_quality_review_response(request)
    content_workflow_store().save_quality_review(response.quality_review)
    return response


@router.post(
    "/api/content/work-items/revision-plan",
    response_model=ContentWorkItemRevisionPlanResponse,
)
def content_work_item_revision_plan(
    request: ContentWorkItemRevisionPlanRequest,
) -> ContentWorkItemRevisionPlanResponse:
    return build_content_work_item_revision_plan_response(request)


@router.post(
    "/api/content/work-items/revision-apply",
    response_model=ContentWorkItemRevisionApplyResponse,
)
def content_work_item_revision_apply(
    request: ContentWorkItemRevisionApplyRequest,
) -> ContentWorkItemRevisionApplyResponse:
    return build_content_work_item_revision_apply_response(request)


@router.post(
    "/api/content/work-items/{work_item_id}/revision-plan",
    response_model=ContentWorkItemRevisionPlanResponse,
)
def content_work_item_revision_plan_for_selected_item(
    work_item_id: str,
    request: ContentWorkItemRevisionPlanRequest,
) -> ContentWorkItemRevisionPlanResponse:
    _snapshot_for_work_item_or_404(work_item_id)
    if request.item.id != work_item_id:
        raise HTTPException(
            status_code=400,
            detail="Content revision plan item does not match the selected work item.",
        )
    return build_content_work_item_revision_plan_response(request)


@router.post(
    "/api/content/work-items/{work_item_id}/revision-apply",
    response_model=ContentWorkItemRevisionApplyResponse,
)
def content_work_item_revision_apply_for_selected_item(
    work_item_id: str,
    request: ContentWorkItemRevisionApplyRequest,
) -> ContentWorkItemRevisionApplyResponse:
    _snapshot_for_work_item_or_404(work_item_id)
    if request.item.id != work_item_id:
        raise HTTPException(
            status_code=400,
            detail="Content revision application item does not match the selected work item.",
        )
    return build_content_work_item_revision_apply_response(request)


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


@router.post(
    "/api/content/work-items/measurement-outcome",
    response_model=ContentWorkItemMeasurementOutcomeResponse,
)
def content_work_item_measurement_outcome(
    request: ContentWorkItemMeasurementOutcomeRequest,
) -> ContentWorkItemMeasurementOutcomeResponse:
    return build_content_work_item_measurement_outcome_response(request)


def _snapshot_for_work_item_or_404(
    work_item_id: str,
    *,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    diagnostics = build_content_diagnostics()
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
        human_review=human_review,
        audit=audit,
    )
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Content work item is not available for the gated workflow.",
        )
    review = content_workflow_store().latest_human_review(work_item_id)
    if human_review is None and review is not None:
        audit_record = content_workflow_store().latest_audit_for_review(review.id)
        snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
            diagnostics,
            work_item_id,
            human_review=review,
            audit=audit_record,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail="Content work item is not available after review lookup.",
            )
    return snapshot


def _snapshot_for_work_item_or_blocked_or_404(
    work_item_id: str,
) -> ContentWorkItemSnapshotResponse:
    diagnostics = build_content_diagnostics()
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
    )
    if snapshot is not None:
        review = content_workflow_store().latest_human_review(work_item_id)
        if review is None:
            return snapshot
        audit_record = content_workflow_store().latest_audit_for_review(review.id)
        reviewed_snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
            diagnostics,
            work_item_id,
            human_review=review,
            audit=audit_record,
        )
        return snapshot if reviewed_snapshot is None else reviewed_snapshot
    blocked_snapshot = build_content_work_item_blocked_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
    )
    if blocked_snapshot is not None:
        return blocked_snapshot
    raise HTTPException(
        status_code=404,
        detail="Content work item is not available for the gated workflow.",
    )


def _ensure_contract_matches_work_item(
    work_item_id: str,
    request: ContentWorkItemStructuredDraftPreviewRequest,
) -> None:
    if request.contract is None:
        return
    if request.contract.model_input.work_item_id == work_item_id:
        return
    raise HTTPException(
        status_code=400,
        detail="Structured draft contract does not match the selected work item.",
    )
