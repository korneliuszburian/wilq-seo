from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.planning import (
    ContentPlanningReviewConflict,
    ContentPlanningReviewRequest,
    ContentPlanningReviewResponse,
    build_content_planning_workspace,
)
from wilq.content.workflow.service_selection import (
    ContentPlanningServiceSelectionError,
    resolve_content_planning_service_selection,
)
from wilq.content.workflow.store import content_workflow_store

ContentPlanningReviewSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_planning_review_route(
    router: APIRouter, *, snapshot_loader: ContentPlanningReviewSnapshotLoader
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/planning-review",
        response_model=ContentPlanningReviewResponse,
        responses={409: {"model": ContentPlanningReviewConflict}},
    )
    def content_work_item_planning_review(
        work_item_id: str, request: ContentPlanningReviewRequest
    ) -> ContentPlanningReviewResponse | JSONResponse:
        snapshot = snapshot_loader(work_item_id)
        workspace = snapshot.planning_workspace
        if request.stage != "scope":
            return _conflict(
                code="manual_section_map_unsupported",
                proposal=workspace.proposal if workspace is not None else None,
                safe_next_step="Sprawdź wygenerowany plan; mapa sekcji nie wymaga osobnej decyzji.",
            )
        if (
            workspace is None
            or workspace.proposal.generation_status != "codex_generated"
            or request.expected_planning_digest != workspace.proposal.planning_digest
        ):
            return _conflict(
                code=("stale_plan" if workspace is not None else "plan_not_generated"),
                proposal=workspace.proposal if workspace is not None else None,
                safe_next_step="Wygeneruj albo odśwież aktualny plan przed review.",
            )
        try:
            selection = resolve_content_planning_service_selection(
                snapshot.service_profile_context, request.service_card_id
            )
        except ContentPlanningServiceSelectionError:
            return _conflict(
                code="service_not_current",
                proposal=workspace.proposal,
                safe_next_step="Odśwież plan i użyj karty usługi związanej z jego exact wejściem.",
            )
        if selection.service_card_id != workspace.proposal.service_card_id:
            return _conflict(
                code="service_mismatch",
                proposal=workspace.proposal,
                safe_next_step="Zatwierdź plan z przypisaną usługą albo wygeneruj nowy plan.",
            )
        store = content_workflow_store()
        status, decision = store.record_planning_review(
            work_item_id,
            request,
            planning_digest=workspace.proposal.planning_digest,
            service_card_id=selection.service_card_id,
            human_override_review_required=selection.human_override_review_required,
        )
        return ContentPlanningReviewResponse(
            status="recorded" if status == "created" else "idempotent",
            decision=decision,
            planning_workspace=build_content_planning_workspace(
                workspace.proposal, store.load_planning_decisions(work_item_id)
            ),
        )


def _conflict(
    *, code: str, proposal: object, safe_next_step: str
) -> JSONResponse:
    proposal_id = getattr(proposal, "proposal_id", None)
    planning_digest = getattr(proposal, "planning_digest", None)
    payload = ContentPlanningReviewConflict(
        code=code,
        current_proposal_id=proposal_id,
        current_planning_digest=planning_digest,
        safe_next_step=safe_next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


__all__ = ["register_content_planning_review_route"]
