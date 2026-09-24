"""Preview-only entrypoint for exact current content disposition authority."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from wilq.content.workflow.current_disposition_approval import (
    ContentCurrentDispositionApprovalRequest,
    ContentCurrentDispositionApprovalResponse,
    CurrentDispositionApprovalError,
    approve_current_disposition_authority,
)
from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionCandidate,
    ContentCurrentDispositionPreviewResponse,
    ContentCurrentDispositionReadProjection,
    historical_current_disposition_blocker,
    prepare_current_disposition_preview,
    read_current_disposition_authority,
)
from wilq.content.workflow.store.store import content_workflow_store


def register_content_current_disposition_authority_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/current-disposition-authorities/preview",
        content_current_disposition_preview_endpoint,
        methods=["POST"],
        response_model=ContentCurrentDispositionPreviewResponse,
    )
    router.add_api_route(
        "/api/content/current-disposition-authorities/{action_id}/approve",
        content_current_disposition_approve_endpoint,
        methods=["POST"],
        response_model=ContentCurrentDispositionApprovalResponse,
    )
    router.add_api_route(
        "/api/content/current-disposition-authorities/{action_id}",
        content_current_disposition_read_endpoint,
        methods=["GET"],
        response_model=ContentCurrentDispositionReadProjection,
    )


def content_current_disposition_preview_endpoint(
    candidate: ContentCurrentDispositionCandidate,
) -> ContentCurrentDispositionPreviewResponse:
    """Keep the batch-bound v1 path readable while new actions use per-URL authority."""

    if candidate.proposed_final_disposition == "keep":
        return ContentCurrentDispositionPreviewResponse(
            status="blocked",
            blockers=(historical_current_disposition_blocker(),),
        )

    try:
        return prepare_current_disposition_preview(content_workflow_store(), candidate)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def content_current_disposition_read_endpoint(
    action_id: str,
) -> ContentCurrentDispositionReadProjection:
    store = content_workflow_store()
    projection = read_current_disposition_authority(store, action_id=action_id)
    if projection.status == "missing":
        return projection
    blocker = historical_current_disposition_blocker()
    return ContentCurrentDispositionReadProjection(
        status="blocked",
        receipt=projection.receipt,
        blockers=(blocker,),
        safe_next_step=blocker.next_step,
    )


def content_current_disposition_approve_endpoint(
    action_id: str,
    request: ContentCurrentDispositionApprovalRequest,
) -> ContentCurrentDispositionApprovalResponse | JSONResponse:
    """Keep batch-bound v1 receipts historical and non-approvable."""

    store = content_workflow_store()
    if store.load_content_current_disposition_proposal(action_id) is not None:
        blocker = historical_current_disposition_blocker()
        projection = ContentCurrentDispositionReadProjection(
            status="blocked",
            receipt=store.load_content_current_disposition_receipt(action_id),
            blockers=(blocker,),
            safe_next_step=blocker.next_step,
        )
        response = ContentCurrentDispositionApprovalResponse(
            status="blocked",
            projection=projection,
            receipt=projection.receipt,
            blockers=(blocker,),
            safe_next_step=blocker.next_step,
        )
        return JSONResponse(status_code=409, content=response.model_dump(mode="json"))

    try:
        return approve_current_disposition_authority(
            store,
            action_id=action_id,
            request=request,
        )
    except CurrentDispositionApprovalError as error:
        return JSONResponse(
            status_code=409,
            content=error.response().model_dump(mode="json"),
        )
