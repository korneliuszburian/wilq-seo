from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from os import environ
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_runtime import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticBlockerCode,
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_service import (
    generate_content_semantic_review,
    read_content_semantic_review,
)
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.quality.semantic_run_state import transition_codex_run_if_status
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore, local_state_store

_REAL_STDIO_CODEX_CLIENT = StdioCodexAppServerClient

ContentSemanticSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]

_SEMANTIC_REVIEW_EXECUTOR = ThreadPoolExecutor(
    # A Codex subprocess can outlive its asyncio timeout during teardown. One
    # stale worker must not monopolize the queue after its run is terminalized.
    max_workers=2,
    thread_name_prefix="wilq-content-review",
)
_DEFAULT_SEMANTIC_REVIEW_TIMEOUT_SECONDS = 180.0


class _DeadlineAwareSemanticClient:
    def __init__(self, client: StdioCodexAppServerClient, run_id: str) -> None:
        self._client = client
        self._run_id = run_id

    def run_structured_turn(self, request):
        client = _client_for_queued_deadline(self._client, self._run_id)
        return client.run_structured_turn(request)


def _semantic_codex_client() -> StdioCodexAppServerClient:
    """Give the full-document reviewer the same bounded budget as planning.

    The semantic prompt contains the complete revision, proposal and planning
    input. The generic Codex client deadline is too short for that structured
    payload on real pages, so the API keeps a separate, configurable deadline.
    Test and harness clients remain unchanged.
    """

    client = content_codex_app_server_client()
    if not isinstance(client, _REAL_STDIO_CODEX_CLIENT):
        return client
    return _REAL_STDIO_CODEX_CLIENT(timeout_seconds=_semantic_timeout_seconds())


def _semantic_timeout_seconds() -> float:
    try:
        configured = float(
            environ.get(
                "WILQ_SEMANTIC_REVIEW_CODEX_TIMEOUT_SECONDS",
                str(_DEFAULT_SEMANTIC_REVIEW_TIMEOUT_SECONDS),
            )
        )
    except (TypeError, ValueError):
        configured = _DEFAULT_SEMANTIC_REVIEW_TIMEOUT_SECONDS
    return max(5.0, configured)


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
        exact_review = _read_exact_review_without_snapshot(work_item_id, revision_id)
        if exact_review is not None:
            return exact_review
        latest_run = _latest_semantic_run(work_item_id, revision_id)
        # A runtime safety violation is an audit event, not a semantic review
        # result. Keep the exact attempt in local state, but expose the
        # revision as not_generated so the operator can retry after isolation
        # is repaired and no partial advisory can be mistaken for a result.
        if latest_run is not None and getattr(latest_run, "error", None) == "runtime_blocked":
            latest_run = None
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
    existing = review_store.for_revision(
        work_item_id,
        revision_id,
        revision.content_digest,
    )
    if existing is not None:
        return _existing_review_response(
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
    return _queue_semantic_review(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision=revision,
        request=request,
        client=client,
        snapshot_loader=snapshot_loader,
    )


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
    latest = max(runs, key=lambda run: run.started_at, default=None)
    if latest is not None and latest.status == "started":
        deadline_at = getattr(latest, "deadline_at", None)
        deadline = deadline_at or (
            latest.started_at
            + timedelta(seconds=_semantic_timeout_seconds())
        )
        if utc_now() >= deadline:
            terminal = latest.model_copy(
                update={
                    "status": "failed",
                    "completed_at": utc_now(),
                    "error": "semantic_review_timeout",
                }
            )
            store = local_state_store()
            latest = (
                transition_codex_run_if_status(store, terminal)
                if hasattr(store, "_connect")
                else store.save_codex_run(terminal)
            ) or latest
    return latest


def _existing_review_response(
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
    review: ContentSemanticReview,
    *,
    status: Literal["idempotent", "ready"],
) -> ContentSemanticReviewResponse:
    return ContentSemanticReviewResponse(
        status=status,
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision_digest,
        review=review,
        run_id=review.codex_run_id,
        safe_next_step=review.safe_next_step,
    )


def _read_exact_review_without_snapshot(
    work_item_id: str,
    revision_id: str,
) -> ContentSemanticReviewResponse | None:
    revision = content_workflow_store().load_draft_revision_state(
        work_item_id
    ).latest_revision
    if revision is None or revision.revision_id != revision_id:
        return None
    review = content_semantic_review_store().for_revision(
        work_item_id,
        revision_id,
        revision.content_digest,
    )
    if review is None:
        return None
    return _existing_review_response(
        work_item_id,
        revision_id,
        revision.content_digest,
        review,
        status="ready",
    )


def _save_queued_semantic_run(
    *,
    work_item_id: str,
    revision_id: str,
    revision: ContentDraftRevision,
    run_id: str,
    store: LocalStateStore,
) -> CodexRun:
    """Publish queued identity before the worker performs exact preflight."""

    return store.save_codex_run(
        CodexRun(
            id=run_id,
            skill="wilq-content-operator",
            hook="content_semantic_review",
            source="wilq_api",
            status="started",
            used_endpoints=[
                f"/api/content/work-items/{work_item_id}/draft-revisions/"
                f"{revision_id}/semantic-review"
            ],
            evidence_ids=[
                evidence_id
                for item in (
                    *revision.sections,
                    *revision.faq,
                    *revision.cta_blocks,
                    *revision.internal_links,
                )
                for evidence_id in item.evidence_ids
            ],
            planning_input_digest=revision.planning_input_digest,
            deadline_at=utc_now() + timedelta(seconds=_semantic_timeout_seconds()),
        )
    )


def _queue_semantic_review(
    *,
    work_item_id: str,
    revision_id: str,
    revision: ContentDraftRevision,
    request: ContentSemanticReviewRequest,
    client: StdioCodexAppServerClient,
    snapshot_loader: ContentSemanticSnapshotLoader,
) -> ContentSemanticReviewResponse:
    active = _latest_semantic_run(work_item_id, revision_id)
    if active is not None and active.status == "started":
        return _generating_response(work_item_id, revision_id, revision.content_digest, active.id)
    run_id = f"codex_content_semantic_review_{uuid4().hex}"
    # Publish the queued run before handing it to the worker.  The worker
    # performs expensive exact-snapshot/planning preflight before its service
    # creates a run; GET must still expose this exact attempt in that window.
    _save_queued_semantic_run(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision=revision,
        run_id=run_id,
        store=local_state_store(),
    )
    _SEMANTIC_REVIEW_EXECUTOR.submit(
        _run_queued_semantic_review,
        work_item_id,
        revision_id,
        request,
        client,
        run_id,
        snapshot_loader,
    )
    return _generating_response(work_item_id, revision_id, revision.content_digest, run_id)


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
    code: ContentSemanticBlockerCode = (
        "runtime_blocked" if blocked else "runtime_failed"
    )
    status: Literal["blocked", "failed"] = "blocked" if blocked else "failed"
    error = getattr(run, "error", None)
    source_code = None if error is None else error.split(":", 1)[-1]
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
                source_codes=[source_code] if source_code else [],
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
        client = _DeadlineAwareSemanticClient(client, run_id)
        result = generate_content_semantic_review(
            snapshot=snapshot_loader(work_item_id),
            revision_id=revision_id,
            request=request,
            client=client,
            store=content_semantic_review_store(),
            run_store=local_state_store(),
            run_id=run_id,
        )
        _terminalize_queued_run_from_result(run_id, result)
    except Exception as error:
        _mark_semantic_run_failed(run_id, error)


def _client_for_queued_deadline(
    client: StdioCodexAppServerClient,
    run_id: str,
) -> StdioCodexAppServerClient:
    run = next(
        (item for item in local_state_store().list_codex_runs() if item.id == run_id),
        None,
    )
    deadline_at = None if run is None else getattr(run, "deadline_at", None)
    if deadline_at is None:
        return client
    remaining = (deadline_at - utc_now()).total_seconds()
    if remaining <= 0:
        raise TimeoutError("semantic review deadline expired before Codex turn")
    return _REAL_STDIO_CODEX_CLIENT(
        timeout_seconds=min(client.timeout_seconds, remaining)
    )


def _terminalize_queued_run_from_result(
    run_id: str, result: ContentSemanticReviewResponse
) -> None:
    store = local_state_store()
    run = next((item for item in store.list_codex_runs() if item.id == run_id), None)
    if run is None or run.status != "started":
        return
    if result.status in {"created", "idempotent", "ready", "stale"}:
        status = "completed"
        error = None
    elif result.status == "blocked":
        status = "blocked"
        error = result.blockers[0].code if result.blockers else "semantic_review_blocked"
    else:
        status = "failed"
        error = result.blockers[0].code if result.blockers else "semantic_review_failed"
    terminal = run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})
    if hasattr(store, "_connect"):
        transition_codex_run_if_status(store, terminal)
    else:
        store.save_codex_run(terminal)


def _mark_semantic_run_failed(run_id: str, error: Exception) -> None:
    store = local_state_store()
    run = next((item for item in store.list_codex_runs() if item.id == run_id), None)
    if run is None or run.status != "started":
        return
    terminal = run.model_copy(
        update={
            "status": "failed",
            "completed_at": utc_now(),
            "error": f"worker_exception:{type(error).__name__}",
        }
    )
    if hasattr(store, "_connect"):
        transition_codex_run_if_status(store, terminal)
    else:
        store.save_codex_run(terminal)


__all__ = ["register_content_semantic_review_routes"]
