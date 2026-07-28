from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import content_codex_app_server_client
from apps.api.wilq_api.routers.content_workflow_http import revision_conflict_next_step
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputReadinessResponse,
    build_new_page_planning_input,
    content_planning_input_readiness,
)
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.planning.new_page_proposal import (
    ContentNewPagePlanningProposalRequest,
    ContentNewPagePlanningProposalWorkspace,
    build_new_page_planning_proposal_workspace,
    generate_new_page_planning_proposal,
    queue_new_page_planning_proposal,
    terminalize_new_page_planning_claim,
)
from wilq.content.workflow.catalog import build_content_inventory_catalog_cached
from wilq.content.workflow.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionReviewRequest,
)
from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPageBriefInput,
    ContentNewPageBriefWorkspace,
    ContentNewPageFoundationCommand,
    ContentNewPageFoundationResult,
    ContentNewPagePlanningFoundation,
    build_new_page_brief_workspace,
    build_new_page_overlap_guard,
    build_new_page_planning_foundation,
    new_page_service_card,
)
from wilq.content.workflow.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
    ContentNewPageDocumentReviewPrerequisiteConflict,
    ContentNewPagePlanningReviewCommand,
    build_new_page_canonical_document_workspace,
)
from wilq.content.workflow.new_page_initial_draft import generate_new_page_initial_draft
from wilq.content.workflow.new_page_revision import (
    ContentNewPageRevisionReviewResponse,
    review_new_page_revision,
)
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.store_new_page import new_page_brief_store
from wilq.storage.local_state import local_state_store

_NEW_PAGE_PLANNING_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="wilq-new-page-plan",
)


def register_content_new_page_brief_routes(router: APIRouter) -> None:
    @router.post(
        "/api/content/new-page-briefs",
        response_model=ContentNewPageBriefWorkspace,
    )
    def create_content_new_page_brief(
        request: ContentNewPageBriefInput,
    ) -> ContentNewPageBriefWorkspace:
        brief = new_page_brief_store().create_new_page_brief(request)
        return build_new_page_brief_workspace(brief)

    @router.get(
        "/api/content/new-page-briefs/{brief_id}",
        response_model=ContentNewPageBriefWorkspace,
    )
    def content_new_page_brief_workspace(brief_id: str) -> ContentNewPageBriefWorkspace:
        brief = new_page_brief_store().load_new_page_brief(brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
        return build_new_page_brief_workspace(
            brief,
            foundation=new_page_brief_store().load_new_page_foundation(brief_id),
        )

    register_content_new_page_continuation_routes(router)


def register_content_new_page_continuation_routes(router: APIRouter) -> None:
    @router.get(
        "/api/content/new-page-briefs/{brief_id}/planning-input",
        response_model=ContentPlanningInputReadinessResponse,
    )
    def content_new_page_planning_input_readiness(
        brief_id: str,
    ) -> ContentPlanningInputReadinessResponse:
        """Read the current, exact input to planning without generating a plan."""

        store = new_page_brief_store()
        brief = store.load_new_page_brief(brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
        foundation = store.load_new_page_foundation(brief_id)
        guard = build_new_page_overlap_guard(
            brief,
            catalog=build_content_inventory_catalog_cached(),
        )
        service_card = (
            new_page_service_card(foundation.service_card_id)
            if foundation is not None
            else None
        )
        result = build_new_page_planning_input(
            brief=brief,
            foundation=foundation,
            overlap_guard=guard,
            service_card=service_card,
        )
        return content_planning_input_readiness(
            result,
            work_item_id=foundation.work_item_id if foundation is not None else None,
        )

    register_content_new_page_planning_proposal_routes(router)
    register_content_new_page_document_routes(router)

    @router.post(
        "/api/content/new-page-briefs/{brief_id}/planning-foundation",
        response_model=ContentNewPageFoundationResult,
        responses={409: {"model": ContentNewPageFoundationResult}},
    )
    def create_content_new_page_planning_foundation(
        brief_id: str,
        request: ContentNewPageFoundationCommand,
    ) -> ContentNewPageFoundationResult | JSONResponse:
        store = new_page_brief_store()
        brief = store.load_new_page_brief(brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
        guard = build_new_page_overlap_guard(
            brief,
            catalog=build_content_inventory_catalog_cached(),
        )
        service_card = new_page_service_card(request.service_card_id)
        if service_card is None:
            result = ContentNewPageFoundationResult(
                status="blocked",
                reason="Wybrana karta usługi nie jest zatwierdzona do użycia w planowaniu.",
                safe_next_step="Wybierz zatwierdzoną kartę usługi zwróconą przez WILQ.",
            )
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        try:
            foundation = build_new_page_planning_foundation(
                brief=brief,
                guard=guard,
                command=request,
                service_card=service_card,
            )
        except ValueError as error:
            result = ContentNewPageFoundationResult(
                status="conflict",
                reason=str(error),
                safe_next_step="Odśwież brief i ponownie sprawdź pokrycie przed zapisem.",
            )
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        try:
            status, stored = store.save_new_page_foundation(foundation)
        except ValueError as error:
            result = ContentNewPageFoundationResult(
                status="conflict",
                reason=str(error),
                safe_next_step=(
                    "Odczytaj zapisaną podstawę planowania zamiast zastępować jej wiązanie."
                ),
            )
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return ContentNewPageFoundationResult(
            status=status,
            foundation=stored,
            reason=(
                "Podstawa planowania jest związana z dokładnym briefem, "
                "kontrolą pokrycia i kartą usługi."
            ),
            safe_next_step="Przygotuj plan dokumentu w kolejnym etapie workflow.",
        )


def register_content_new_page_planning_proposal_routes(router: APIRouter) -> None:
    @router.get(
        "/api/content/new-page-briefs/{brief_id}/planning-proposal",
        response_model=ContentNewPagePlanningProposalWorkspace,
    )
    def content_new_page_planning_proposal_status(
        brief_id: str,
    ) -> ContentNewPagePlanningProposalWorkspace:
        return _new_page_planning_proposal_workspace(brief_id)

    @router.post(
        "/api/content/new-page-briefs/{brief_id}/planning-proposal",
        response_model=ContentNewPagePlanningProposalWorkspace,
    )
    def generate_new_page_content_planning_proposal(
        brief_id: str,
        request: ContentNewPagePlanningProposalRequest,
    ) -> ContentNewPagePlanningProposalWorkspace:
        workspace = _new_page_planning_proposal_workspace(brief_id)
        if workspace.readiness.status != "ready":
            return workspace
        store = new_page_brief_store()
        brief = store.load_new_page_brief(brief_id)
        foundation = store.load_new_page_foundation(brief_id)
        assert brief is not None and foundation is not None
        result = build_new_page_planning_input(
            brief=brief,
            foundation=foundation,
            overlap_guard=build_new_page_overlap_guard(
                brief, catalog=build_content_inventory_catalog_cached()
            ),
            service_card=new_page_service_card(foundation.service_card_id),
        )
        queued, should_run = queue_new_page_planning_proposal(
            workspace=workspace,
            build_result=result,
            request=request,
            store=content_planning_proposal_store(),
        )
        if should_run:
            _NEW_PAGE_PLANNING_EXECUTOR.submit(
                _run_new_page_planning_generation,
                brief_id,
                request,
                queued.proposal_status,
            )
        return queued


def register_content_new_page_document_routes(router: APIRouter) -> None:
    @router.get(
        "/api/content/new-page-briefs/{brief_id}/canonical-document",
        response_model=ContentNewPageCanonicalDocumentWorkspace,
    )
    def content_new_page_canonical_document(
        brief_id: str,
    ) -> ContentNewPageCanonicalDocumentWorkspace:
        return _new_page_canonical_document_workspace(brief_id)

    register_content_new_page_document_review_routes(router)

    @router.post(
        "/api/content/new-page-briefs/{brief_id}/initial-draft",
        response_model=ContentInitialDraftResponse,
    )
    def create_new_page_initial_draft(
        brief_id: str, request: ContentInitialDraftRequest
    ) -> ContentInitialDraftResponse:
        brief, foundation, proposal, workspace = _new_page_draft_inputs(brief_id)
        return generate_new_page_initial_draft(
            brief=brief,
            foundation=foundation,
            proposal=proposal,
            decisions=content_workflow_store().load_planning_decisions(foundation.work_item_id),
            workspace=workspace,
            request=request,
            client=content_codex_app_server_client(),
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
            endpoint_path=f"/api/content/new-page-briefs/{brief_id}/initial-draft",
        )


def register_content_new_page_document_review_routes(router: APIRouter) -> None:
    @router.post(
        "/api/content/new-page-briefs/{brief_id}/planning-review",
        response_model=ContentNewPageCanonicalDocumentWorkspace,
        responses={
            409: {
                "model": (
                    ContentNewPageCanonicalDocumentWorkspace
                    | ContentNewPageDocumentReviewPrerequisiteConflict
                )
            }
        },
    )
    def review_new_page_content_plan(
        brief_id: str,
        request: ContentNewPagePlanningReviewCommand,
    ) -> (
        ContentNewPageCanonicalDocumentWorkspace
        | ContentNewPageDocumentReviewPrerequisiteConflict
        | JSONResponse
    ):
        prerequisite = _new_page_document_review_prerequisite(brief_id)
        if prerequisite is not None:
            return JSONResponse(status_code=409, content=prerequisite.model_dump(mode="json"))
        workspace = _new_page_canonical_document_workspace(brief_id)
        if (
            workspace.status == "blocked"
            or workspace.proposal_id != request.expected_proposal_id
            or workspace.planning_digest != request.expected_planning_digest
            or workspace.planning_input_digest != request.expected_planning_input_digest
        ):
            return JSONResponse(status_code=409, content=workspace.model_dump(mode="json"))
        status, _ = content_workflow_store().record_planning_review(
            workspace.work_item_id,
            request.as_planning_review_request(workspace.service_card_id),
            planning_digest=request.expected_planning_digest,
            service_card_id=workspace.service_card_id,
            human_override_review_required=False,
        )
        del status
        return _new_page_canonical_document_workspace(brief_id)

    @router.post(
        "/api/content/new-page-briefs/{brief_id}/draft-revisions/{revision_id}/review",
        response_model=ContentNewPageRevisionReviewResponse,
        responses={
            409: {
                "model": (
                    ContentDraftRevisionConflictResponse
                    | ContentNewPageDocumentReviewPrerequisiteConflict
                )
            }
        },
    )
    def review_new_page_draft_revision(
        brief_id: str,
        revision_id: str,
        request: ContentDraftRevisionReviewRequest,
    ) -> (
        ContentNewPageRevisionReviewResponse
        | ContentNewPageDocumentReviewPrerequisiteConflict
        | JSONResponse
    ):
        prerequisite = _new_page_document_review_prerequisite(brief_id)
        if prerequisite is not None:
            return JSONResponse(status_code=409, content=prerequisite.model_dump(mode="json"))
        workspace = _new_page_canonical_document_workspace(brief_id)
        try:
            result = review_new_page_revision(
                workspace=workspace,
                revision_id=revision_id,
                request=request,
                store=content_workflow_store(),
            )
        except ValueError:
            return _new_page_revision_conflict_response(
                code="revision_not_reviewable",
                workspace=workspace,
                safe_next_step=(
                    "Odśwież dokument nowej strony i sprawdź jego dokładne powiązanie "
                    "z zatwierdzonym planem przed ponownym review."
                ),
            )
        if result.status == "conflict" or result.review is None:
            if result.conflict is None:
                raise RuntimeError("New-page revision review conflict lacks details.")
            return JSONResponse(
                status_code=409,
                content=ContentDraftRevisionConflictResponse(
                    code=result.conflict.code,
                    current_revision_id=result.conflict.current_revision_id,
                    current_digest=result.conflict.current_revision_digest,
                    safe_next_step=revision_conflict_next_step(result.conflict.code),
                ).model_dump(mode="json"),
            )
        return ContentNewPageRevisionReviewResponse(
            status="recorded" if result.status == "created" else "idempotent",
            review=result.review,
        )


def _new_page_revision_conflict_response(
    *,
    code: ContentDraftRevisionPublicConflictCode,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    safe_next_step: str,
) -> JSONResponse:
    revision = workspace.canonical_revision
    payload = ContentDraftRevisionConflictResponse(
        code=code,
        current_revision_id=None if revision is None else revision.revision_id,
        current_digest=None if revision is None else revision.content_digest,
        safe_next_step=safe_next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


def _new_page_document_review_prerequisite(
    brief_id: str,
) -> ContentNewPageDocumentReviewPrerequisiteConflict | None:
    store = new_page_brief_store()
    brief = store.load_new_page_brief(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
    if store.load_new_page_foundation(brief_id) is None:
        return ContentNewPageDocumentReviewPrerequisiteConflict(
            brief_id=brief_id,
            safe_next_step=(
                "Zapisz dokładną podstawę planowania nowej strony przed review planu "
                "lub dokumentu."
            ),
        )
    return None


def _new_page_planning_proposal_workspace(
    brief_id: str,
) -> ContentNewPagePlanningProposalWorkspace:
    store = new_page_brief_store()
    brief = store.load_new_page_brief(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
    foundation = store.load_new_page_foundation(brief_id)
    guard = build_new_page_overlap_guard(
        brief,
        catalog=build_content_inventory_catalog_cached(),
    )
    service_card = (
        new_page_service_card(foundation.service_card_id) if foundation is not None else None
    )
    return build_new_page_planning_proposal_workspace(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
        store=content_planning_proposal_store(),
    )


def _new_page_canonical_document_workspace(
    brief_id: str,
) -> ContentNewPageCanonicalDocumentWorkspace:
    store = new_page_brief_store()
    brief = store.load_new_page_brief(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
    foundation = store.load_new_page_foundation(brief_id)
    proposal_workspace = _new_page_planning_proposal_workspace(brief_id)
    proposal_status = proposal_workspace.proposal_status
    proposal = None if proposal_status is None else proposal_status.proposal
    workspace = build_new_page_canonical_document_workspace(
        brief=brief,
        foundation=foundation,
        proposal=proposal,
        decisions=(
            []
            if foundation is None
            else content_workflow_store().load_planning_decisions(foundation.work_item_id)
        ),
        revision_state=(
            None
            if foundation is None
            else content_workflow_store().load_draft_revision_state(foundation.work_item_id)
        ),
    )
    if workspace is None:
        raise HTTPException(
            status_code=409,
            detail="Brakuje zapisanej podstawy planowania nowej strony.",
        )
    return workspace


def _new_page_draft_inputs(
    brief_id: str,
) -> tuple[
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
    ContentPlanningProposal,
    ContentNewPageCanonicalDocumentWorkspace,
]:
    store = new_page_brief_store()
    brief = store.load_new_page_brief(brief_id)
    foundation = store.load_new_page_foundation(brief_id)
    workspace = _new_page_canonical_document_workspace(brief_id)
    proposal_status = _new_page_planning_proposal_workspace(brief_id).proposal_status
    proposal = None if proposal_status is None else proposal_status.proposal
    if brief is None or foundation is None or proposal is None:
        raise HTTPException(status_code=409, detail="Brakuje dokładnego planu nowej strony.")
    return brief, foundation, proposal, workspace


def _run_new_page_planning_generation(
    brief_id: str,
    request: ContentNewPagePlanningProposalRequest,
    queued_response: ContentPlanningProposalResponse | None,
) -> None:
    """Rebuild current input inside the worker before it can call Codex."""
    claim_store = content_planning_proposal_store()
    if queued_response is None:
        return
    try:
        workspace = _new_page_planning_proposal_workspace(brief_id)
        if workspace.readiness.status != "ready":
            terminalize_new_page_planning_claim(
                queued_response, claim_store, code="planning_input_blocked"
            )
            return
        store = new_page_brief_store()
        brief = store.load_new_page_brief(brief_id)
        foundation = store.load_new_page_foundation(brief_id)
        if brief is None or foundation is None:
            terminalize_new_page_planning_claim(
                queued_response, claim_store, code="planning_input_missing"
            )
            return
        result = build_new_page_planning_input(
            brief=brief,
            foundation=foundation,
            overlap_guard=build_new_page_overlap_guard(
                brief,
                catalog=build_content_inventory_catalog_cached(),
            ),
            service_card=new_page_service_card(foundation.service_card_id),
        )
        current = result.planning_input
        if (
            current is None
            or current.planning_input_digest != queued_response.planning_input_digest
        ):
            terminalize_new_page_planning_claim(
                queued_response, claim_store, code="stale_input"
            )
            return
        generated = generate_new_page_planning_proposal(
            workspace=workspace,
            build_result=result,
            request=request,
            client=content_codex_app_server_client(),
            store=claim_store,
            run_store=local_state_store(),
            endpoint_path=f"/api/content/new-page-briefs/{brief_id}/planning-proposal",
        )
        if generated.proposal_status is not None:
            claim_store.save_terminal_response(generated.proposal_status)
    except Exception:
        terminalize_new_page_planning_claim(
            queued_response, claim_store, code="runtime_failed"
        )
