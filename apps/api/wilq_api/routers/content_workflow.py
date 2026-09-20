from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_catalog_routes import register_content_catalog_routes
from apps.api.wilq_api.routers.content_model_routes import (
    register_content_model_routes,
)
from apps.api.wilq_api.routers.content_production_classification import (
    register_content_production_classification_routes,
)
from apps.api.wilq_api.routers.content_refresh_preparation_authority import (
    content_refresh_preparation_authority,
)
from apps.api.wilq_api.routers.content_snapshot import (
    snapshot_for_work_item_or_404 as _snapshot_for_work_item_or_404,
)
from apps.api.wilq_api.routers.content_workflow_http import (
    revision_conflict_next_step,
)
from wilq.content.drafts.package import ContentDraftPackage
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
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.proposal_packet_binding import bind_research_packet
from wilq.content.regulatory.source_reviews import regulatory_source_review_store
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionReviewRequest,
    ContentDraftRevisionReviewResponse,
    ContentDraftRevisionSaveRequest,
    ContentDraftRevisionSaveResponse,
    ContentDraftRevisionWorkspace,
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
from wilq.content.workflow.documents.editor_child import (
    editor_child_official_source_references,
    editor_child_page_assets,
    request_has_full_document_fields,
    validate_full_document_child,
)
from wilq.content.workflow.documents.editor_child import (
    editor_child_retained_lineage as retained_lineage,
)
from wilq.content.workflow.documents.revision_save_validation import (
    RevisionValidationViolation,
    validate_canonical_html_alignment,
    validate_review_evidence,
    validate_revision_sections,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionConflict,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionState,
    content_draft_package_digest,
)
from wilq.content.workflow.material_review import read_content_material_review
from wilq.content.workflow.pipeline_steps.entry import (
    ContentWorkflowEntryResponse,
    build_content_workflow_entry,
)
from wilq.content.workflow.pipeline_steps.snapshot_assembly import (
    _gate_revision_workspace,
    build_content_draft_revision_workspace,
)
from wilq.content.workflow.pipeline_steps.stage_measurement import (
    build_content_work_item_learning_proposal_response,
    build_content_work_item_measurement_outcome_response,
)
from wilq.content.workflow.refresh_preparation import RefreshPreparationRuntimeAuthorized
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationBinding,
    refresh_preparation_bindings_match_authority,
)
from wilq.content.workflow.store.refresh_preparation_atomic import RefreshPreparationAtomicityError
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store

router = APIRouter()


def semantic_review_snapshot_for_work_item_or_404(
    work_item_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Rebuild semantic-review context from an immutable refresh binding.

    Refresh preparation selects a service card explicitly.  Semantic review
    must use that same persisted selection, otherwise the normal diagnostics
    matcher can produce a different planning input and falsely mark the exact
    revision context stale.
    """

    workflow_store = content_workflow_store()
    revision_state = workflow_store.load_draft_revision_state(work_item_id)
    revision = revision_state.latest_revision
    binding = None if revision is None else revision.refresh_preparation_binding
    if binding is None:
        assembled = _snapshot_for_work_item_or_404(work_item_id)
        return _apply_semantic_material_gate(
            assembled,
            work_item_id=work_item_id,
            revision_state=revision_state,
        )
    canonical = _snapshot_for_work_item_or_404(
        work_item_id,
        revision_state_override=revision_state,
        service_card_id_override=binding.service_card_id,
        prefer_revision_bound_proposal=True,
    )
    authorization = _persisted_refresh_authorization_for_binding(workflow_store, binding)
    if authorization is None:
        return _fail_closed_semantic_review_snapshot(canonical)
    if not _canonical_refresh_binding_matches_authority(
        canonical,
        binding=binding,
        authorization=authorization,
    ):
        return _fail_closed_semantic_review_snapshot(canonical)
    request = ContentPlanningProposalRequest(
        content_kind=binding.content_kind,
        service_card_id=binding.service_card_id,
        expected_planning_input_digest=authorization.planning_input_digest,
        requested_by="semantic_review",
        refresh_preparation_authorization_id=binding.authorization_id,
        expected_refresh_preparation_authorization_digest=binding.authorization_digest,
    )
    resolved = content_refresh_preparation_authority().resolve_planning(work_item_id, request)
    if not isinstance(resolved, RefreshPreparationRuntimeAuthorized):
        return _fail_closed_semantic_review_snapshot(canonical)
    if not _refresh_binding_matches_authority(
        binding,
        resolved.authorization,
    ):
        return _fail_closed_semantic_review_snapshot(canonical)
    bound_revision_workspace = _binding_aware_revision_workspace(
        resolved_snapshot=resolved.snapshot,
        canonical_snapshot=canonical,
        revision_state=revision_state,
    )
    return resolved.snapshot.model_copy(
        update={
            "planning_workspace": canonical.planning_workspace,
            "revision_workspace": bound_revision_workspace,
        }
    )


_SEMANTIC_REVIEW_REFRESH_AUTHORIZATION_NEXT_STEP = (
    "Odśwież exact przygotowanie refresh i użyj zapisanej autoryzacji dla tej rewizji; "
    "semantic review pozostaje zablokowane do czasu zgodności authorization, planu i packetu."
)


def _fail_closed_semantic_review_snapshot(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Make an invalid refresh authority visibly unusable for semantic review."""

    revision_workspace = snapshot.revision_workspace.model_copy(
        update={
            "can_review": False,
            "can_save": False,
            "safe_next_step": _SEMANTIC_REVIEW_REFRESH_AUTHORIZATION_NEXT_STEP,
        }
    )
    return snapshot.model_copy(
        update={
            "planning_workspace": None,
            "revision_workspace": revision_workspace,
        }
    )


def _canonical_refresh_binding_matches_authority(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    binding: ContentRefreshPreparationBinding,
    authorization: ContentRefreshPreparationAuthorization,
) -> bool:
    try:
        planning = snapshot.planning_workspace
        proposal = None if planning is None else planning.proposal
        proposal_binding = None if proposal is None else proposal.refresh_preparation_binding
        return bool(
            proposal_binding is not None
            and proposal_binding == binding
            and refresh_preparation_bindings_match_authority(
                proposal_binding,
                authorization.binding,
            )
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _refresh_binding_matches_authority(
    binding: ContentRefreshPreparationBinding,
    authorization: ContentRefreshPreparationAuthorization,
) -> bool:
    try:
        return (
            authorization.authorization_id == binding.authorization_id
            and authorization.authorization_digest == binding.authorization_digest
            and refresh_preparation_bindings_match_authority(
                binding,
                authorization.binding,
            )
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _persisted_refresh_authorization_for_binding(
    workflow_store: ContentWorkflowStore,
    binding: ContentRefreshPreparationBinding,
) -> ContentRefreshPreparationAuthorization | None:
    """Return only the exact authority receipt carried by a packet-bound revision."""

    try:
        authorization = workflow_store.load_refresh_preparation_authorization(
            binding.authorization_id
        )
    except (AttributeError, LookupError, TypeError, ValueError):
        return None
    if not isinstance(authorization, ContentRefreshPreparationAuthorization):
        return None
    if (
        authorization.authorization_id != binding.authorization_id
        or authorization.authorization_digest != binding.authorization_digest
    ):
        return None
    try:
        matches_authority = refresh_preparation_bindings_match_authority(
            binding,
            authorization.binding,
        )
    except (AttributeError, TypeError, ValueError):
        return None
    return authorization if matches_authority else None


def _binding_aware_revision_workspace(
    *,
    resolved_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    canonical_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_state: ContentDraftRevisionState,
) -> ContentDraftRevisionWorkspace:
    """Compose exact refresh plan with the draft package bound at draft creation.

    The authority snapshot validates the immutable refresh binding and retains
    the package used by the initial draft.  The canonical snapshot supplies the
    persisted revision-bound planning proposal.  Mixing both avoids a later
    baseline rebuild from marking the exact revision stale.
    """

    planning = canonical_snapshot.planning_workspace
    package = resolved_snapshot.draft_package.draft_package_result.draft_package
    if planning is None or package is None:
        return canonical_snapshot.revision_workspace
    workspace = _recompute_semantic_revision_workspace(
        assembled_snapshot=resolved_snapshot,
        planning_snapshot=canonical_snapshot,
        revision_state=revision_state,
        work_item_id=getattr(canonical_snapshot.preflight.item, "id", ""),
    )
    return workspace


def _apply_semantic_material_gate(
    assembled_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    work_item_id: str,
    revision_state: ContentDraftRevisionState,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Rebuild the exact workspace once material review can change its gate."""

    if (
        assembled_snapshot.planning_workspace is None
        or assembled_snapshot.revision_workspace is None
    ):
        return assembled_snapshot
    workspace = _recompute_semantic_revision_workspace(
        assembled_snapshot=assembled_snapshot,
        planning_snapshot=assembled_snapshot,
        revision_state=revision_state,
        work_item_id=work_item_id,
    )
    return assembled_snapshot.model_copy(update={"revision_workspace": workspace})


def _recompute_semantic_revision_workspace(
    *,
    assembled_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_state: ContentDraftRevisionState,
    work_item_id: str,
) -> ContentDraftRevisionWorkspace:
    planning = planning_snapshot.planning_workspace
    package = assembled_snapshot.draft_package.draft_package_result.draft_package
    workspace = planning_snapshot.revision_workspace
    if planning is None or package is None or workspace is None:
        raise ValueError("Semantic material gate requires planning, package and workspace.")
    rebuilt_workspace = build_content_draft_revision_workspace(
        item=planning_snapshot.preflight.item,
        draft_package=package,
        state=revision_state,
        structured_contract_present=(
            planning_snapshot.structured_generation.structured_generation_result.contract
            is not None
        ),
        planning_digest=(
            planning.proposal.planning_digest
            if getattr(planning, "section_map_current", True)
            else None
        ),
        planning_input_digest=planning.proposal.planning_input_digest,
        service_card_id=planning.proposal.service_card_id,
    )
    return _gate_revision_workspace(
        rebuilt_workspace,
        planning,
        material_confidence=_semantic_material_confidence(
            work_item_id=work_item_id,
            original_confidence=planning_snapshot.preflight.item.wordpress_content_material_confidence,
        ),
    )


def _semantic_material_confidence(
    *,
    work_item_id: str,
    original_confidence: str | None,
) -> str | None:
    """Remove only the material blocker after exact current receipt evaluation."""

    if original_confidence != "review_required" or not work_item_id:
        return original_confidence
    try:
        current = read_content_material_review(
            work_item_id=work_item_id,
            store=content_workflow_store(),
        )
    except (LookupError, RuntimeError, ValueError):
        return original_confidence
    return None if current.status == "approved_current" else original_confidence


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
        provenance, metadata = retained_lineage(latest_revision, request.correction_reason)
        official_sources = editor_child_official_source_references(request, latest_revision)
        return ContentDraftRevisionAppendCommand(
            schema_version="wilq_content_draft_revision_v2",
            work_item_id=work_item_id,
            base_revision_id=latest_revision.revision_id,
            draft_package_id=latest_revision.draft_package_id,
            draft_package_digest=latest_revision.draft_package_digest,
            planning_digest=latest_revision.planning_digest,
            planning_input_digest=latest_revision.planning_input_digest,
            research_packet_id=latest_revision.research_packet_id,
            research_packet_digest=latest_revision.research_packet_digest,
            content_kind=latest_revision.content_kind,
            service_card_id=latest_revision.service_card_id,
            service_digest=latest_revision.service_digest,
            inventory_digest=latest_revision.inventory_digest,
            source_material_ids=latest_revision.source_material_ids,
            knowledge_card_ids=latest_revision.knowledge_card_ids,
            source_provenance=provenance,
            final_canonical_url=latest_revision.final_canonical_url,
            title=request.title,
            page_assets=editor_child_page_assets(request, latest_revision),
            sections=request.sections,
            faq=latest_revision.faq if request.faq is None else request.faq,
            cta_blocks=latest_revision.cta_blocks,
            internal_links=latest_revision.internal_links,
            official_source_references=official_sources,
            proposal_metadata=metadata,
            refresh_preparation_binding=latest_revision.refresh_preparation_binding,
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
        content_kind=save_context.content_kind,
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
    snapshot = semantic_review_snapshot_for_work_item_or_404(work_item_id)
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    item = snapshot.preflight.item
    final_canonical_url = item.final_canonical_url or item.intended_final_url
    workspace = snapshot.revision_workspace
    planning = snapshot.planning_workspace
    latest_revision = workspace.latest_revision
    request_would_create_child = (
        latest_revision is not None and request.base_revision_id == latest_revision.revision_id
    )
    full_document_fields = request_has_full_document_fields(request)
    if (
        latest_revision is not None
        and full_document_fields
        and request.base_revision_id != latest_revision.revision_id
    ):
        return _workspace_conflict_response(
            code="stale_base",
            snapshot=snapshot,
            safe_next_step=revision_conflict_next_step("stale_base"),
        )
    if request_would_create_child and full_document_fields and not workspace.context_current:
        return _workspace_conflict_response(
            code="stale_context",
            snapshot=snapshot,
            safe_next_step=revision_conflict_next_step("stale_context"),
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
        _raise_revision_violation(validate_canonical_html_alignment(request, latest_revision))
    else:
        _raise_revision_violation(
            validate_revision_sections(
                request,
                snapshot,
                latest_revision=latest_revision,
                revision_context_current=workspace.context_current,
            )
        )
        _validate_full_document_request(request, latest_revision, workspace.context_current)

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
    try:
        with current_editor_draft_context_guard(
            lambda: _editor_save_context(
                semantic_review_snapshot_for_work_item_or_404(work_item_id)
            )
        ):
            result = content_workflow_store().append_draft_revision(command)
    except RefreshPreparationAtomicityError:
        return _workspace_conflict_response(
            code="stale_context",
            snapshot=snapshot,
            safe_next_step=revision_conflict_next_step("stale_context"),
        )
    if result.status == "conflict":
        if result.conflict is None:
            raise RuntimeError("Revision append conflict is missing conflict details.")
        return _revision_conflict_response(result.conflict)
    if result.revision is None:
        raise RuntimeError("Successful revision append is missing the saved revision.")

    refreshed = semantic_review_snapshot_for_work_item_or_404(work_item_id)
    return ContentDraftRevisionSaveResponse(
        status=result.status,
        revision=result.revision,
        workspace=refreshed.revision_workspace,
    )


def _validate_full_document_request(
    request: ContentDraftRevisionSaveRequest,
    latest_revision: ContentDraftRevision | None,
    revision_context_current: bool,
) -> None:
    try:
        validate_full_document_child(
            request,
            latest_revision,
            revision_context_current=revision_context_current,
            approved_source_urls={
                fact.source_id: fact.source_url_or_path
                for fact in regulatory_source_review_store().approved_source_facts()
            },
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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
    if proposal.planning_input_digest is None:
        return None
    if proposal.content_kind == "service":
        if service_card_id is None:
            return None
        planning_snapshot = with_explicit_content_service_selection(snapshot, service_card_id)
    else:
        if service_card_id is not None:
            return None
        planning_snapshot = snapshot
    planning_result = build_content_planning_input(
        planning_snapshot,
        service_card_id=service_card_id,
    )
    planning_input = planning_result.planning_input
    if planning_input is not None and proposal.research_packet_id is not None:
        planning_input, packet_block = bind_research_packet(
            snapshot=planning_snapshot,
            planning_input=planning_input,
            request=ContentPlanningProposalRequest(
                content_kind=proposal.content_kind,
                service_card_id=service_card_id,
                expected_planning_input_digest=planning_input.planning_input_digest,
                research_packet_id=proposal.research_packet_id,
                expected_research_packet_digest=proposal.research_packet_digest,
                requested_by="editor_save_context",
            ),
            require_packet=True,
        )
        if packet_block is not None:
            return None
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
        content_kind=proposal.content_kind,
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
    snapshot = semantic_review_snapshot_for_work_item_or_404(work_item_id)
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
    _raise_revision_violation(validate_review_evidence(request, snapshot))

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

    refreshed = semantic_review_snapshot_for_work_item_or_404(work_item_id)
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
    deployment = public_deployment(
        store,
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision.content_digest,
    )
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
    if revision is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wskazanej rewizji dokumentu.")
    deployment = public_deployment(
        store,
        work_item_id=request.work_item_id,
        revision_id=request.revision_id,
        revision_digest=revision.content_digest,
    )
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
    publication_source_connector = getattr(deployment, "publication_source_connector", None)
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


def _raise_revision_violation(violation: RevisionValidationViolation | None) -> None:
    if violation is not None:
        raise HTTPException(status_code=violation.status_code, detail=violation.detail)


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
    semantic_review_snapshot_loader=semantic_review_snapshot_for_work_item_or_404,
)
register_content_catalog_routes(router)
register_content_production_classification_routes(router)
