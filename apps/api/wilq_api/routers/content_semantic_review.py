from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from os import environ
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
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
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import local_state_store

_REAL_STDIO_CODEX_CLIENT = StdioCodexAppServerClient

ContentSemanticSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]

_SEMANTIC_REVIEW_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="wilq-content-review",
)
_DEFAULT_SEMANTIC_REVIEW_TIMEOUT_SECONDS = 180.0


def _semantic_codex_client():
    """Give the full-document reviewer the same bounded budget as planning.

    The semantic prompt contains the complete revision, proposal and planning
    input. The generic Codex client deadline is too short for that structured
    payload on real pages, so the API keeps a separate, configurable deadline.
    Test and harness clients remain unchanged.
    """

    client = content_codex_app_server_client()
    if not isinstance(client, _REAL_STDIO_CODEX_CLIENT):
        return client
    try:
        timeout_seconds = float(
            environ.get(
                "WILQ_SEMANTIC_REVIEW_CODEX_TIMEOUT_SECONDS",
                str(_DEFAULT_SEMANTIC_REVIEW_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        timeout_seconds = _DEFAULT_SEMANTIC_REVIEW_TIMEOUT_SECONDS
    return _REAL_STDIO_CODEX_CLIENT(timeout_seconds=max(5.0, timeout_seconds))


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
        latest_run = _latest_semantic_run(work_item_id, revision_id)
        if latest_run is not None and latest_run.status == "started":
            revision = content_workflow_store().load_draft_revision_state(
                work_item_id
            ).latest_revision
            return _generating_response(
                work_item_id,
                revision_id,
                None if revision is None else revision.content_digest,
                latest_run.id,
            )
        snapshot = snapshot_loader(work_item_id)
        if latest_run is not None and latest_run.status in {"failed", "blocked"}:
            revision = snapshot.revision_workspace.latest_revision
            if revision is not None and revision.revision_id == revision_id:
                return _terminal_run_response(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                    revision_digest=revision.content_digest,
                    run=latest_run,
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
        client = _semantic_codex_client()
        revision = snapshot.revision_workspace.latest_revision
        if (
            isinstance(client, StdioCodexAppServerClient)
            and revision is not None
            and revision.revision_id == revision_id
            and revision.content_digest == request.expected_revision_digest
        ):
            # Known preflight blockers must be returned before queueing.  Otherwise
            # the browser sees a misleading ``generating`` response, while the
            # worker exits before starting a CodexRun (for example when semantic
            # review storage still needs an approved maintenance window).  The
            # read-only readiness check cannot invoke Codex or mutate state.
            review_store = content_semantic_review_store()
            if not review_store.write_ready():
                return generate_content_semantic_review(
                    snapshot=snapshot,
                    revision_id=revision_id,
                    request=request,
                    client=client,
                    store=review_store,
                    run_store=local_state_store(),
                )
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


def _terminal_run_response(
    *,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
    run: CodexRun,
) -> ContentSemanticReviewResponse:
    blocked = run.status == "blocked"
    code = "runtime_blocked" if blocked else "runtime_failed"
    status = "blocked" if blocked else "failed"
    return ContentSemanticReviewResponse(
        status=status,
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision_digest,
        run_id=run.id,
        runtime=ContentCodexRuntimeTrace(status=status),
        blockers=[
            ContentSemanticReviewBlocker(
                code=code,
                label=(
                    "Codex zatrzymał sprawdzenie semantyczne"
                    if blocked
                    else "Codex nie zakończył sprawdzenia semantycznego"
                ),
                reason=(
                    "Poprzednia próba review została bezpiecznie zatrzymana; "
                    "tekst nie został zmieniony."
                    if blocked
                    else "Poprzednia próba review nie zwróciła poprawnego wyniku; "
                    "tekst nie został zmieniony."
                ),
                next_step="Uruchom nową próbę review dla tej samej exact rewizji.",
                source_codes=[run.error] if run.error else [],
            )
        ],
        safe_next_step="Uruchom nową próbę review dla tej samej exact rewizji.",
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
