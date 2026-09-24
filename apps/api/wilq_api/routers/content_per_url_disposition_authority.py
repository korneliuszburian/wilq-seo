"""Public ActionObject preview and readback for exact per-URL dispositions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.per_url_disposition_authority import (
    PerUrlDispositionCandidate,
    PerUrlDispositionPreviewResponse,
    PerUrlDispositionProjection,
    prepare_per_url_disposition_preview,
    read_per_url_disposition_authority,
)
from wilq.content.workflow.store.store import content_workflow_store


def register_content_per_url_disposition_authority_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/per-url-disposition-authorities/preview",
        content_per_url_disposition_preview_endpoint,
        methods=["POST"],
        response_model=PerUrlDispositionPreviewResponse,
    )
    router.add_api_route(
        "/api/content/per-url-disposition-authorities/{action_id}",
        content_per_url_disposition_read_endpoint,
        methods=["GET"],
        response_model=PerUrlDispositionProjection,
    )


def content_per_url_disposition_preview_endpoint(
    candidate: PerUrlDispositionCandidate,
) -> PerUrlDispositionPreviewResponse:
    try:
        return prepare_per_url_disposition_preview(content_workflow_store(), candidate)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def content_per_url_disposition_read_endpoint(
    action_id: str,
) -> PerUrlDispositionProjection:
    return read_per_url_disposition_authority(content_workflow_store(), action_id=action_id)


__all__ = ["register_content_per_url_disposition_authority_routes"]
