from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.content.drafts.initial_full_draft import generate_initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store import content_workflow_store
from wilq.storage.local_state import local_state_store

ContentInitialDraftSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]


def register_content_initial_draft_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/initial-draft",
        response_model=ContentInitialDraftResponse,
        responses={409: {"model": ContentInitialDraftResponse}},
    )
    def content_work_item_initial_full_draft(
        work_item_id: str,
        request: ContentInitialDraftRequest,
    ) -> ContentInitialDraftResponse | JSONResponse:
        result = generate_initial_full_draft(
            snapshot=snapshot_loader(work_item_id),
            request=request,
            client=content_codex_app_server_client(),
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
        )
        if result.status == "conflict":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return result


__all__ = ["register_content_initial_draft_route"]
