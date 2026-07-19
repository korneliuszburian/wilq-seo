from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

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
        def load_planning_decisions(self, _work_item_id: str):
            return []

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


def test_initial_draft_status_ignores_failed_run_from_an_older_plan(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    stale_run = SimpleNamespace(
        hook="content_initial_full_draft",
        used_endpoints=[endpoint],
        started_at=datetime(2026, 7, 18, tzinfo=UTC),
        status="failed",
        id="stale-run",
        error="codex_timeout",
        proposal_id="old-proposal",
        planning_input_digest="0" * 64,
    )

    class LocalState:
        def list_codex_runs(self):
            return [stale_run]

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return SimpleNamespace(
                proposal_id="current-proposal",
                planning_input_digest="1" * 64,
            )

    class WorkflowStore:
        def load_planning_decisions(self, _work_item_id: str):
            return []

        def load_draft_revision_state(self, _work_item_id: str):
            return SimpleNamespace(latest_revision=None)

    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: LocalState())
    monkeypatch.setattr(
        content_initial_draft,
        "content_planning_proposal_store",
        lambda: ProposalStore(),
    )
    monkeypatch.setattr(
        content_initial_draft,
        "content_workflow_store",
        lambda: WorkflowStore(),
    )
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(
            AssertionError("status GET must remain snapshot-free")
        ),
    )

    response = TestClient(app).get(endpoint)

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "planning_not_approved"


def test_initial_draft_status_does_not_expose_unapproved_latest_proposal(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return SimpleNamespace(
                proposal_id="unapproved-latest",
                planning_input_digest="1" * 64,
            )

    class WorkflowStore:
        def load_planning_decisions(self, _work_item_id: str):
            return []

        def load_draft_revision_state(self, _work_item_id: str):
            return SimpleNamespace(latest_revision=None)

    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: LocalState())
    monkeypatch.setattr(
        content_initial_draft,
        "content_planning_proposal_store",
        lambda: ProposalStore(),
    )
    monkeypatch.setattr(
        content_initial_draft,
        "content_workflow_store",
        lambda: WorkflowStore(),
    )
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(
            AssertionError("status GET must remain snapshot-free")
        ),
    )

    response = TestClient(app).get(endpoint)

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["proposal_id"] is None


def test_initial_draft_status_uses_proposal_bound_to_approved_plan(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    current = SimpleNamespace(
        proposal_id="approved-plan-proposal",
        planning_input_digest="1" * 64,
    )
    stale = SimpleNamespace(
        proposal_id="stale-newer-proposal",
        planning_input_digest="2" * 64,
    )

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest_for_planning_digest(self, _work_item_id: str, planning_digest: str):
            return current if planning_digest == "a" * 64 else None

        def latest(self, _work_item_id: str):
            return stale

    class WorkflowStore:
        def load_planning_decisions(self, _work_item_id: str):
            return [
                SimpleNamespace(decision="approved", planning_digest="a" * 64),
                SimpleNamespace(decision="approved", planning_digest="a" * 64),
            ]

        def load_draft_revision_state(self, _work_item_id: str):
            return SimpleNamespace(latest_revision=None)

    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: LocalState())
    monkeypatch.setattr(
        content_initial_draft,
        "content_planning_proposal_store",
        lambda: ProposalStore(),
    )
    monkeypatch.setattr(content_initial_draft, "content_workflow_store", lambda: WorkflowStore())
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(
            AssertionError("status GET must remain snapshot-free")
        ),
    )

    response = TestClient(app).get(endpoint)

    assert response.status_code == 200
    assert response.json()["proposal_id"] == "approved-plan-proposal"


def test_initial_draft_status_blocks_old_revision_when_newer_planning_job_exists(
    monkeypatch,
) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    current = SimpleNamespace(
        proposal_id="approved-plan-proposal",
        planning_input_digest="1" * 64,
        service_card_id="service-bdo",
    )
    newer = SimpleNamespace(planning_input_digest="2" * 64)

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest_for_planning_digest(self, _work_item_id: str, planning_digest: str):
            return current if planning_digest == "a" * 64 else None

        def latest_generation_response(
            self,
            _work_item_id: str,
            _service_card_id: str | None = None,
        ):
            return newer

    class WorkflowStore:
        def load_planning_decisions(self, _work_item_id: str):
            return [
                SimpleNamespace(decision="approved", planning_digest="a" * 64),
                SimpleNamespace(decision="approved", planning_digest="a" * 64),
            ]

        def load_draft_revision_state(self, _work_item_id: str):
            return SimpleNamespace(latest_revision=None)

    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: LocalState())
    monkeypatch.setattr(
        content_initial_draft,
        "content_planning_proposal_store",
        lambda: ProposalStore(),
    )
    monkeypatch.setattr(content_initial_draft, "content_workflow_store", lambda: WorkflowStore())
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(
            AssertionError("status GET must remain snapshot-free")
        ),
    )

    response = TestClient(app).get(endpoint)

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "stale_planning_input"


def test_initial_draft_status_ignores_newer_job_for_another_service(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    current = SimpleNamespace(
        proposal_id="approved-plan-proposal",
        planning_input_digest="1" * 64,
        service_card_id="service-bdo",
    )
    other_service = SimpleNamespace(planning_input_digest="2" * 64)

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest_for_planning_digest(self, _work_item_id: str, planning_digest: str):
            return current if planning_digest == "a" * 64 else None

        def latest_generation_response(self, _work_item_id: str, service_card_id: str):
            return other_service if service_card_id == "service-other" else None

    class WorkflowStore:
        def load_planning_decisions(self, _work_item_id: str):
            return [
                SimpleNamespace(decision="approved", planning_digest="a" * 64),
                SimpleNamespace(decision="approved", planning_digest="a" * 64),
            ]

        def load_draft_revision_state(self, _work_item_id: str):
            return SimpleNamespace(latest_revision=None)

    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: LocalState())
    monkeypatch.setattr(
        content_initial_draft,
        "content_planning_proposal_store",
        lambda: ProposalStore(),
    )
    monkeypatch.setattr(content_initial_draft, "content_workflow_store", lambda: WorkflowStore())
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(
            AssertionError("status GET must remain snapshot-free")
        ),
    )

    response = TestClient(app).get(endpoint)

    assert response.status_code == 200
    assert response.json()["blockers"][0]["code"] == "planning_not_approved"
