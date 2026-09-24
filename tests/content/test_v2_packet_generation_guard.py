"""Queued planning must revalidate the v2 packet before model and persistence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wilq.content.planning.generated_proposal as generated_proposal
import wilq.content.planning.route_packet_binding as route_binding
from tests.content.packet_plan_draft_fixtures import build_packet_preparation_case
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.input_sources import ContentPlanningInventory


def test_v2_guard_rebuilds_current_base_input_and_rejects_bound_digest_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_input = build_packet_preparation_case(tmp_path).planning_input.model_copy(
        update={
            "inventory": ContentPlanningInventory(
                status="available", content_status="available", acf_section_status="missing"
            )
        }
    )
    packet_id = "content_research_packet_v2_exact"
    packet_digest = "a" * 64
    bound_input = raw_input.model_copy(
        update={
            "research_packet_id": packet_id,
            "research_packet_digest": packet_digest,
            "planning_input_digest": "b" * 64,
        }
    )
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="ekologus_service_bdo_reporting",
        expected_planning_input_digest=bound_input.planning_input_digest,
        research_packet_id=packet_id,
        expected_research_packet_digest=packet_digest,
        requested_by="wilku",
    )
    snapshot = SimpleNamespace()
    monkeypatch.setattr(
        route_binding, "_rebuild_current_v2_base_input", lambda *_: (raw_input, ()), raising=False
    )
    monkeypatch.setattr(
        route_binding,
        "bind_research_packet",
        lambda **_: (bound_input, None),
        raising=False,
    )

    assert route_binding.packet_generation_guard(
        request=request,
        planning_input=bound_input,
        snapshot=snapshot,  # type: ignore[arg-type]
        store=SimpleNamespace(),  # type: ignore[arg-type]
    ) is None

    changed = bound_input.model_copy(update={"planning_input_digest": "c" * 64})
    blocked = route_binding.packet_generation_guard(
        request=request,
        planning_input=changed,
        snapshot=snapshot,  # type: ignore[arg-type]
        store=SimpleNamespace(),  # type: ignore[arg-type]
    )
    assert blocked is not None
    assert blocked.status == "blocked"
    assert blocked.blockers[0].code == "research_packet_conflict"


def test_direct_v2_generation_requires_a_fresh_pre_persistence_guard(
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
    monkeypatch.setattr(
        generated_proposal,
        "_prepare_generation",
        lambda **_: pytest.fail("unguarded direct v2 entered generation"),
    )
    snapshot = SimpleNamespace(preflight=SimpleNamespace(item=SimpleNamespace(id="wi_exact")))

    blocked = generated_proposal.generate_content_planning_proposal(
        snapshot=snapshot,  # type: ignore[arg-type]
        request=request,
        client=SimpleNamespace(),  # type: ignore[arg-type]
        store=SimpleNamespace(),  # type: ignore[arg-type]
        run_store=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert blocked.status == "blocked"
    assert blocked.blockers[0].code == "research_packet_blocked"
    assert blocked.blockers[0].owner == "WILQ content workflow"
