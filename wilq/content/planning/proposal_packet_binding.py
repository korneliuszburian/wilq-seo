"""Exact research-packet binding for planning generation."""

from __future__ import annotations

from typing import Literal, cast

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.approved_packet_v2 import (
    CurrentPreviewLoader,
    resolve_approved_packet_v2_for_planning,
)
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
from wilq.content.planning.packet_input_binding import bind_packet_identity_to_planning_input
from wilq.content.planning.source_pack_projection import (
    project_research_packet_v2_facts,
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
from wilq.content.workflow.research_packet_v2_preview import ResearchPacketV2PreviewBlocker
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store


def bind_research_packet(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    require_packet: bool = False,
    workflow_store: ContentWorkflowStore | None = None,
    current_v2_preview_loader: CurrentPreviewLoader | None = None,
) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]:
    """Reload and validate the packet before a planner turn can start."""

    store = workflow_store or content_workflow_store()
    if (
        request.research_packet_id is not None
        and request.research_packet_id.startswith("content_research_packet_v3_")
    ):
        return None, _v3_packet_requires_intent_response(
            planning_input=planning_input,
            request=request,
        )
    if request.research_packet_id and request.research_packet_id.startswith(
        "content_research_packet_v2_"
    ):
        return _bind_approved_v2_packet(
            store=store,
            planning_input=planning_input,
            request=request,
            current_preview_loader=current_v2_preview_loader,
        )
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


def _v3_packet_requires_intent_response(
    *,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="research_packet_action_required",
        label="Pakiet v3 wymaga audytowanego intentu generowania",
        reason=(
            "Pakiet v3 nie może wejść do historycznego source-pack bindingu "
            "ani do surowego model turnu."
        ),
        next_step="Użyj exact v3 planning intent z aktualnym receipt i audytowanym dispatch.",
        owner="WILQ content workflow",
        source_codes=["research_packet_v3_intent_required"],
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=planning_input.work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        research_packet_id=request.research_packet_id,
        research_packet_digest=request.expected_research_packet_digest,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _bind_approved_v2_packet(
    *,
    store: ContentWorkflowStore,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    current_preview_loader: CurrentPreviewLoader | None,
) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]:
    if request.source_pack_binding_id is not None:
        return None, _v2_blocked_response(
            planning_input,
            request,
            ResearchPacketV2PreviewBlocker(
                code="research_packet_v2_legacy_binding_forbidden",
                owner="WILQ content workflow",
                safe_next_step="Usuń historyczny binding v1 z komendy planu v2.",
            ),
        )
    view = resolve_approved_packet_v2_for_planning(
        store=store,
        packet_id=request.research_packet_id or "",
        expected_digest=request.expected_research_packet_digest or "",
        planning_input=planning_input,
        current_preview_loader=current_preview_loader,
    )
    if isinstance(view, ResearchPacketV2PreviewBlocker):
        return None, _v2_blocked_response(planning_input, request, view)
    try:
        projected = project_research_packet_v2_facts(
            planning_input,
            view.preview.selected_facts,
            ekologus_source_facts(),
        )
        return bind_packet_identity_to_planning_input(
            projected,
            work_item_id=view.current_work_item_id,
            packet_id=view.packet_id,
            packet_digest=view.packet_digest,
        ), None
    except ValueError:
        return None, _v2_blocked_response(
            planning_input,
            request,
            ResearchPacketV2PreviewBlocker(
                code="research_packet_v2_fact_projection_blocked",
                owner="WILQ content workflow",
                evidence_ids=view.evidence_ids,
                safe_next_step="Odczytaj i zatwierdź aktualne fakty źródłowe pakietu v2.",
            ),
        )


def _v2_blocked_response(
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    blocker: ResearchPacketV2PreviewBlocker,
) -> ContentPlanningProposalResponse:
    code: Literal[
        "research_packet_missing", "research_packet_conflict", "research_packet_blocked"
    ] = (
        "research_packet_missing"
        if blocker.code == "research_packet_v2_approval_missing"
        else "research_packet_conflict"
        if blocker.code in {
            "research_packet_v2_digest_mismatch",
            "research_packet_v2_planning_input_changed",
            "research_packet_v2_work_item_mismatch",
            "research_packet_v2_current_drift",
        }
        else "research_packet_blocked"
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=planning_input.work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=request.research_packet_id,
        research_packet_digest=request.expected_research_packet_digest,
        input_summary=content_planning_input_summary(planning_input),
        blockers=[
            ContentPlanningProposalBlocker(
                code=code,
                label="Zatwierdzony pakiet v2 nie jest bieżący",
                reason="Pakiet v2 nie ma dokładnego bieżącego powiązania z planem i źródłami.",
                next_step=blocker.safe_next_step,
                owner=blocker.owner,
                source_codes=[blocker.code, *blocker.evidence_ids],
            )
        ],
        safe_next_step=blocker.safe_next_step,
    )


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
