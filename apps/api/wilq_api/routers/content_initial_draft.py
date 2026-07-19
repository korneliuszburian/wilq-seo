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
from wilq.content.drafts.initial_full_draft import generate_initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import local_state_store

ContentInitialDraftSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]

_INITIAL_DRAFT_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="wilq-content-draft",
)


def register_content_initial_draft_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/initial-draft",
        response_model=ContentInitialDraftResponse,
        responses={409: {"model": ContentInitialDraftResponse}},
    )
    def content_work_item_initial_full_draft(
        work_item_id: str,
        request: ContentInitialDraftRequest,
    ) -> ContentInitialDraftResponse | JSONResponse:
        snapshot = snapshot_loader(work_item_id)
        client = content_codex_app_server_client()
        if _can_queue_initial_draft(snapshot, request) and isinstance(
            client, StdioCodexAppServerClient
        ):
            existing = _latest_initial_draft_run(work_item_id)
            if existing is not None and existing.status == "started":
                proposal = snapshot.planning_workspace.proposal
                return ContentInitialDraftResponse(
                    status="generating",
                    work_item_id=work_item_id,
                    proposal_id=proposal.proposal_id,
                    run_id=existing.id,
                    blockers=[_generation_in_progress_blocker()],
                    safe_next_step=(
                        "Pełny tekst jest już przygotowywany; nie uruchamiaj drugiego."
                    ),
                )
            run_id = f"codex_content_initial_draft_{uuid4().hex}"
            _INITIAL_DRAFT_EXECUTOR.submit(
                _run_queued_initial_draft,
                work_item_id,
                request,
                client,
                run_id,
                snapshot_loader,
            )
            proposal = snapshot.planning_workspace.proposal
            return ContentInitialDraftResponse(
                status="generating",
                work_item_id=work_item_id,
                proposal_id=proposal.proposal_id,
                run_id=run_id,
                blockers=[_generation_in_progress_blocker()],
                safe_next_step="Pełny tekst jest przygotowywany; odśwież ten etap za chwilę.",
            )
        result = generate_initial_full_draft(
            snapshot=snapshot,
            request=request,
            client=client,
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
        )
        if result.status == "conflict":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return result

    @router.get(
        "/api/content/work-items/{work_item_id}/initial-draft",
        response_model=ContentInitialDraftResponse,
    )
    def content_work_item_initial_full_draft_status(
        work_item_id: str,
    ) -> ContentInitialDraftResponse:
        endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
        runs = [
            run
            for run in local_state_store().list_codex_runs()
            if (
                run.hook == "content_initial_full_draft"
                and endpoint in run.used_endpoints
            )
        ]
        proposal_store = content_planning_proposal_store()
        proposal = _proposal_bound_to_latest_approved_plan(
            work_item_id,
            proposal_store,
        ) or proposal_store.latest(work_item_id)
        latest = max(
            (
                run
                for run in runs
                if proposal is None
                or (
                    run.proposal_id == proposal.proposal_id
                    and run.planning_input_digest == proposal.planning_input_digest
                )
            ),
            key=lambda run: run.started_at,
            default=None,
        )
        revision = content_workflow_store().load_draft_revision_state(work_item_id).latest_revision
        if latest is not None and latest.status == "started":
            return ContentInitialDraftResponse(
                status="generating",
                work_item_id=work_item_id,
                proposal_id=None if proposal is None else proposal.proposal_id,
                run_id=latest.id,
                blockers=[_generation_in_progress_blocker()],
                safe_next_step="Pełny tekst jest przygotowywany; odśwież ten etap za chwilę.",
            )
        if (
            latest is not None
            and latest.status == "completed"
            and revision is not None
            and proposal is not None
            and revision.planning_input_digest == proposal.planning_input_digest
        ):
            return ContentInitialDraftResponse(
                status="created",
                work_item_id=work_item_id,
                proposal_id=None if proposal is None else proposal.proposal_id,
                run_id=latest.id,
                revision=revision,
                safe_next_step=(
                    "Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji."
                ),
            )
        if latest is not None and latest.status in {"failed", "blocked"}:
            code = "runtime_failed" if latest.status == "failed" else "runtime_blocked"
            blocker = ContentInitialDraftBlocker(
                code=code,
                label="Nie udało się przygotować pełnego tekstu",
                reason=latest.error or "Generowanie zostało zatrzymane przez bramkę workflow.",
                next_step="Otwórz blocker i ponów po poprawieniu aktualnego wejścia.",
            )
            return ContentInitialDraftResponse(
                status=latest.status,
                work_item_id=work_item_id,
                proposal_id=None if proposal is None else proposal.proposal_id,
                run_id=latest.id,
                blockers=[blocker],
                safe_next_step=blocker.next_step,
            )
        blocker = ContentInitialDraftBlocker(
            code="planning_not_approved",
            label="Pełny tekst czeka na aktualny plan",
            reason="Nie ma zakończonego uruchomienia pełnego tekstu dla bieżącego planu.",
            next_step="Zatwierdź zakres i mapę sekcji, a następnie uruchom pełny tekst.",
        )
        return ContentInitialDraftResponse(
            status="blocked",
            work_item_id=work_item_id,
            proposal_id=None if proposal is None else proposal.proposal_id,
            blockers=[blocker],
            safe_next_step=blocker.next_step,
        )


def _proposal_bound_to_latest_approved_plan(
    work_item_id: str,
    proposal_store,
):
    decisions = content_workflow_store().load_planning_decisions(work_item_id)
    approved_digests = [
        decision.planning_digest
        for decision in decisions
        if decision.decision == "approved"
    ]
    if len(approved_digests) < 2 or len(set(approved_digests)) != 1:
        return None
    return proposal_store.latest_for_planning_digest(work_item_id, approved_digests[0])


def _can_queue_initial_draft(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
) -> bool:
    planning = snapshot.planning_workspace
    if (
        planning is None
        or not planning.scope_current
        or not planning.section_map_current
        or (
            snapshot.revision_workspace.latest_revision is not None
            and snapshot.revision_workspace.context_current
        )
    ):
        return False
    proposal = planning.proposal
    return (
        proposal.proposal_id == request.expected_proposal_id
        and proposal.planning_digest == request.expected_planning_digest
        and proposal.planning_input_digest == request.expected_planning_input_digest
    )


def _generation_in_progress_blocker() -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code="generation_in_progress",
        label="Pełny tekst jest przygotowywany",
        reason="WILQ pracuje na zatwierdzonym planie; wynik pojawi się w tym samym workflow.",
        next_step="Odśwież etap tekstu za chwilę. Nie uruchamiaj drugiego generowania.",
    )


def _latest_initial_draft_run(work_item_id: str) -> CodexRun | None:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    runs = [
        run
        for run in local_state_store().list_codex_runs()
        if run.hook == "content_initial_full_draft" and endpoint in run.used_endpoints
    ]
    return max(runs, key=lambda run: run.started_at, default=None)


def _run_queued_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    run_id: str,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
) -> None:
    try:
        generate_initial_full_draft(
            snapshot=snapshot_loader(work_item_id),
            request=request,
            client=client,
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
            run_id=run_id,
        )
    except Exception as error:
        # The generator records typed terminal state whenever it reaches its
        # own runtime boundary. A worker exception must not leave a permanent
        # ``started`` run or make every retry appear to be still running.
        _mark_initial_draft_run_failed(run_id, error)


def _mark_initial_draft_run_failed(run_id: str, error: Exception) -> None:
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


__all__ = ["register_content_initial_draft_route"]
