"""Parent-safe observer for the v2 planner's final currentness authority."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import wilq.content.planning.generated_proposal as generated_proposal
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)


def test_direct_v2_planner_requires_guard_before_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="ekologus_service_bdo_reporting",
        expected_planning_input_digest="a" * 64,
        research_packet_id="content_research_packet_v2_exact",
        expected_research_packet_digest="b" * 64,
        requested_by="wilku",
    )
    entered_generation = False

    def prepare(**_: object) -> tuple[None, ContentPlanningProposalResponse]:
        nonlocal entered_generation
        entered_generation = True
        return None, ContentPlanningProposalResponse(
            status="blocked",
            work_item_id="wi_exact",
            content_kind="service",
            service_card_id=request.service_card_id,
            blockers=[
                generated_proposal.ContentPlanningProposalBlocker(
                    code="research_packet_blocked",
                    label="test",
                    reason="test",
                    next_step="test",
                )
            ],
            safe_next_step="test",
        )

    monkeypatch.setattr(generated_proposal, "_prepare_generation", prepare)
    snapshot = SimpleNamespace(preflight=SimpleNamespace(item=SimpleNamespace(id="wi_exact")))
    response = generated_proposal.generate_content_planning_proposal(
        snapshot=snapshot,  # type: ignore[arg-type]
        request=request,
        client=SimpleNamespace(),  # type: ignore[arg-type]
        store=SimpleNamespace(),  # type: ignore[arg-type]
        run_store=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert not entered_generation
    assert response.status == "blocked"
    assert response.blockers[0].owner == "WILQ content workflow"
