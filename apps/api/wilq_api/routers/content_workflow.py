from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_model_routes import (
    register_content_model_routes,
)
from apps.api.wilq_api.routers.content_snapshot import (
    snapshot_for_default_work_item_or_404 as _snapshot_for_default_work_item_or_404,
)
from apps.api.wilq_api.routers.content_snapshot import (
    snapshot_for_work_item_or_404 as _snapshot_for_work_item_or_404,
)
from apps.api.wilq_api.routers.content_snapshot import (
    snapshot_for_work_item_or_blocked_or_404 as _snapshot_for_work_item_or_blocked_or_404,
)
from apps.api.wilq_api.routers.content_workflow_http import (
    project_content_work_item_browser_snapshot,
    revision_conflict_next_step,
)
from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
from wilq.connectors.wordpress.authoring import (
    WordPressAuthoringProfile,
    build_wordpress_authoring_profile,
)
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichmentResponse,
    build_content_opportunity_enrichment_response,
)
from wilq.content.knowledge.cards import (
    ContentKnowledgeCardsResponse,
    content_knowledge_cards_response,
)
from wilq.content.knowledge.service_profile import (
    ContentServiceProfileResponse,
    content_service_profile_response,
)
from wilq.content.workflow.api import (
    build_content_wordpress_draft_activation_packet_response,
    build_content_wordpress_draft_write_readiness_response,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_quality_review_response,
    build_content_work_item_revision_apply_response,
    build_content_work_item_revision_plan_response,
    build_content_work_item_snapshot_audit_response,
    build_content_work_item_snapshot_human_review_response,
    build_content_work_item_wordpress_authoring_payload_preview_response,
    build_content_work_item_wordpress_draft_execution_response,
)
from wilq.content.workflow.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionReviewRequest,
    ContentDraftRevisionReviewResponse,
    ContentDraftRevisionSaveRequest,
    ContentDraftRevisionSaveResponse,
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
    ContentWordPressExistingDraftUpdateReadinessResponse,
    ContentWorkItemBlockedSnapshotResponse,
    ContentWorkItemBrowserSnapshotResponse,
    ContentWorkItemBrowserWorkflowSnapshotResponse,
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemHumanReviewRequest,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemLearningProposalRequest,
    ContentWorkItemLearningProposalResponse,
    ContentWorkItemMeasurementCommand,
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
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
    ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
    ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
    ContentWorkItemWordPressDraftExecutionRequest,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffRequest,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.planning import (
    ContentPlanningDecision,
    ContentPlanningProposal,
    ContentPlanningReviewRequest,
    ContentPlanningReviewResponse,
    ContentPlanningWorkspace,
)
from wilq.content.workflow.queue import (
    ContentWorkItemQueueResponse,
    build_content_work_item_queue_response,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionConflict,
    ContentDraftRevisionReviewCommand,
    content_draft_package_digest,
)
from wilq.content.workflow.service_selection import (
    ContentPlanningServiceSelection,
    ContentPlanningServiceSelectionError,
    resolve_content_planning_service_selection,
)
from wilq.content.workflow.stage_drafts import (
    build_content_work_item_draft_package_response,
)
from wilq.content.workflow.stage_measurement import (
    build_content_work_item_learning_proposal_response,
    build_content_work_item_measurement_outcome_response,
)
from wilq.content.workflow.stage_preparation import (
    build_content_work_item_preflight_response,
    build_content_work_item_sales_brief_response,
)
from wilq.content.workflow.stage_readiness import (
    build_content_wordpress_existing_draft_update_readiness_response,
)
from wilq.content.workflow.stage_review import (
    build_content_work_item_human_review_response,
    build_content_work_item_wordpress_draft_handoff_response,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas.core import utc_now

router = APIRouter()


@router.get(
    "/api/content/knowledge-cards",
    response_model=ContentKnowledgeCardsResponse,
)
def content_knowledge_cards() -> ContentKnowledgeCardsResponse:
    return content_knowledge_cards_response()


@router.get(
    "/api/content/service-profile",
    response_model=ContentServiceProfileResponse,
)
def content_service_profile() -> ContentServiceProfileResponse:
    return content_service_profile_response()


@router.get(
    "/api/content/wordpress/authoring-profile",
    response_model=WordPressAuthoringProfile,
)
def content_wordpress_authoring_profile() -> WordPressAuthoringProfile:
    return build_wordpress_authoring_profile(
        "wordpress_ekologus",
        include_dev_content=True,
    )


@router.get(
    "/api/content/wordpress/draft-write-readiness",
    response_model=ContentWordPressDraftWriteReadinessResponse,
)
def content_wordpress_draft_write_readiness(
    action_id: str = "act_prepare_wordpress_draft_handoff",
) -> ContentWordPressDraftWriteReadinessResponse:
    return build_content_wordpress_draft_write_readiness_response(action_id=action_id)


@router.get(
    "/api/content/wordpress/existing-draft-update-readiness",
    response_model=ContentWordPressExistingDraftUpdateReadinessResponse,
)
def content_wordpress_existing_draft_update_readiness(
    work_item_id: str | None = None,
) -> ContentWordPressExistingDraftUpdateReadinessResponse:
    snapshot = (
        _snapshot_for_work_item_or_404(work_item_id)
        if work_item_id is not None
        else _snapshot_for_default_work_item_or_404()
    )
    return build_content_wordpress_existing_draft_update_readiness_response(snapshot)


@router.get(
    "/api/content/wordpress/draft-activation-packet",
    response_model=ContentWordPressDraftActivationPacketResponse,
)
def content_wordpress_draft_activation_packet(
    work_item_id: str | None = None,
) -> ContentWordPressDraftActivationPacketResponse:
    if work_item_id is not None:
        return build_content_wordpress_draft_activation_packet_response(
            _snapshot_for_work_item_or_404(work_item_id),
            latest_execution_result=content_workflow_store().latest_wordpress_draft_execution(
                work_item_id
            ),
        )
    snapshot = _snapshot_for_default_work_item_or_404()
    return build_content_wordpress_draft_activation_packet_response(
        snapshot,
        latest_execution_result=content_workflow_store().latest_wordpress_draft_execution(
            snapshot.preflight.item.id
        ),
    )


@router.get(
    "/api/content/work-items/queue",
    response_model=ContentWorkItemQueueResponse,
)
def content_work_item_queue() -> ContentWorkItemQueueResponse:
    return build_content_work_item_queue_response(build_content_diagnostics_cached())


@router.get(
    "/api/content/work-items/snapshot",
    response_model=ContentWorkItemBrowserWorkflowSnapshotResponse,
)
def content_work_item_snapshot() -> ContentWorkItemBrowserWorkflowSnapshotResponse:
    return project_content_work_item_browser_snapshot(
        _snapshot_for_default_work_item_or_404()
    )


@router.get(
    "/api/content/work-items/{work_item_id}/snapshot",
    response_model=ContentWorkItemBrowserSnapshotResponse,
)
def content_work_item_snapshot_for_selected_item(
    work_item_id: str,
) -> ContentWorkItemBrowserSnapshotResponse:
    snapshot = _snapshot_for_work_item_or_blocked_or_404(work_item_id)
    if isinstance(snapshot, ContentWorkItemBlockedSnapshotResponse):
        return snapshot
    return project_content_work_item_browser_snapshot(snapshot)


@router.get(
    "/api/content/work-items/{work_item_id}/enrichment",
    response_model=ContentOpportunityEnrichmentResponse,
)
def content_work_item_enrichment(
    work_item_id: str,
) -> ContentOpportunityEnrichmentResponse:
    diagnostics = build_content_diagnostics_cached()
    return build_content_opportunity_enrichment_response(
        diagnostics,
        work_item_id,
        queue=build_content_work_item_queue_response(diagnostics),
    )


@router.post(
    "/api/content/work-items/{work_item_id}/planning-review",
    response_model=ContentPlanningReviewResponse,
)
def content_work_item_planning_review(
    work_item_id: str,
    request: ContentPlanningReviewRequest,
) -> ContentPlanningReviewResponse:
    snapshot = _snapshot_for_work_item_or_404(work_item_id)
    workspace = snapshot.planning_workspace
    if workspace is None or (
        request.expected_planning_digest != workspace.proposal.planning_digest
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Plan treści zmienił się. Odśwież element przed zapisaniem decyzji."
            ),
        )
    if request.stage == "section_map" and not workspace.scope_current:
        raise HTTPException(
            status_code=409,
            detail="Najpierw zatwierdź aktualny zakres treści.",
        )
    if (
        request.stage == "section_map"
        and request.service_card_id is not None
        and request.service_card_id != workspace.proposal.service_card_id
    ):
        raise HTTPException(
            status_code=422,
            detail="Usługę można zmienić tylko podczas review zakresu.",
        )
    try:
        selection = resolve_content_planning_service_selection(
            snapshot.service_profile_context,
            request.service_card_id,
        )
    except ContentPlanningServiceSelectionError as error:
        _raise_service_selection_http_error(error)
    selected_proposal = _planning_proposal_for_service_selection(
        work_item_id,
        workspace,
        request,
        selection,
    )
    status, decision = content_workflow_store().record_planning_review(
        work_item_id,
        request,
        planning_digest=selected_proposal.planning_digest,
        service_card_id=selection.service_card_id,
        human_override_review_required=selection.human_override_review_required,
    )
    refreshed = _snapshot_for_work_item_or_404(work_item_id)
    if refreshed.planning_workspace is None:
        raise RuntimeError("Planning review succeeded without a planning workspace.")
    return ContentPlanningReviewResponse(
        status="recorded" if status == "created" else "idempotent",
        decision=decision,
        planning_workspace=refreshed.planning_workspace,
    )


def _raise_service_selection_http_error(
    error: ContentPlanningServiceSelectionError,
) -> NoReturn:
    if error.code == "candidate_not_allowed":
        raise HTTPException(
            status_code=422,
            detail="Wybrana karta usługi nie jest dozwolona dla tego work itemu.",
        ) from error
    raise HTTPException(
        status_code=409,
        detail="Brakuje aktualnej rekomendacji usługi. Odśwież work item.",
    ) from error


def _planning_proposal_for_service_selection(
    work_item_id: str,
    workspace: ContentPlanningWorkspace,
    request: ContentPlanningReviewRequest,
    selection: ContentPlanningServiceSelection,
) -> ContentPlanningProposal:
    if request.stage != "scope":
        return workspace.proposal
    transient_scope = ContentPlanningDecision(
        decision_id="content_planning_review_transient_service_selection",
        decision_number=(
            1
            if workspace.scope_decision is None
            else workspace.scope_decision.decision_number + 1
        ),
        work_item_id=work_item_id,
        stage="scope",
        planning_digest=request.expected_planning_digest,
        service_card_id=selection.service_card_id,
        human_override_review_required=selection.human_override_review_required,
        decision=request.decision,
        reviewed_by=request.reviewed_by,
        checked_items=request.checked_items,
        notes=request.notes,
        created_at=utc_now(),
    )
    transient_snapshot = _snapshot_for_work_item_or_404(
        work_item_id,
        planning_decisions_override=[transient_scope],
    )
    if transient_snapshot.planning_workspace is None:
        raise HTTPException(
            status_code=409,
            detail="Nie udało się zbudować planu dla wybranej usługi.",
        )
    return transient_snapshot.planning_workspace.proposal


@router.post(
    "/api/content/work-items/{work_item_id}/draft-revisions",
    response_model=ContentDraftRevisionSaveResponse,
    responses={409: {"model": ContentDraftRevisionConflictResponse}},
)
def content_work_item_draft_revision_save(
    work_item_id: str,
    request: ContentDraftRevisionSaveRequest,
) -> ContentDraftRevisionSaveResponse | JSONResponse:
    snapshot = _snapshot_for_work_item_or_404(work_item_id)
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    item = snapshot.preflight.item
    final_canonical_url = item.final_canonical_url or item.intended_final_url
    workspace = snapshot.revision_workspace
    planning = snapshot.planning_workspace
    latest_revision = workspace.latest_revision
    request_would_create_child = (
        latest_revision is not None
        and request.base_revision_id == latest_revision.revision_id
    )
    if (
        draft_package is None
        or not final_canonical_url
        or planning is None
        or not planning.scope_current
        or not planning.section_map_current
        or (latest_revision is None and not workspace.can_save)
        or (not workspace.can_save and request_would_create_child)
    ):
        return _workspace_conflict_response(
            code="workspace_not_saveable",
            snapshot=snapshot,
            safe_next_step=workspace.safe_next_step,
        )
    _validate_revision_sections(request, snapshot)

    result = content_workflow_store().append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=work_item_id,
            base_revision_id=request.base_revision_id,
            draft_package_id=draft_package.id,
            draft_package_digest=content_draft_package_digest(draft_package),
            planning_digest=planning.proposal.planning_digest,
            final_canonical_url=final_canonical_url,
            title=request.title,
            sections=request.sections,
            created_by=request.created_by,
        )
    )
    if result.status == "conflict":
        if result.conflict is None:
            raise RuntimeError("Revision append conflict is missing conflict details.")
        return _revision_conflict_response(result.conflict)
    if result.revision is None:
        raise RuntimeError("Successful revision append is missing the saved revision.")

    refreshed = _snapshot_for_work_item_or_404(work_item_id)
    return ContentDraftRevisionSaveResponse(
        status=result.status,
        revision=result.revision,
        workspace=refreshed.revision_workspace,
    )


@router.post(
    "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review",
    response_model=ContentDraftRevisionReviewResponse,
    responses={409: {"model": ContentDraftRevisionConflictResponse}},
)
def content_work_item_draft_revision_review(
    work_item_id: str,
    revision_id: str,
    request: ContentDraftRevisionReviewRequest,
) -> ContentDraftRevisionReviewResponse | JSONResponse:
    snapshot = _snapshot_for_work_item_or_404(work_item_id)
    workspace = snapshot.revision_workspace
    latest_revision = workspace.latest_revision
    idempotent_retry = _review_request_matches_latest(
        request=request,
        revision_id=revision_id,
        snapshot=snapshot,
    )
    if latest_revision is None or (not workspace.can_review and not idempotent_retry):
        return _workspace_conflict_response(
            code="revision_not_reviewable",
            snapshot=snapshot,
            safe_next_step=workspace.safe_next_step,
        )
    _validate_review_evidence(request, snapshot)

    result = content_workflow_store().review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=work_item_id,
            revision_id=revision_id,
            revision_digest=request.expected_revision_digest,
            base_decision_id=(
                None
                if workspace.latest_review is None
                else workspace.latest_review.decision_id
            ),
            reviewed_by=request.reviewed_by,
            decision=request.decision,
            notes=request.notes,
            checked_items=request.checked_items,
            evidence_ids=request.evidence_ids,
        )
    )
    if result.status == "conflict":
        if result.conflict is None:
            raise RuntimeError("Revision review conflict is missing conflict details.")
        return _revision_conflict_response(result.conflict)
    if result.review is None:
        raise RuntimeError("Successful revision review is missing the saved decision.")

    refreshed = _snapshot_for_work_item_or_404(work_item_id)
    return ContentDraftRevisionReviewResponse(
        status="recorded" if result.status == "created" else "idempotent",
        review=result.review,
        workspace=refreshed.revision_workspace,
    )


@router.post(
    "/api/content/work-items/snapshot/human-review",
    response_model=ContentWorkItemHumanReviewResponse,
)
def content_work_item_snapshot_human_review(
    request: ContentWorkItemSnapshotHumanReviewRequest,
) -> ContentWorkItemHumanReviewResponse:
    response = build_content_work_item_snapshot_human_review_response(
        build_content_diagnostics_cached(),
        request,
    )
    if response.review_recordable and response.review is not None:
        content_workflow_store().save_human_review(response.review)
        return response.model_copy(update={"review_recorded": True})
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
    if response.review_recordable and response.review is not None:
        content_workflow_store().save_human_review(response.review)
        return response.model_copy(update={"review_recorded": True})
    return response


@router.post(
    "/api/content/work-items/snapshot/audit",
    response_model=ContentWorkItemWordPressDraftHandoffResponse,
)
def content_work_item_snapshot_audit(
    request: ContentWorkItemSnapshotAuditRequest,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    diagnostics = build_content_diagnostics_cached()
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
    response = build_content_work_item_wordpress_draft_execution_response(request)
    if (
        request.handoff is not None
        and response.execution_result.status == "created"
        and response.execution_result.wordpress_post_id
    ):
        content_workflow_store().save_wordpress_draft_execution(
            request.handoff.work_item_id,
            response.execution_result,
        )
    return response


@router.post(
    "/api/content/work-items/wordpress-authoring-payload-preview",
    response_model=ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
)
def content_work_item_wordpress_authoring_payload_preview(
    request: ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
) -> ContentWorkItemWordPressAuthoringPayloadPreviewResponse:
    return build_content_work_item_wordpress_authoring_payload_preview_response(request)


@router.post(
    "/api/content/work-items/measurement-window",
    response_model=ContentWorkItemMeasurementWindowResponse,
)
def content_work_item_measurement_window(
    request: ContentWorkItemMeasurementCommand,
) -> ContentWorkItemMeasurementWindowResponse:
    response = _snapshot_for_work_item_or_404(request.work_item_id).measurement_window
    window = response.measurement_window_result.window
    if window is not None:
        content_workflow_store().save_measurement_window(window)
    return response


@router.post(
    "/api/content/work-items/measurement-outcome",
    response_model=ContentWorkItemMeasurementOutcomeResponse,
)
def content_work_item_measurement_outcome(
    request: ContentWorkItemMeasurementOutcomeRequest,
) -> ContentWorkItemMeasurementOutcomeResponse:
    try:
        return build_content_work_item_measurement_outcome_response(request)
    except LookupError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/api/content/work-items/learning-proposal",
    response_model=ContentWorkItemLearningProposalResponse,
)
def content_work_item_learning_proposal(
    request: ContentWorkItemLearningProposalRequest,
) -> ContentWorkItemLearningProposalResponse:
    try:
        return build_content_work_item_learning_proposal_response(request)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _validate_revision_sections(
    request: ContentDraftRevisionSaveRequest,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> None:
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    if draft_package is None:
        raise HTTPException(status_code=422, detail="Brakuje pakietu sekcji do zapisu wersji.")
    request_headings = [section.heading for section in request.sections]
    expected_headings = [section.heading for section in draft_package.sections]
    if request_headings != expected_headings:
        raise HTTPException(
            status_code=422,
            detail=(
                "Zapisywana wersja musi zawierać dokładnie wszystkie sekcje "
                "zatwierdzonego planu, w tej samej kolejności."
            ),
        )
    for section, expected_section in zip(
        request.sections,
        draft_package.sections,
        strict=True,
    ):
        if section.evidence_ids != expected_section.evidence_ids:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Dowody sekcji muszą dokładnie odpowiadać zatwierdzonemu planowi: "
                    + section.heading
                ),
            )


def _validate_review_evidence(
    request: ContentDraftRevisionReviewRequest,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> None:
    latest_revision = snapshot.revision_workspace.latest_revision
    if latest_revision is None:
        raise HTTPException(
            status_code=422,
            detail="Brakuje zapisanej wersji, której dowody można sprawdzić.",
        )
    allowed_evidence = {
        evidence_id for section in latest_revision.sections for evidence_id in section.evidence_ids
    }
    unknown_evidence = sorted(set(request.evidence_ids).difference(allowed_evidence))
    if unknown_evidence:
        raise HTTPException(
            status_code=422,
            detail=(
                "Decyzja zawiera dowody spoza snapshotu tego zadania: "
                + ", ".join(unknown_evidence)
            ),
        )


def _review_request_matches_latest(
    *,
    request: ContentDraftRevisionReviewRequest,
    revision_id: str,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> bool:
    review = snapshot.revision_workspace.latest_review
    if review is None:
        return False
    return (
        review.revision_id == revision_id
        and review.revision_digest == request.expected_revision_digest
        and review.reviewed_by == request.reviewed_by
        and review.decision == request.decision
        and review.notes == request.notes
        and review.checked_items == request.checked_items
        and review.evidence_ids == request.evidence_ids
    )


def _workspace_conflict_response(
    *,
    code: ContentDraftRevisionPublicConflictCode,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    safe_next_step: str,
) -> JSONResponse:
    latest_revision = snapshot.revision_workspace.latest_revision
    payload = ContentDraftRevisionConflictResponse(
        code=code,
        current_revision_id=(None if latest_revision is None else latest_revision.revision_id),
        current_digest=(None if latest_revision is None else latest_revision.content_digest),
        safe_next_step=safe_next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


def _revision_conflict_response(conflict: ContentDraftRevisionConflict) -> JSONResponse:
    payload = ContentDraftRevisionConflictResponse(
        code=conflict.code,
        current_revision_id=conflict.current_revision_id,
        current_digest=conflict.current_revision_digest,
        safe_next_step=revision_conflict_next_step(conflict.code),
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


register_content_model_routes(
    router,
    snapshot_loader=_snapshot_for_work_item_or_404,
)
