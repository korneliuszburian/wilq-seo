"""Public exact dispatch of one already applied planning ActionObject."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.planning.generation_intent_dispatch import (
    PlanningGenerationDispatchOutcome,
    QueueDispatcher,
    dispatch_applied_planning_intent,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.storage.local_state import LocalStateStore, local_state_store

SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_planning_generation_dispatch_route(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader,
    workflow_store_factory: Callable[[], ContentWorkflowStore] = content_workflow_store,
    audit_store_factory: Callable[[], LocalStateStore] = local_state_store,
    proposal_store_factory: Callable[[], ContentPlanningProposalStore] = (
        content_planning_proposal_store
    ),
    enqueue: QueueDispatcher | None = None,
) -> None:
    @router.post(
        "/api/content/planning-generation-intents/{action_id}/dispatch",
        response_model=PlanningGenerationDispatchOutcome,
        responses={409: {"model": PlanningGenerationDispatchOutcome}},
    )
    def dispatch_intent(action_id: str) -> PlanningGenerationDispatchOutcome | JSONResponse:
        outcome = dispatch_applied_planning_intent(
            action_id,
            workflow_store=workflow_store_factory(),
            audit_store=audit_store_factory(),
            proposal_store=proposal_store_factory(),
            snapshot_loader=snapshot_loader,
            enqueue=enqueue,
        )
        if outcome.status == "blocked":
            return JSONResponse(status_code=409, content=outcome.model_dump(mode="json"))
        return outcome


__all__ = ["register_content_planning_generation_dispatch_route"]
