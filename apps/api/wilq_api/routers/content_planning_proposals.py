from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.content.planning.generated_proposal import (
    generate_content_planning_proposal,
    read_content_planning_proposal,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import (
    content_planning_proposal_store,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.storage.local_state import local_state_store

ContentPlanningSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]


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
        return read_content_planning_proposal(
            snapshot=snapshot_loader(work_item_id),
            store=content_planning_proposal_store(),
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
        result = generate_content_planning_proposal(
            snapshot=snapshot_loader(work_item_id),
            request=request,
            client=content_codex_app_server_client(),
            store=content_planning_proposal_store(),
            run_store=local_state_store(),
        )
        if result.status == "stale":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        if result.blockers and result.blockers[0].code == "unknown_service_card":
            return JSONResponse(status_code=422, content=result.model_dump(mode="json"))
        return result


__all__ = ["register_content_planning_proposal_routes"]
