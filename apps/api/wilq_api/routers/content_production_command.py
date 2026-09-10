"""One API-owned command over the existing content production seams."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict

from apps.api.wilq_api.routers.content_codex_proposal import (
    _current_planning_input,
    content_codex_app_server_client,
)
from apps.api.wilq_api.routers.content_initial_draft import _submit_initial_draft
from wilq.content.drafts.codex_section_proposal import propose_content_section_revision
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
    ContentRevisionRepairProposalRequest,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.production_command import (
    ContentProductionCommand,
    ContentProductionCommandRequest,
    ContentProductionCommandResponse,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.storage.local_state import local_state_store


class ContentProductionCommandValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = "production_command_request_invalid"


class _NoEchoProductionCommandRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def no_echo_route_handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={"detail": "production_command_request_invalid"},
                )

        return no_echo_route_handler


def register_content_production_command_route(
    router: APIRouter,
    *,
    snapshot_loader: Callable[[str], ContentWorkItemWorkflowSnapshotResponse],
) -> None:
    def initial_executor(
        work_item_id: str,
        request: ContentInitialDraftRequest,
    ) -> ContentInitialDraftResponse:
        result = _submit_initial_draft(work_item_id, request, snapshot_loader)
        if isinstance(result, JSONResponse):
            return ContentInitialDraftResponse.model_validate(json.loads(bytes(result.body)))
        return result

    def repair_executor(
        work_item_id: str,
        request: ContentRevisionRepairProposalRequest,
    ) -> ContentCodexSectionProposalResponse:
        snapshot = snapshot_loader(work_item_id)
        base_revision = getattr(
            getattr(snapshot, "revision_workspace", None), "latest_revision", None
        )
        if base_revision is not None and base_revision.refresh_preparation_binding is not None:
            from apps.api.wilq_api.routers.content_workflow import (
                semantic_review_snapshot_for_work_item_or_404,
            )

            snapshot = semantic_review_snapshot_for_work_item_or_404(work_item_id)
            base_revision = snapshot.revision_workspace.latest_revision
        semantic_review = (
            None
            if base_revision is None
            else content_semantic_review_store().for_revision(
                work_item_id,
                base_revision.revision_id,
                base_revision.content_digest,
            )
        )
        return propose_content_section_revision(
            snapshot=snapshot,
            base_revision_id=base_revision.revision_id if base_revision is not None else "missing",
            request=ContentCodexSectionProposalRequest(
                expected_base_digest=request.expected_base_digest,
                selected_section_ids=request.selected_section_ids,
                selected_cta_ids=request.selected_cta_ids,
                requested_by=request.requested_by,
            ),
            client=content_codex_app_server_client(),
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
            semantic_review=semantic_review,
            planning_input=_current_planning_input(snapshot),
        )

    async def content_production_command(
        request: ContentProductionCommandRequest,
        work_item_id: str = Path(
            ..., min_length=1, max_length=240, pattern=r"^[a-z][a-z0-9_-]*$"
        ),
    ) -> JSONResponse:
        command = ContentProductionCommand(
            journal=content_workflow_store(),
            initial_executor=initial_executor,
            repair_executor=repair_executor,
        )
        result = await asyncio.to_thread(command.run, work_item_id, request)
        status_code = {
            "reused": 200,
            "idempotent": 200,
            "generating": 202,
            "created": 201,
            "blocked": 409,
        }[result.status]
        return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))

    router.add_api_route(
        "/api/content/work-items/{work_item_id}/production-command",
        content_production_command,
        methods=["POST"],
        response_model=ContentProductionCommandResponse,
        responses={
            200: {"model": ContentProductionCommandResponse},
            201: {"model": ContentProductionCommandResponse},
            202: {"model": ContentProductionCommandResponse},
            409: {"model": ContentProductionCommandResponse},
            422: {"model": ContentProductionCommandValidationErrorResponse},
        },
        route_class_override=_NoEchoProductionCommandRoute,
        tags=["content"],
    )


__all__ = ["register_content_production_command_route"]
