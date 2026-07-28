from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.canonical.landing_identity import landing_page_metric_lookup_path
from wilq.content.measurement.deployment import (
    ContentPublicDeploymentConfirmationCommand,
    confirm_public_deployment,
    public_deployment_observations,
)
from wilq.content.workflow.contracts import (
    ContentPublicDeploymentConfirmationResponse,
    ContentPublicDeploymentReadResponse,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.store_public_deployment import (
    public_deployment,
    save_public_deployment,
)
from wilq.schemas.core import utc_now
from wilq.storage.metric_store import metric_store


def register_content_public_deployment_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/public-deployments",
        confirm_content_public_deployment,
        methods=["POST"],
        response_model=ContentPublicDeploymentConfirmationResponse,
    )
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/public-deployment",
        read_content_public_deployment,
        methods=["GET"],
        response_model=ContentPublicDeploymentReadResponse,
    )


def confirm_content_public_deployment(
    work_item_id: str,
    revision_id: str,
    request: ContentPublicDeploymentConfirmationCommand,
) -> ContentPublicDeploymentConfirmationResponse:
    store = content_workflow_store()
    revision = next(
        (
            candidate
            for candidate in store.list_draft_revisions(work_item_id)
            if candidate.revision_id == revision_id
        ),
        None,
    )
    review = store.load_draft_revision_review(
        work_item_id=work_item_id,
        revision_id=revision_id,
    )
    if revision is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wskazanej rewizji dokumentu.")
    if (
        review is None
        or review.decision != "approved"
        or review.work_item_id != revision.work_item_id
        or review.revision_id != revision.revision_id
        or review.revision_digest != revision.content_digest
    ):
        raise HTTPException(
            status_code=409,
            detail="Publiczne wdrożenie można potwierdzić wyłącznie dla zatwierdzonej rewizji.",
        )
    try:
        deployment = confirm_public_deployment(
            revision=revision,
            command=request,
            publication_facts=metric_store().list_metric_facts_by_evidence_ids(
                [request.publication_evidence_id]
            ),
            now=utc_now(),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ContentPublicDeploymentConfirmationResponse(
        deployment=save_public_deployment(store, deployment)
    )


def read_content_public_deployment(
    work_item_id: str,
    revision_id: str,
) -> ContentPublicDeploymentReadResponse:
    store = content_workflow_store()
    deployment = public_deployment(
        store,
        work_item_id=work_item_id,
        revision_id=revision_id,
    )
    revision = next(
        (
            candidate
            for candidate in store.list_draft_revisions(work_item_id)
            if candidate.revision_id == revision_id
        ),
        None,
    )
    review = (
        None
        if revision is None
        else store.load_draft_revision_review(
            work_item_id=work_item_id, revision_id=revision_id
        )
    )
    approved_exact_revision = (
        revision is not None
        and review is not None
        and review.decision == "approved"
        and review.work_item_id == revision.work_item_id
        and review.revision_id == revision.revision_id
        and review.revision_digest == revision.content_digest
    )
    observations = (
        public_deployment_observations(
            revision=revision,
            facts=metric_store().list_metric_facts_for_content_url(
                ["wordpress_ekologus"],
                revision.final_canonical_url or "",
                content_path=landing_page_metric_lookup_path(revision.final_canonical_url),
            ),
        )
        if approved_exact_revision and revision is not None and revision.final_canonical_url
        else []
    )
    return ContentPublicDeploymentReadResponse(
        deployment=deployment,
        publication_observations=observations,
        safe_next_step=(
            "Potwierdź publiczne wdrożenie na podstawie odczytu WordPressa."
            if deployment is None
            else "Przygotuj okno pomiaru dla tego potwierdzonego wdrożenia."
        ),
    )


__all__ = ["register_content_public_deployment_routes"]
