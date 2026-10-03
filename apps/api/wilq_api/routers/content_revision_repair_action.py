"""Public exact preview and one-shot dispatch for a reviewed revision repair."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.wilq_api.routers.content_codex_proposal import content_codex_app_server_client
from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_section_proposal import propose_content_section_revision
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
)
from wilq.content.drafts.revision_repair_action import (
    ContentRevisionRepairBinding,
    ContentRevisionRepairReceipt,
    ContentRevisionRepairSnapshot,
    content_revision_repair_action,
    prepare_content_revision_repair_snapshot,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    content_planning_inventory_digest,
)
from wilq.content.quality.independent_review_store import content_independent_review_store
from wilq.content.quality.review_packet_binding import resolve_content_review_inputs
from wilq.content.quality.semantic_review_contracts import ContentSemanticReview
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.documents.codex_revision_commit import (
    ContentDraftRevisionContext,
    current_editor_draft_context_guard,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    content_draft_package_digest,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import ActionObject
from wilq.storage.local_state import LocalStateStore, local_state_store


class ContentRevisionRepairPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_base_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_section_ids: list[str] = Field(default_factory=list, max_length=1)
    selected_cta_ids: list[str] = Field(default_factory=list, max_length=1)
    requested_by: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def require_one_component(self) -> ContentRevisionRepairPreviewRequest:
        if len(self.selected_section_ids) + len(self.selected_cta_ids) != 1:
            raise ValueError("Repair preview requires exactly one stable component ID.")
        if any(not value.strip() for value in [*self.selected_section_ids, *self.selected_cta_ids]):
            raise ValueError("Repair component IDs cannot be blank.")
        if not self.requested_by.strip():
            raise ValueError("Repair preview requires visible requester attribution.")
        return self


class ContentRevisionRepairPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["preview_ready"] = "preview_ready"
    action_id: str
    action: ActionObject
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False


class ContentRevisionRepairBlockedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["blocked"] = "blocked"
    work_item_id: str
    blocker_code: str
    safe_next_step: str
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False


class ContentRevisionRepairDispatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["created", "idempotent", "blocked"]
    action_id: str
    work_item_id: str
    base_revision_id: str
    run_id: str | None = None
    revision: ContentDraftRevision | None = None
    child_review_status: Literal[
        "unreviewed", "approved", "needs_changes", "rejected", "deferred"
    ] = "unreviewed"
    own_review_required: Literal[True] = True
    publish_ready: Literal[False] = False
    blockers: list[str] = Field(default_factory=list)
    safe_next_step: str

    @model_validator(mode="after")
    def require_child_shape(self) -> ContentRevisionRepairDispatchResponse:
        if self.status == "blocked" and self.revision is not None:
            raise ValueError("Blocked repair readback cannot carry a child revision.")
        if self.status in {"created", "idempotent"}:
            if self.revision is None or self.revision.base_revision_id != self.base_revision_id:
                raise ValueError("Repair success must return its exact immutable child.")
            if self.child_review_status != "unreviewed":
                raise ValueError("A repair child must receive its own separate review.")
        return self


SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
ClientFactory = Callable[[], CodexAppServerClientProtocol]


def register_content_revision_repair_action_routes(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader,
    workflow_store_factory: Callable[[], ContentWorkflowStore] | None = None,
    run_store_factory: Callable[[], LocalStateStore] | None = None,
    client_factory: ClientFactory | None = None,
) -> None:
    make_store = workflow_store_factory or content_workflow_store
    make_run_store = run_store_factory or local_state_store
    _register_preview_route(router, snapshot_loader, make_store)
    _register_readback_route(router, make_store)
    _register_dispatch_route(
        router,
        snapshot_loader=snapshot_loader,
        make_store=make_store,
        make_run_store=make_run_store,
        client_factory=client_factory,
    )


def _register_preview_route(
    router: APIRouter,
    snapshot_loader: SnapshotLoader,
    make_store: Callable[[], ContentWorkflowStore],
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/repair-action/preview",
        response_model=ContentRevisionRepairPreviewResponse,
        responses={409: {"model": ContentRevisionRepairBlockedResponse}},
    )
    def preview(
        work_item_id: str,
        base_revision_id: str,
        request: ContentRevisionRepairPreviewRequest,
    ) -> ContentRevisionRepairPreviewResponse | JSONResponse:
        return _preview_repair_action(
            work_item_id, base_revision_id, request, snapshot_loader, make_store()
        )


def _preview_repair_action(
    work_item_id: str,
    base_revision_id: str,
    request: ContentRevisionRepairPreviewRequest,
    snapshot_loader: SnapshotLoader,
    store: ContentWorkflowStore,
) -> ContentRevisionRepairPreviewResponse | JSONResponse:
    try:
        snapshot = prepare_content_revision_repair_snapshot(
            workflow_snapshot=snapshot_loader(work_item_id),
            work_item_id=work_item_id,
            base_revision_id=base_revision_id,
            expected_base_digest=request.expected_base_digest,
            selected_section_ids=request.selected_section_ids,
            selected_cta_ids=request.selected_cta_ids,
            requested_by=request.requested_by,
            workflow_store=store,
            semantic_review_store=content_semantic_review_store(),
            independent_review_store=content_independent_review_store(),
        )
        if store.record_content_revision_repair_snapshot(snapshot) == "conflict":
            raise ValueError("repair_preview_snapshot_conflict")
    except ValueError as error:
        return _blocked(work_item_id, str(error))
    action = content_revision_repair_action(snapshot)
    return ContentRevisionRepairPreviewResponse(action_id=action.id, action=action)


def _register_readback_route(
    router: APIRouter, make_store: Callable[[], ContentWorkflowStore]
) -> None:
    @router.get(
        "/api/content/draft-repair-actions/{action_id}",
        response_model=ContentRevisionRepairDispatchResponse,
    )
    def readback(action_id: str) -> ContentRevisionRepairDispatchResponse:
        store = make_store()
        snapshot = store.load_content_revision_repair_snapshot(action_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="content_revision_repair_not_found")
        return _readback(action_id, snapshot, store)


def _register_dispatch_route(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader,
    make_store: Callable[[], ContentWorkflowStore],
    make_run_store: Callable[[], LocalStateStore],
    client_factory: ClientFactory | None,
) -> None:
    @router.post(
        "/api/content/draft-repair-actions/{action_id}/dispatch",
        response_model=ContentRevisionRepairDispatchResponse,
    )
    def dispatch(action_id: str) -> ContentRevisionRepairDispatchResponse:
        return _dispatch_repair_action(
            action_id,
            snapshot_loader=snapshot_loader,
            store=make_store(),
            run_store=make_run_store(),
            client_factory=client_factory,
        )


def _dispatch_repair_action(
    action_id: str,
    *,
    snapshot_loader: SnapshotLoader,
    store: ContentWorkflowStore,
    run_store: LocalStateStore,
    client_factory: ClientFactory | None,
) -> ContentRevisionRepairDispatchResponse:
    snapshot = store.load_content_revision_repair_snapshot(action_id)
    receipt = store.load_content_revision_repair_receipt(action_id)
    if snapshot is None or receipt is None or receipt.snapshot != snapshot:
        raise HTTPException(status_code=409, detail="content_revision_repair_authority_missing")
    existing = _readback(action_id, snapshot, store)
    if existing.status in {"created", "idempotent"}:
        return existing
    binding = _ensure_dispatch_binding(snapshot, receipt, store)
    if isinstance(binding, ContentRevisionRepairDispatchResponse):
        return binding
    if store.load_content_revision_repair_worker_start(action_id) is not None:
        return _dispatch_blocked(snapshot, "repair_reconciliation_required", run_id=binding.run_id)
    fresh, planning_input, blocker, safe_next_step = _resolve_dispatch_inputs(
        snapshot, snapshot_loader, store
    )
    if blocker is not None:
        return _dispatch_blocked(
            snapshot, blocker, run_id=binding.run_id, safe_next_step=safe_next_step
        )
    if fresh is None or planning_input is None:
        return _dispatch_blocked(snapshot, "missing_planning_input", run_id=binding.run_id)
    if not store.start_content_revision_repair_worker(
        receipt,
        binding,
        lambda: _repair_snapshot_is_current(snapshot, snapshot_loader, store),
    ):
        return _dispatch_blocked(snapshot, "repair_claim_or_context_changed", run_id=binding.run_id)
    semantic = content_semantic_review_store().for_revision(
        snapshot.work_item_id, snapshot.base_revision_id, snapshot.base_digest
    )
    if semantic is None:
        return _dispatch_blocked(snapshot, "repair_semantic_review_changed", run_id=binding.run_id)
    try:
        result = _run_repair_proposal(
            snapshot=snapshot,
            fresh=fresh,
            planning_input=planning_input,
            semantic=semantic,
            snapshot_loader=snapshot_loader,
            store=store,
            run_store=run_store,
            run_id=binding.run_id,
            client_factory=client_factory,
        )
    except (RuntimeError, ValueError, OSError):
        return _dispatch_blocked(snapshot, "repair_execution_failed", run_id=binding.run_id)
    if result.status not in {"created", "idempotent"}:
        return _dispatch_blocked(
            snapshot,
            ",".join(blocker.code for blocker in result.blockers) or "repair_execution_blocked",
            run_id=binding.run_id,
        )
    return _readback(action_id, snapshot, store, expected_run_id=binding.run_id)


def _ensure_dispatch_binding(
    snapshot: ContentRevisionRepairSnapshot,
    receipt: ContentRevisionRepairReceipt,
    store: ContentWorkflowStore,
) -> ContentRevisionRepairBinding | ContentRevisionRepairDispatchResponse:
    binding = store.load_content_revision_repair_binding(snapshot.action_id)
    if binding is not None:
        return binding
    binding = ContentRevisionRepairBinding(
        action_id=snapshot.action_id,
        receipt_digest=receipt.receipt_digest,
        payload_digest=receipt.action_payload_digest,
        context_digest=snapshot.context_digest,
        run_id=f"codex_content_revision_repair_{receipt.receipt_digest}",
    )
    if store.record_content_revision_repair_binding(receipt, binding) == "conflict":
        return _dispatch_blocked(snapshot, "repair_dispatch_conflict")
    return binding


def _resolve_dispatch_inputs(
    snapshot: ContentRevisionRepairSnapshot,
    snapshot_loader: SnapshotLoader,
    store: ContentWorkflowStore,
) -> tuple[
    ContentWorkItemWorkflowSnapshotResponse | None,
    ContentPlanningInput | None,
    str | None,
    str | None,
]:
    if not _repair_snapshot_is_current(snapshot, snapshot_loader, store):
        return None, None, "repair_review_or_source_changed", None
    fresh = snapshot_loader(snapshot.work_item_id)
    base = fresh.revision_workspace.latest_revision
    if base is None or base.revision_id != snapshot.base_revision_id:
        return None, None, "repair_base_changed", None
    resolution = resolve_content_review_inputs(
        snapshot=fresh,
        revision_id=snapshot.base_revision_id,
        expected_revision_digest=snapshot.base_digest,
        workflow_store=store,
        snapshot_loader=snapshot_loader,
    )
    if resolution.blocker is not None:
        return None, None, resolution.blocker.code, resolution.blocker.next_step
    if resolution.inputs is None:
        return (
            None,
            None,
            "missing_planning_input",
            "Odśwież albo wygeneruj aktualny plan przed naprawą.",
        )
    return fresh, resolution.inputs.planning_input, None, None


def _current_repair_editor_context(
    snapshot: ContentRevisionRepairSnapshot,
    snapshot_loader: SnapshotLoader,
    store: ContentWorkflowStore,
) -> ContentDraftRevisionContext | None:
    if not _repair_snapshot_is_current(snapshot, snapshot_loader, store):
        return None
    try:
        current = snapshot_loader(snapshot.work_item_id)
    except (LookupError, OSError, ValueError):
        return None
    resolution = resolve_content_review_inputs(
        snapshot=current,
        revision_id=snapshot.base_revision_id,
        expected_revision_digest=snapshot.base_digest,
        workflow_store=store,
        snapshot_loader=snapshot_loader,
    )
    try:
        current = snapshot_loader(snapshot.work_item_id)
    except (LookupError, OSError, ValueError):
        return None
    if (
        resolution.blocker is not None
        or resolution.inputs is None
        or not _repair_snapshot_is_current(snapshot, snapshot_loader, store)
    ):
        return None
    inputs = resolution.inputs
    draft_package = current.draft_package.draft_package_result.draft_package
    planning_input = inputs.planning_input
    if (
        draft_package is None
        or not planning_input.final_canonical_url
        or planning_input.work_item_id != snapshot.work_item_id
        or inputs.revision.revision_id != snapshot.base_revision_id
        or inputs.revision.content_digest != snapshot.base_digest
        or inputs.proposal.planning_digest != inputs.revision.planning_digest
        or inputs.proposal.planning_input_digest != planning_input.planning_input_digest
    ):
        return None
    return ContentDraftRevisionContext(
        work_item_id=planning_input.work_item_id,
        draft_package_id=draft_package.id,
        draft_package_digest=content_draft_package_digest(draft_package),
        planning_digest=inputs.proposal.planning_digest,
        planning_input_digest=planning_input.planning_input_digest,
        content_kind=planning_input.content_kind,
        service_card_id=planning_input.confirmed_service_card_id,
        inventory_digest=content_planning_inventory_digest(planning_input.inventory),
        final_canonical_url=planning_input.final_canonical_url,
    )


class _GuardedRepairClient:
    def __init__(
        self,
        snapshot: ContentRevisionRepairSnapshot,
        snapshot_loader: SnapshotLoader,
        store: ContentWorkflowStore,
        client_factory: ClientFactory | None,
    ) -> None:
        self.snapshot = snapshot
        self.snapshot_loader = snapshot_loader
        self.store = store
        self.client_factory = client_factory

    def run_structured_turn(
        self, turn: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        if not _repair_snapshot_is_current(self.snapshot, self.snapshot_loader, self.store):
            raise ValueError("content_revision_repair_context_changed")
        client = (self.client_factory or content_codex_app_server_client)()
        return client.run_structured_turn(turn)


def _run_repair_proposal(
    *,
    snapshot: ContentRevisionRepairSnapshot,
    fresh: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    semantic: ContentSemanticReview,
    snapshot_loader: SnapshotLoader,
    store: ContentWorkflowStore,
    run_store: LocalStateStore,
    run_id: str,
    client_factory: ClientFactory | None,
) -> ContentCodexSectionProposalResponse:
    request = ContentCodexSectionProposalRequest(
        expected_base_digest=snapshot.base_digest,
        selected_section_ids=list(snapshot.selected_section_ids),
        selected_cta_ids=list(snapshot.selected_cta_ids),
        requested_by=snapshot.requested_by,
    )
    with current_editor_draft_context_guard(
        lambda: _current_repair_editor_context(snapshot, snapshot_loader, store)
    ):
        return propose_content_section_revision(
            snapshot=fresh,
            base_revision_id=snapshot.base_revision_id,
            request=request,
            client=_GuardedRepairClient(snapshot, snapshot_loader, store, client_factory),
            workflow_store=store,
            run_store=run_store,
            run_id=run_id,
            semantic_review=semantic,
            planning_input=planning_input,
        )


def _repair_snapshot_is_current(
    expected: ContentRevisionRepairSnapshot,
    snapshot_loader: SnapshotLoader,
    store: ContentWorkflowStore,
) -> bool:
    try:
        fresh = prepare_content_revision_repair_snapshot(
            workflow_snapshot=snapshot_loader(expected.work_item_id),
            work_item_id=expected.work_item_id,
            base_revision_id=expected.base_revision_id,
            expected_base_digest=expected.base_digest,
            selected_section_ids=list(expected.selected_section_ids),
            selected_cta_ids=list(expected.selected_cta_ids),
            requested_by=expected.requested_by,
            workflow_store=store,
            semantic_review_store=content_semantic_review_store(),
            independent_review_store=content_independent_review_store(),
        )
    except (ValueError, LookupError, OSError):
        return False
    return fresh == expected


def _readback(
    action_id: str,
    snapshot: ContentRevisionRepairSnapshot,
    store: ContentWorkflowStore,
    *,
    expected_run_id: str | None = None,
) -> ContentRevisionRepairDispatchResponse:
    binding = store.load_content_revision_repair_binding(action_id)
    state = store.load_draft_revision_state(snapshot.work_item_id)
    revision = state.latest_revision
    if (
        binding is None
        or revision is None
        or revision.base_revision_id != snapshot.base_revision_id
        or revision.proposal_metadata is None
        or revision.proposal_metadata.codex_run_id != binding.run_id
        or (expected_run_id is not None and binding.run_id != expected_run_id)
    ):
        if store.load_content_revision_repair_worker_start(action_id) is not None:
            return _dispatch_blocked(
                snapshot,
                "repair_reconciliation_required",
                run_id=None if binding is None else binding.run_id,
            )
        return _dispatch_blocked(
            snapshot, "repair_child_not_found", run_id=None if binding is None else binding.run_id
        )
    revisions = store.list_draft_revisions(snapshot.work_item_id)
    base = next((item for item in revisions if item.revision_id == snapshot.base_revision_id), None)
    metadata = revision.proposal_metadata
    selected_headings = (
        []
        if not snapshot.selected_section_ids or base is None
        else [
            section.heading
            for section in base.sections
            if section.section_id in snapshot.selected_section_ids
        ]
    )
    if (
        base is None
        or revision.planning_digest != base.planning_digest
        or revision.planning_input_digest != base.planning_input_digest
        or revision.research_packet_id != base.research_packet_id
        or revision.research_packet_digest != base.research_packet_digest
        or revision.source_material_ids != base.source_material_ids
        or revision.knowledge_card_ids != base.knowledge_card_ids
        or revision.source_provenance != base.source_provenance
        or (
            snapshot.selected_section_ids
            and metadata.selected_section_headings != selected_headings
        )
        or (
            snapshot.selected_cta_ids
            and metadata.selected_cta_ids != list(snapshot.selected_cta_ids)
        )
        or revision.generation_authorization is not None
    ):
        return _dispatch_blocked(snapshot, "repair_child_lineage_mismatch", run_id=binding.run_id)
    child_review = state.latest_review
    child_review_status = (
        "unreviewed"
        if child_review is None or child_review.revision_id != revision.revision_id
        else child_review.decision
    )
    if child_review_status != "unreviewed":
        return _dispatch_blocked(snapshot, "repair_child_already_reviewed", run_id=binding.run_id)
    return ContentRevisionRepairDispatchResponse(
        status="created",
        action_id=action_id,
        work_item_id=snapshot.work_item_id,
        base_revision_id=snapshot.base_revision_id,
        run_id=binding.run_id,
        revision=revision,
        child_review_status="unreviewed",
        safe_next_step="Wykonaj własne semantic/source i human review nowej child rewizji.",
    )


def _dispatch_blocked(
    snapshot: ContentRevisionRepairSnapshot,
    code: str,
    *,
    run_id: str | None = None,
    safe_next_step: str | None = None,
) -> ContentRevisionRepairDispatchResponse:
    return ContentRevisionRepairDispatchResponse(
        status="blocked",
        action_id=snapshot.action_id,
        work_item_id=snapshot.work_item_id,
        base_revision_id=snapshot.base_revision_id,
        run_id=run_id,
        blockers=[code],
        safe_next_step=safe_next_step
        or "Odczytaj trwały repair run i child; nie uruchamiaj ponownie niejednoznacznego turnu.",
    )


def _blocked(work_item_id: str, code: str) -> JSONResponse:
    result = ContentRevisionRepairBlockedResponse(
        work_item_id=work_item_id,
        blocker_code=code,
        safe_next_step=(
            "Odczytaj current review, exact źródła i bazę, a potem "
            "przygotuj nowy ActionObject."
        ),
    )
    return JSONResponse(status_code=409, content=result.model_dump(mode="json"))


__all__ = ["register_content_revision_repair_action_routes"]
