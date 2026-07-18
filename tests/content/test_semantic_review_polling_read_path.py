from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
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


def test_semantic_review_returns_known_storage_blocker_before_queueing(monkeypatch) -> None:
    app = FastAPI()
    work_item_id = "content_work_item_bdo"
    revision_id = "content_revision_bdo_full_1"
    endpoint = (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision_id}/semantic-review"
    )
    sentinel = JSONResponse(status_code=409, content={"status": "blocked"})
    queued = False

    class Revision:
        revision_id = "content_revision_bdo_full_1"
        content_digest = "a" * 64

    class Snapshot:
        revision_workspace = SimpleNamespace(latest_revision=Revision())

    class ReviewStore:
        def write_ready(self):
            return False

    class FakeCodexClient:
        pass

    def submit(*_args, **_kwargs):
        nonlocal queued
        queued = True

    monkeypatch.setattr(
        content_semantic_review,
        "content_semantic_review_store",
        lambda: ReviewStore(),
    )
    monkeypatch.setattr(
        content_semantic_review,
        "content_codex_app_server_client",
        lambda: FakeCodexClient(),
    )
    monkeypatch.setattr(content_semantic_review, "StdioCodexAppServerClient", FakeCodexClient)
    monkeypatch.setattr(
        content_semantic_review,
        "generate_content_semantic_review",
        lambda **_kwargs: sentinel,
    )
    monkeypatch.setattr(content_semantic_review._SEMANTIC_REVIEW_EXECUTOR, "submit", submit)
    content_semantic_review.register_content_semantic_review_routes(
        app,
        snapshot_loader=lambda _work_item_id: Snapshot(),
    )

    response = TestClient(app).post(
        endpoint,
        json={"expected_revision_digest": "a" * 64, "requested_by": "wilku"},
    )

    assert response.status_code == 409
    assert queued is False
