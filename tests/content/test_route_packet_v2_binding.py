"""The planning route must consume approved v2 without preparing a v1 packet."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wilq.content.planning.route_packet_binding as route_binding
from tests.content.packet_plan_draft_fixtures import build_packet_preparation_case
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest


def test_route_binds_approved_v2_without_entering_legacy_packet_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = build_packet_preparation_case(tmp_path).planning_input
    bound = raw.model_copy(
        update={
            "research_packet_id": "content_research_packet_v2_exact",
            "research_packet_digest": "b" * 64,
            "planning_input_digest": "c" * 64,
        }
    )
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="ekologus_service_bdo_reporting",
        expected_planning_input_digest=raw.planning_input_digest,
        research_packet_id=bound.research_packet_id,
        expected_research_packet_digest=bound.research_packet_digest,
        requested_by="wilku",
    )
    monkeypatch.setattr(route_binding, "canonical_inventory_work_item_id", lambda value: value)
    monkeypatch.setattr(
        route_binding, "store_has_source_pack_for_work_item", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        route_binding,
        "packet_blocked_response",
        lambda **_: SimpleNamespace(status="blocked"),
    )
    monkeypatch.setattr(
        route_binding, "bind_research_packet", lambda **_: (bound, None)
    )

    result = route_binding.prepare_and_bind_research_packet(
        work_item_id=raw.work_item_id,
        request=request,
        planning_input=raw,
        snapshot=SimpleNamespace(),  # type: ignore[arg-type]
        store=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert result.response is None
    assert result.planning_input is bound
    assert result.request.research_packet_id == bound.research_packet_id
    assert result.request.expected_research_packet_digest == bound.research_packet_digest
    assert result.request.expected_planning_input_digest == bound.planning_input_digest
    assert result.request.source_pack_binding_id is None
