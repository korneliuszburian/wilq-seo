"""Durable dispatch into the existing initial full-draft pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.full_draft_generation_v3 import full_draft_generation_v3_snapshot
from wilq.content.drafts.full_draft_generation_v3_contracts import (
    FullDraftGenerationV3Binding,
    FullDraftGenerationV3Receipt,
)
from wilq.content.drafts.initial_draft_queue import (
    ContentInitialDraftSnapshotLoader,
    InitialDraftExecutor,
    context_checked_initial_draft_workflow_store,
    queued_initial_draft_response,
    snapshot_initial_draft_context_digest,
)
from wilq.content.drafts.initial_draft_response import initial_draft_packet_fields
from wilq.content.drafts.initial_draft_run import (
    _initial_draft_run_metadata,
    _new_initial_draft_run,
    effective_initial_draft_deadline,
    finish_initial_draft_run,
)
from wilq.content.drafts.initial_draft_runtime_contract import initial_draft_timeout_seconds
from wilq.content.drafts.initial_full_draft import (
    generate_initial_full_draft,
    prepare_initial_draft_plan_for_writer,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.store.store_full_draft_generation_v3 import (
    assert_full_draft_v3_authority,
)
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


def _blocked(
    work_item_id: str, code: str, run: CodexRun | None = None
) -> ContentInitialDraftResponse:
    blocker = ContentInitialDraftBlocker(
        code="stale_initial_draft_context" if run is None else "runtime_blocked",
        label="Przygotowanie tekstu wymaga sprawdzenia",
        reason="Dokładna autoryzacja lub zapisany przebieg nie pozwala na generowanie.",
        next_step="Sprawdź zapisany przebieg i uzgodnij jego wynik przed nową autoryzacją.",
        source_codes=[code] + ([] if run is None or run.error is None else [run.error]),
        owner="WILQ content workflow",
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=None if run is None else run.proposal_id,
        run_id=None if run is None else run.id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _run(run_store: LocalStateStore, run_id: str) -> CodexRun | None:
    return next((item for item in run_store.list_codex_runs() if item.id == run_id), None)


def _run_blocker(
    receipt: FullDraftGenerationV3Receipt,
    run: CodexRun | None,
    workflow_store: ContentWorkflowStore,
) -> ContentInitialDraftResponse | None:
    if run is None:
        return _blocked(receipt.snapshot.work_item_id, "full_draft_v3_run_missing")
    if run.status != "started":
        return _blocked(receipt.snapshot.work_item_id, f"full_draft_v3_run_{run.status}", run)
    if utc_now() >= effective_initial_draft_deadline(run):
        started = workflow_store.load_full_draft_generation_v3_worker_start(
            receipt.snapshot.action_id
        )
        code = "full_draft_v3_reconciliation_required" if started else "full_draft_v3_run_expired"
        return _blocked(receipt.snapshot.work_item_id, code, run)
    return None


def read_full_draft_generation_v3_status(
    work_item_id: str,
    *,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
) -> ContentInitialDraftResponse | None:
    revision = workflow_store.load_draft_revision_state(work_item_id).latest_revision
    if revision is None or revision.generation_authorization is None:
        receipt = workflow_store.latest_full_draft_generation_v3_receipt(work_item_id)
        if receipt is None:
            return None
        claim = workflow_store.load_full_draft_generation_v3_dispatch(receipt.snapshot.action_id)
        if claim is None:
            return None
        run = _run(run_store, claim.run_id)
        blocked = _run_blocker(receipt, run, workflow_store)
        if blocked is not None:
            return blocked
        return queued_initial_draft_response(
            work_item_id, receipt.snapshot.proposal_id, claim.run_id, True
        )
    binding = revision.generation_authorization
    receipt = workflow_store.load_full_draft_generation_v3_receipt(binding.action_id)
    claim = workflow_store.load_full_draft_generation_v3_dispatch(binding.action_id)
    worker = workflow_store.load_full_draft_generation_v3_worker_start(binding.action_id)
    run = _run(run_store, binding.run_id)
    if (
        receipt is None
        or claim != binding
        or run is None
        or run.status != "completed"
        or worker is None
        or worker.binding != binding
        or binding
        != FullDraftGenerationV3Binding.from_receipt(receipt).model_copy(update={"run_id": run.id})
        or receipt.snapshot.work_item_id != work_item_id
        or revision.proposal_metadata is None
        or revision.proposal_metadata.codex_run_id != run.id
        or run.proposal_id != receipt.snapshot.proposal_id
        or run.planning_input_digest != revision.planning_input_digest
        or run.planning_digest != revision.planning_digest
        or run.action_ids != [binding.action_id]
    ):
        return _blocked(work_item_id, "full_draft_v3_readback_mismatch")
    return ContentInitialDraftResponse(
        status="created",
        work_item_id=work_item_id,
        proposal_id=run.proposal_id,
        run_id=run.id,
        revision=revision,
        **initial_draft_packet_fields(revision=revision),
        safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
    )


@dataclass(frozen=True)
class _DispatchContext:
    receipt: FullDraftGenerationV3Receipt
    workflow_store: ContentWorkflowStore
    run_store: LocalStateStore
    snapshot_loader: ContentInitialDraftSnapshotLoader
    client_factory: Callable[[], CodexAppServerClientProtocol]

    def request(
        self, binding: FullDraftGenerationV3Binding | None = None
    ) -> ContentInitialDraftRequest:
        expected = self.receipt.snapshot
        return ContentInitialDraftRequest(
            expected_proposal_id=expected.proposal_id,
            expected_planning_digest=expected.planning_digest,
            expected_planning_input_digest=expected.planning_input_digest,
            requested_by=self.receipt.confirmed_by,
            generation_authorization=binding,
        )

    def current_guard(self) -> None:
        expected = self.receipt.snapshot
        fresh = self.snapshot_loader(expected.work_item_id)
        if (
            fresh.planning_workspace is None
            or not fresh.planning_workspace.section_map_current
            or fresh.revision_workspace.latest_revision is not None
            or full_draft_generation_v3_snapshot(
                fresh.planning_workspace.proposal, store=self.workflow_store
            )
            != expected
        ):
            raise ValueError("full_draft_v3_plan_changed")
        prepared = prepare_initial_draft_plan_for_writer(
            snapshot=fresh,
            request=self.request(),
            workflow_store=self.workflow_store,
        )
        if prepared is not None:
            raise ValueError(prepared.blockers[0].code)

    def guard(self) -> ContentInitialDraftResponse | None:
        try:
            self.current_guard()
            with self.workflow_store._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                assert_full_draft_v3_authority(connection, self.receipt, self.workflow_store.path)
        except ValueError as error:
            return _blocked(self.receipt.snapshot.work_item_id, str(error))
        return None

    def new_run(self, snapshot: ContentWorkItemWorkflowSnapshotResponse) -> CodexRun:
        expected = self.receipt.snapshot
        if snapshot.planning_workspace is None:
            raise ValueError("full_draft_v3_plan_missing")
        return _new_initial_draft_run(
            endpoint=f"/api/content/work-items/{expected.work_item_id}/initial-draft",
            metadata=_initial_draft_run_metadata(),
            evidence_ids=list(expected.evidence_ids),
            source_material_ids=snapshot.planning_workspace.proposal.source_material_ids,
            proposal_id=expected.proposal_id,
            planning_digest=expected.planning_digest,
            planning_input_digest=expected.planning_input_digest,
            context_digest=snapshot_initial_draft_context_digest(
                snapshot, snapshot.planning_workspace.proposal
            ),
            expected_base_revision_id=None,
            timeout_seconds=initial_draft_timeout_seconds(),
        )


class _GuardedClient:
    def __init__(self, context: _DispatchContext, binding: FullDraftGenerationV3Binding) -> None:
        self.context = context
        self.binding = binding

    def run_structured_turn(
        self, turn: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        blocked = _run_blocker(
            self.context.receipt,
            _run(self.context.run_store, self.binding.run_id),
            self.context.workflow_store,
        )
        if blocked is not None or self.context.guard() is not None:
            raise ValueError("stale_initial_draft_context")
        return self.context.client_factory().run_structured_turn(turn)


def _run_once(context: _DispatchContext, binding: FullDraftGenerationV3Binding) -> None:
    run = _run(context.run_store, binding.run_id)
    if run is None:
        return
    try:
        if not context.workflow_store.start_full_draft_generation_v3_worker(
            context.receipt, binding, context.current_guard
        ):
            return
        generate_initial_full_draft(
            snapshot=context.snapshot_loader(context.receipt.snapshot.work_item_id),
            request=context.request(binding),
            client=_GuardedClient(context, binding),
            run_store=context.run_store,
            run_id=binding.run_id,
            workflow_store=context_checked_initial_draft_workflow_store(
                snapshot_loader=context.snapshot_loader,
                work_item_id=context.receipt.snapshot.work_item_id,
                pre_persistence_guard=context.guard,
            ),
        )
    except Exception:
        finish_initial_draft_run(
            context.run_store, run, status="blocked", error="full_draft_v3_reconciliation_required"
        )


def dispatch_full_draft_generation_v3(
    action_id: str,
    *,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    client_factory: Callable[[], CodexAppServerClientProtocol],
    executor: InitialDraftExecutor,
) -> ContentInitialDraftResponse:
    receipt = workflow_store.load_full_draft_generation_v3_receipt(action_id)
    if receipt is None:
        return _blocked("unknown", "full_draft_v3_authorization_missing")
    observed = read_full_draft_generation_v3_status(
        receipt.snapshot.work_item_id,
        workflow_store=workflow_store,
        run_store=run_store,
    )
    claim = workflow_store.load_full_draft_generation_v3_dispatch(action_id)
    if claim is not None:
        if observed is not None and observed.status != "generating":
            return observed
        if workflow_store.load_full_draft_generation_v3_worker_start(action_id) is not None:
            return observed or _blocked(
                receipt.snapshot.work_item_id, "full_draft_v3_reconciliation_required"
            )
    context = _DispatchContext(receipt, workflow_store, run_store, snapshot_loader, client_factory)
    snapshot = snapshot_loader(receipt.snapshot.work_item_id)
    try:
        binding, _new = workflow_store.claim_full_draft_generation_v3(
            receipt,
            lambda: context.new_run(snapshot),
            context.current_guard,
        )
    except ValueError as error:
        return _blocked(receipt.snapshot.work_item_id, str(error))
    terminal = _run_blocker(receipt, _run(run_store, binding.run_id), workflow_store)
    if terminal is not None:
        return terminal
    try:
        executor.submit(_run_once, context, binding)
    except Exception:
        observed = read_full_draft_generation_v3_status(
            receipt.snapshot.work_item_id,
            workflow_store=workflow_store,
            run_store=run_store,
        )
        if observed is not None and observed.status != "generating":
            return observed
        return _blocked(
            receipt.snapshot.work_item_id,
            "full_draft_v3_submission_unconfirmed",
            _run(run_store, binding.run_id),
        )
    return read_full_draft_generation_v3_status(
        receipt.snapshot.work_item_id,
        workflow_store=workflow_store,
        run_store=run_store,
    ) or _blocked(receipt.snapshot.work_item_id, "full_draft_v3_run_missing")
