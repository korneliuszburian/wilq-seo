"""Build one exact planning input for a proposal generation attempt."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_responses import (
    blocked_from_input,
    blocked_response,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse


class PacketBinder(Protocol):
    def __call__(
        self,
        *,
        snapshot: ContentWorkItemWorkflowSnapshotResponse,
        planning_input: ContentPlanningInput,
        request: ContentPlanningProposalRequest,
        require_packet: bool,
    ) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]: ...


SnapshotSelector = Callable[
    [ContentWorkItemWorkflowSnapshotResponse, str],
    ContentWorkItemWorkflowSnapshotResponse,
]


def build_generation_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    *,
    select_service: SnapshotSelector,
    bind_packet: PacketBinder,
    require_research_packet: bool = False,
) -> tuple[
    ContentPlanningInput | None,
    list[ContentPlanningInputBlocker],
    ContentPlanningProposalResponse | None,
]:
    if request.content_kind == "service" and request.service_card_id not in {
        candidate.service_card_id
        for candidate in snapshot.service_profile_context.service_candidates
    }:
        return None, [], blocked_response(
            snapshot.preflight.item.id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=None,
            blockers=[
                ContentPlanningProposalBlocker(
                    code="unknown_service_card",
                    label="Usługa nie należy do tego zadania",
                    reason="Wybrana karta nie wynika z dokładnego dopasowania strony i wiedzy WILQ.",  # noqa: E501
                    next_step="Wybierz jedną z usług pokazanych dla tej strony.",
                )
            ],
        )
    planning_snapshot = (
        select_service(snapshot, request.service_card_id)
        if request.content_kind == "service" and request.service_card_id is not None
        else snapshot
    )
    result = build_content_planning_input(
        planning_snapshot,
        service_card_id=request.service_card_id,
    )
    if result.planning_input is None:
        return None, [], blocked_from_input(
            snapshot.preflight.item.id,
            service_card_id=request.service_card_id,
            blockers=result.blockers,
            content_kind=request.content_kind,
        )
    bound_planning_input, packet_response = bind_packet(
        snapshot=snapshot,
        planning_input=result.planning_input,
        request=request,
        require_packet=require_research_packet,
    )
    if packet_response is not None:
        return None, [], packet_response
    if bound_planning_input is None:
        raise RuntimeError("Research packet binding returned no planning input.")
    return bound_planning_input, result.blockers, None


__all__ = ["PacketBinder", "SnapshotSelector", "build_generation_input"]
