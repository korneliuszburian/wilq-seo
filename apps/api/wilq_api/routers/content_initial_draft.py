from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_runtime import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.initial_draft_run import (
    claim_initial_draft_run,
    effective_initial_draft_deadline,
    initial_draft_context_digest,
    transition_initial_draft_run_if_status,
)
from wilq.content.drafts.initial_full_draft import generate_initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import content_draft_package_digest
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import local_state_store

ContentInitialDraftSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]

_INITIAL_DRAFT_EXECUTOR = ThreadPoolExecutor(
    # Assurance may spend minutes in a Codex subprocess. A stale worker must
    # not monopolize the queue and prevent a later exact proposal from being
    # retried.
    max_workers=2,
    thread_name_prefix="wilq-content-draft",
)
_DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS = 900.0


class _InitialDraftDeadlineClient:
    def __init__(
        self,
        base: StdioCodexAppServerClient,
        run_id: str,
        snapshot_loader: ContentInitialDraftSnapshotLoader,
        work_item_id: str,
    ) -> None:
        self._base = base
        self._run_id = run_id
        self._snapshot_loader = snapshot_loader
        self._work_item_id = work_item_id

    def run_structured_turn(self, request):
        run = next(
            (item for item in local_state_store().list_codex_runs() if item.id == self._run_id),
            None,
        )
        if run is None or run.status != "started":
            raise TimeoutError("initial draft run is no longer active")
        snapshot = self._snapshot_loader(self._work_item_id)
        planning = snapshot.planning_workspace
        if (
            planning is None
            or run.initial_draft_context_digest
            != _snapshot_initial_draft_context_digest(snapshot, planning.proposal)
        ):
            transition_initial_draft_run_if_status(
                local_state_store(),
                run,
                status="blocked",
                error="stale_initial_draft_context",
            )
            raise TimeoutError("initial draft context changed")
        remaining = (effective_initial_draft_deadline(run) - utc_now()).total_seconds()
        if remaining <= 0:
            raise TimeoutError("initial draft deadline expired")
        return StdioCodexAppServerClient(
            timeout_seconds=min(self._base.timeout_seconds, remaining)
        ).run_structured_turn(request)


class _ContextCheckedWorkflowStore:
    def __init__(self, base, snapshot_loader, work_item_id: str) -> None:
        self._base = base
        self._snapshot_loader = snapshot_loader
        self._work_item_id = work_item_id

    def append_draft_revision(self, command, *, completed_codex_run=None):
        snapshot = self._snapshot_loader(self._work_item_id)
        planning = snapshot.planning_workspace
        if planning is None:
            raise ValueError("stale_initial_draft_context")
        current_digest = _snapshot_initial_draft_context_digest(snapshot, planning.proposal)
        if (
            completed_codex_run is not None
            and completed_codex_run.initial_draft_context_digest
            != current_digest
        ):
            raise ValueError("stale_initial_draft_context")
        return self._base.append_draft_revision(
            command, completed_codex_run=completed_codex_run
        )

_INITIAL_DRAFT_BLOCKER_CODES = {
    "planning_not_ready",
    "planning_not_generated",
    "stale_planning_input",
    "proposal_mismatch",
    "revision_already_exists",
    "missing_generation_contract",
    "runtime_blocked",
    "runtime_failed",
    "invalid_structured_output",
    "document_scope_mismatch",
    "generated_claim_blocked",
    "draft_assurance_failed",
    "draft_assurance_runtime_failed",
    "draft_assurance_invalid_output",
    "revision_conflict",
    "persistence_failed",
    "generation_in_progress",
}


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
        return _read_initial_draft_status(work_item_id)


def _submit_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
) -> ContentInitialDraftResponse | JSONResponse:
    snapshot = snapshot_loader(work_item_id)
    client = content_codex_app_server_client()
    if _can_queue_initial_draft(snapshot, request) and isinstance(
        client, StdioCodexAppServerClient
    ):
        return _queue_initial_draft(work_item_id, request, client, snapshot_loader, snapshot)
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


def _queue_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentInitialDraftResponse:
    planning = snapshot.planning_workspace
    if planning is None:
        raise RuntimeError("Initial draft queue requires a planning workspace.")
    proposal = planning.proposal
    context_digest = _snapshot_initial_draft_context_digest(snapshot, proposal)
    claim = claim_initial_draft_run(
        local_state_store(),
        work_item_id=work_item_id,
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
        evidence_ids=list(getattr(proposal, "evidence_ids", [])),
        timeout_seconds=_DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS,
        context_current=snapshot.revision_workspace.context_current,
        context_digest=context_digest,
        expected_base_revision_id=getattr(
            snapshot.revision_workspace.latest_revision, "revision_id", None
        ),
    )
    run_id = claim.run.id
    if claim.canonical_revision is not None:
        return ContentInitialDraftResponse(
            status="created",
            work_item_id=work_item_id,
            proposal_id=proposal.proposal_id,
            run_id=claim.run.id,
            revision=claim.canonical_revision,
            safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
        )
    if not claim.newly_claimed:
        return _queued_initial_draft_response(
            work_item_id, proposal.proposal_id, run_id, True
        )
    _INITIAL_DRAFT_EXECUTOR.submit(
        _run_queued_initial_draft,
        work_item_id,
        request,
        client,
        run_id,
        snapshot_loader,
    )
    return _queued_initial_draft_response(
        work_item_id, proposal.proposal_id, run_id, False
    )


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


def _read_initial_draft_status(work_item_id: str) -> ContentInitialDraftResponse:
    proposal = _latest_generated_proposal(work_item_id, content_planning_proposal_store())
    stale = _stale_initial_draft_response(work_item_id, proposal)
    if stale is not None:
        return stale
    revision = content_workflow_store().load_draft_revision_state(work_item_id).latest_revision
    latest = _latest_run_for_proposal(work_item_id, proposal, revision)
    if latest is not None and latest.status == "started" and _run_matches_revision_context(
        latest, revision, proposal
    ):
        return _queued_initial_draft_response(
            work_item_id,
            None if proposal is None else proposal.proposal_id,
            latest.id,
            False,
        )
    canonical_run = _canonical_revision_run(revision, proposal)
    if canonical_run is not None:
        return ContentInitialDraftResponse(
            status="created",
            work_item_id=work_item_id,
            proposal_id=proposal.proposal_id,
            run_id=canonical_run.id,
            revision=revision,
            safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
        )
    if _completed_initial_draft_matches(latest, revision, proposal):
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
    revision: object | None = None,
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
    revision: object | None,
) -> bool:
    metadata = getattr(revision, "proposal_metadata", None)
    return bool(
        revision is not None
        and getattr(revision, "planning_digest", None) == proposal.planning_digest
        and getattr(revision, "planning_input_digest", None)
        == proposal.planning_input_digest
        and getattr(metadata, "codex_run_id", None) == run.id
    )


def _canonical_revision_run(
    revision: object | None,
    proposal: ContentPlanningProposal | None,
) -> CodexRun | None:
    metadata = getattr(revision, "proposal_metadata", None)
    run_id = getattr(metadata, "codex_run_id", None)
    if revision is None or proposal is None or not run_id:
        return None
    if (
        getattr(revision, "planning_digest", None) != proposal.planning_digest
        or getattr(revision, "planning_input_digest", None)
        != proposal.planning_input_digest
    ):
        return None
    return next(
        (
            run
            for run in local_state_store().list_codex_runs()
            if run.id == run_id
            and run.status == "completed"
            and run.proposal_id == proposal.proposal_id
            and run.planning_digest in {None, proposal.planning_digest}
            and run.planning_input_digest == proposal.planning_input_digest
        ),
        None,
    )


def _run_matches_revision_context(
    run: CodexRun,
    revision: object | None,
    proposal: ContentPlanningProposal | None,
) -> bool:
    if proposal is None or run.initial_draft_context_digest is None:
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
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
    )


def _completed_initial_draft_matches(
    run: CodexRun | None,
    revision: object,
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


def _can_queue_initial_draft(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
) -> bool:
    planning = snapshot.planning_workspace
    if (
        planning is None
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
        reason=(
            "WILQ pracuje na dokładnym wygenerowanym planie; "
            "wynik pojawi się w tym samym workflow."
        ),
        next_step="Odśwież etap tekstu za chwilę. Nie uruchamiaj drugiego generowania.",
    )


def _latest_initial_draft_run(work_item_id: str) -> CodexRun | None:
    endpoint = f"/api/content/work-items/{work_item_id}/initial-draft"
    runs = [
        run
        for run in local_state_store().list_codex_runs()
        if run.hook == "content_initial_full_draft" and endpoint in run.used_endpoints
    ]
    latest = max(runs, key=lambda run: run.started_at, default=None)
    return _expire_stale_initial_draft_run(latest)


def _expire_stale_initial_draft_run(run: CodexRun | None) -> CodexRun | None:
    if run is None or run.status != "started":
        return run
    if utc_now() < effective_initial_draft_deadline(run):
        return run
    return transition_initial_draft_run_if_status(
        local_state_store(), run, status="failed", error="initial_draft_timeout"
    )


def _run_queued_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    run_id: str,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
) -> None:
    try:
        snapshot = snapshot_loader(work_item_id)
        run = next(
            (item for item in local_state_store().list_codex_runs() if item.id == run_id),
            None,
        )
        planning = snapshot.planning_workspace
        if run is None or planning is None or (
            run.initial_draft_context_digest
            and run.initial_draft_context_digest
            != _snapshot_initial_draft_context_digest(snapshot, planning.proposal)
        ):
            _mark_initial_draft_run_failed(run_id, RuntimeError("stale_initial_draft_context"))
            return
        deadline_client = _InitialDraftDeadlineClient(
            client, run_id, snapshot_loader, work_item_id
        )
        result = generate_initial_full_draft(
            snapshot=snapshot,
            request=request,
            client=deadline_client,
            workflow_store=_ContextCheckedWorkflowStore(
                content_workflow_store(), snapshot_loader, work_item_id
            ),
            run_store=local_state_store(),
            run_id=run_id,
        )
        if result.status in {"blocked", "failed", "conflict"}:
            _persist_terminal_preflight_run(
                snapshot=snapshot,
                request=request,
                result=result,
                run_id=run_id,
            )
    except Exception as error:
        # The generator records typed terminal state whenever it reaches its
        # own runtime boundary. A worker exception must not leave a permanent
        # ``started`` run or make every retry appear to be still running.
        _mark_initial_draft_run_failed(run_id, error)


def _snapshot_initial_draft_context_digest(snapshot, proposal) -> str:
    package = getattr(
        getattr(getattr(snapshot, "draft_package", None), "draft_package_result", None),
        "draft_package",
        None,
    )
    item = getattr(getattr(snapshot, "preflight", None), "item", None)
    return initial_draft_context_digest(
        base_revision_id=getattr(
            getattr(snapshot.revision_workspace, "latest_revision", None),
            "revision_id",
            None,
        ),
        draft_package_id=getattr(package, "id", None),
        draft_package_digest=None if package is None else content_draft_package_digest(package),
        final_canonical_url=getattr(item, "final_canonical_url", None)
        or getattr(item, "intended_final_url", None),
        service_card_id=getattr(proposal, "service_card_id", None),
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
    )


def _persist_terminal_preflight_run(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    result: ContentInitialDraftResponse,
    run_id: str,
) -> None:
    store = local_state_store()
    status: Literal["failed", "blocked"] = (
        "failed" if result.status == "failed" else "blocked"
    )
    blocker_code = result.blockers[0].code if result.blockers else status
    existing = next(
        (run for run in store.list_codex_runs() if run.id == run_id), None
    )
    if existing is not None:
        transition_initial_draft_run_if_status(
            store, existing, status=status, error=blocker_code
        )
        return
    store.save_codex_run(
        CodexRun(
            id=run_id,
            skill="wilq-content-operator",
            hook="content_initial_full_draft",
            source="wilq_api",
            status=status,
            used_endpoints=[
                f"/api/content/work-items/{snapshot.preflight.item.id}/initial-draft"
            ],
            evidence_ids=[],
            proposal_id=request.expected_proposal_id,
            planning_input_digest=request.expected_planning_input_digest,
            completed_at=utc_now(),
            error=blocker_code,
        )
    )


def _terminal_blocker_details(
    run: CodexRun,
) -> tuple[ContentInitialDraftBlockerCode, list[str]]:
    code, separator, source_text = (run.error or "").partition("|")
    if code in _INITIAL_DRAFT_BLOCKER_CODES:
        return code, source_text.split(",") if separator and source_text else []  # type: ignore[return-value]
    return ("runtime_failed" if run.status == "failed" else "runtime_blocked"), []


def _mark_initial_draft_run_failed(run_id: str, error: Exception) -> None:
    store = local_state_store()
    run = next((item for item in store.list_codex_runs() if item.id == run_id), None)
    if run is None or run.status != "started":
        return
    transition_initial_draft_run_if_status(
        store,
        run,
        status="failed",
        error=f"worker_exception:{type(error).__name__}",
    )


__all__ = ["register_content_initial_draft_route"]
