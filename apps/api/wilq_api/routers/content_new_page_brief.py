from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import content_codex_app_server_client
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputReadinessResponse,
    build_new_page_planning_input,
    content_planning_input_readiness,
)
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.planning.new_page_proposal import (
    ContentNewPagePlanningProposalRequest,
    ContentNewPagePlanningProposalWorkspace,
    build_new_page_planning_proposal_workspace,
    generate_new_page_planning_proposal,
    queue_new_page_planning_proposal,
)
from wilq.content.workflow.catalog import build_content_inventory_catalog_cached
from wilq.content.workflow.new_page import (
    ContentNewPageBriefInput,
    ContentNewPageBriefWorkspace,
    ContentNewPageFoundationCommand,
    ContentNewPageFoundationResult,
    build_new_page_brief_workspace,
    build_new_page_overlap_guard,
    build_new_page_planning_foundation,
    new_page_service_card,
)
from wilq.content.workflow.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
    ContentNewPagePlanningReviewCommand,
    build_new_page_canonical_document_workspace,
)
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
                _run_new_page_planning_generation, brief_id, request
            )
        return queued

    @router.get(
        "/api/content/new-page-briefs/{brief_id}/canonical-document",
        response_model=ContentNewPageCanonicalDocumentWorkspace,
    )
    def content_new_page_canonical_document(
        brief_id: str,
    ) -> ContentNewPageCanonicalDocumentWorkspace:
        return _new_page_canonical_document_workspace(brief_id)

    @router.post(
        "/api/content/new-page-briefs/{brief_id}/planning-review",
        response_model=ContentNewPageCanonicalDocumentWorkspace,
        responses={409: {"model": ContentNewPageCanonicalDocumentWorkspace}},
    )
    def review_new_page_content_plan(
        brief_id: str,
        request: ContentNewPagePlanningReviewCommand,
    ) -> ContentNewPageCanonicalDocumentWorkspace:
        workspace = _new_page_canonical_document_workspace(brief_id)
        if (
            workspace.status == "blocked"
            or workspace.proposal_id != request.expected_proposal_id
            or workspace.planning_digest != request.expected_planning_digest
            or workspace.planning_input_digest != request.expected_planning_input_digest
        ):
            raise HTTPException(
                status_code=409,
                detail="Plan nowej strony zmienił się albo nie jest gotowy do review.",
            )
        status, _ = content_workflow_store().record_planning_review(
            workspace.work_item_id,
            request.as_planning_review_request(workspace.service_card_id),
            planning_digest=request.expected_planning_digest,
            service_card_id=workspace.service_card_id,
            human_override_review_required=False,
        )
        del status
        return _new_page_canonical_document_workspace(brief_id)


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
    )
    if workspace is None:
        raise HTTPException(
            status_code=409,
            detail="Brakuje zapisanej podstawy planowania nowej strony.",
        )
    return workspace


def _run_new_page_planning_generation(
    brief_id: str,
    request: ContentNewPagePlanningProposalRequest,
) -> None:
    """Rebuild current input inside the worker before it can call Codex."""

    workspace = _new_page_planning_proposal_workspace(brief_id)
    if workspace.readiness.status != "ready":
        return
    store = new_page_brief_store()
    brief = store.load_new_page_brief(brief_id)
    foundation = store.load_new_page_foundation(brief_id)
    if brief is None or foundation is None:
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
    generated = generate_new_page_planning_proposal(
        workspace=workspace,
        build_result=result,
        request=request,
        client=content_codex_app_server_client(),
        store=content_planning_proposal_store(),
        run_store=local_state_store(),
        endpoint_path=f"/api/content/new-page-briefs/{brief_id}/planning-proposal",
    )
    if generated.proposal_status is not None:
        content_planning_proposal_store().save_terminal_response(generated.proposal_status)
