"""Packet preparation and guards used by the planning route."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    bind_research_packet_to_planning_input,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalBlockerCode,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.input_summary import content_planning_input_summary
from wilq.content.planning.source_pack_projection import (
    project_selected_source_pack_facts,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.refresh_preparation import (
    ContentRefreshPreparationAuthority,
    RefreshPreparationRuntimeAuthorized,
)
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.content.workflow.research_packet import ContentResearchPacketBlocker
from wilq.content.workflow.research_packet_preparation import (
    ContentResearchPacketPreparationResult,
    ResearchPacketPreparationStore,
    current_research_packet_blocker,
    prepare_content_research_packet,
)
from wilq.content.workflow.store.store import content_workflow_store


@dataclass(frozen=True, slots=True)
class ContentResearchPacketRouteBinding:
    """Typed route outcome; HTTP status rendering belongs to the API adapter."""

    response: ContentPlanningProposalResponse | None
    planning_input: ContentPlanningInput | None
    request: ContentPlanningProposalRequest


def prepare_and_bind_research_packet(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    planning_input: ContentPlanningInput,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    store: ResearchPacketPreparationStore | None = None,
) -> ContentResearchPacketRouteBinding:
    """Prepare a packet on POST only, then carry its immutable binding onward."""

    workflow_store = store or content_workflow_store()
    has_source_pack = bool(
        request.source_pack_binding_id
        or store_has_source_pack_for_work_item(work_item_id, store=workflow_store)
    )
    if not has_source_pack:
        missing = ContentResearchPacketBlocker(
            seam="source_pack_binding",
            reason="source_pack_binding_missing",
            evidence_ids=(),
            next_step_pl=("Zapisz exact current source-pack binding przed przygotowaniem planu."),
        )
        return ContentResearchPacketRouteBinding(
            response=packet_blocked_response(
                work_item_id=work_item_id,
                request=request,
                planning_input=planning_input,
                result=ContentResearchPacketPreparationResult.blocked_result(missing),
            ),
            planning_input=None,
            request=request,
        )
    result = prepare_content_research_packet(
        store=workflow_store,
        snapshot=snapshot,
        planning_input=planning_input,
        source_pack_binding_id=request.source_pack_binding_id,
        expected_source_pack_binding_digest=request.expected_source_pack_binding_digest,
    )
    if (
        result.packet is not None
        and request.research_packet_id is not None
        and (
            request.research_packet_id != result.packet.packet_id
            or request.expected_research_packet_digest != result.packet.packet_digest
        )
    ):
        result = ContentResearchPacketPreparationResult.blocked_result(
            _packet_conflict_blocker(result),
            packet=result.packet,
        )
    if result.status == "blocked" or result.packet is None:
        return ContentResearchPacketRouteBinding(
            response=packet_blocked_response(
                work_item_id=work_item_id,
                request=request,
                planning_input=planning_input,
                result=result,
            ),
            planning_input=None,
            request=request,
        )
    packet = result.packet
    try:
        projected_input = project_selected_source_pack_facts(
            planning_input,
            packet.approved_source_fact_ids,
            ekologus_source_facts(),
        )
    except ValueError:
        projection_blocker = ContentResearchPacketBlocker(
            seam="source_facts",
            reason="source_fact_not_registered",
            evidence_ids=packet.evidence_ids,
            next_step_pl=("Odśwież source-fact registry i source-pack względem bieżących faktów."),
        )
        return ContentResearchPacketRouteBinding(
            response=packet_blocked_response(
                work_item_id=work_item_id,
                request=request,
                planning_input=planning_input,
                result=ContentResearchPacketPreparationResult.blocked_result(
                    projection_blocker,
                    packet=packet,
                ),
            ),
            planning_input=None,
            request=request,
        )
    bound_input = bind_research_packet_to_planning_input(projected_input, packet)
    bound_request = request.model_copy(
        update={
            "research_packet_id": packet.packet_id,
            "expected_research_packet_digest": packet.packet_digest,
            "expected_planning_input_digest": bound_input.planning_input_digest,
            "source_pack_binding_id": packet.source_pack_binding_id,
            "expected_source_pack_binding_digest": packet.source_pack_binding_digest,
        }
    )
    return ContentResearchPacketRouteBinding(
        response=None,
        planning_input=bound_input,
        request=bound_request,
    )


def store_has_source_pack_for_work_item(
    work_item_id: str,
    *,
    store: ResearchPacketPreparationStore | None = None,
) -> bool:
    return bool(
        (store or content_workflow_store()).list_content_source_pack_bindings(
            current_work_item_id=work_item_id
        )
    )


def packet_blocked_response(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    planning_input: ContentPlanningInput,
    result: ContentResearchPacketPreparationResult,
) -> ContentPlanningProposalResponse:
    blocker = result.blocker
    if blocker is None:
        raise RuntimeError("Blocked research packet preparation requires a blocker.")
    response = packet_blocked_model_response(
        status="blocked",
        work_item_id=work_item_id,
        request=request,
        planning_input=planning_input,
        packet=result.packet,
        code=_proposal_blocker_code(blocker.reason),
        reason=blocker.next_step_pl,
        next_step=blocker.next_step_pl,
        evidence_ids=blocker.evidence_ids,
    )
    return response


def packet_generation_guard(
    *,
    request: ContentPlanningProposalRequest,
    planning_input: ContentPlanningInput,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    store: ResearchPacketPreparationStore | None = None,
) -> ContentPlanningProposalResponse | None:
    if request.research_packet_id is None or request.expected_research_packet_digest is None:
        return None
    workflow_store = store or content_workflow_store()
    packet = workflow_store.load_content_research_packet(request.research_packet_id)
    if packet is None:
        reason = "source_pack_binding_missing"
        next_step = "Odczytaj bieżący research packet przed zakończeniem planowania."
        evidence_ids: tuple[str, ...] = ()
    elif packet.packet_digest != request.expected_research_packet_digest:
        reason = "packet_conflict"
        next_step = "Odśwież exact packet i uruchom plan dla bieżącego digestu."
        evidence_ids = packet.evidence_ids
    else:
        blocker = current_research_packet_blocker(
            store=workflow_store,
            packet=packet,
            snapshot=snapshot,
            planning_input=planning_input,
        )
        if blocker is None:
            return None
        reason = blocker.reason
        next_step = blocker.next_step_pl
        evidence_ids = blocker.evidence_ids
    return packet_blocked_model_response(
        status="blocked",
        work_item_id=planning_input.work_item_id,
        request=request,
        planning_input=planning_input,
        packet=packet,
        code=_proposal_blocker_code(reason),
        reason=reason,
        next_step=next_step,
        evidence_ids=evidence_ids,
    )


def authorized_refresh_generation_context(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    planning_input: ContentPlanningInput,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    authority: ContentRefreshPreparationAuthority,
    initial_resolution: RefreshPreparationRuntimeAuthorized,
) -> tuple[
    ContentRefreshPreparationBinding,
    Callable[[], ContentPlanningProposalResponse | None],
    Callable[[str], ContentWorkItemWorkflowSnapshotResponse],
]:
    """Keep refresh authority on its receipt digest after packet binding."""

    bound_request = request.model_copy(
        update={"expected_planning_input_digest": planning_input.planning_input_digest}
    )
    authority_request = bound_request.model_copy(
        update={
            "expected_planning_input_digest": (
                initial_resolution.planning_input.planning_input_digest
            )
        }
    )
    packet_bound_binding = initial_resolution.binding.model_copy(
        update={"planning_input_digest": planning_input.planning_input_digest}
    )

    def guard() -> ContentPlanningProposalResponse | None:
        resolved = authority.resolve_planning(work_item_id, authority_request)
        refresh_block = authority.planning_block_response(resolved, bound_request)
        if refresh_block is not None:
            return refresh_block
        if not isinstance(resolved, RefreshPreparationRuntimeAuthorized):
            return packet_generation_guard(
                request=bound_request,
                planning_input=planning_input,
                snapshot=snapshot,
            )
        return packet_generation_guard(
            request=bound_request,
            planning_input=planning_input,
            snapshot=resolved.snapshot,
        )

    def current_snapshot(_work_item_id: str) -> ContentWorkItemWorkflowSnapshotResponse:
        current = authority.resolve_planning(work_item_id, authority_request)
        if not isinstance(current, RefreshPreparationRuntimeAuthorized):
            raise RuntimeError("refresh_preparation_authority_changed")
        return current.snapshot

    return packet_bound_binding, guard, current_snapshot


def packet_blocked_model_response(
    *,
    status: Literal["blocked"],
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    planning_input: ContentPlanningInput,
    packet: object | None = None,
    code: ContentPlanningProposalBlockerCode = "research_packet_blocked",
    reason: str = "Research packet nie jest aktualny.",
    next_step: str = "Odśwież exact packet i spróbuj ponownie.",
    evidence_ids: tuple[str, ...] = (),
) -> ContentPlanningProposalResponse:
    packet_id = getattr(packet, "packet_id", None)
    packet_digest = getattr(packet, "packet_digest", None)
    blocker = ContentPlanningProposalBlocker(
        code=code,
        label="Nie przygotowano exact research packetu",
        reason=reason,
        next_step=next_step,
        source_codes=[reason, *evidence_ids],
    )
    return ContentPlanningProposalResponse(
        status=status,
        work_item_id=work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=packet_id or request.research_packet_id,
        research_packet_digest=packet_digest or request.expected_research_packet_digest,
        input_summary=content_planning_input_summary(planning_input),
        blockers=[blocker],
        safe_next_step=next_step,
    )


def legacy_unbound_packet_response(
    response: ContentPlanningProposalResponse,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="research_packet_conflict",
        label="Zachowany plan nie ma server-owned research packetu",
        reason=(
            "Historyczny plan nie jest związany z exact packetem przygotowanym przez WILQ; "
            "nie wolno użyć go jako bieżącego planu."
        ),
        next_step="Uruchom nową próbę planu, aby przygotować packet dla bieżącego kontekstu.",
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=response.work_item_id,
        content_kind=response.content_kind,
        service_card_id=response.service_card_id,
        planning_input_digest=response.planning_input_digest,
        input_summary=response.input_summary,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _packet_conflict_blocker(
    result: ContentResearchPacketPreparationResult,
) -> ContentResearchPacketBlocker:
    packet = result.packet
    return ContentResearchPacketBlocker(
        seam="source_pack_binding",
        reason="packet_conflict",
        evidence_ids=() if packet is None else packet.evidence_ids,
        next_step_pl="Odśwież exact packet i uruchom plan dla bieżącego digestu.",
    )


def _proposal_blocker_code(reason: str) -> ContentPlanningProposalBlockerCode:
    return cast(
        ContentPlanningProposalBlockerCode,
        {
            "source_pack_binding_missing": "research_packet_missing",
            "packet_conflict": "research_packet_conflict",
        }.get(reason, "research_packet_blocked"),
    )


__all__ = [
    "ContentResearchPacketRouteBinding",
    "legacy_unbound_packet_response",
    "packet_blocked_model_response",
    "packet_generation_guard",
    "authorized_refresh_generation_context",
    "prepare_and_bind_research_packet",
    "store_has_source_pack_for_work_item",
]
