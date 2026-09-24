"""A reviewed intent reaches the planning queue only after durable apply audit."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast

import pytest

from apps.api.wilq_api.routers.content_planning_generation_dispatch import (
    register_content_planning_generation_dispatch_route,
)
from tests.content.test_planning_generation_intent import _client, _lifecycle
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_intent import PlanningGenerationIntentApplyBlocker
from wilq.content.planning.generation_intent_dispatch import (
    PlanningGenerationDispatchOutcome,
    dispatch_applied_planning_intent,
)
from wilq.content.planning.packet_input_binding import bind_packet_identity_to_planning_input
from wilq.content.planning.source_pack_projection import project_research_packet_v2_facts
from wilq.storage.local_state import LocalStateStore


def test_dispatch_requires_persisted_apply_audit_then_reuses_exact_queue_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, preview, raw_input, registry = _client(tmp_path, monkeypatch)
    projected = project_research_packet_v2_facts(
        raw_input, preview.selected_facts, (registry["fact"],)
    )
    bound = bind_packet_identity_to_planning_input(
        projected,
        work_item_id=raw_input.work_item_id,
        packet_id=f"content_research_packet_v2_{preview.preview_hash[:24]}",
        packet_digest=preview.preview_hash,
    )
    prepared = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent/preview",
        json={
            "content_kind": "service",
            "service_card_id": "card_exact",
            "packet_id": bound.research_packet_id,
            "packet_digest": bound.research_packet_digest,
            "expected_raw_planning_input_digest": raw_input.planning_input_digest,
            "expected_projected_planning_input_digest": bound.planning_input_digest,
        },
    )
    assert prepared.status_code == 200, prepared.text
    action_id = prepared.json()["action_id"]
    queued_keys: set[tuple[str, str]] = set()
    queue_calls: list[dict[str, object]] = []

    def enqueue(**kwargs: object) -> ContentPlanningProposalResponse:
        queue_calls.append(kwargs)
        request = cast(ContentPlanningProposalRequest, kwargs["request"])
        digest = request.expected_planning_input_digest
        key = (str(kwargs["work_item_id"]), digest)
        queued_keys.add(key)
        return ContentPlanningProposalResponse(
            status="generating",
            work_item_id=key[0],
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=digest,
            research_packet_id=request.research_packet_id,
            research_packet_digest=request.expected_research_packet_digest,
            safe_next_step="Odczytaj status planu.",
        )

    register_content_planning_generation_dispatch_route(
        client.app.router,
        snapshot_loader=lambda _id: None,  # type: ignore[arg-type]
        workflow_store_factory=lambda: store,
        audit_store_factory=lambda: LocalStateStore(tmp_path / "audit.sqlite3"),
        proposal_store_factory=lambda: ContentPlanningProposalStore(tmp_path / "proposal.sqlite3"),
        enqueue=enqueue,
    )
    path = f"/api/content/planning-generation-intents/{action_id}/dispatch"

    before = client.post(path)
    assert before.status_code == 409
    assert before.json()["blocker"]["code"] == "planning_generation_intent_not_applied"
    assert queue_calls == []

    assert _lifecycle(client, action_id)["applied"] is True
    without_audit = dispatch_applied_planning_intent(
        action_id,
        workflow_store=store,
        audit_store=LocalStateStore(tmp_path / "missing-audit.sqlite3"),
        proposal_store=ContentPlanningProposalStore(tmp_path / "proposal.sqlite3"),
        snapshot_loader=lambda _id: None,  # type: ignore[arg-type]
        enqueue=enqueue,
    )
    assert without_audit.status == "blocked"
    assert without_audit.blocker is not None
    assert without_audit.blocker.code == "planning_apply_audit_missing"
    assert queue_calls == []

    first = client.post(path)
    second = client.post(path)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "accepted"
    assert queued_keys == {(raw_input.work_item_id, bound.planning_input_digest)}
    assert len(queue_calls) == 2
    request = cast(ContentPlanningProposalRequest, queue_calls[0]["request"])
    assert request.research_packet_id == bound.research_packet_id
    assert request.source_pack_binding_id is None
    assert callable(queue_calls[0]["generation_guard"])


def test_apply_dispatches_only_after_its_audit_is_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, preview, raw_input, registry = _client(tmp_path, monkeypatch)
    projected = project_research_packet_v2_facts(
        raw_input, preview.selected_facts, (registry["fact"],)
    )
    bound = bind_packet_identity_to_planning_input(
        projected,
        work_item_id=raw_input.work_item_id,
        packet_id=f"content_research_packet_v2_{preview.preview_hash[:24]}",
        packet_digest=preview.preview_hash,
    )
    prepared = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent/preview",
        json={
            "content_kind": "service",
            "service_card_id": "card_exact",
            "packet_id": bound.research_packet_id,
            "packet_digest": bound.research_packet_digest,
            "expected_raw_planning_input_digest": raw_input.planning_input_digest,
            "expected_projected_planning_input_digest": bound.planning_input_digest,
        },
    )
    assert prepared.status_code == 200
    action_id = prepared.json()["action_id"]
    observed: list[str] = []

    def dispatch_after_apply(value: str) -> PlanningGenerationDispatchOutcome:
        events = LocalStateStore(tmp_path / "audit.sqlite3").list_audit_events(action_id=value)
        assert any(event.event_type == "apply_succeeded" for event in events)
        assert store.load_planning_generation_intent_receipt(value) is not None
        observed.append(value)
        blocker = PlanningGenerationIntentApplyBlocker(
            code="synthetic_no_model",
            safe_next_step="Synthetic test ends after audit.",
        )
        return PlanningGenerationDispatchOutcome(
            status="blocked",
            action_id=value,
            blocker=blocker,
            safe_next_step=blocker.safe_next_step,
        )

    actions_module = importlib.import_module("apps.api.wilq_api.routers.actions")
    monkeypatch.setattr(
        actions_module, "_post_apply_planning_dispatch", dispatch_after_apply, raising=False
    )
    applied = _lifecycle(client, action_id)

    assert observed == [action_id]
    assert applied["applied"] is True
