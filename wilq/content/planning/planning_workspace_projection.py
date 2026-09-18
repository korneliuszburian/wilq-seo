"""Projection of exact planning review decisions onto a ready proposal."""

from __future__ import annotations

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.workflow.decisions.planning import (
    ContentPlanningDecision,
    build_content_planning_workspace,
)


def with_current_planning_workspace(
    response: ContentPlanningProposalResponse,
    decisions: list[ContentPlanningDecision],
) -> ContentPlanningProposalResponse:
    """Project review only when it binds to the response's exact ready plan."""

    if response.status != "ready" or response.proposal is None:
        return response.model_copy(update={"planning_workspace": None})
    proposal = response.proposal
    exact_decisions = [
        decision
        for decision in decisions
        if decision.work_item_id == proposal.work_item_id
        and decision.planning_digest == proposal.planning_digest
        and (
            decision.service_card_id is None or decision.service_card_id == proposal.service_card_id
        )
    ]
    return response.model_copy(
        update={
            "planning_workspace": build_content_planning_workspace(
                proposal,
                exact_decisions,
            )
        }
    )


__all__ = ["with_current_planning_workspace"]
