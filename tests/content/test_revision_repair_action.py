from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from threading import Barrier, Event

import pytest
from fastapi.testclient import TestClient

from tests.content.revision_repair_fixtures import (
    prepare_reviewed_repair_action,
)
from tests.content.test_full_draft_generation_v3 import _authorize, _case, _prepare


def test_public_repair_preview_is_not_the_legacy_blocked_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    action_id = _prepare(case)
    _authorize(case, action_id)
    dispatch = case.http.post(f"/api/content/full-draft-generations-v3/{action_id}/dispatch")
    assert dispatch.status_code == 200, dispatch.text
    root = case.http.get(
        f"/api/content/work-items/{case.proposal.work_item_id}/initial-draft"
    ).json()["revision"]
    from apps.api.wilq_api.routers.content_revision_repair_action import (
        register_content_revision_repair_action_routes,
    )

    register_content_revision_repair_action_routes(
        case.app.router,
        snapshot_loader=lambda _work_item_id: case.snapshot,
        workflow_store_factory=lambda: case.workflow_store,
        run_store_factory=lambda: case.audit_store,
    )
    response = case.http.post(
        f"/api/content/work-items/{case.proposal.work_item_id}/draft-revisions/"
        f"{root['revision_id']}/repair-action/preview",
        json={
            "expected_base_digest": root["content_digest"],
            "selected_section_ids": [root["sections"][0]["section_id"]],
            "requested_by": "synthetic-operator",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["status"] == "blocked"
    assert response.json()["blocker_code"] == "repair_review_context_missing"


def _root(case):
    action_id = _prepare(case)
    _authorize(case, action_id)
    dispatch = case.http.post(f"/api/content/full-draft-generations-v3/{action_id}/dispatch")
    assert dispatch.status_code == 200, dispatch.text
    return case.http.get(
        f"/api/content/work-items/{case.proposal.work_item_id}/initial-draft"
    ).json()["revision"]


def test_reviewed_action_dispatches_one_exact_child_that_needs_its_own_review(
    tmp_path: Path, monkeypatch
) -> None:
    case, root, action_id, repair_client = prepare_reviewed_repair_action(tmp_path, monkeypatch)
    assert repair_client.model_count == 0
    action_route = f"/api/content/draft-repair-actions/{action_id}"
    dispatched = case.http.post(f"{action_route}/dispatch")
    assert dispatched.status_code == 200, dispatched.text
    assert repair_client.model_count == 1
    assert repair_client.request is not None
    child = dispatched.json()["revision"]
    assert child is not None, dispatched.text
    assert child["base_revision_id"] == root["revision_id"]
    assert child["content_digest"] != root["content_digest"]
    assert child["research_packet_id"] == root["research_packet_id"]
    assert child["research_packet_digest"] == root["research_packet_digest"]
    assert child["proposal_metadata"]["codex_run_id"] == dispatched.json()["run_id"]
    assert child["generation_authorization"] is None
    assert dispatched.json()["own_review_required"] is True
    assert dispatched.json()["child_review_status"] == "unreviewed"
    assert {section["section_id"] for section in child["sections"]} == {
        section["section_id"] for section in root["sections"]
    }
    assert {
        evidence_id for section in child["sections"] for evidence_id in section["evidence_ids"]
    } == set(case.fact.evidence_ids)
    assert {
        evidence_id for section in root["sections"] for evidence_id in section["evidence_ids"]
    } == set(case.fact.evidence_ids)

    readback = case.http.get(action_route)
    assert readback.status_code == 200, readback.text
    assert readback.json()["revision"] == child
    replay_turns = len(case.turns)
    replay_model_count = repair_client.model_count
    replay = case.http.post(f"{action_route}/dispatch")
    assert replay.status_code == 200, replay.text
    assert replay.json()["revision"] == child
    assert len(case.turns) == replay_turns
    assert repair_client.model_count == replay_model_count == 1


def _drift_current_packet_planning_input(case) -> None:
    packet = case.current["packet"]
    case.current["packet"] = type(packet).model_validate(
        packet.model_dump(mode="json") | {"planning_input_digest": "0" * 64}
    )


@pytest.mark.parametrize("drift_phase", ["before_model", "after_model"])
def test_packet_planning_input_drift_blocks_repair_without_child(
    tmp_path: Path, monkeypatch, drift_phase: str
) -> None:
    case, _root, action_id, repair_client = prepare_reviewed_repair_action(tmp_path, monkeypatch)
    if drift_phase == "before_model":
        _drift_current_packet_planning_input(case)
    else:
        repair_client.after_model = lambda _request: _drift_current_packet_planning_input(case)

    action_route = f"/api/content/draft-repair-actions/{action_id}"
    dispatched = case.http.post(f"{action_route}/dispatch")

    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["status"] == "blocked"
    assert dispatched.json()["revision"] is None
    assert repair_client.model_count == (0 if drift_phase == "before_model" else 1)
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 1
    )

    replay = case.http.post(f"{action_route}/dispatch")
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "blocked"
    assert replay.json()["revision"] is None
    assert repair_client.model_count == (0 if drift_phase == "before_model" else 1)
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 1
    )


def test_simultaneous_public_dispatches_start_one_repair_worker(
    tmp_path: Path, monkeypatch
) -> None:
    case, _root, action_id, repair_client = prepare_reviewed_repair_action(tmp_path, monkeypatch)
    model_entered = Event()
    release_model = Event()
    start_together = Barrier(3)
    original_run = repair_client.run_structured_turn

    def block_first_model(request):
        model_entered.set()
        assert release_model.wait(timeout=10), "test did not release the repair model turn"
        return original_run(request)

    monkeypatch.setattr(repair_client, "run_structured_turn", block_first_model)
    action_route = f"/api/content/draft-repair-actions/{action_id}/dispatch"
    clients = [TestClient(case.app), TestClient(case.app)]

    def dispatch(client: TestClient):
        start_together.wait(timeout=10)
        return client.post(action_route)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(dispatch, client) for client in clients]
            start_together.wait(timeout=10)
            assert model_entered.wait(timeout=10), "no dispatch reached the model turn"
            completed, pending = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
            assert len(completed) == 1, "the competing dispatch did not finish while model was held"
            blocked = completed.pop().result()
            assert blocked.status_code == 200, blocked.text
            assert blocked.json()["status"] == "blocked"
            assert blocked.json()["blockers"]
            assert blocked.json()["revision"] is None
            assert len(pending) == 1
            release_model.set()
            responses = [future.result(timeout=10) for future in futures]
    finally:
        release_model.set()
        for client in clients:
            client.close()

    assert repair_client.model_count == 1
    assert sum(response.json()["status"] == "created" for response in responses) == 1
    assert sum(response.json()["status"] == "blocked" for response in responses) == 1
    state = case.workflow_store.load_draft_revision_state(case.proposal.work_item_id)
    assert state.revision_count == 2
    replay = case.http.post(action_route)
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] in {"created", "idempotent"}
    assert repair_client.model_count == 1
