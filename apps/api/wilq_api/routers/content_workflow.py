from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_catalog_routes import register_content_catalog_routes
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
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics_cached,
    build_content_freshness_assessment_fast,
)
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichmentResponse,
    build_content_opportunity_enrichment_response,
)
from wilq.content.workflow.api import (
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_snapshot_audit_response,
    build_content_work_item_snapshot_human_review_response,
    build_content_work_item_wordpress_draft_execution_response,
)
from wilq.content.workflow.content_html import content_html_from_markdown
from wilq.content.workflow.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionReviewRequest,
    ContentDraftRevisionReviewResponse,
    ContentDraftRevisionSaveRequest,
    ContentDraftRevisionSaveResponse,
    ContentWorkItemBlockedSnapshotResponse,
    ContentWorkItemBrowserSnapshotResponse,
    ContentWorkItemBrowserWorkflowSnapshotResponse,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemLearningProposalRequest,
    ContentWorkItemLearningProposalResponse,
    ContentWorkItemMeasurementCommand,
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemSnapshotAuditRequest,
    ContentWorkItemSnapshotHumanReviewRequest,
    ContentWorkItemWordPressDraftExecutionRequest,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.entry import (
    ContentWorkflowEntryResponse,
    build_content_workflow_entry,
)
from wilq.content.workflow.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.planning import ContentPlanningWorkspace
from wilq.content.workflow.queue import (
    ContentWorkItemQueueResponse,
    build_content_work_item_queue_response,
    build_selected_content_work_item_queue_response,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionConflict,
    ContentDraftRevisionReviewCommand,
    content_draft_package_digest,
)
from wilq.content.workflow.stage_measurement import (
    build_content_work_item_learning_proposal_response,
    build_content_work_item_measurement_outcome_response,
)
from wilq.content.workflow.store import content_workflow_store

router = APIRouter()


@router.get(
    "/api/content/work-items/queue",
    response_model=ContentWorkItemQueueResponse,
)
def content_work_item_queue(
    work_item_id: str | None = Query(default=None),
) -> ContentWorkItemQueueResponse:
    if work_item_id is not None:
        inventory_decision = inventory_decision_for_work_item(
            work_item_id,
            # A selected inventory item is the operator's explicit request to
            # open the workflow.  Keep this first read limited to the catalog;
            # the heavier WordPress material read belongs to the snapshot and
            # must not make the decision screen look like a stalled refresh.
            read_material=False,
            allow_material_pending=True,
        )
        if inventory_decision is not None:
            return build_selected_content_work_item_queue_response(
                inventory_decision,
                build_content_freshness_assessment_fast(
                    relevant_connector_ids=inventory_decision.source_connectors,
                ),
            )
    return build_content_work_item_queue_response(
        build_content_diagnostics_cached(),
        selected_work_item_id=work_item_id,
    )


@router.get(
    "/api/content/workflow-entry",
    response_model=ContentWorkflowEntryResponse,
)
def content_workflow_entry(
    search: str | None = Query(default=None, max_length=120),
) -> ContentWorkflowEntryResponse:
    return build_content_workflow_entry(search=search)


@router.get(
    "/api/content/work-items/snapshot",
    response_model=ContentWorkItemBrowserWorkflowSnapshotResponse,
)
def content_work_item_snapshot() -> ContentWorkItemBrowserWorkflowSnapshotResponse:
    return project_content_work_item_browser_snapshot(_snapshot_for_default_work_item_or_404())


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
        queue=build_content_work_item_queue_response(
            diagnostics,
            selected_work_item_id=work_item_id,
        ),
    )


def _build_editor_save_command(
    *,
    work_item_id: str,
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision | None,
    draft_package: ContentDraftPackage,
    planning: ContentPlanningWorkspace,
    final_canonical_url: str,
    revision_context_current: bool,
) -> ContentDraftRevisionAppendCommand:
    if (
        latest_revision is not None
        and latest_revision.schema_version == "wilq_content_draft_revision_v2"
        and request.base_revision_id == latest_revision.revision_id
        and latest_revision.planning_digest is not None
        and revision_context_current
    ):
        return ContentDraftRevisionAppendCommand(
            schema_version="wilq_content_draft_revision_v2",
            work_item_id=work_item_id,
            base_revision_id=latest_revision.revision_id,
            draft_package_id=latest_revision.draft_package_id,
            draft_package_digest=latest_revision.draft_package_digest,
            planning_digest=latest_revision.planning_digest,
            planning_input_digest=latest_revision.planning_input_digest,
            service_card_id=latest_revision.service_card_id,
            service_digest=latest_revision.service_digest,
            inventory_digest=latest_revision.inventory_digest,
            source_material_ids=latest_revision.source_material_ids,
            knowledge_card_ids=latest_revision.knowledge_card_ids,
            final_canonical_url=latest_revision.final_canonical_url,
            title=request.title,
            page_assets=(
                None
                if latest_revision.page_assets is None
                else latest_revision.page_assets.model_copy(
                    update={"wordpress_title": request.title}
                )
            ),
            sections=request.sections,
            faq=latest_revision.faq,
            cta_blocks=latest_revision.cta_blocks,
            internal_links=latest_revision.internal_links,
            proposal_metadata=(
                None
                if request.correction_reason == "canonical_html_alignment"
                else latest_revision.proposal_metadata
            ),
            correction_reason=request.correction_reason,
            created_by=request.created_by,
        )
    return ContentDraftRevisionAppendCommand(
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
        latest_revision is not None and request.base_revision_id == latest_revision.revision_id
    )
    if (
        draft_package is None
        or not final_canonical_url
        or planning is None
        or not planning.section_map_current
        or (latest_revision is None and not workspace.can_save)
        or (not workspace.can_save and request_would_create_child)
    ):
        return _workspace_conflict_response(
            code="workspace_not_saveable",
            snapshot=snapshot,
            safe_next_step=workspace.safe_next_step,
        )
    if request.correction_reason == "canonical_html_alignment":
        _validate_canonical_html_alignment(request, latest_revision)
    else:
        _validate_revision_sections(request, snapshot)

    command = _build_editor_save_command(
        work_item_id=work_item_id,
        request=request,
        latest_revision=latest_revision,
        draft_package=draft_package,
        planning=planning,
        final_canonical_url=final_canonical_url,
        revision_context_current=workspace.context_current,
    )
    result = content_workflow_store().append_draft_revision(command)
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
                None if workspace.latest_review is None else workspace.latest_review.decision_id
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
    "/api/content/work-items/measurement-window",
    response_model=ContentWorkItemMeasurementWindowResponse,
)
def content_work_item_measurement_window(
    request: ContentWorkItemMeasurementCommand,
) -> ContentWorkItemMeasurementWindowResponse:
    from wilq.content.measurement.evidence import (
        build_confirmed_deployment_measurement_window,
        load_content_measurement_facts,
    )
    from wilq.content.measurement.window import content_measurement_window_outcome_blockers
    from wilq.content.workflow.store_public_deployment import public_deployment

    snapshot = _snapshot_for_work_item_or_404(request.work_item_id)
    store = content_workflow_store()
    revision = next(
        (
            candidate
            for candidate in store.list_draft_revisions(request.work_item_id)
            if candidate.revision_id == request.revision_id
        ),
        None,
    )
    deployment = public_deployment(
        store, work_item_id=request.work_item_id, revision_id=request.revision_id
    )
    if revision is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wskazanej rewizji dokumentu.")
    if deployment is not None and deployment.revision_digest != revision.content_digest:
        deployment = None
    result = build_confirmed_deployment_measurement_window(
        deployment=deployment,
        metric_facts=(
            [] if deployment is None else load_content_measurement_facts(deployment.public_url)
        ),
    )
    response = ContentWorkItemMeasurementWindowResponse(
        item=snapshot.measurement_window.item,
        updated_item=(
            snapshot.measurement_window.item.model_copy(
                update={
                    "measurement_window_status": result.window.status,
                    "measurement_window_id": result.window.id,
                }
            )
            if result.window is not None
            else snapshot.measurement_window.item
        ),
        measurement_window_result=result,
        outcome_blockers=(
            content_measurement_window_outcome_blockers(result.window)
            if result.window is not None
            else []
        ),
    )
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


def _validate_canonical_html_alignment(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision | None,
) -> None:
    if latest_revision is None or request.base_revision_id != latest_revision.revision_id:
        raise HTTPException(
            status_code=409,
            detail="Korekta HTML wymaga aktualnej wersji bazowej.",
        )
    if request.title != latest_revision.title or len(request.sections) != len(
        latest_revision.sections
    ):
        raise HTTPException(
            status_code=422,
            detail="Korekta HTML nie może zmieniać zakresu wersji.",
        )
    changed_html = False
    for submitted, current in zip(request.sections, latest_revision.sections, strict=True):
        if (
            submitted.section_id != current.section_id
            or submitted.heading != current.heading
            or submitted.body_markdown != current.body_markdown
            or submitted.query_terms != current.query_terms
            or submitted.evidence_ids != current.evidence_ids
            or submitted.claim_ids != current.claim_ids
            or submitted.source_material_ids != current.source_material_ids
            or submitted.knowledge_card_ids != current.knowledge_card_ids
        ):
            raise HTTPException(
                status_code=422,
                detail="Korekta HTML może zmienić wyłącznie kanoniczne HTML sekcji.",
            )
        expected_html = content_html_from_markdown(current.body_markdown)
        if submitted.content_html != expected_html:
            raise HTTPException(
                status_code=422,
                detail="Korekta HTML musi wynikać dokładnie z Markdownu wersji bazowej.",
            )
        changed_html = changed_html or current.content_html != expected_html
    if not changed_html:
        raise HTTPException(
            status_code=422,
            detail="Wersja bazowa nie wymaga korekty kanonicznego HTML.",
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
    allowed_evidence = _revision_evidence_ids(latest_revision)
    unknown_evidence = sorted(set(request.evidence_ids).difference(allowed_evidence))
    if unknown_evidence:
        raise HTTPException(
            status_code=422,
            detail=(
                "Decyzja zawiera dowody spoza snapshotu tego zadania: "
                + ", ".join(unknown_evidence)
            ),
        )


def _revision_evidence_ids(revision: ContentDraftRevision) -> set[str]:
    """Return every evidence lineage attached to the persisted document."""

    return {
        evidence_id
        for evidence_ids in (
            *(section.evidence_ids for section in revision.sections),
            *(faq.evidence_ids for faq in revision.faq),
            *(cta.evidence_ids for cta in revision.cta_blocks),
            *(link.evidence_ids for link in revision.internal_links),
        )
        for evidence_id in evidence_ids
    }


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
register_content_catalog_routes(router)
