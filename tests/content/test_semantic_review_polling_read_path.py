from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_semantic_review


def test_active_semantic_review_poll_avoids_heavy_snapshot_loader(monkeypatch) -> None:
    app = FastAPI()
    work_item_id = "content_work_item_bdo"
    revision_id = "content_revision_bdo_full_1"
    endpoint = (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/semantic-review"
    )
    snapshot_calls = 0

    def snapshot_loader(_work_item_id: str):
        nonlocal snapshot_calls
        snapshot_calls += 1
        raise AssertionError("active semantic polling must not rebuild the snapshot")

    active_run = SimpleNamespace(
        hook="content_semantic_review",
        status="started",
        id="codex_content_semantic_review_active",
        started_at=datetime(2026, 7, 18, 8, 0, tzinfo=UTC),
        used_endpoints=[endpoint],
    )

    class LocalState:
        def list_codex_runs(self):
            return [active_run]

    class RevisionStore:
        def load_draft_revision_state(self, _work_item_id: str):
            return SimpleNamespace(
                latest_revision=SimpleNamespace(
                    revision_id=revision_id,
                    content_digest="a" * 64,
                )
            )

    monkeypatch.setattr(content_semantic_review, "local_state_store", lambda: LocalState())
    monkeypatch.setattr(
        content_semantic_review,
        "content_workflow_store",
        lambda: RevisionStore(),
    )
    content_semantic_review.register_content_semantic_review_routes(
        app,
        snapshot_loader=snapshot_loader,
    )

    response = TestClient(app).get(endpoint)

    assert response.status_code == 200
    assert response.json()["status"] == "generating"
    assert response.json()["run_id"] == active_run.id
    assert response.json()["revision_digest"] == "a" * 64
    assert snapshot_calls == 0
