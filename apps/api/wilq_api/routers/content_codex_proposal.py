from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_section_proposal import (
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
    propose_content_section_revision,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store import content_workflow_store
from wilq.storage.local_state import local_state_store

ContentSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def content_codex_app_server_client() -> StdioCodexAppServerClient:
    return StdioCodexAppServerClient()


def register_content_codex_proposal_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal",
        response_model=ContentCodexSectionProposalResponse,
        responses={409: {"model": ContentCodexSectionProposalResponse}},
    )
    def content_work_item_codex_section_proposal(
        work_item_id: str,
        base_revision_id: str,
        request: ContentCodexSectionProposalRequest,
    ) -> ContentCodexSectionProposalResponse | JSONResponse:
        result = propose_content_section_revision(
            snapshot=snapshot_loader(work_item_id),
            base_revision_id=base_revision_id,
            request=request,
            client=content_codex_app_server_client(),
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
        )
        if result.status == "conflict":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return result


__all__ = ["register_content_codex_proposal_route"]
