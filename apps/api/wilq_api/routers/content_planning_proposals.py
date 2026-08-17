from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.generated_proposal import (
    read_content_planning_proposal,
    with_current_planning_workspace,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store.store import content_workflow_store

ContentPlanningSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_planning_proposal_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentPlanningSnapshotLoader,
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/planning-proposals",
        response_model=ContentPlanningProposalResponse,
    )
    def content_work_item_planning_proposal_status(
        work_item_id: str,
    ) -> ContentPlanningProposalResponse:
        return _get_content_work_item_planning_proposal_status(
            work_item_id=work_item_id, snapshot_loader=snapshot_loader
        )

    @router.post(
        "/api/content/work-items/{work_item_id}/planning-proposals",
        response_model=ContentPlanningProposalResponse,
        responses={
            409: {"model": ContentPlanningProposalResponse},
            422: {"model": ContentPlanningProposalResponse},
        },
    )
    def content_work_item_planning_proposal_generate(
        work_item_id: str,
        request: ContentPlanningProposalRequest,
    ) -> ContentPlanningProposalResponse | JSONResponse:
        return _generate_content_work_item_planning_proposal(
            work_item_id=work_item_id,
            request=request,
            snapshot_loader=snapshot_loader,
        )


def _get_content_work_item_planning_proposal_status(
    *, work_item_id: str, snapshot_loader: ContentPlanningSnapshotLoader
) -> ContentPlanningProposalResponse:
    snapshot = snapshot_loader(work_item_id)
    response = read_content_planning_proposal(
        snapshot=snapshot, store=content_planning_proposal_store()
    )
    return with_current_planning_workspace(
        response, content_workflow_store().load_planning_decisions(work_item_id)
    )


def _generate_content_work_item_planning_proposal(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
) -> ContentPlanningProposalResponse | JSONResponse:
    store = content_planning_proposal_store()
    unknown_response = _unknown_service_card_response(work_item_id=work_item_id, request=request)
    if unknown_response is not None:
        return unknown_response
    zero_digest_response = _zero_digest_response(work_item_id=work_item_id, request=request)
    if zero_digest_response is not None:
        return zero_digest_response
    planning_input, request, early_response = planning_generation_queue.prepare_planning_generation(
        work_item_id=work_item_id,
        request=request,
        snapshot_loader=snapshot_loader,
        store=store,
    )
    if early_response is not None:
        return early_response
    if planning_input is None:
        raise RuntimeError("Planning preparation returned no input or blocker.")
    return planning_generation_queue.enqueue_planning_generation(
        planning_input=planning_input,
        work_item_id=work_item_id,
        request=request,
        snapshot_loader=snapshot_loader,
        store=store,
    )


def _unknown_service_card_response(
    *, work_item_id: str, request: ContentPlanningProposalRequest
) -> JSONResponse | None:
    if any(
        card.id == request.service_card_id and card.card_type == "service"
        for card in ekologus_content_knowledge_cards()
    ):
        return None
    unknown = ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        service_card_id=request.service_card_id,
        blockers=[
            ContentPlanningProposalBlocker(
                code="unknown_service_card",
                label="Nieznana karta usługi",
                reason="Wybrana karta nie istnieje w aktualnym katalogu usług WILQ.",
                next_step="Wybierz kartę usługi zwróconą dla tego work itemu.",
            )
        ],
        safe_next_step="Wybierz kartę usługi zwróconą dla tego work itemu.",
    )
    return JSONResponse(status_code=422, content=unknown.model_dump(mode="json"))


def _zero_digest_response(
    *, work_item_id: str, request: ContentPlanningProposalRequest
) -> JSONResponse | None:
    if request.expected_planning_input_digest != "0" * 64:
        return None
    stale = ContentPlanningProposalResponse(
        status="stale",
        work_item_id=work_item_id,
        service_card_id=request.service_card_id,
        blockers=[
            ContentPlanningProposalBlocker(
                code="stale_input",
                label="Wejście planu jest nieaktualne",
                reason="Pusty digest nie może reprezentować bieżącego wejścia planowania.",
                next_step="Odśwież stan planu i użyj aktualnego digestu.",
            )
        ],
        safe_next_step="Odśwież stan planu i użyj aktualnego digestu.",
    )
    return JSONResponse(status_code=409, content=stale.model_dump(mode="json"))


__all__ = ["register_content_planning_proposal_routes"]
