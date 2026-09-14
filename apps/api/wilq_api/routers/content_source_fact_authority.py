"""Preview-only entrypoint for exact per-work-item source-fact authority."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from wilq.content.workflow.source_fact_authority import (
    ContentSourceFactAuthorityCandidateProjection,
    ContentSourceFactAuthorityPreviewCommand,
    ContentSourceFactAuthorityPreviewResponse,
    ContentSourceFactAuthorityReadProjection,
    build_content_source_fact_authority_candidate_projection,
    prepare_content_source_fact_authority_preview,
    read_content_source_fact_authority,
)
from wilq.content.workflow.store.store import content_workflow_store


def register_content_source_fact_authority_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/source-fact-authority-reviews/preview",
        content_source_fact_authority_preview_endpoint,
        methods=["POST"],
        response_model=ContentSourceFactAuthorityPreviewResponse,
    )
    router.add_api_route(
        "/api/content/source-fact-authority-reviews/candidates/{identity_binding_id}",
        content_source_fact_authority_candidates_endpoint,
        methods=["GET"],
        response_model=ContentSourceFactAuthorityCandidateProjection,
    )
    router.add_api_route(
        "/api/content/source-fact-authority-reviews/{action_id}",
        content_source_fact_authority_read_endpoint,
        methods=["GET"],
        response_model=ContentSourceFactAuthorityReadProjection,
    )


def content_source_fact_authority_preview_endpoint(
    command: ContentSourceFactAuthorityPreviewCommand,
) -> ContentSourceFactAuthorityPreviewResponse:
    """Store a non-authoritative proposal and return its server-built preview."""

    try:
        return prepare_content_source_fact_authority_preview(content_workflow_store(), command)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def content_source_fact_authority_candidates_endpoint(
    identity_binding_id: Annotated[
        str, Path(pattern=r"^[a-z][a-z0-9_-]{0,239}$")
    ],
) -> ContentSourceFactAuthorityCandidateProjection:
    """Read exact scoped candidates; never persist selection or authority."""

    store = content_workflow_store()
    identity = store.load_content_delivery_identity(identity_binding_id)
    classification = (
        None
        if identity is None
        else store.load_production_classification_for_work_item(identity.current_work_item_id)
    )
    return build_content_source_fact_authority_candidate_projection(
        identity_binding_id,
        identity=identity,
        classification=classification,
    )


def content_source_fact_authority_read_endpoint(
    action_id: str,
) -> ContentSourceFactAuthorityReadProjection:
    try:
        return read_content_source_fact_authority(content_workflow_store(), action_id=action_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
