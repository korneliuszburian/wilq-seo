from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_catalog_routes import register_content_catalog_routes
from apps.api.wilq_api.routers.content_model_routes import (
    register_content_model_routes,
)
from apps.api.wilq_api.routers.content_snapshot import (
    snapshot_for_work_item_or_404 as _snapshot_for_work_item_or_404,
)
from apps.api.wilq_api.routers.content_workflow_http import (
    revision_conflict_next_step,
)
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftSection
from wilq.content.measurement.deployment import ContentPublicDeployment
from wilq.content.measurement.read_contracts import (
    ContentMeasurementReadResponse,
    build_content_measurement_read,
)
from wilq.content.planning.dynamic_input import (
    build_content_planning_input,
    content_planning_inventory_digest,
)
from wilq.content.planning.generated_proposal import (
    with_explicit_content_service_selection,
)
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionReviewRequest,
    ContentDraftRevisionReviewResponse,
    ContentDraftRevisionSaveRequest,
    ContentDraftRevisionSaveResponse,
    ContentWorkItemLearningProposalRequest,
    ContentWorkItemLearningProposalResponse,
    ContentWorkItemMeasurementCommand,
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.planning import ContentPlanningWorkspace
from wilq.content.workflow.documents.codex_revision_commit import (
    ContentDraftRevisionContext,
    current_editor_draft_context_guard,
)
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionConflict,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionSection,
    content_draft_package_digest,
)
from wilq.content.workflow.pipeline_steps.entry import (
    ContentWorkflowEntryResponse,
    build_content_workflow_entry,
)
from wilq.content.workflow.pipeline_steps.stage_measurement import (
    build_content_work_item_learning_proposal_response,
    build_content_work_item_measurement_outcome_response,
)
from wilq.content.workflow.store.store import content_workflow_store

router = APIRouter()


@router.get(
    "/api/content/workflow-entry",
    response_model=ContentWorkflowEntryResponse,
)
def content_workflow_entry(
    search: str | None = Query(default=None, max_length=120),
) -> ContentWorkflowEntryResponse:
    return build_content_workflow_entry(search=search)


def _build_editor_save_command(
    *,
    work_item_id: str,
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision | None,
    draft_package: ContentDraftPackage,
    planning: ContentPlanningWorkspace,
    final_canonical_url: str,
    revision_context_current: bool,
    save_context: ContentDraftRevisionContext | None = None,
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
            official_source_references=latest_revision.official_source_references,
            # An editor save is a human-authored child revision, not a replay
            # of the parent Codex completion. The immutable base revision
            # retains the original proposal/run lineage; carrying that run ID
            # into this child would incorrectly require a second completion.
            proposal_metadata=None,
            correction_reason=request.correction_reason,
            created_by=request.created_by,
        )
    if save_context is None:
        raise ValueError("Editor save requires an exact current context binding.")
    return ContentDraftRevisionAppendCommand(
        work_item_id=work_item_id,
        base_revision_id=request.base_revision_id,
        draft_package_id=draft_package.id,
        draft_package_digest=content_draft_package_digest(draft_package),
        planning_digest=planning.proposal.planning_digest,
        planning_input_digest=save_context.planning_input_digest,
        service_card_id=save_context.service_card_id,
        inventory_digest=save_context.inventory_digest,
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
        _validate_revision_sections(
            request,
            snapshot,
            latest_revision=latest_revision,
            revision_context_current=workspace.context_current,
        )

    save_context = _editor_save_context(snapshot)
    if save_context is None:
        return _workspace_conflict_response(
            code="stale_context",
            snapshot=snapshot,
            safe_next_step=revision_conflict_next_step("stale_context"),
        )

    command = _build_editor_save_command(
        work_item_id=work_item_id,
        request=request,
        latest_revision=latest_revision,
        draft_package=draft_package,
        planning=planning,
        final_canonical_url=final_canonical_url,
        revision_context_current=workspace.context_current,
        save_context=save_context,
    )
    with current_editor_draft_context_guard(
        lambda: _editor_save_context(_snapshot_for_work_item_or_404(work_item_id))
    ):
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


def _editor_save_context(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentDraftRevisionContext | None:
    planning = snapshot.planning_workspace
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    item = snapshot.preflight.item
    final_canonical_url = item.final_canonical_url or item.intended_final_url
    if planning is None or draft_package is None or not final_canonical_url:
        return None
    proposal = planning.proposal
    service_card_id = proposal.service_card_id
    if service_card_id is None or proposal.planning_input_digest is None:
        return None
    planning_snapshot = with_explicit_content_service_selection(snapshot, service_card_id)
    planning_result = build_content_planning_input(
        planning_snapshot,
        service_card_id=service_card_id,
    )
    planning_input = planning_result.planning_input
    if (
        planning_input is None
        or planning_input.planning_input_digest != proposal.planning_input_digest
    ):
        return None
    return ContentDraftRevisionContext(
        work_item_id=item.id,
        draft_package_id=draft_package.id,
        draft_package_digest=content_draft_package_digest(draft_package),
        planning_digest=proposal.planning_digest,
        planning_input_digest=planning_input.planning_input_digest,
        service_card_id=service_card_id,
        inventory_digest=content_planning_inventory_digest(planning_input.inventory),
        final_canonical_url=final_canonical_url,
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


@router.get(
    "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/measurement",
    response_model=ContentMeasurementReadResponse,
)
def content_work_item_measurement_read(
    work_item_id: str,
    revision_id: str,
) -> ContentMeasurementReadResponse:
    from wilq.content.workflow.store.store_public_deployment import public_deployment

    store = content_workflow_store()
    revision = next(
        (
            candidate
            for candidate in store.list_draft_revisions(work_item_id)
            if candidate.revision_id == revision_id
        ),
        None,
    )
    if revision is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wskazanej rewizji dokumentu.")
    deployment = public_deployment(store, work_item_id=work_item_id, revision_id=revision_id)
    return build_content_measurement_read(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision.content_digest,
        deployment=deployment,
    )


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
    from wilq.content.workflow.store.store_public_deployment import public_deployment

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
    item = _measurement_item_for_revision(revision, deployment)
    response = ContentWorkItemMeasurementWindowResponse(
        item=item,
        updated_item=(
            item.model_copy(
                update={
                    "measurement_window_status": result.window.status,
                    "measurement_window_id": result.window.id,
                }
            )
            if result.window is not None
            else item
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


def _measurement_item_for_revision(
    revision: ContentDraftRevision,
    deployment: ContentPublicDeployment | None,
) -> ContentWorkItem:
    """Project only persisted revision/deployment facts for measurement.

    Measurement begins after a confirmed public deployment, so it must not
    require the transient diagnostics queue that first introduced an existing
    page.  The compatibility response still carries a ``ContentWorkItem``, but
    this narrow projection is derived solely from the exact revision and its
    exact deployment.
    """

    public_url = getattr(deployment, "public_url", None)
    publication_evidence_id = getattr(deployment, "publication_evidence_id", None)
    publication_source_connector = getattr(
        deployment, "publication_source_connector", None
    )
    return ContentWorkItem(
        id=revision.work_item_id,
        topic=getattr(revision, "title", "Zmierzony dokument"),
        source_public_url=public_url,
        final_canonical_url=public_url,
        intended_final_url=public_url,
        wordpress_title_or_h1=getattr(revision, "title", None),
        evidence_ids=[] if publication_evidence_id is None else [publication_evidence_id],
        source_connectors=(
            [] if publication_source_connector is None else [publication_source_connector]
        ),
        wordpress_post_id=getattr(deployment, "wordpress_post_id", None),
    )


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
    *,
    latest_revision: ContentDraftRevision | None,
    revision_context_current: bool,
) -> None:
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    if draft_package is None:
        raise HTTPException(status_code=422, detail="Brakuje pakietu sekcji do zapisu wersji.")
    request_headings = [section.heading for section in request.sections]
    # A current v2 child edits the exact immutable document. Its body can have
    # been generated from a richer planning proposal than the legacy editor
    # package, so validate its section contract against that exact parent.
    # A stale parent remains bound to the current package and cannot bypass the
    # normal current-context gate below.
    expected_sections: Sequence[ContentDraftSection | ContentDraftRevisionSection] = (
        latest_revision.sections
        if (
            latest_revision is not None
            and latest_revision.schema_version == "wilq_content_draft_revision_v2"
            and request.base_revision_id == latest_revision.revision_id
            and revision_context_current
        )
        else draft_package.sections
    )
    expected_headings = [section.heading for section in expected_sections]
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
        expected_sections,
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
