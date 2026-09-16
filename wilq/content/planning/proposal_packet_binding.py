"""Exact research-packet binding for planning generation."""

from __future__ import annotations

from typing import Literal, cast

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    bind_research_packet_to_planning_input,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.source_pack_projection import (
    project_selected_source_pack_facts,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.research_packet import (
    ContentResearchPacket,
    ContentResearchPacketBlocker,
)
from wilq.content.workflow.research_packet_preparation import (
    ResearchPacketPreparationStore,
    current_research_packet_blocker,
)
from wilq.content.workflow.store.store import content_workflow_store


def bind_research_packet(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    require_packet: bool = False,
) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]:
    """Reload and validate the packet before a planner turn can start."""

    store = content_workflow_store()
    if request.research_packet_id is None:
        if require_packet:
            return None, _blocked_response(
                planning_input=planning_input,
                request=request,
                packet=None,
                blocker=ContentResearchPacketBlocker(
                    seam="source_pack_binding",
                    reason="source_pack_binding_missing",
                    evidence_ids=(),
                    next_step_pl=(
                        "Przygotuj i odczytaj server-owned research packet przed "
                        "uruchomieniem planu."
                    ),
                ),
            )
        return planning_input, None
    packet = store.load_content_research_packet(request.research_packet_id)
    blocker = _packet_blocker(
        store=store,
        packet=packet,
        request=request,
        snapshot=snapshot,
        planning_input=planning_input,
    )
    if blocker is not None:
        return None, _blocked_response(
            planning_input=planning_input,
            request=request,
            packet=packet,
            blocker=blocker,
        )
    if packet is None:
        raise RuntimeError("Research packet binding returned no packet without a blocker.")
    try:
        projected_input = project_selected_source_pack_facts(
            planning_input,
            packet.approved_source_fact_ids,
            ekologus_source_facts(),
        )
    except ValueError:
        return None, _blocked_response(
            planning_input=planning_input,
            request=request,
            packet=packet,
            blocker=ContentResearchPacketBlocker(
                seam="source_facts",
                reason="source_fact_not_registered",
                evidence_ids=packet.evidence_ids,
                next_step_pl=(
                    "Odśwież source-fact registry i source-pack względem bieżących faktów."
                ),
            ),
        )
    return bind_research_packet_to_planning_input(projected_input, packet), None


def _packet_blocker(
    *,
    store: ResearchPacketPreparationStore,
    packet: ContentResearchPacket | None,
    request: ContentPlanningProposalRequest,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
) -> ContentResearchPacketBlocker | None:
    if packet is None:
        return ContentResearchPacketBlocker(
            seam="source_pack_binding",
            reason="source_pack_binding_missing",
            evidence_ids=(),
            next_step_pl="Odczytaj bieżący research packet przed uruchomieniem planu.",
        )
    if request.expected_research_packet_digest != packet.packet_digest:
        return ContentResearchPacketBlocker(
            seam="source_pack_binding",
            reason="packet_conflict",
            evidence_ids=packet.evidence_ids,
            next_step_pl="Odśwież exact packet i uruchom plan dla bieżącego digestu.",
        )
    return current_research_packet_blocker(
        store=store,
        packet=packet,
        snapshot=snapshot,
        planning_input=planning_input,
    )


def _blocked_response(
    *,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    packet: ContentResearchPacket | None,
    blocker: ContentResearchPacketBlocker,
) -> ContentPlanningProposalResponse:
    code = cast(
        Literal[
            "research_packet_missing",
            "research_packet_blocked",
            "research_packet_conflict",
        ],
        {
            "source_pack_binding_missing": "research_packet_missing",
            "packet_conflict": "research_packet_conflict",
        }.get(blocker.reason, "research_packet_blocked"),
    )
    proposal_blocker = ContentPlanningProposalBlocker(
        code=code,
        label="Research packet nie jest aktualny",
        reason=blocker.next_step_pl,
        next_step=blocker.next_step_pl,
        source_codes=[blocker.reason, *blocker.evidence_ids],
    )
    packet_id = getattr(packet, "packet_id", request.research_packet_id)
    packet_digest = getattr(packet, "packet_digest", request.expected_research_packet_digest)
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=planning_input.work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
        input_summary=content_planning_input_summary(planning_input),
        blockers=[proposal_blocker],
        safe_next_step=proposal_blocker.next_step,
    )


__all__ = ["bind_research_packet"]
