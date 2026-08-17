from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import BoundedSemaphore
from typing import ParamSpec, TypeVar

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_runtime import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts import initial_draft_queue
from wilq.content.drafts.initial_draft_run import (
    effective_initial_draft_deadline,
    initial_draft_context_digest,
    revision_matches_initial_draft_context,
    transition_initial_draft_run_if_status,
)
from wilq.content.drafts.initial_full_draft import generate_initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
    parse_content_initial_draft_blocker_code,
)
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.store.store import content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import local_state_store

ContentInitialDraftSnapshotLoader = initial_draft_queue.ContentInitialDraftSnapshotLoader

_P = ParamSpec("_P")
_T = TypeVar("_T")


InitialDraftQueueFullError = initial_draft_queue.InitialDraftQueueFullError


def _can_queue_initial_draft(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
) -> bool:
    return initial_draft_queue.can_queue_initial_draft(snapshot, request)


def _snapshot_initial_draft_context_digest(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
) -> str:
    return initial_draft_queue.snapshot_initial_draft_context_digest(snapshot, proposal)


def _queue_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentInitialDraftResponse:
    return initial_draft_queue.submit_initial_draft_to_queue(
        work_item_id,
        request,
        client,
        snapshot_loader,
        snapshot,
        _INITIAL_DRAFT_EXECUTOR,
        stale_response=lambda item_id: _read_initial_draft_status(
            item_id, snapshot_loader=snapshot_loader
        ),
    )


def _persist_terminal_preflight_run(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    result: ContentInitialDraftResponse,
    run_id: str,
) -> None:
    initial_draft_queue._persist_terminal_preflight_run(
        snapshot=snapshot, request=request, result=result, run_id=run_id
    )


class BoundedInitialDraftExecutor:
    """Reject work once both draft workers are occupied instead of queueing it."""

    def __init__(self, *, max_workers: int) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="wilq-content-draft",
        )
        self._capacity = BoundedSemaphore(max_workers)

    def submit(
        self,
        fn: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Future[_T]:
        if not self._capacity.acquire(blocking=False):
            raise InitialDraftQueueFullError("initial draft executor capacity is full")
        try:
            future = self._executor.submit(fn, *args, **kwargs)
        except BaseException:
            self._capacity.release()
            raise
        future.add_done_callback(lambda _future: self._capacity.release())
        return future

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


_INITIAL_DRAFT_EXECUTOR = BoundedInitialDraftExecutor(max_workers=2)
# Regulated documents run an independent assurance critic with bounded repair
# rounds; a full BDO-style pass needs more wall clock than a plain draft.
_DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS = 2400.0
_INITIAL_DRAFT_QUEUE_RETRY_SECONDS = 5


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
        return _submit_initial_draft(work_item_id, request, snapshot_loader)

    @router.get(
        "/api/content/work-items/{work_item_id}/initial-draft",
        response_model=ContentInitialDraftResponse,
    )
    def content_work_item_initial_full_draft_status(
        work_item_id: str,
    ) -> ContentInitialDraftResponse:
        return _read_initial_draft_status(work_item_id, snapshot_loader=snapshot_loader)


def _submit_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
) -> ContentInitialDraftResponse | JSONResponse:
    snapshot = snapshot_loader(work_item_id)
    client = content_codex_app_server_client()
    if initial_draft_queue.can_queue_initial_draft(snapshot, request, client):
        return initial_draft_queue.submit_initial_draft_to_queue(
            work_item_id,
            request,
            client,
            snapshot_loader,
            snapshot,
            _INITIAL_DRAFT_EXECUTOR,
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


def _queued_initial_draft_response(
    work_item_id: str,
    proposal_id: str | None,
    run_id: str,
    already_running: bool,
) -> ContentInitialDraftResponse:
    return ContentInitialDraftResponse(
        status="generating",
        work_item_id=work_item_id,
        proposal_id=proposal_id,
        run_id=run_id,
        blockers=[_generation_in_progress_blocker()],
        safe_next_step=(
            "Pełny tekst jest już przygotowywany; nie uruchamiaj drugiego."
            if already_running
            else "Pełny tekst jest przygotowywany; odśwież ten etap za chwilę."
        ),
    )


def _initial_draft_queue_full_response(
    work_item_id: str,
    proposal_id: str | None,
    run_id: str,
) -> ContentInitialDraftResponse:
    blocker = ContentInitialDraftBlocker(
        code="initial_draft_queue_full",
        label="Kolejka pełnego tekstu jest pełna",
        reason="Dwa pełne teksty są już przygotowywane i WILQ nie zakolejkuje cichej próby.",
        next_step="Ponów uruchomienie za kilka sekund dla tego samego aktualnego planu.",
        retry_after_seconds=_INITIAL_DRAFT_QUEUE_RETRY_SECONDS,
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=proposal_id,
        run_id=run_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _read_initial_draft_status(
    work_item_id: str,
    *,
    snapshot_loader: ContentInitialDraftSnapshotLoader | None = None,
) -> ContentInitialDraftResponse:
    proposal = _latest_generated_proposal(work_item_id, content_planning_proposal_store())
    stale = _stale_initial_draft_response(work_item_id, proposal)
    if stale is not None:
        return stale
    revision = content_workflow_store().load_draft_revision_state(work_item_id).latest_revision
    unscoped_latest = _latest_run_for_proposal(work_item_id, proposal, revision)
    unscoped_canonical = _canonical_revision_run(revision, proposal)
    needs_current_context = bool(
        (
            unscoped_latest is not None
            and getattr(unscoped_latest, "initial_draft_context_digest", None)
        )
        or (
            unscoped_canonical is not None
            and getattr(unscoped_canonical, "initial_draft_context_digest", None)
        )
        or _has_context_bound_initial_draft_run(work_item_id)
    )
    context_digest = None
    if needs_current_context:
        current_proposal, context_digest = _current_initial_draft_context(
            work_item_id,
            snapshot_loader,
        )
        if current_proposal is not None:
            proposal = current_proposal
    latest = (
        _latest_run_for_proposal(
            work_item_id,
            proposal,
            revision,
            context_digest=context_digest,
        )
        if needs_current_context
        else unscoped_latest
    )
    if (
        latest is not None
        and latest.status == "started"
        and _run_matches_revision_context(
            latest,
            revision,
            proposal,
            context_digest=context_digest,
        )
    ):
        return _queued_initial_draft_response(
            work_item_id,
            None if proposal is None else proposal.proposal_id,
            latest.id,
            False,
        )
    canonical_run = (
        _canonical_revision_run(
            revision,
            proposal,
            context_digest=context_digest,
        )
        if needs_current_context
        else unscoped_canonical
    )
    if canonical_run is not None and proposal is not None and revision is not None:
        return ContentInitialDraftResponse(
            status="created",
            work_item_id=work_item_id,
            proposal_id=proposal.proposal_id,
            run_id=canonical_run.id,
            revision=revision,
            safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
        )
    if (
        _completed_initial_draft_matches(latest, revision, proposal)
        and latest is not None
        and proposal is not None
        and revision is not None
    ):
        return ContentInitialDraftResponse(
            status="created",
            work_item_id=work_item_id,
            proposal_id=proposal.proposal_id,
            run_id=latest.id,
            revision=revision,
            safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
        )
    if latest is not None and latest.status in {"failed", "blocked"}:
        return _terminal_initial_draft_response(work_item_id, proposal, latest)
    return _initial_draft_not_started_response(work_item_id, proposal)


def _current_initial_draft_context(
    work_item_id: str,
    snapshot_loader: ContentInitialDraftSnapshotLoader | None,
) -> tuple[ContentPlanningProposal | None, str | None]:
    """Read the source-owned context used to select a visible draft run.

    A queued run never establishes this value: a delayed request must not be
    able to make an older package, URL, service, or planning lineage current.
    """

    if snapshot_loader is None:
        return None, None
    snapshot = snapshot_loader(work_item_id)
    planning = snapshot.planning_workspace
    if planning is None:
        return None, ""
    current = planning.proposal
    return current, initial_draft_queue.snapshot_initial_draft_context_digest(snapshot, current)


def _has_context_bound_initial_draft_run(work_item_id: str) -> bool:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    return any(
        run.hook == "content_initial_full_draft"
        and endpoint in run.used_endpoints
        and getattr(run, "initial_draft_context_digest", None) is not None
        for run in local_state_store().list_codex_runs()
    )


def _stale_initial_draft_response(
    work_item_id: str,
    proposal: ContentPlanningProposal | None,
) -> ContentInitialDraftResponse | None:
    if proposal is None:
        return None
    proposal_store = content_planning_proposal_store()
    latest_for_service = getattr(
        proposal_store,
        "latest_for_service",
        getattr(proposal_store, "latest_generation_response", lambda *_: None),
    )
    newer = latest_for_service(work_item_id, getattr(proposal, "service_card_id", None))
    if (
        newer is None
        or newer.planning_input_digest is None
        or getattr(newer, "proposal_id", None) == proposal.proposal_id
        or newer.planning_input_digest == proposal.planning_input_digest
    ):
        return None
    blocker = ContentInitialDraftBlocker(
        code="stale_planning_input",
        label="Metryki albo kontekst planu zmieniły się",
        reason="Nowsze uruchomienie planowania ma inny planning_input_digest niż rewizja.",
        next_step="Wygeneruj nowy plan przed tworzeniem tekstu.",
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=proposal.proposal_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _latest_run_for_proposal(
    work_item_id: str,
    proposal: ContentPlanningProposal | None,
    revision: ContentDraftRevision | None = None,
    *,
    context_digest: str | None = None,
) -> CodexRun | None:
    if proposal is None:
        return None
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    latest = max(
        (
            run
            for run in local_state_store().list_codex_runs()
            if (
                run.hook == "content_initial_full_draft"
                and endpoint in run.used_endpoints
                and run.proposal_id == proposal.proposal_id
                and run.planning_input_digest == proposal.planning_input_digest
                and (context_digest is None or run.initial_draft_context_digest == context_digest)
                and (
                    getattr(run, "planning_digest", None)
                    == getattr(proposal, "planning_digest", None)
                    or (
                        run.planning_digest is None
                        and _legacy_run_matches_revision(run, proposal, revision)
                    )
                )
            )
        ),
        key=lambda run: run.started_at,
        default=None,
    )
    return _expire_stale_initial_draft_run(latest)


def _legacy_run_matches_revision(
    run: CodexRun,
    proposal: ContentPlanningProposal,
    revision: ContentDraftRevision | None,
) -> bool:
    metadata = getattr(revision, "proposal_metadata", None)
    return bool(
        revision is not None
        and getattr(revision, "planning_digest", None) == proposal.planning_digest
        and getattr(revision, "planning_input_digest", None) == proposal.planning_input_digest
        and getattr(metadata, "codex_run_id", None) == run.id
    )


def _canonical_revision_run(
    revision: ContentDraftRevision | None,
    proposal: ContentPlanningProposal | None,
    *,
    context_digest: str | None = None,
) -> CodexRun | None:
    metadata = getattr(revision, "proposal_metadata", None)
    run_id = getattr(metadata, "codex_run_id", None)
    if revision is None or proposal is None or not run_id:
        return None
    proposal_id = proposal.proposal_id
    planning_input_digest = proposal.planning_input_digest
    if proposal_id is None or planning_input_digest is None:
        return None
    if (
        getattr(revision, "planning_digest", None) != proposal.planning_digest
        or getattr(revision, "planning_input_digest", None) != proposal.planning_input_digest
    ):
        return None
    if context_digest is not None and not revision_matches_initial_draft_context(
        revision,
        proposal_id=proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=planning_input_digest,
        context_digest=context_digest,
    ):
        return None
    return next(
        (
            run
            for run in local_state_store().list_codex_runs()
            if run.id == run_id
            and run.status == "completed"
            and run.proposal_id == proposal_id
            and run.planning_digest in {None, proposal.planning_digest}
            and run.planning_input_digest == planning_input_digest
        ),
        None,
    )


def _run_matches_revision_context(
    run: CodexRun,
    revision: ContentDraftRevision | None,
    proposal: ContentPlanningProposal | None,
    *,
    context_digest: str | None = None,
) -> bool:
    if proposal is None or run.initial_draft_context_digest is None:
        return False
    proposal_id = proposal.proposal_id
    planning_input_digest = proposal.planning_input_digest
    if proposal_id is None or planning_input_digest is None:
        return False
    if context_digest is not None and run.initial_draft_context_digest != context_digest:
        return False
    if revision is None:
        return run.initial_draft_base_revision_id is None
    if run.initial_draft_base_revision_id == revision.revision_id:
        return True
    package_digest = getattr(revision, "draft_package_digest", None)
    return run.initial_draft_context_digest == initial_draft_context_digest(
        base_revision_id=getattr(revision, "base_revision_id", None),
        draft_package_id=getattr(revision, "draft_package_id", None),
        draft_package_digest=package_digest,
        final_canonical_url=getattr(revision, "final_canonical_url", None),
        service_card_id=getattr(revision, "service_card_id", None),
        proposal_id=proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=planning_input_digest,
    )


def _completed_initial_draft_matches(
    run: CodexRun | None,
    revision: ContentDraftRevision | None,
    proposal: ContentPlanningProposal | None,
) -> bool:
    return bool(
        run is not None
        and run.status == "completed"
        and revision is not None
        and proposal is not None
        and getattr(revision, "planning_input_digest", None) == proposal.planning_input_digest
    )


def _terminal_initial_draft_response(
    work_item_id: str,
    proposal: ContentPlanningProposal | None,
    run: CodexRun,
) -> ContentInitialDraftResponse:
    code, source_codes = _terminal_blocker_details(run)
    blocker = ContentInitialDraftBlocker(
        code=code,
        label="Nie udało się przygotować pełnego tekstu",
        reason=run.error or "Generowanie zostało zatrzymane przez bramkę workflow.",
        next_step=(
            "Popraw wskazany blocker i uruchom nową próbę."
            if code not in {"runtime_failed", "runtime_blocked"}
            else "Otwórz blocker i ponów po sprawdzeniu runtime."
        ),
        source_codes=source_codes,
        retry_after_seconds=(
            _INITIAL_DRAFT_QUEUE_RETRY_SECONDS if code == "initial_draft_queue_full" else None
        ),
    )
    return ContentInitialDraftResponse(
        status="failed" if run.status == "failed" else "blocked",
        work_item_id=work_item_id,
        proposal_id=None if proposal is None else proposal.proposal_id,
        run_id=run.id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _initial_draft_not_started_response(
    work_item_id: str,
    proposal: ContentPlanningProposal | None,
) -> ContentInitialDraftResponse:
    blocker = (
        ContentInitialDraftBlocker(
            code="draft_not_started",
            label="Pełny tekst nie został jeszcze uruchomiony",
            reason="Aktualny wygenerowany plan jest gotowy, ale nie ma uruchomienia tekstu.",
            next_step="Przygotuj pełny tekst z widocznego szkicu struktury.",
        )
        if proposal is not None
        else ContentInitialDraftBlocker(
            code="planning_not_ready",
            label="Pełny tekst czeka na aktualny plan",
            reason="Nie ma aktualnego wygenerowanego planu dla bieżącego kontekstu.",
            next_step="Wygeneruj aktualny plan dla bieżącego kontekstu.",
        )
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=None if proposal is None else proposal.proposal_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _latest_generated_proposal(
    work_item_id: str,
    proposal_store: ContentPlanningProposalStore,
) -> ContentPlanningProposal | None:
    proposal = proposal_store.latest(work_item_id)
    if not (
        proposal is not None
        and getattr(proposal, "generation_status", None) == "codex_generated"
        and getattr(proposal, "proposal_id", None)
        and getattr(proposal, "planning_input_digest", None)
    ):
        return None
    return proposal


def _generation_in_progress_blocker() -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code="generation_in_progress",
        label="Pełny tekst jest przygotowywany",
        reason=(
            "WILQ pracuje na dokładnym wygenerowanym planie; wynik pojawi się w tym samym workflow."
        ),
        next_step="Odśwież etap tekstu za chwilę. Nie uruchamiaj drugiego generowania.",
    )


def _expire_stale_initial_draft_run(run: CodexRun | None) -> CodexRun | None:
    if run is None or run.status != "started":
        return run
    if utc_now() < effective_initial_draft_deadline(run):
        return run
    return transition_initial_draft_run_if_status(
        local_state_store(), run, status="failed", error="initial_draft_timeout"
    )


def _terminal_blocker_details(
    run: CodexRun,
) -> tuple[ContentInitialDraftBlockerCode, list[str]]:
    code, separator, source_text = (run.error or "").partition("|")
    parsed_code = parse_content_initial_draft_blocker_code(code)
    if parsed_code is not None:
        return parsed_code, source_text.split(",") if separator and source_text else []
    return ("runtime_failed" if run.status == "failed" else "runtime_blocked"), []


__all__ = ["register_content_initial_draft_route"]
