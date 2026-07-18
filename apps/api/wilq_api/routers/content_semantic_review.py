from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReviewBlocker,
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_service import (
    generate_content_semantic_review,
    read_content_semantic_review,
)
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import local_state_store

ContentSemanticSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]

_SEMANTIC_REVIEW_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="wilq-content-review",
)


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
        active = _latest_semantic_run(work_item_id, revision_id)
        if active is not None and active.status == "started":
            snapshot = snapshot_loader(work_item_id)
            revision = snapshot.revision_workspace.latest_revision
            return _generating_response(
                work_item_id,
                revision_id,
                None if revision is None else revision.content_digest,
                active.id,
            )
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
        snapshot = snapshot_loader(work_item_id)
        client = content_codex_app_server_client()
        revision = snapshot.revision_workspace.latest_revision
        if (
            isinstance(client, StdioCodexAppServerClient)
            and revision is not None
            and revision.revision_id == revision_id
            and revision.content_digest == request.expected_revision_digest
        ):
            active = _latest_semantic_run(work_item_id, revision_id)
            if active is not None and active.status == "started":
                return _generating_response(
                    work_item_id, revision_id, revision.content_digest, active.id
                )
            run_id = f"codex_content_semantic_review_{uuid4().hex}"
            _SEMANTIC_REVIEW_EXECUTOR.submit(
                _run_queued_semantic_review,
                work_item_id,
                revision_id,
                request,
                client,
                run_id,
                snapshot_loader,
            )
            return _generating_response(
                work_item_id, revision_id, revision.content_digest, run_id
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


def _latest_semantic_run(work_item_id: str, revision_id: str) -> CodexRun | None:
    endpoint = (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/semantic-review"
    )
    runs = [
        run
        for run in local_state_store().list_codex_runs()
        if run.hook == "content_semantic_review" and endpoint in run.used_endpoints
    ]
    return max(runs, key=lambda run: run.started_at, default=None)


def _generating_response(
    work_item_id: str,
    revision_id: str,
    revision_digest: str | None,
    run_id: str,
) -> ContentSemanticReviewResponse:
    return ContentSemanticReviewResponse(
        status="generating",
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision_digest,
        run_id=run_id,
        blockers=[
            ContentSemanticReviewBlocker(
                code="generation_in_progress",
                label="Sprawdzenie tekstu jest przygotowywane",
                reason=(
                    "WILQ analizuje dokładną rewizję; wynik pozostanie advisory "
                    "i wymaga człowieka."
                ),
                next_step="Odśwież sprawdzenie za chwilę. Nie uruchamiaj drugiego review.",
            )
        ],
        safe_next_step="Odśwież sprawdzenie za chwilę. Nie uruchamiaj drugiego review.",
    )


def _run_queued_semantic_review(
    work_item_id: str,
    revision_id: str,
    request: ContentSemanticReviewRequest,
    client: StdioCodexAppServerClient,
    run_id: str,
    snapshot_loader: ContentSemanticSnapshotLoader,
) -> None:
    try:
        generate_content_semantic_review(
            snapshot=snapshot_loader(work_item_id),
            revision_id=revision_id,
            request=request,
            client=client,
            store=content_semantic_review_store(),
            run_store=local_state_store(),
            run_id=run_id,
        )
    except Exception as error:
        _mark_semantic_run_failed(run_id, error)


def _mark_semantic_run_failed(run_id: str, error: Exception) -> None:
    store = local_state_store()
    run = next((item for item in store.list_codex_runs() if item.id == run_id), None)
    if run is None or run.status != "started":
        return
    store.save_codex_run(
        run.model_copy(
            update={
                "status": "failed",
                "completed_at": utc_now(),
                "error": f"worker_exception:{type(error).__name__}",
            }
        )
    )


__all__ = ["register_content_semantic_review_routes"]
