from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_service import (
    generate_content_semantic_review,
    read_content_semantic_review,
)
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.storage.local_state import local_state_store

ContentSemanticSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]


def register_content_semantic_review_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentSemanticSnapshotLoader,
) -> None:
    path = (
        "/api/content/work-items/{work_item_id}/draft-revisions/"
        "{revision_id}/semantic-review"
    )

    @router.get(path, response_model=ContentSemanticReviewResponse)
    def content_revision_semantic_review(
        work_item_id: str,
        revision_id: str,
    ) -> ContentSemanticReviewResponse:
        snapshot = snapshot_loader(work_item_id)
        result = read_content_semantic_review(
            snapshot=snapshot,
            revision_id=revision_id,
            store=content_semantic_review_store(),
        )
        return result

    @router.post(
        path,
        response_model=ContentSemanticReviewResponse,
        responses={409: {"model": ContentSemanticReviewResponse}},
    )
    def generate_content_revision_semantic_review(
        work_item_id: str,
        revision_id: str,
        request: ContentSemanticReviewRequest,
    ) -> ContentSemanticReviewResponse | JSONResponse:
        result = generate_content_semantic_review(
            snapshot=snapshot_loader(work_item_id),
            revision_id=revision_id,
            request=request,
            client=content_codex_app_server_client(),
            store=content_semantic_review_store(),
            run_store=local_state_store(),
        )
        if result.status == "conflict":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return result


__all__ = ["register_content_semantic_review_routes"]
