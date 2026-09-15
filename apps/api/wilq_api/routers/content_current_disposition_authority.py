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
    """Persist only a candidate and return an exact server-built action preview."""

    try:
        return prepare_current_disposition_preview(content_workflow_store(), candidate)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def content_current_disposition_read_endpoint(
    action_id: str,
) -> ContentCurrentDispositionReadProjection:
    return read_current_disposition_authority(content_workflow_store(), action_id=action_id)


def content_current_disposition_approve_endpoint(
    action_id: str,
    request: ContentCurrentDispositionApprovalRequest,
) -> ContentCurrentDispositionApprovalResponse | JSONResponse:
    """Run the exact local-only lifecycle and expose typed 409 conflicts."""

    try:
        return approve_current_disposition_authority(
            content_workflow_store(),
            action_id=action_id,
            request=request,
        )
    except CurrentDispositionApprovalError as error:
        return JSONResponse(
            status_code=409,
            content=error.response().model_dump(mode="json"),
        )
