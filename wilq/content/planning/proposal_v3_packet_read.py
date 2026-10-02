"""Exact current v3 packet verification for the planning status read path.

The approved v3 research packet lives in the append-only v3 approval receipt and
reviewed preview records, not in the legacy workflow packet store.  Without this
seam the planning status read cannot resolve a v3 packet id and reports
``research_packet_conflict`` for a plan that is exact and current.

This verification deliberately stays read-only and connector-free: it checks the
immutable approved record, the unchanged unbound planning context, the unchanged
official-fact registry, and the exact plan-to-packet linkage.  Re-projecting the
packet here would call the snapshot pipeline that already embeds this read.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.frozen_planning_input import validate_v3_frozen_input_integrity
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.planning.packet_input_binding import (
    V3_PACKET_ID_PREFIX,
    is_v3_research_packet_id,
)
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Preview
from wilq.content.workflow.research_packet_v3_receipt import (
    ResearchPacketV3ApprovalReceipt,
    ResearchPacketV3PreviewRecord,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store

# The exact record is gone or does not match the plan; that is a conflict, not a
# freshness finding.  Every other v3 blocker keeps its own typed reason.
_MISSING_RECORD_CODES = frozenset(
    {
        "research_packet_v3_approval_missing",
        "research_packet_v3_digest_mismatch",
        "research_packet_v3_generation_linkage_missing",
        "research_packet_v3_receipt_unavailable",
        "research_packet_v3_snapshot_missing",
        "research_packet_v3_snapshot_unavailable",
    }
)

SourceFactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
GenerationLinkageReader = Callable[[ContentPlanningProposal], str | None]


@dataclass(frozen=True, slots=True)
class V3PlanningPacketContext:
    """Retained exact input and receipt, with separately observed write authority."""

    proposal: ContentPlanningProposal
    planning_input: ContentPlanningInput
    packet: ResearchPacketV3Preview
    receipt: ResearchPacketV3ApprovalReceipt
    subject: ContentPlanningSubject
    current_authority: bool

    def model_binding(self) -> dict[str, object]:
        return {
            "packet_id": self.receipt.packet_id,
            "packet_digest": self.receipt.packet_digest,
            "receipt_digest": self.receipt.receipt_digest,
            "subject_key": self.subject.subject_key,
        }


@dataclass(frozen=True, slots=True)
class V3PacketPlanningRead:
    """Exact v3 packet verification result for the planning status read."""

    approved_input_digest: str | None = None
    generation_input_digest: str | None = None
    blocker_code: str | None = None
    blocker_next_step: str = ""
    blocker_evidence_ids: tuple[str, ...] = ()
    blocker_owner: str = "WILQ content workflow"
    context: V3PlanningPacketContext | None = None

    @property
    def exact(self) -> bool:
        return self.blocker_code is None and self.generation_input_digest is not None

    @property
    def missing(self) -> bool:
        return self.blocker_code in _MISSING_RECORD_CODES


def verify_current_v3_packet_for_planning_input(
    *,
    proposal: ContentPlanningProposal,
    planning_input: ContentPlanningInput,
    generation_linkage_reader: GenerationLinkageReader,
    store: ContentWorkflowStore | None = None,
    source_facts_loader: SourceFactsLoader | None = None,
) -> V3PacketPlanningRead:
    """Verify the exact approved v3 packet against the current read-only context."""

    packet_id = proposal.research_packet_id
    packet_digest = proposal.research_packet_digest
    if packet_id is None or packet_digest is None:
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_approval_missing",
            blocker_next_step="Wybierz plan z exact receipt i pakietem v3.",
        )
    try:
        packet_store = store or content_workflow_store()
    except Exception:
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_receipt_unavailable",
            blocker_next_step="Odczytaj ponownie lokalny store pakietów v3.",
        )
    record, _receipt, blocker = _approved_preview_record(
        packet_store,
        packet_id=packet_id,
        packet_digest=packet_digest,
    )
    if blocker is not None:
        return blocker
    if record is None:
        return _context_blocked(
            "research_packet_v3_receipt_unavailable", "Odczytaj ponownie lokalny store pakietów v3."
        )
    snapshot = record.snapshot
    currentness_blocker = _currentness_blocker(
        snapshot=snapshot,
        work_item_id=planning_input.work_item_id,
        planning_input=planning_input,
        source_facts_loader=source_facts_loader,
    )
    if currentness_blocker is not None:
        return currentness_blocker
    try:
        generation_input_digest = generation_linkage_reader(proposal)
    except ValueError:
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_generation_linkage_invalid",
            blocker_next_step=(
                "Sprawdź zgodność exact planu, zadania i ukończonego przebiegu generowania."
            ),
            blocker_evidence_ids=snapshot.verification_evidence_ids,
        )
    except Exception:
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_generation_linkage_unavailable",
            blocker_next_step=("Odczytaj ponownie lokalny zapis generowania dla tego pakietu v3."),
            blocker_evidence_ids=snapshot.verification_evidence_ids,
        )
    if generation_input_digest is None:
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_generation_linkage_missing",
            blocker_next_step=(
                "Wygeneruj plan z tego dokładnego pakietu v3, zanim pokażesz go jako aktualny."
            ),
            blocker_evidence_ids=snapshot.verification_evidence_ids,
        )
    return V3PacketPlanningRead(
        approved_input_digest=snapshot.planning_input_digest,
        generation_input_digest=generation_input_digest,
    )


def _approved_preview_record(
    packet_store: ContentWorkflowStore,
    *,
    packet_id: str,
    packet_digest: str,
) -> tuple[
    ResearchPacketV3PreviewRecord | None,
    ResearchPacketV3ApprovalReceipt | None,
    V3PacketPlanningRead | None,
]:
    try:
        receipt = packet_store.load_research_packet_v3_approval_receipt(packet_id)
    except Exception:
        return (
            None,
            None,
            V3PacketPlanningRead(
                blocker_code="research_packet_v3_receipt_unavailable",
                blocker_next_step="Odczytaj ponownie receipt pakietu v3.",
            ),
        )
    if receipt is None:
        return (
            None,
            None,
            V3PacketPlanningRead(
                blocker_code="research_packet_v3_approval_missing",
                blocker_next_step=("Zatwierdź dokładny pakiet v3 przez ActionObject przed planem."),
            ),
        )
    if receipt.packet_id != packet_id or receipt.packet_digest != packet_digest:
        return (
            None,
            None,
            V3PacketPlanningRead(
                blocker_code="research_packet_v3_digest_mismatch",
                blocker_next_step="Wybierz receipt zgodny z dokładnym ID i digestem pakietu v3.",
                blocker_evidence_ids=receipt.verification_evidence_ids,
            ),
        )
    try:
        record = packet_store.load_research_packet_v3_preview(packet_digest)
    except Exception:
        return (
            None,
            None,
            V3PacketPlanningRead(
                blocker_code="research_packet_v3_snapshot_unavailable",
                blocker_next_step="Odczytaj ponownie dokładny zapisany podgląd pakietu v3.",
                blocker_evidence_ids=receipt.verification_evidence_ids,
            ),
        )
    if record is None:
        return (
            None,
            None,
            V3PacketPlanningRead(
                blocker_code="research_packet_v3_snapshot_missing",
                blocker_next_step="Odtwórz dokładny zapisany podgląd zatwierdzonego pakietu v3.",
                blocker_evidence_ids=receipt.verification_evidence_ids,
            ),
        )
    if record.preview_hash != packet_digest or record.snapshot.preview_hash != packet_digest:
        return (
            None,
            None,
            V3PacketPlanningRead(
                blocker_code="research_packet_v3_digest_mismatch",
                blocker_next_step="Odczytaj podgląd zgodny z dokładnym receipt pakietu v3.",
            ),
        )
    return record, receipt, None


def resolve_v3_planning_packet_context(
    *,
    proposal: ContentPlanningProposal,
    current_input: ContentPlanningInput | None = None,
    proposal_store: ContentPlanningProposalStore | None = None,
    workflow_store: ContentWorkflowStore | None = None,
    require_current_authority: bool = True,
) -> V3PacketPlanningRead:
    """One exact context for draft/review; a history read never grants authority."""

    packet_id, packet_digest = proposal.research_packet_id, proposal.research_packet_digest
    if packet_id is None or packet_digest is None or not is_v3_research_packet_id(packet_id):
        return _context_blocked(
            "research_packet_v3_approval_missing", "Wybierz exact plan z pakietem v3."
        )
    try:
        packet_store = workflow_store or content_workflow_store()
        plan_store = proposal_store or content_planning_proposal_store()
    except Exception:
        return _context_blocked(
            "research_packet_v3_receipt_unavailable", "Odczytaj ponownie lokalny store."
        )
    record, receipt, blocker = _approved_preview_record(
        packet_store,
        packet_id=packet_id,
        packet_digest=packet_digest,
    )
    if blocker is not None:
        return blocker
    if record is None or receipt is None:
        return _context_blocked(
            "research_packet_v3_receipt_unavailable", "Odczytaj ponownie lokalny store."
        )
    retained = _retained_v3_context(proposal, record, receipt, current_input, plan_store)
    if isinstance(retained, V3PacketPlanningRead):
        return retained
    if require_current_authority:
        blocker = _current_context_blocker(retained, current_input, packet_store)
        if blocker is not None:
            return blocker
        retained = replace(retained, current_authority=True)
    return V3PacketPlanningRead(
        approved_input_digest=retained.packet.planning_input_digest,
        generation_input_digest=retained.planning_input.planning_input_digest,
        context=retained,
    )


def _context_blocked(code: str, next_step: str) -> V3PacketPlanningRead:
    return V3PacketPlanningRead(blocker_code=code, blocker_next_step=next_step)


def _retained_v3_context(
    proposal: ContentPlanningProposal,
    record: ResearchPacketV3PreviewRecord,
    receipt: ResearchPacketV3ApprovalReceipt,
    current_input: ContentPlanningInput | None,
    plan_store: ContentPlanningProposalStore,
) -> V3PlanningPacketContext | V3PacketPlanningRead:
    packet = record.snapshot
    subject = ContentPlanningSubject(
        content_kind=proposal.content_kind,
        service_card_id=proposal.service_card_id,
    )
    if (
        record.work_item_id != proposal.work_item_id
        or packet.work_item_id != proposal.work_item_id
        or (packet.content_kind is not None and packet.content_kind != subject.content_kind)
        or packet.service_card_id != subject.service_card_id
        or (
            current_input is not None
            and (
                current_input.work_item_id != proposal.work_item_id
                or current_input.content_kind != subject.content_kind
                or current_input.confirmed_service_card_id != subject.service_card_id
            )
        )
    ):
        return _context_blocked(
            "research_packet_v3_subject_mismatch", "Odczytaj exact temat planu i pakietu."
        )
    try:
        frozen = plan_store.frozen_planning_input(
            proposal.work_item_id,
            proposal.planning_input_digest or "",
        )
    except Exception:
        frozen = None
    if frozen is None:
        return _context_blocked(
            "research_packet_v3_frozen_input_unavailable", "Odczytaj zapisane wejście planu."
        )
    try:
        validate_v3_frozen_input_integrity(proposal, frozen)
    except ValueError:
        return _context_blocked(
            "research_packet_v3_frozen_input_identity_mismatch",
            "Zapisane wejście nie pasuje do dokładnego planu v3.",
        )
    if packet.page_url is not None and packet.page_url != frozen.final_canonical_url:
        return _context_blocked(
            "research_packet_v3_identity_mismatch", "Odczytaj plan dla dokładnej strony."
        )
    try:
        linkage = plan_store.v3_plan_generation_linkage_exact(proposal)
    except ValueError:
        return _context_blocked(
            "research_packet_v3_generation_linkage_invalid", "Odczytaj exact plan."
        )
    except Exception:
        return _context_blocked(
            "research_packet_v3_generation_linkage_unavailable", "Odczytaj exact plan."
        )
    if linkage != frozen.planning_input_digest:
        return _context_blocked("research_packet_v3_plan_linkage_mismatch", "Odczytaj exact plan.")
    return V3PlanningPacketContext(
        proposal=proposal,
        planning_input=frozen,
        packet=packet,
        receipt=receipt,
        subject=subject,
        current_authority=False,
    )


def _current_context_blocker(
    context: V3PlanningPacketContext,
    current_input: ContentPlanningInput | None,
    packet_store: ContentWorkflowStore,
) -> V3PacketPlanningRead | None:
    from wilq.content.planning.generation_intent_v3 import resolve_approved_packet_v3_for_planning
    from wilq.content.planning.packet_model_projection_v3 import (
        ResearchPacketV3ModelProjectionBlocked,
        validate_frozen_input_for_packet_v3,
    )
    from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Blocker

    if current_input is not None:
        blocker = _currentness_blocker(
            snapshot=context.packet,
            work_item_id=current_input.work_item_id,
            planning_input=current_input,
            source_facts_loader=None,
        )
        if blocker is not None:
            return blocker
    try:
        facts = _current_source_facts()
    except Exception:
        return _context_blocked(
            "research_packet_v3_registry_unavailable", "Odczytaj rejestr official facts."
        )
    try:
        validate_frozen_input_for_packet_v3(
            context.planning_input,
            packet=context.packet,
            source_facts=facts,
        )
    except ResearchPacketV3ModelProjectionBlocked as error:
        return _context_blocked(error.code, error.safe_next_step)
    current = resolve_approved_packet_v3_for_planning(
        store=packet_store,
        work_item_id=context.proposal.work_item_id,
        packet_id=context.receipt.packet_id,
        expected_digest=context.receipt.packet_digest,
    )
    if isinstance(current, ResearchPacketV3Blocker):
        return V3PacketPlanningRead(
            blocker_code=current.code,
            blocker_next_step=current.safe_next_step,
            blocker_evidence_ids=current.evidence_ids,
            blocker_owner=current.owner,
        )
    if current.receipt != context.receipt or current.approved_preview != context.packet:
        return _context_blocked(
            "research_packet_v3_digest_mismatch", "Odśwież exact receipt pakietu."
        )
    return None


def _currentness_blocker(
    *,
    snapshot: ResearchPacketV3Preview,
    work_item_id: str,
    planning_input: ContentPlanningInput,
    source_facts_loader: SourceFactsLoader | None,
) -> V3PacketPlanningRead | None:
    if snapshot.work_item_id != work_item_id:
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_identity_mismatch",
            blocker_next_step=("Odczytaj plan i pakiet dla dokładnego bieżącego work itemu."),
            blocker_evidence_ids=snapshot.verification_evidence_ids,
        )
    approved_input_digest = snapshot.planning_input_digest
    if (
        approved_input_digest is not None
        and planning_input.planning_input_digest != approved_input_digest
    ):
        return V3PacketPlanningRead(
            blocker_code="research_packet_v3_input_drift",
            blocker_next_step=("Odśwież kontekst strony i zatwierdź nowy pakiet v3 przed planem."),
            blocker_evidence_ids=snapshot.verification_evidence_ids,
        )
    registry_drift = _registry_drift_code(snapshot.selected_facts, source_facts_loader)
    if registry_drift is not None:
        return V3PacketPlanningRead(
            blocker_code=registry_drift,
            blocker_next_step=("Zatwierdź official facts ponownie i przygotuj nowy pakiet v3."),
            blocker_evidence_ids=snapshot.verification_evidence_ids,
        )
    return None


def _registry_drift_code(
    selected_facts: tuple[object, ...],
    source_facts_loader: SourceFactsLoader | None,
) -> str | None:
    if not selected_facts:
        return "research_packet_v3_selected_facts_invalid"
    try:
        registry = {
            fact.source_id: fact for fact in (source_facts_loader or _current_source_facts)()
        }
    except Exception:
        return "research_packet_v3_registry_unavailable"
    for selected in selected_facts:
        fact = registry.get(getattr(selected, "source_fact_id", ""))
        if fact is None:
            return "research_packet_v3_registry_drift"
        if canonical_json_digest(fact.model_dump(mode="json")) != getattr(
            selected, "fact_digest", None
        ):
            return "research_packet_v3_registry_drift"
    return None


def _current_source_facts() -> tuple[ContentSourceFact, ...]:
    from wilq.content.knowledge import source_facts

    # Late lookup keeps one registry source for the read and its callers.
    return tuple(source_facts.ekologus_source_facts())


__all__ = [
    "V3_PACKET_ID_PREFIX",
    "V3PacketPlanningRead",
    "V3PlanningPacketContext",
    "is_v3_research_packet_id",
    "verify_current_v3_packet_for_planning_input",
    "resolve_v3_planning_packet_context",
]
