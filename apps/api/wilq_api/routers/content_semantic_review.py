from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_runtime import content_codex_app_server_client
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.quality import semantic_review_queue
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_service import (
    generate_content_semantic_review,
    read_content_semantic_review,
)
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.store.store import content_workflow_store
from wilq.storage.local_state import local_state_store

ContentSemanticSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_semantic_review_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentSemanticSnapshotLoader,
) -> None:
    path = "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review"

    @router.get(path, response_model=ContentSemanticReviewResponse)
    def content_revision_semantic_review(
        work_item_id: str, revision_id: str
    ) -> ContentSemanticReviewResponse:
        exact_review = semantic_review_queue.read_exact_review_without_snapshot(
            work_item_id, revision_id
        )
        if exact_review is not None:
            return exact_review
        latest_run = semantic_review_queue.latest_semantic_run(work_item_id, revision_id)
        if latest_run is not None and getattr(latest_run, "error", None) == "runtime_blocked":
            latest_run = None
        if latest_run is not None and latest_run.status == "started":
            revision = (
                content_workflow_store().load_draft_revision_state(work_item_id).latest_revision
            )
            return semantic_review_queue.generating_response(
                work_item_id,
                revision_id,
                None if revision is None else revision.content_digest,
                latest_run.id,
            )
        snapshot = snapshot_loader(work_item_id)
        if latest_run is not None and latest_run.status in {"failed", "blocked"}:
            revision = snapshot.revision_workspace.latest_revision
            if revision is not None and revision.revision_id == revision_id:
                return semantic_review_queue.terminal_run_response(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                    revision_digest=revision.content_digest,
                    run=latest_run,
                )
        return read_content_semantic_review(
            snapshot=snapshot,
            revision_id=revision_id,
            store=content_semantic_review_store(),
        )

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
        snapshot = snapshot_loader(work_item_id)
        client = semantic_review_queue.semantic_codex_client(content_codex_app_server_client)
        revision = snapshot.revision_workspace.latest_revision
        if (
            isinstance(client, StdioCodexAppServerClient)
            and revision is not None
            and revision.revision_id == revision_id
            and revision.content_digest == request.expected_revision_digest
        ):
            return _handle_exact_semantic_post(
                snapshot=snapshot,
                work_item_id=work_item_id,
                revision_id=revision_id,
                revision=revision,
                request=request,
                client=client,
                snapshot_loader=snapshot_loader,
            )
        result = generate_content_semantic_review(
            snapshot=snapshot,
            revision_id=revision_id,
            request=request,
            client=client,
            store=content_semantic_review_store(),
            run_store=local_state_store(),
        )
        if result.status == "conflict":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return result


def _handle_exact_semantic_post(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    work_item_id: str,
    revision_id: str,
    revision: ContentDraftRevision,
    request: ContentSemanticReviewRequest,
    client: StdioCodexAppServerClient,
    snapshot_loader: ContentSemanticSnapshotLoader,
) -> ContentSemanticReviewResponse | JSONResponse:
    review_store = content_semantic_review_store()
    existing = review_store.for_revision(work_item_id, revision_id, revision.content_digest)
    if existing is not None:
        return semantic_review_queue.existing_review_response(
            work_item_id,
            revision_id,
            revision.content_digest,
            existing,
            status="idempotent",
        )
    if not review_store.write_ready():
        return generate_content_semantic_review(
            snapshot=snapshot,
            revision_id=revision_id,
            request=request,
            client=client,
            store=review_store,
            run_store=local_state_store(),
        )
    return semantic_review_queue.queue_semantic_review(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision=revision,
        request=request,
        client=client,
        snapshot_loader=snapshot_loader,
    )


__all__ = ["register_content_semantic_review_routes"]
