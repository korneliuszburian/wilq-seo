"""Explicit recovery route for one fully audited v3 planning intent."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.planning.generation_intent_v3_dispatch import (
    PlanningGenerationIntentV3DispatchOutcome,
    ProjectionLoader,
    dispatch_applied_planning_intent_v3,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.storage.local_state import LocalStateStore, local_state_store

StoreFactory = Callable[[], ContentWorkflowStore]
AuditStoreFactory = Callable[[], LocalStateStore]
ProposalStoreFactory = Callable[[], ContentPlanningProposalStore]
SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
QueueDispatcher = Callable[..., ContentPlanningProposalResponse]


def register_content_planning_generation_dispatch_v3_route(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader | None = None,
    workflow_store_factory: StoreFactory | None = None,
    audit_store_factory: AuditStoreFactory | None = None,
    proposal_store_factory: ProposalStoreFactory | None = None,
    enqueue: QueueDispatcher | None = None,
    projection_loader: ProjectionLoader | None = None,
) -> None:
    load_snapshot = snapshot_loader or _planning_generation_snapshot_loader
    make_workflow_store = workflow_store_factory or content_workflow_store
    make_audit_store = audit_store_factory or local_state_store
    make_proposal_store = proposal_store_factory or content_planning_proposal_store

    @router.post(
        "/api/content/planning-generation-intents-v3/{action_id}/dispatch",
        response_model=PlanningGenerationIntentV3DispatchOutcome,
        responses={409: {"model": PlanningGenerationIntentV3DispatchOutcome}},
    )
    def dispatch_intent_v3(
        action_id: str,
    ) -> PlanningGenerationIntentV3DispatchOutcome | JSONResponse:
        outcome = dispatch_applied_planning_intent_v3(
            action_id,
            workflow_store=make_workflow_store(),
            audit_store=make_audit_store(),
            proposal_store=make_proposal_store(),
            snapshot_loader=load_snapshot,
            enqueue=enqueue,
            projection_loader=projection_loader,
        )
        if outcome.status == "blocked":
            return JSONResponse(status_code=409, content=outcome.model_dump(mode="json"))
        return outcome


def _planning_generation_snapshot_loader(
    work_item_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404

    return snapshot_for_work_item_or_404(work_item_id)


__all__ = ["register_content_planning_generation_dispatch_v3_route"]
