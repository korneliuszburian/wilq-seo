"""Dispatch one audited planning intent through the existing durable queue."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_intent import (
    PLANNING_GENERATION_INTENT_ADAPTER,
    PlanningGenerationIntentApplyBlocker,
    PlanningGenerationIntentProposal,
    PlanningGenerationIntentReceipt,
    current_generation_intent_input,
    planning_generation_intent_action,
)
from wilq.content.planning.route_packet_binding import packet_generation_guard
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import AuditEvent
from wilq.storage.local_state import LocalStateStore

SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
QueueDispatcher = Callable[..., ContentPlanningProposalResponse]


class PlanningGenerationDispatchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["planning_generation_dispatch"] = "planning_generation_dispatch"
    status: Literal["accepted", "blocked"]
    action_id: str = Field(min_length=1)
    work_item_id: str | None = None
    intent_receipt_id: str | None = None
    planning_input_digest: str | None = None
    proposal_status: str | None = None
    blocker: PlanningGenerationIntentApplyBlocker | None = None
    safe_next_step: str = Field(min_length=1)
    external_write_attempted: Literal[False] = False

    @model_validator(mode="after")
    def require_outcome(self) -> PlanningGenerationDispatchOutcome:
        if self.status == "blocked" and self.blocker is None:
            raise ValueError("Blocked dispatch requires its typed blocker.")
        if self.status == "accepted" and (
            self.blocker is not None or self.intent_receipt_id is None
        ):
            raise ValueError("Accepted dispatch requires exact intent receipt and no blocker.")
        return self


def dispatch_applied_planning_intent(
    action_id: str,
    *,
    workflow_store: ContentWorkflowStore,
    audit_store: LocalStateStore,
    proposal_store: ContentPlanningProposalStore,
    snapshot_loader: SnapshotLoader,
    enqueue: QueueDispatcher | None = None,
) -> PlanningGenerationDispatchOutcome:
    try:
        proposal = workflow_store.load_planning_generation_intent_proposal(action_id)
        receipt = workflow_store.load_planning_generation_intent_receipt(action_id)
    except Exception:
        return _blocked(action_id, "planning_generation_intent_unavailable", (),
                        "Ponów odczyt dokładnego zamiaru planowania.")
    if proposal is None:
        return _blocked(action_id, "planning_generation_intent_missing", (),
                        "Przygotuj i zatwierdź dokładny zamiar planowania.")
    snapshot = proposal.snapshot
    if receipt is None:
        return _blocked(action_id, "planning_generation_intent_not_applied",
                        snapshot.evidence_ids, "Zakończ review, confirm i apply ActionObject.")
    if (
        receipt.action_id != action_id
        or receipt.snapshot != snapshot
        or receipt.action_payload_digest
        != canonical_json_digest(planning_generation_intent_action(proposal).payload)
        or snapshot.dispatch_after_apply_audit is not True
    ):
        return _blocked(action_id, "planning_generation_intent_receipt_conflict",
                        snapshot.evidence_ids, "Odczytaj ponownie dokładny receipt akcji.")
    audit_blocker = _audited_apply_blocker(action_id, proposal, receipt, audit_store)
    if audit_blocker is not None:
        return _blocked_from(action_id, audit_blocker)
    current = current_generation_intent_input(proposal, workflow_store, snapshot_loader)
    if isinstance(current, PlanningGenerationIntentApplyBlocker):
        return _blocked_from(action_id, current)
    request = ContentPlanningProposalRequest(
        content_kind=snapshot.content_kind,
        service_card_id=snapshot.service_card_id,
        expected_planning_input_digest=snapshot.projected_planning_input_digest,
        research_packet_id=snapshot.packet_id,
        expected_research_packet_digest=snapshot.packet_digest,
        requested_by=receipt.confirmed_by,
    )
    def guard() -> ContentPlanningProposalResponse | None:
        try:
            return packet_generation_guard(
                request=request,
                planning_input=current,
                snapshot=snapshot_loader(snapshot.work_item_id),
                store=workflow_store,
            )
        except Exception:
            return _guard_unavailable_response(request, snapshot.work_item_id)

    from wilq.content.planning.planning_generation_queue import enqueue_planning_generation

    dispatch = enqueue or enqueue_planning_generation
    try:
        result = dispatch(
            planning_input=current,
            work_item_id=snapshot.work_item_id,
            request=request,
            snapshot_loader=snapshot_loader,
            store=proposal_store,
            generation_guard=guard,
        )
    except Exception:
        return _blocked(
            action_id,
            "planning_generation_queue_unavailable",
            snapshot.evidence_ids,
            "Ponów dispatch tej samej intencji po sprawdzeniu kolejki.",
        )
    if result.status not in {"generating", "created", "idempotent", "ready"}:
        first = result.blockers[0] if result.blockers else None
        return _blocked(
            action_id,
            first.code if first is not None else "planning_generation_not_queued",
            snapshot.evidence_ids,
            result.safe_next_step or "Odczytaj bieżący status planowania.",
        )
    return PlanningGenerationDispatchOutcome(
        status="accepted",
        action_id=action_id,
        work_item_id=snapshot.work_item_id,
        intent_receipt_id=receipt.receipt_id,
        planning_input_digest=current.planning_input_digest,
        proposal_status=result.status,
        safe_next_step="Odczytaj status planu dla dokładnej strony i pakietu.",
    )


def _audited_apply_blocker(
    action_id: str,
    proposal: PlanningGenerationIntentProposal,
    receipt: PlanningGenerationIntentReceipt,
    audit_store: LocalStateStore,
) -> PlanningGenerationIntentApplyBlocker | None:
    snapshot = proposal.snapshot
    try:
        events = audit_store.list_audit_events(action_id=action_id)
        mutation_audits = audit_store.list_action_mutation_audits(action_id=action_id)
    except Exception:
        return _blocker("planning_apply_audit_unavailable", snapshot.evidence_ids,
                        "Ponów odczyt trwałego audytu apply.")
    apply_events = sorted(
        (event for event in events if event.event_type.startswith("apply_")),
        key=lambda event: (event.created_at, event.id), reverse=True,
    )
    if not apply_events or apply_events[0].event_type != "apply_succeeded":
        return _blocker("planning_apply_audit_missing", snapshot.evidence_ids,
                        "Zakończ udane apply ActionObject i odczytaj jego audyt.")
    applied = apply_events[0]
    payload_digest = canonical_json_digest(planning_generation_intent_action(proposal).payload)
    if applied.details.get("context_digest") != snapshot.context_digest or (
        applied.details.get("payload_digest") != payload_digest
    ):
        return _blocker("planning_apply_audit_binding_mismatch", snapshot.evidence_ids,
                        "Ponów pełny lifecycle dla dokładnej intencji.")
    mutation = next(
        (item for item in mutation_audits if item.audit_event_id == applied.id), None
    )
    if (
        mutation is None or mutation.status != "applied"
        or mutation.mutation_adapter != PLANNING_GENERATION_INTENT_ADAPTER
        or mutation.external_write_attempted
    ):
        return _blocker("planning_mutation_audit_missing", snapshot.evidence_ids,
                        "Odczytaj zgodny audyt lokalnego apply.")
    chain, _ = revision_bound_action_chain(
        events,
        confirmed_by=receipt.confirmed_by,
        binding_from_event=_audit_binding,
        expected_binding=(snapshot.context_digest, payload_digest),
    )
    if chain is None or (
        chain[0].id != receipt.preview_audit_id
        or chain[1].id != receipt.review_audit_id
        or chain[2].id != receipt.confirmation_audit_id
        or chain[3].id != receipt.impact_audit_id
        or "reviewed_exact_generation_intent" not in chain[1].details.get("checked_items", [])
    ):
        return _blocker("planning_action_chain_changed", snapshot.evidence_ids,
                        "Przeprowadź ponownie pełny review dokładnej intencji.")
    return None


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("context_digest")
    payload = event.details.get("payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _guard_unavailable_response(
    request: ContentPlanningProposalRequest, work_item_id: str
) -> ContentPlanningProposalResponse:
    from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalBlocker

    blocker = ContentPlanningProposalBlocker(
        code="research_packet_blocked",
        label="Nie można odczytać bieżącego pakietu v2",
        reason="Bieżący snapshot albo pakiet v2 jest niedostępny.",
        next_step="Ponów dispatch po odświeżeniu bieżących źródeł.",
        owner="WILQ content workflow",
    )
    return ContentPlanningProposalResponse(
        status="blocked", work_item_id=work_item_id,
        content_kind=request.content_kind, service_card_id=request.service_card_id,
        research_packet_id=request.research_packet_id,
        research_packet_digest=request.expected_research_packet_digest,
        blockers=[blocker], safe_next_step=blocker.next_step,
    )


def _blocker(
    code: str, evidence_ids: tuple[str, ...], step: str
) -> PlanningGenerationIntentApplyBlocker:
    return PlanningGenerationIntentApplyBlocker(
        code=code, evidence_ids=tuple(sorted(set(evidence_ids))), safe_next_step=step,
    )


def _blocked_from(
    action_id: str, blocker: PlanningGenerationIntentApplyBlocker
) -> PlanningGenerationDispatchOutcome:
    return PlanningGenerationDispatchOutcome(
        status="blocked", action_id=action_id, blocker=blocker,
        safe_next_step=blocker.safe_next_step,
    )


def _blocked(
    action_id: str, code: str, evidence_ids: tuple[str, ...], step: str
) -> PlanningGenerationDispatchOutcome:
    return _blocked_from(action_id, _blocker(code, evidence_ids, step))


__all__ = ["PlanningGenerationDispatchOutcome", "dispatch_applied_planning_intent"]
