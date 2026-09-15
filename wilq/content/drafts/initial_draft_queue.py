"""Queue policy and guarded execution for initial full drafts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, Protocol

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
    StdioCodexAppServerClient,
)
from wilq.content.drafts.initial_draft_persistence import InitialDraftPrePersistenceGuardError
from wilq.content.drafts.initial_draft_response import initial_draft_packet_fields
from wilq.content.drafts.initial_draft_run import (
    InitialDraftClaim,
    InitialDraftClaimContext,
    InitialDraftRuntimePolicyError,
    claim_initial_draft_run,
    effective_initial_draft_deadline,
    initial_draft_context_digest_for_proposal,
    initial_draft_proposal_context,
    safe_initial_draft_run_error,
    transition_initial_draft_run_if_status,
)
from wilq.content.drafts.initial_full_draft import generate_initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.documents.codex_revision_commit import (
    current_initial_draft_context_guard,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionWriteResult,
    content_draft_package_digest,
)
from wilq.content.workflow.research_packet import ContentResearchPacket
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import local_state_store

ContentInitialDraftSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
InitialDraftGenerationGuard = Callable[[], ContentInitialDraftResponse | None]


class InitialDraftQueueFullError(RuntimeError):
    pass


class InitialDraftExecutor(Protocol):
    def submit(self, fn: Callable[..., object], /, *args: object, **kwargs: object) -> object: ...


_DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS = 2400.0
_INITIAL_DRAFT_QUEUE_RETRY_SECONDS = 5


def snapshot_initial_draft_context_digest(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
) -> str:
    package = getattr(
        getattr(getattr(snapshot, "draft_package", None), "draft_package_result", None),
        "draft_package",
        None,
    )
    item = getattr(getattr(snapshot, "preflight", None), "item", None)
    return initial_draft_context_digest_for_proposal(
        base_revision_id=getattr(
            getattr(snapshot.revision_workspace, "latest_revision", None),
            "revision_id",
            None,
        ),
        draft_package_id=getattr(package, "id", None),
        draft_package_digest=None if package is None else content_draft_package_digest(package),
        final_canonical_url=getattr(item, "final_canonical_url", None)
        or getattr(item, "intended_final_url", None),
        proposal_context=initial_draft_proposal_context(proposal),
    )


def can_queue_initial_draft(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    client: CodexAppServerClientProtocol | None = None,
) -> bool:
    if client is not None and not isinstance(client, StdioCodexAppServerClient):
        return False
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
    return bool(
        proposal.proposal_id == request.expected_proposal_id
        and proposal.planning_digest == request.expected_planning_digest
        and proposal.planning_input_digest == request.expected_planning_input_digest
    )


def _legacy_existing_page_packet_response(
    work_item_id: str,
    proposal: ContentPlanningProposal,
) -> ContentInitialDraftResponse | None:
    if getattr(proposal, "goal", "refresh_existing") == "new_page":
        return None
    if (
        getattr(proposal, "research_packet_id", None) is not None
        and getattr(proposal, "research_packet_digest", None) is not None
    ):
        return None
    blocker = ContentInitialDraftBlocker(
        code="research_packet_missing",
        label="Brakuje aktualnego research packetu",
        reason="Pełny tekst istniejącej strony wymaga exact current research packetu.",
        next_step="Przygotuj exact current research packet i uruchom tekst ponownie.",
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=proposal.proposal_id,
        **initial_draft_packet_fields(proposal=proposal),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


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

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
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
            != snapshot_initial_draft_context_digest(snapshot, planning.proposal)
        ):
            transition_initial_draft_run_if_status(
                local_state_store(), run, status="blocked", error="stale_initial_draft_context"
            )
            raise TimeoutError("initial draft context changed")
        remaining = (effective_initial_draft_deadline(run) - utc_now()).total_seconds()
        if remaining <= 0:
            raise TimeoutError("initial draft deadline expired")
        # The run owns the deadline.  The injected base client commonly has
        # the app-server's short generic default, which must not truncate a
        # bounded full-draft run before its persisted deadline.
        return StdioCodexAppServerClient(timeout_seconds=remaining).run_structured_turn(request)


class _ContextCheckedWorkflowStore:
    def __init__(
        self,
        base: ContentWorkflowStore,
        snapshot_loader: ContentInitialDraftSnapshotLoader,
        work_item_id: str,
        pre_persistence_guard: InitialDraftGenerationGuard | None = None,
    ) -> None:
        self._base = base
        self._snapshot_loader = snapshot_loader
        self._work_item_id = work_item_id
        self._pre_persistence_guard = pre_persistence_guard

    def append_draft_revision(
        self,
        command: ContentDraftRevisionAppendCommand,
        *,
        completed_codex_run: CodexRun | None = None,
    ) -> ContentDraftRevisionWriteResult:
        if self._pre_persistence_guard is not None:
            guarded = self._pre_persistence_guard()
            if guarded is not None:
                raise InitialDraftPrePersistenceGuardError(guarded)
        with current_initial_draft_context_guard(self._current_context_digest):
            return self._base.append_draft_revision(
                command, completed_codex_run=completed_codex_run
            )

    def load_content_research_packet(self, packet_id: str) -> ContentResearchPacket | None:
        return self._base.load_content_research_packet(packet_id)

    def _load_content_research_packet_preparation_receipt(self, receipt_id: str) -> Any:
        return self._base._load_content_research_packet_preparation_receipt(receipt_id)

    def load_content_source_pack_binding(self, binding_id: str) -> ContentSourcePackBinding | None:
        return self._base.load_content_source_pack_binding(binding_id)

    def list_content_source_pack_bindings(
        self, *, current_work_item_id: str | None = None
    ) -> list[ContentSourcePackBinding]:
        return self._base.list_content_source_pack_bindings(
            current_work_item_id=current_work_item_id
        )

    def load_content_delivery_identity(
        self, binding_id: str
    ) -> ContentDeliveryIdentityBinding | None:
        return self._base.load_content_delivery_identity(binding_id)

    def load_production_classification_for_work_item(self, work_item_id: str) -> Any:
        return self._base.load_production_classification_for_work_item(work_item_id)

    def load_content_source_fact_authority_receipt_for_identity(
        self,
        identity_binding_id: str,
        current_work_item_id: str,
        source_fact_ids: tuple[str, ...],
    ) -> Any:
        return self._base.load_content_source_fact_authority_receipt_for_identity(
            identity_binding_id,
            current_work_item_id,
            source_fact_ids,
        )

    def _current_context_digest(self) -> str:
        snapshot = self._snapshot_loader(self._work_item_id)
        planning = snapshot.planning_workspace
        if planning is None:
            raise ValueError("stale_initial_draft_context")
        return snapshot_initial_draft_context_digest(snapshot, planning.proposal)


def context_checked_initial_draft_workflow_store(
    *,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    work_item_id: str,
    pre_persistence_guard: InitialDraftGenerationGuard | None = None,
) -> _ContextCheckedWorkflowStore:
    """Expose the existing atomic append guard for direct and queued draft paths."""

    return _ContextCheckedWorkflowStore(
        content_workflow_store(),
        snapshot_loader,
        work_item_id,
        pre_persistence_guard=pre_persistence_guard,
    )


def submit_initial_draft_to_queue(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    executor: InitialDraftExecutor,
    stale_response: Callable[[str], ContentInitialDraftResponse] | None = None,
    pre_generation_guard: InitialDraftGenerationGuard | None = None,
    pre_persistence_guard: InitialDraftGenerationGuard | None = None,
) -> ContentInitialDraftResponse:
    prepared = _prepare_initial_draft_queue_claim(
        work_item_id=work_item_id,
        request=request,
        client=client,
        snapshot_loader=snapshot_loader,
        stale_response=stale_response,
        pre_generation_guard=pre_generation_guard,
    )
    if isinstance(prepared, ContentInitialDraftResponse):
        return prepared
    snapshot, proposal, claim = prepared
    if claim.run is None:
        return _stale_initial_draft_context_response(
            work_item_id,
            proposal.proposal_id,
            proposal=proposal,
        )
    run_id = claim.run.id
    if claim.canonical_revision is not None:
        return ContentInitialDraftResponse(
            status="created",
            work_item_id=work_item_id,
            proposal_id=proposal.proposal_id,
            run_id=run_id,
            **initial_draft_packet_fields(proposal=proposal, revision=claim.canonical_revision),
            revision=claim.canonical_revision,
            safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
        )
    if not claim.newly_claimed:
        return queued_initial_draft_response(
            work_item_id, proposal.proposal_id, run_id, True, proposal=proposal
        )
    try:
        executor.submit(
            run_queued_initial_draft,
            work_item_id,
            request,
            client,
            run_id,
            snapshot_loader,
            pre_generation_guard,
            pre_persistence_guard,
        )
    except InitialDraftQueueFullError:
        transition_initial_draft_run_if_status(
            local_state_store(), claim.run, status="blocked", error="initial_draft_queue_full"
        )
        return initial_draft_queue_full_response(
            work_item_id, proposal.proposal_id, run_id, proposal=proposal
        )
    return queued_initial_draft_response(
        work_item_id, proposal.proposal_id, run_id, False, proposal=proposal
    )


def _prepare_initial_draft_queue_claim(
    *,
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    stale_response: Callable[[str], ContentInitialDraftResponse] | None,
    pre_generation_guard: InitialDraftGenerationGuard | None,
) -> (
    tuple[
        ContentWorkItemWorkflowSnapshotResponse,
        ContentPlanningProposal,
        InitialDraftClaim,
    ]
    | ContentInitialDraftResponse
):
    if pre_generation_guard is not None:
        guarded = pre_generation_guard()
        if guarded is not None:
            return guarded
    snapshot = snapshot_loader(work_item_id)
    planning = snapshot.planning_workspace
    if planning is not None:
        packet_response = _legacy_existing_page_packet_response(work_item_id, planning.proposal)
        if packet_response is not None:
            return packet_response
    if not can_queue_initial_draft(snapshot, request, client):
        return _stale_initial_draft_context_response(
            work_item_id,
            request.expected_proposal_id,
            stale_response=stale_response,
            research_packet_id=request.research_packet_id,
            research_packet_digest=request.research_packet_digest,
        )
    if planning is None:
        raise RuntimeError("Initial draft queue requires a planning workspace.")
    proposal = planning.proposal
    proposal_id = proposal.proposal_id
    planning_input_digest = proposal.planning_input_digest
    if proposal_id is None or planning_input_digest is None:
        return initial_draft_not_started_response(work_item_id, proposal)
    try:
        claim = claim_initial_draft_run(
            local_state_store(),
            work_item_id=work_item_id,
            proposal_id=proposal_id,
            planning_digest=proposal.planning_digest,
            planning_input_digest=planning_input_digest,
            evidence_ids=list(getattr(proposal, "evidence_ids", [])),
            source_material_ids=list(getattr(proposal, "source_material_ids", [])),
            timeout_seconds=_DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS,
            context_digest=snapshot_initial_draft_context_digest(snapshot, proposal),
            research_packet_digest=getattr(proposal, "research_packet_digest", None),
            expected_base_revision_id=getattr(
                snapshot.revision_workspace.latest_revision, "revision_id", None
            ),
            current_context=lambda: _current_initial_draft_claim_context(
                snapshot_loader, work_item_id
            ),
        )
    except InitialDraftRuntimePolicyError as error:
        return _runtime_policy_response(
            work_item_id,
            proposal_id,
            proposal=proposal,
            code=error.code,
            reason=error.safe_message,
        )
    return snapshot, proposal, claim


def _stale_initial_draft_context_response(
    work_item_id: str,
    proposal_id: str | None,
    *,
    proposal: ContentPlanningProposal | None = None,
    research_packet_id: str | None = None,
    research_packet_digest: str | None = None,
    stale_response: Callable[[str], ContentInitialDraftResponse] | None = None,
) -> ContentInitialDraftResponse:
    if stale_response is not None:
        response = stale_response(work_item_id)
        return response.model_copy(
            update=initial_draft_packet_fields(
                proposal=proposal,
                revision=response.revision,
                research_packet_id=research_packet_id,
                research_packet_digest=research_packet_digest,
            )
        )
    blocker = ContentInitialDraftBlocker(
        code="stale_initial_draft_context",
        label="Nieaktualny kontekst szkicu",
        reason="Kontekst szkicu zmienił się przed uzyskaniem atomowego claimu.",
        next_step="Odśwież bieżący kontekst przed ponownym uruchomieniem szkicu.",
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=proposal_id,
        **initial_draft_packet_fields(
            proposal=proposal,
            research_packet_id=research_packet_id,
            research_packet_digest=research_packet_digest,
        ),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _runtime_policy_response(
    work_item_id: str,
    proposal_id: str | None,
    *,
    proposal: ContentPlanningProposal | None = None,
    code: Literal["runtime_blocked"],
    reason: str,
) -> ContentInitialDraftResponse:
    blocker = ContentInitialDraftBlocker(
        code=code,
        label="Runtime Codexa jest niedostępny",
        reason=reason,
        next_step="Sprawdź przypiętą politykę embedded Codex runtime i spróbuj ponownie.",
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=proposal_id,
        **initial_draft_packet_fields(proposal=proposal),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _current_initial_draft_claim_context(
    snapshot_loader: ContentInitialDraftSnapshotLoader, work_item_id: str
) -> InitialDraftClaimContext | None:
    snapshot = snapshot_loader(work_item_id)
    planning = snapshot.planning_workspace
    if planning is None:
        return None
    proposal = planning.proposal
    if proposal.proposal_id is None or proposal.planning_input_digest is None:
        return None
    return InitialDraftClaimContext(
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
        context_digest=snapshot_initial_draft_context_digest(snapshot, proposal),
        base_revision_id=getattr(snapshot.revision_workspace.latest_revision, "revision_id", None),
        context_current=snapshot.revision_workspace.context_current,
    )


def run_queued_initial_draft(
    work_item_id: str,
    request: ContentInitialDraftRequest,
    client: StdioCodexAppServerClient,
    run_id: str,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    pre_generation_guard: InitialDraftGenerationGuard | None = None,
    pre_persistence_guard: InitialDraftGenerationGuard | None = None,
) -> None:
    try:
        if pre_generation_guard is not None:
            guarded = pre_generation_guard()
            if guarded is not None:
                snapshot = snapshot_loader(work_item_id)
                _persist_terminal_preflight_run(
                    snapshot=snapshot,
                    request=request,
                    result=guarded,
                    run_id=run_id,
                )
                return
        snapshot = snapshot_loader(work_item_id)
        run = next(
            (item for item in local_state_store().list_codex_runs() if item.id == run_id), None
        )
        planning = snapshot.planning_workspace
        if (
            run is None
            or planning is None
            or (
                run.initial_draft_context_digest
                and run.initial_draft_context_digest
                != snapshot_initial_draft_context_digest(snapshot, planning.proposal)
            )
        ):
            _mark_initial_draft_run_failed(run_id, RuntimeError("stale_initial_draft_context"))
            return
        result = generate_initial_full_draft(
            snapshot=snapshot,
            request=request,
            client=_InitialDraftDeadlineClient(client, run_id, snapshot_loader, work_item_id),
            workflow_store=_ContextCheckedWorkflowStore(
                content_workflow_store(),
                snapshot_loader,
                work_item_id,
                pre_persistence_guard=pre_persistence_guard,
            ),
            run_store=local_state_store(),
            run_id=run_id,
        )
        if result.status in {"blocked", "failed", "conflict"}:
            _persist_terminal_preflight_run(
                snapshot=snapshot, request=request, result=result, run_id=run_id
            )
    except Exception as error:
        _mark_initial_draft_run_failed(run_id, error)


def queued_initial_draft_response(
    work_item_id: str,
    proposal_id: str | None,
    run_id: str,
    already_running: bool,
    *,
    proposal: ContentPlanningProposal | None = None,
) -> ContentInitialDraftResponse:
    blocker = ContentInitialDraftBlocker(
        code="generation_in_progress",
        label="Pełny tekst jest przygotowywany",
        reason=(
            "WILQ pracuje na dokładnym wygenerowanym planie; wynik pojawi się w tym samym workflow."
        ),
        next_step="Odśwież etap tekstu za chwilę. Nie uruchamiaj drugiego generowania.",
    )
    return ContentInitialDraftResponse(
        status="generating",
        work_item_id=work_item_id,
        proposal_id=proposal_id,
        run_id=run_id,
        **initial_draft_packet_fields(proposal=proposal),
        blockers=[blocker],
        safe_next_step="Pełny tekst jest już przygotowywany; nie uruchamiaj drugiego."
        if already_running
        else "Pełny tekst jest przygotowywany; odśwież ten etap za chwilę.",
    )


def initial_draft_queue_full_response(
    work_item_id: str,
    proposal_id: str | None,
    run_id: str,
    *,
    proposal: ContentPlanningProposal | None = None,
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
        **initial_draft_packet_fields(proposal=proposal),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def initial_draft_not_started_response(
    work_item_id: str, proposal: ContentPlanningProposal | None
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
        **initial_draft_packet_fields(proposal=proposal),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _persist_terminal_preflight_run(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    result: ContentInitialDraftResponse,
    run_id: str,
) -> None:
    store = local_state_store()
    status: Literal["failed", "blocked"] = "failed" if result.status == "failed" else "blocked"
    run_error = safe_initial_draft_run_error(result.blockers[0]) if result.blockers else status
    existing = next((run for run in store.list_codex_runs() if run.id == run_id), None)
    if existing is not None:
        transition_initial_draft_run_if_status(store, existing, status=status, error=run_error)
        return
    store.save_codex_run(
        CodexRun(
            id=run_id,
            skill="wilq-content-operator",
            hook="content_initial_full_draft",
            source="wilq_api",
            status=status,
            used_endpoints=[f"/api/content/work-items/{snapshot.preflight.item.id}/initial-draft"],
            evidence_ids=[],
            proposal_id=request.expected_proposal_id,
            planning_input_digest=request.expected_planning_input_digest,
            completed_at=utc_now(),
            error=run_error,
        )
    )


def _mark_initial_draft_run_failed(run_id: str, error: Exception) -> None:
    store = local_state_store()
    run = next((item for item in store.list_codex_runs() if item.id == run_id), None)
    if run is None or run.status != "started":
        return
    transition_initial_draft_run_if_status(
        store, run, status="failed", error=f"worker_exception:{type(error).__name__}"
    )
