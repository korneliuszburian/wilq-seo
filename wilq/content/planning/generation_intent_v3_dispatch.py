"""Audited v3 planning-intent dispatch into the durable proposal queue."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal import generate_content_planning_proposal
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ADAPTER,
    PlanningGenerationIntentV3Proposal,
    PlanningGenerationIntentV3Receipt,
    planning_generation_intent_v3_action,
    planning_generation_intent_v3_context_digest,
    project_approved_packet_v3_for_planning,
    resolve_approved_packet_v3_for_planning,
)
from wilq.content.planning.packet_model_projection_v3 import (
    ResearchPacketV3ModelProjection,
    ResearchPacketV3ModelProjectionBlocked,
    content_planning_turn_request_v3,
    project_planning_input_for_packet_v3,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.content.workflow.research_packet_v3_preview import (
    ResearchPacketV3Blocker,
    ResearchPacketV3Preview,
)
from wilq.content.workflow.source_pack_v3 import SourcePackV3Preview
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import AuditEvent
from wilq.storage.local_state import LocalStateStore

SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
ProjectionLoader = Callable[
    [str, str, str], ResearchPacketV3ModelProjection | ResearchPacketV3Blocker
]
SourcePackLoader = Callable[[str], SourcePackV3Preview]
PacketPreviewLoader = Callable[[str], ResearchPacketV3Preview]
SourceFactsLoader = Callable[[], tuple[ContentSourceFact, ...]]


class PlanningGenerationIntentV3DispatchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["planning_generation_intent_v3_dispatch"] = (
        "planning_generation_intent_v3_dispatch"
    )
    status: Literal["accepted", "blocked"]
    action_id: str = Field(min_length=1)
    work_item_id: str | None = None
    intent_receipt_id: str | None = None
    planning_input_digest: str | None = None
    proposal_status: str | None = None
    blocker: ResearchPacketV3Blocker | None = None
    safe_next_step: str = Field(min_length=1)
    generation_performed: Literal[False] = False
    external_write_attempted: Literal[False] = False

    @model_validator(mode="after")
    def require_outcome(self) -> PlanningGenerationIntentV3DispatchOutcome:
        if self.status == "blocked" and self.blocker is None:
            raise ValueError("Blocked v3 dispatch requires a typed blocker.")
        if self.status == "accepted" and (
            self.blocker is not None or self.intent_receipt_id is None
        ):
            raise ValueError("Accepted v3 dispatch requires its exact local intent receipt.")
        return self


@dataclass(frozen=True, slots=True)
class _V3DispatchAuthority:
    proposal: PlanningGenerationIntentV3Proposal
    receipt: PlanningGenerationIntentV3Receipt


def dispatch_applied_planning_intent_v3(
    action_id: str,
    *,
    workflow_store: ContentWorkflowStore,
    audit_store: LocalStateStore,
    proposal_store: ContentPlanningProposalStore,
    snapshot_loader: SnapshotLoader,
    enqueue: Callable[..., ContentPlanningProposalResponse] | None = None,
    projection_loader: ProjectionLoader | None = None,
    source_pack_loader: SourcePackLoader | None = None,
    current_packet_loader: PacketPreviewLoader | None = None,
    source_facts_loader: SourceFactsLoader | None = None,
) -> PlanningGenerationIntentV3DispatchOutcome:
    """Queue one exact current v3 plan only after its local ActionObject audit."""

    authority, blocker = _load_dispatch_authority(
        action_id,
        workflow_store=workflow_store,
        audit_store=audit_store,
    )
    if blocker is not None:
        return _blocked_from(action_id, blocker)
    if authority is None:
        return _blocked(
            action_id,
            "generation_intent_v3_authority_unavailable",
            (),
            "Odczytaj ponownie exact intent v3 i pełny audyt ActionObject.",
        )
    proposal = authority.proposal
    receipt = authority.receipt
    load_projection = projection_loader or (
        lambda work_item_id, packet_id, digest: _load_current_projection(
            work_item_id=work_item_id,
            packet_id=packet_id,
            digest=digest,
            workflow_store=workflow_store,
            snapshot_loader=snapshot_loader,
            source_pack_loader=source_pack_loader,
            current_packet_loader=current_packet_loader,
            source_facts_loader=source_facts_loader,
        )
    )
    current = load_projection(
        proposal.snapshot.work_item_id,
        proposal.snapshot.packet_id,
        proposal.snapshot.packet_digest,
    )
    if isinstance(current, ResearchPacketV3Blocker):
        return _blocked_from(action_id, current)
    if current.intent_context_digest != proposal.snapshot.context_digest:
        return _blocked(
            action_id,
            "generation_intent_v3_projection_changed",
            tuple(current.planning_input.evidence_ids),
            "Przygotuj nowy intent dla aktualnego, zatwierdzonego pakietu v3.",
        )
    request = _request_for_projection(current, receipt.confirmed_by)
    observed_blockers: list[ResearchPacketV3Blocker] = []
    guard = _build_currentness_guard(
        action_id=action_id,
        proposal=proposal,
        receipt=receipt,
        request=request,
        workflow_store=workflow_store,
        audit_store=audit_store,
        projection_loader=load_projection,
        observed_blockers=observed_blockers,
    )
    runner = _build_generation_runner(
        proposal=proposal,
        projection_loader=load_projection,
        observed_blockers=observed_blockers,
    )
    return _enqueue_v3_generation(
        action_id=action_id,
        proposal=proposal,
        receipt=receipt,
        request=request,
        planning_input=current.planning_input,
        snapshot_loader=snapshot_loader,
        proposal_store=proposal_store,
        generation_guard=guard,
        generation_runner=runner,
        enqueue=enqueue,
        observed_blockers=observed_blockers,
    )


def _load_dispatch_authority(
    action_id: str,
    *,
    workflow_store: ContentWorkflowStore,
    audit_store: LocalStateStore,
) -> tuple[_V3DispatchAuthority | None, ResearchPacketV3Blocker | None]:
    try:
        proposal = workflow_store.load_planning_generation_intent_v3_proposal(action_id)
        receipt = workflow_store.load_planning_generation_intent_v3_receipt(action_id)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return None, _blocker(
            "generation_intent_v3_receipt_unavailable",
            (),
            "Odczytaj ponownie exact v3 intent i jego lokalny receipt.",
        )
    if proposal is None:
        return None, _blocker(
            "generation_intent_v3_proposal_missing",
            (),
            "Przygotuj dokładny intent v3 z aktualnego zatwierdzonego pakietu.",
        )
    if receipt is None:
        return None, _blocker(
            "generation_intent_v3_receipt_missing",
            proposal.snapshot.evidence_ids,
            "Zakończ pełny ActionObject lifecycle intentu v3 przed dispatch.",
        )
    receipt_blocker = _validate_exact_receipt(action_id, proposal, receipt)
    if receipt_blocker is not None:
        return None, receipt_blocker
    audit_blocker = _validate_audited_apply(action_id, proposal, receipt, audit_store)
    if audit_blocker is not None:
        return None, audit_blocker
    return _V3DispatchAuthority(proposal=proposal, receipt=receipt), None


def _build_currentness_guard(
    *,
    action_id: str,
    proposal: PlanningGenerationIntentV3Proposal,
    receipt: PlanningGenerationIntentV3Receipt,
    request: ContentPlanningProposalRequest,
    workflow_store: ContentWorkflowStore,
    audit_store: LocalStateStore,
    projection_loader: ProjectionLoader,
    observed_blockers: list[ResearchPacketV3Blocker],
) -> Callable[[], ContentPlanningProposalResponse | None]:
    def blocked(blocker: ResearchPacketV3Blocker) -> ContentPlanningProposalResponse:
        observed_blockers.append(blocker)
        return _proposal_blocked(proposal.snapshot.work_item_id, request, blocker)

    def guard() -> ContentPlanningProposalResponse | None:
        try:
            receipt_current = workflow_store.load_planning_generation_intent_v3_receipt(action_id)
        except (OSError, RuntimeError, ValueError, sqlite3.Error):
            receipt_current = None
        receipt_blocker = _validate_exact_receipt(action_id, proposal, receipt_current)
        if receipt_blocker is not None:
            return blocked(receipt_blocker)
        audit_blocker = _validate_audited_apply(action_id, proposal, receipt, audit_store)
        if audit_blocker is not None:
            return blocked(audit_blocker)
        fresh = projection_loader(
            proposal.snapshot.work_item_id,
            proposal.snapshot.packet_id,
            proposal.snapshot.packet_digest,
        )
        if isinstance(fresh, ResearchPacketV3Blocker):
            return blocked(fresh)
        if (
            fresh.intent_context_digest != proposal.snapshot.context_digest
            or fresh.planning_input.planning_input_digest
            != request.expected_planning_input_digest
        ):
            return blocked(_projection_drift_blocker(fresh))
        return None

    return guard


def _build_generation_runner(
    *,
    proposal: PlanningGenerationIntentV3Proposal,
    projection_loader: ProjectionLoader,
    observed_blockers: list[ResearchPacketV3Blocker],
) -> Callable[..., ContentPlanningProposalResponse]:
    def runner(
        *,
        snapshot: ContentWorkItemWorkflowSnapshotResponse,
        request: ContentPlanningProposalRequest,
        client: CodexAppServerClientProtocol,
        store: ContentPlanningProposalStore,
        run_store: LocalStateStore,
        pre_persistence_guard: Callable[[], ContentPlanningProposalResponse | None] | None,
        refresh_preparation_binding: ContentRefreshPreparationBinding | None,
    ) -> ContentPlanningProposalResponse:
        guarded = None if pre_persistence_guard is None else pre_persistence_guard()
        if guarded is not None:
            return guarded
        fresh = projection_loader(
            proposal.snapshot.work_item_id,
            proposal.snapshot.packet_id,
            proposal.snapshot.packet_digest,
        )
        if isinstance(fresh, ResearchPacketV3Blocker):
            observed_blockers.append(fresh)
            return _proposal_blocked(proposal.snapshot.work_item_id, request, fresh)
        if (
            fresh.intent_context_digest != proposal.snapshot.context_digest
            or fresh.planning_input.planning_input_digest
            != request.expected_planning_input_digest
            or snapshot.preflight.item.id != proposal.snapshot.work_item_id
        ):
            blocker = _projection_drift_blocker(fresh)
            observed_blockers.append(blocker)
            return _proposal_blocked(proposal.snapshot.work_item_id, request, blocker)
        return generate_content_planning_proposal(
            snapshot=snapshot,
            request=request,
            client=client,
            store=store,
            run_store=run_store,
            refresh_preparation_binding=refresh_preparation_binding,
            pre_persistence_guard=pre_persistence_guard,
            prepared_planning_input=fresh.planning_input,
            turn_request_builder=lambda _planning_input, operator_hint: (
                content_planning_turn_request_v3(fresh, operator_hint=operator_hint)
            ),
        )

    return runner


def _enqueue_v3_generation(
    *,
    action_id: str,
    proposal: PlanningGenerationIntentV3Proposal,
    receipt: PlanningGenerationIntentV3Receipt,
    request: ContentPlanningProposalRequest,
    planning_input: ContentPlanningInput,
    snapshot_loader: SnapshotLoader,
    proposal_store: ContentPlanningProposalStore,
    generation_guard: Callable[[], ContentPlanningProposalResponse | None],
    generation_runner: Callable[..., ContentPlanningProposalResponse],
    enqueue: Callable[..., ContentPlanningProposalResponse] | None,
    observed_blockers: list[ResearchPacketV3Blocker],
) -> PlanningGenerationIntentV3DispatchOutcome:
    from wilq.content.planning.planning_generation_queue import enqueue_planning_generation

    try:
        result = (enqueue or enqueue_planning_generation)(
            planning_input=planning_input,
            work_item_id=proposal.snapshot.work_item_id,
            request=request,
            snapshot_loader=snapshot_loader,
            store=proposal_store,
            generation_guard=generation_guard,
            generation_runner=generation_runner,
        )
    except Exception:
        return _blocked(
            proposal.action_id,
            "planning_generation_queue_unavailable",
            proposal.snapshot.evidence_ids,
            "Ponów dispatch tej samej exact intencji v3 po sprawdzeniu kolejki.",
        )
    if result.status not in {"generating", "created", "idempotent", "ready"}:
        if observed_blockers:
            return _blocked_from(action_id, observed_blockers[-1])
        blocker = result.blockers[0] if result.blockers else None
        return _blocked(
            action_id,
            blocker.code if blocker is not None else "planning_generation_not_queued",
            proposal.snapshot.evidence_ids,
            result.safe_next_step or "Odczytaj bieżący status planu dla tej strony.",
        )
    return PlanningGenerationIntentV3DispatchOutcome(
        status="accepted",
        action_id=action_id,
        work_item_id=proposal.snapshot.work_item_id,
        intent_receipt_id=receipt.receipt_id,
        planning_input_digest=request.expected_planning_input_digest,
        proposal_status=result.status,
        safe_next_step="Odczytaj status wygenerowanego planu dla dokładnej strony.",
    )


def _projection_drift_blocker(
    fresh: ResearchPacketV3ModelProjection,
) -> ResearchPacketV3Blocker:
    return _blocker(
        "research_packet_v3_current_drift",
        tuple(fresh.planning_input.evidence_ids),
        "Bieżąca projekcja v3 różni się od intentu zatwierdzonego przez Wilku.",
    )


def _load_current_projection(
    *,
    work_item_id: str,
    packet_id: str,
    digest: str,
    workflow_store: ContentWorkflowStore,
    snapshot_loader: SnapshotLoader,
    source_pack_loader: SourcePackLoader | None,
    current_packet_loader: PacketPreviewLoader | None,
    source_facts_loader: SourceFactsLoader | None,
) -> ResearchPacketV3ModelProjection | ResearchPacketV3Blocker:
    try:
        snapshot = snapshot_loader(work_item_id)
        if snapshot.preflight.item.id != work_item_id:
            return _blocker(
                "research_packet_v3_identity_mismatch",
                (),
                "Odczytaj snapshot dla dokładnego work itemu zatwierdzonego pakietu.",
            )
        service_card_id = snapshot.service_profile_context.service_card_id
        planning_result = build_content_planning_input(
            snapshot, service_card_id=service_card_id
        )
        if planning_result.planning_input is None:
            codes = tuple(blocker.code for blocker in planning_result.blockers)
            return _blocker(
                codes[0] if codes else "planning_input_unavailable",
                tuple(snapshot.preflight.item.evidence_ids),
                "Odtwórz bieżący typed planning input dla strony.",
            )
        load_pack = source_pack_loader or _load_current_source_pack
        pack = load_pack(work_item_id)
        load_packet = current_packet_loader or _load_current_packet
        current_packet = load_packet(work_item_id)
    except Exception:
        return _blocker(
            "research_packet_v3_current_read_unavailable",
            (),
            "Ponów dokładny odczyt aktualnego pakietu v3 i strony.",
        )
    if current_packet.status != "ready":
        return current_packet.blocker or _blocker(
            "research_packet_v3_current_blocked",
            current_packet.verification_evidence_ids,
            "Usuń blokadę bieżącego pakietu v3.",
        )
    view = resolve_approved_packet_v3_for_planning(
        store=workflow_store,
        work_item_id=work_item_id,
        packet_id=packet_id,
        expected_digest=digest,
        current_preview_loader=lambda _work_item_id: current_packet,
    )
    if isinstance(view, ResearchPacketV3Blocker):
        return view
    try:
        projection = project_planning_input_for_packet_v3(
            planning_result.planning_input,
            packet=view.approved_preview,
            source_pack=pack,
            source_facts=(source_facts_loader or (lambda: tuple(ekologus_source_facts())))(),
        )
        return replace(
            projection,
            intent_context_digest=planning_generation_intent_v3_context_digest(
                project_approved_packet_v3_for_planning(view)
            ),
        )
    except ResearchPacketV3ModelProjectionBlocked as error:
        return _blocker(
            error.code,
            view.approved_preview.verification_evidence_ids,
            error.safe_next_step,
        )
    except Exception:
        return _blocker(
            "research_packet_v3_model_projection_unavailable",
            view.approved_preview.verification_evidence_ids,
            "Odtwórz exact model projection z bieżącego pakietu v3.",
        )


def _load_current_source_pack(work_item_id: str) -> SourcePackV3Preview:
    from apps.api.wilq_api.routers.content_source_pack_v3 import (
        read_current_source_pack_v3_preview,
    )

    return read_current_source_pack_v3_preview(work_item_id)


def _load_current_packet(work_item_id: str) -> ResearchPacketV3Preview:
    from apps.api.wilq_api.routers.content_research_packet_v3_preview import (
        read_current_research_packet_v3_preview,
    )

    return read_current_research_packet_v3_preview(work_item_id)


def _request_for_projection(
    projection: ResearchPacketV3ModelProjection,
    requested_by: str,
) -> ContentPlanningProposalRequest:
    planning_input = projection.planning_input
    return ContentPlanningProposalRequest(
        content_kind=planning_input.content_kind,
        service_card_id=planning_input.confirmed_service_card_id,
        expected_planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=planning_input.research_packet_id,
        expected_research_packet_digest=planning_input.research_packet_digest,
        requested_by=requested_by,
    )


def _validate_exact_receipt(
    action_id: str,
    proposal: PlanningGenerationIntentV3Proposal,
    receipt: PlanningGenerationIntentV3Receipt | None,
) -> ResearchPacketV3Blocker | None:
    if receipt is None:
        return _blocker(
            "generation_intent_v3_receipt_missing",
            proposal.snapshot.evidence_ids,
            "Zakończ pełny ActionObject lifecycle intentu v3 przed dispatch.",
        )
    action = planning_generation_intent_v3_action(proposal)
    if (
        receipt.action_id != action_id
        or receipt.snapshot != proposal.snapshot
        or receipt.action_payload_digest != canonical_json_digest(action.payload)
        or receipt.generation_performed
        or receipt.model_enqueued
        or receipt.external_write_attempted
    ):
        return _blocker(
            "generation_intent_v3_receipt_conflict",
            proposal.snapshot.evidence_ids,
            "Odczytaj niezmieniony intent i lokalny receipt v3.",
        )
    return None


def _validate_audited_apply(
    action_id: str,
    proposal: PlanningGenerationIntentV3Proposal,
    receipt: PlanningGenerationIntentV3Receipt,
    audit_store: LocalStateStore,
) -> ResearchPacketV3Blocker | None:
    snapshot = proposal.snapshot
    try:
        events = audit_store.list_audit_events(action_id=action_id)
        mutation_audits = audit_store.list_action_mutation_audits(action_id=action_id)
    except Exception:
        return _blocker(
            "generation_intent_v3_audit_unavailable",
            snapshot.evidence_ids,
            "Ponów odczyt trwałego ActionObject audytu intentu v3.",
        )
    action = planning_generation_intent_v3_action(proposal)
    payload_digest = canonical_json_digest(action.payload)
    applies = sorted(
        (event for event in events if event.event_type.startswith("apply_")),
        key=lambda event: (event.created_at, event.id),
        reverse=True,
    )
    if not applies or applies[0].event_type != "apply_succeeded":
        return _blocker(
            "generation_intent_v3_apply_audit_missing",
            snapshot.evidence_ids,
            "Odczytaj udane local-only apply dokładnego intentu v3.",
        )
    applied = applies[0]
    if (
        applied.details.get("context_digest") != snapshot.context_digest
        or applied.details.get("payload_digest") != payload_digest
    ):
        return _blocker(
            "generation_intent_v3_apply_audit_mismatch",
            snapshot.evidence_ids,
            "Powtórz pełny lifecycle dla dokładnego intentu v3.",
        )
    mutation = next(
        (audit for audit in mutation_audits if audit.audit_event_id == applied.id),
        None,
    )
    if (
        mutation is None
        or mutation.status != "applied"
        or mutation.mutation_adapter != PLANNING_GENERATION_INTENT_V3_ADAPTER
        or mutation.external_write_attempted
    ):
        return _blocker(
            "generation_intent_v3_mutation_audit_missing",
            snapshot.evidence_ids,
            "Odczytaj zgodny audyt lokalnego receipt apply.",
        )
    chain, _ = revision_bound_action_chain(
        events,
        confirmed_by=receipt.confirmed_by,
        binding_from_event=_audit_binding,
        expected_binding=(snapshot.context_digest, payload_digest),
    )
    if chain is None or (
        tuple(event.id for event in chain)
        != (
            receipt.preview_audit_id,
            receipt.review_audit_id,
            receipt.confirmation_audit_id,
            receipt.impact_audit_id,
        )
        or "reviewed_exact_generation_intent_v3"
        not in chain[1].details.get("checked_items", [])
    ):
        return _blocker(
            "generation_intent_v3_action_chain_changed",
            snapshot.evidence_ids,
            "Przeprowadź ponownie pełny review exact intentu v3.",
        )
    return None


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("context_digest")
    payload = event.details.get("payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _proposal_blocked(
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    blocker: ResearchPacketV3Blocker,
) -> ContentPlanningProposalResponse:
    response_blocker = ContentPlanningProposalBlocker(
        code="research_packet_blocked",
        label="Zatwierdzony pakiet v3 wymaga ponownego sprawdzenia",
        reason=blocker.code,
        next_step=blocker.safe_next_step,
        owner=blocker.owner,
        source_codes=[blocker.code],
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        research_packet_id=request.research_packet_id,
        research_packet_digest=request.expected_research_packet_digest,
        blockers=[response_blocker],
        safe_next_step=blocker.safe_next_step,
    )


def _blocker(
    code: str,
    evidence_ids: tuple[str, ...],
    step: str,
    owner: Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"] = (
        "WILQ content workflow"
    ),
) -> ResearchPacketV3Blocker:
    return ResearchPacketV3Blocker(
        code=code,
        owner=owner,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=step,
    )


def _blocked(
    action_id: str,
    code: str,
    evidence_ids: tuple[str, ...],
    step: str,
    owner: Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"] = (
        "WILQ content workflow"
    ),
) -> PlanningGenerationIntentV3DispatchOutcome:
    blocker = _blocker(code, evidence_ids, step, owner)
    return _blocked_from(action_id, blocker)


def _blocked_from(
    action_id: str,
    blocker: ResearchPacketV3Blocker,
) -> PlanningGenerationIntentV3DispatchOutcome:
    return PlanningGenerationIntentV3DispatchOutcome(
        status="blocked",
        action_id=action_id,
        blocker=blocker,
        safe_next_step=blocker.safe_next_step,
    )


__all__ = [
    "PlanningGenerationIntentV3DispatchOutcome",
    "dispatch_applied_planning_intent_v3",
]
