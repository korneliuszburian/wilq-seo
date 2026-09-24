"""An approved v2 packet is consumable only from current exact inputs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wilq.content.planning.proposal_packet_binding as packet_binding
from tests.content.packet_plan_draft_fixtures import build_packet_preparation_case
from tests.content.test_research_packet_v2_preview import _ready_inputs
from tests.content.test_research_packet_v2_store import _preview_record, _receipt
from wilq.content.planning.approved_packet_v2 import (
    ApprovedPacketV2PlanningView,
    resolve_approved_packet_v2_for_planning,
)
from wilq.content.planning.dynamic_input import _digest
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.packet_input_binding import (
    bind_packet_identity_to_planning_input,
    unbind_packet_identity_from_planning_input,
)
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    ResearchPacketV2PreviewBlocker,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_v2_planning_view_requires_approved_exact_current_receipt(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    record = _preview_record()
    source_pack, planning_input = _ready_inputs()
    del source_pack
    receipt = _receipt(record)

    missing = resolve_approved_packet_v2_for_planning(
        store=store,
        packet_id=receipt.packet_id,
        expected_digest=receipt.packet_digest,
        planning_input=planning_input,
        current_preview_loader=lambda _id, _input: record.snapshot,
    )
    assert isinstance(missing, ResearchPacketV2PreviewBlocker)
    assert missing.code == "research_packet_v2_approval_missing"

    assert store.record_research_packet_v2_preview(record) == "created"
    assert store._record_research_packet_v2_approval_receipt(receipt) == "created"
    current = resolve_approved_packet_v2_for_planning(
        store=store,
        packet_id=receipt.packet_id,
        expected_digest=receipt.packet_digest,
        planning_input=planning_input,
        current_preview_loader=lambda _id, _input: record.snapshot,
    )
    assert isinstance(current, ApprovedPacketV2PlanningView)
    assert current.packet_id == receipt.packet_id
    assert current.packet_digest == receipt.packet_digest
    assert current.approved_source_fact_ids == ("fact_exact",)
    assert not hasattr(current, "source_pack_binding_id")

    changed_input = resolve_approved_packet_v2_for_planning(
        store=store,
        packet_id=receipt.packet_id,
        expected_digest=receipt.packet_digest,
        planning_input=planning_input.model_copy(update={"planning_input_digest": "9" * 64}),
        current_preview_loader=lambda _id, _input: record.snapshot,
    )
    assert isinstance(changed_input, ResearchPacketV2PreviewBlocker)
    assert changed_input.code == "research_packet_v2_planning_input_changed"

    blocked_preview = ResearchPacketV2Preview(
        status="blocked",
        work_item_id="wi_exact",
        blocker=ResearchPacketV2PreviewBlocker(
            code="material_meaning_changed",
            owner="WILQ content workflow",
            evidence_ids=("ev_current",),
            safe_next_step="Przejrzyj bieżący materiał.",
        ),
    )
    drift = resolve_approved_packet_v2_for_planning(
        store=store,
        packet_id=receipt.packet_id,
        expected_digest=receipt.packet_digest,
        planning_input=planning_input,
        current_preview_loader=lambda _id, _input: blocked_preview,
    )
    assert isinstance(drift, ResearchPacketV2PreviewBlocker)
    assert drift.code == "material_meaning_changed"


def test_v2_packet_identity_binding_recovers_the_exact_unbound_input(tmp_path: Path) -> None:
    planning_input = build_packet_preparation_case(tmp_path).planning_input
    unbound_payload = planning_input.model_dump(mode="json")
    unbound_payload.pop("planning_input_digest")
    planning_input = planning_input.model_copy(
        update={"planning_input_digest": _digest(unbound_payload)}
    )
    bound = bind_packet_identity_to_planning_input(
        planning_input,
        work_item_id=planning_input.work_item_id,
        packet_id="content_research_packet_v2_exact",
        packet_digest="a" * 64,
    )

    assert bound.research_packet_id == "content_research_packet_v2_exact"
    assert bound.planning_input_digest != planning_input.planning_input_digest
    assert unbind_packet_identity_from_planning_input(bound).planning_input_digest == (
        planning_input.planning_input_digest
    )


def test_planner_binds_real_v2_receipt_without_v1_binding_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    record = _preview_record()
    receipt = _receipt(record)
    _source_pack, planning_input = _ready_inputs()
    planning_input = planning_input.model_copy(update={"source_facts": []})
    view = ApprovedPacketV2PlanningView(
        packet_id=receipt.packet_id,
        packet_digest=receipt.packet_digest,
        current_work_item_id=record.work_item_id,
        approved_source_fact_ids=("fact_exact",),
        evidence_ids=record.snapshot.evidence_ids,
        preview=record.snapshot,
    )
    monkeypatch.setattr(packet_binding, "resolve_approved_packet_v2_for_planning", lambda **_: view)
    monkeypatch.setattr(
        packet_binding,
        "project_research_packet_v2_facts",
        lambda current, _facts, _registry: current,
    )
    monkeypatch.setattr(packet_binding, "ekologus_source_facts", lambda: [])
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="ekologus_service_bdo_reporting",
        expected_planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=receipt.packet_id,
        expected_research_packet_digest=receipt.packet_digest,
        requested_by="wilku",
    )

    bound, blocked = packet_binding.bind_research_packet(
        snapshot=SimpleNamespace(),  # type: ignore[arg-type]
        planning_input=planning_input,
        request=request,
        require_packet=True,
        workflow_store=store,
        current_v2_preview_loader=lambda _id, _input: record.snapshot,
    )

    assert blocked is None
    assert bound is not None
    assert bound.research_packet_id == receipt.packet_id
    assert bound.research_packet_digest == receipt.packet_digest
    assert request.source_pack_binding_id is None
