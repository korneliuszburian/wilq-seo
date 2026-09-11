"""Refresh-authorized initial-draft submit and status behavior."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from fastapi.responses import JSONResponse

from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts import initial_draft_queue
from wilq.content.drafts.initial_full_draft import generate_initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.refresh_preparation import (
    ContentRefreshPreparationAuthority,
    RefreshPreparationRuntimeAuthorized,
)
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.storage.local_state import LocalStateStore


class RefreshDraftWorkflowStore(Protocol):
    def load_draft_revision_state(self, work_item_id: str) -> ContentDraftRevisionState: ...


LegacyStatusReader = Callable[
    [str, Callable[[str], ContentWorkItemWorkflowSnapshotResponse]],
    ContentInitialDraftResponse,
]
ConflictResponse = Callable[[ContentInitialDraftResponse], JSONResponse]
ClientFactory = Callable[[], StdioCodexAppServerClient]


def submit_authorized_refresh_initial_draft(
    *,
    work_item_id: str,
    request: ContentInitialDraftRequest,
    authority: ContentRefreshPreparationAuthority,
    initial_resolution: RefreshPreparationRuntimeAuthorized,
    client_factory: ClientFactory,
    executor: initial_draft_queue.InitialDraftExecutor,
    conflict_response: ConflictResponse,
    legacy_status_reader: LegacyStatusReader,
    workflow_store: RefreshDraftWorkflowStore,
    run_store: LocalStateStore,
) -> ContentInitialDraftResponse | JSONResponse:
    current = [initial_resolution]

    def guard() -> ContentInitialDraftResponse | None:
        resolved = authority.resolve_initial_draft(work_item_id, request)
        response = authority.initial_draft_block_response(resolved, request)
        if response is None and isinstance(resolved, RefreshPreparationRuntimeAuthorized):
            current[0] = resolved
        return response

    def current_snapshot(_work_item_id: str) -> ContentWorkItemWorkflowSnapshotResponse:
        return current[0].snapshot

    blocked = guard()
    if blocked is not None:
        return conflict_response(blocked)
    snapshot = current_snapshot(work_item_id)
    existing = existing_authorized_refresh_initial_draft_response(
        work_item_id,
        proposal=(
            None if snapshot.planning_workspace is None else snapshot.planning_workspace.proposal
        ),
        binding=initial_resolution.binding,
        workflow_store=workflow_store,
    )
    if existing is not None:
        return existing
    client = client_factory()
    if initial_draft_queue.can_queue_initial_draft(snapshot, request, client):
        return initial_draft_queue.submit_initial_draft_to_queue(
            work_item_id,
            request,
            client,
            current_snapshot,
            snapshot,
            executor,
            pre_generation_guard=guard,
            pre_persistence_guard=guard,
        )
    result = generate_initial_full_draft(
        snapshot=snapshot,
        request=request,
        client=client,
        workflow_store=initial_draft_queue.context_checked_initial_draft_workflow_store(
            snapshot_loader=current_snapshot,
            work_item_id=work_item_id,
            pre_persistence_guard=guard,
        ),
        run_store=run_store,
    )
    return conflict_response(result) if result.status == "conflict" else result


def read_authorized_refresh_initial_draft_status(
    *,
    work_item_id: str,
    refresh_authority: ContentRefreshPreparationAuthority,
    proposal_store: ContentPlanningProposalStore,
    workflow_store: RefreshDraftWorkflowStore,
    legacy_status_reader: LegacyStatusReader,
) -> ContentInitialDraftResponse | None:
    proposal = _latest_generated_proposal(work_item_id, proposal_store)
    binding = None if proposal is None else proposal.refresh_preparation_binding
    revision = workflow_store.load_draft_revision_state(work_item_id).latest_revision
    if proposal is not None and binding is None:
        return legacy_unbound_refresh_initial_draft_block(
            work_item_id,
            proposal_id=proposal.proposal_id,
        )
    if proposal is None and revision is not None and revision.refresh_preparation_binding is None:
        return legacy_unbound_refresh_initial_draft_block(work_item_id, proposal_id=None)
    if (
        proposal is None
        or proposal.proposal_id is None
        or proposal.planning_input_digest is None
        or binding is None
    ):
        return None
    request = ContentInitialDraftRequest(
        expected_proposal_id=proposal.proposal_id,
        expected_planning_digest=proposal.planning_digest,
        expected_planning_input_digest=proposal.planning_input_digest,
        requested_by="status_read",
        refresh_preparation_authorization_id=binding.authorization_id,
        expected_refresh_preparation_authorization_digest=binding.authorization_digest,
    )
    resolved = refresh_authority.resolve_initial_draft(work_item_id, request)
    blocked = refresh_authority.initial_draft_block_response(resolved, request)
    if blocked is not None:
        return blocked.model_copy(update={"status": "blocked"})
    if not isinstance(resolved, RefreshPreparationRuntimeAuthorized):
        raise RuntimeError("Refresh initial-draft status lost its resolved authority.")
    existing = existing_authorized_refresh_initial_draft_response(
        work_item_id,
        proposal=proposal,
        binding=resolved.binding,
        workflow_store=workflow_store,
    )
    if existing is not None:
        return existing
    if revision is not None and revision.refresh_preparation_binding != resolved.binding:
        return legacy_unbound_refresh_initial_draft_block(
            work_item_id,
            proposal_id=proposal.proposal_id,
        )
    return legacy_status_reader(work_item_id, lambda _work_item_id: resolved.snapshot)


def legacy_unbound_refresh_initial_draft_block(
    work_item_id: str,
    *,
    proposal_id: str | None,
) -> ContentInitialDraftResponse:
    blocker = ContentInitialDraftBlocker(
        code="refresh_preparation_proposal_binding_mismatch",
        label="Zachowany plan lub tekst V1 nie ma receiptu refresh",
        reason=(
            "Klasyfikacja refresh nie może użyć zachowanego planu albo rewizji V1 bez "
            "authorization ID i digestu. Nie ponawiaj generowania z tego artefaktu."
        ),
        next_step=(
            "Wykonaj osobną re-adjudykację/reconciliation zachowanego artefaktu albo "
            "rozpocznij pracę dla nowego inputu refresh."
        ),
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        proposal_id=proposal_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def existing_authorized_refresh_initial_draft_response(
    work_item_id: str,
    *,
    proposal: ContentPlanningProposal | None,
    binding: ContentRefreshPreparationBinding,
    workflow_store: RefreshDraftWorkflowStore,
) -> ContentInitialDraftResponse | None:
    if proposal is None or proposal.proposal_id is None:
        return None
    revision = workflow_store.load_draft_revision_state(work_item_id).latest_revision
    metadata = None if revision is None else revision.proposal_metadata
    if (
        revision is None
        or revision.refresh_preparation_binding != binding
        or revision.planning_digest != proposal.planning_digest
        or revision.planning_input_digest != proposal.planning_input_digest
        or metadata is None
    ):
        return None
    return ContentInitialDraftResponse(
        status="created",
        work_item_id=work_item_id,
        proposal_id=proposal.proposal_id,
        run_id=metadata.codex_run_id,
        revision=revision,
        safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
    )


def _latest_generated_proposal(
    work_item_id: str,
    proposal_store: ContentPlanningProposalStore,
) -> ContentPlanningProposal | None:
    proposal = proposal_store.latest(work_item_id)
    if not (
        proposal is not None
        and proposal.generation_status == "codex_generated"
        and proposal.proposal_id
        and proposal.planning_input_digest
    ):
        return None
    return proposal


__all__ = [
    "existing_authorized_refresh_initial_draft_response",
    "legacy_unbound_refresh_initial_draft_block",
    "read_authorized_refresh_initial_draft_status",
    "submit_authorized_refresh_initial_draft",
]
