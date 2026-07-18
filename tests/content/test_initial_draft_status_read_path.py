from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_initial_draft


def test_initial_draft_status_get_avoids_heavy_snapshot_loader(monkeypatch) -> None:
    app = FastAPI()
    snapshot_calls = 0

    def snapshot_loader(_work_item_id: str):
        nonlocal snapshot_calls
        snapshot_calls += 1
        raise AssertionError("status GET must not rebuild the workflow snapshot")

    class EmptyLocalState:
        def list_codex_runs(self):
            return []

    class EmptyProposalStore:
        def latest(self, _work_item_id: str):
            return None

    class EmptyWorkflowStore:
        def load_draft_revision_state(self, _work_item_id: str):
            return type("RevisionState", (), {"latest_revision": None})()

    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: EmptyLocalState())
    monkeypatch.setattr(
        content_initial_draft,
        "content_planning_proposal_store",
        lambda: EmptyProposalStore(),
    )
    monkeypatch.setattr(
        content_initial_draft,
        "content_workflow_store",
        lambda: EmptyWorkflowStore(),
    )
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=snapshot_loader,
    )

    response = TestClient(app).get(
        "/api/content/work-items/content_work_item_bdo/initial-draft"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "planning_not_approved"
    assert snapshot_calls == 0
