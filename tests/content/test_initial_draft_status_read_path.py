from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_initial_draft
from wilq.content.drafts import initial_draft_queue
from wilq.schemas import CodexRun


def test_legacy_completed_run_requires_exact_revision_lineage() -> None:
    run = SimpleNamespace(id="legacy-run", planning_digest=None)
    proposal = SimpleNamespace(
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
    )
    revision = SimpleNamespace(
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        proposal_metadata=SimpleNamespace(codex_run_id="legacy-run"),
    )
    assert content_initial_draft._legacy_run_matches_revision(run, proposal, revision)
    revision.proposal_metadata.codex_run_id = "other-run"
    assert not content_initial_draft._legacy_run_matches_revision(run, proposal, revision)


def test_canonical_revision_run_precedes_later_retry(monkeypatch) -> None:
    canonical = CodexRun(
        id="run-1",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="completed",
        proposal_id="proposal-1",
        planning_digest=None,
        planning_input_digest="b" * 64,
        used_endpoints=["/api/content/work-items/work/initial-draft"],
    )
    retry = canonical.model_copy(
        update={
            "id": "run-2",
            "status": "blocked",
            "planning_digest": "a" * 64,
            "error": "revision_already_exists",
        }
    )
    class Store:
        def list_codex_runs(self):
            return [canonical, retry]
    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: Store())
    proposal = SimpleNamespace(
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
    )
    revision = SimpleNamespace(
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        proposal_metadata=SimpleNamespace(codex_run_id="run-1"),
    )
    assert content_initial_draft._canonical_revision_run(revision, proposal) == canonical


def test_first_initial_draft_run_is_visible_without_revision() -> None:
    run = CodexRun(
        id="first-run",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="started",
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        initial_draft_context_digest="c" * 64,
        initial_draft_base_revision_id=None,
    )
    proposal = SimpleNamespace(
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
    )
    assert content_initial_draft._run_matches_revision_context(run, None, proposal)


def test_status_uses_current_context_not_a_later_stale_run(monkeypatch) -> None:
    now = datetime.now(UTC)
    proposal = SimpleNamespace(
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        generation_status="codex_generated",
        service_card_id=None,
    )
    snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(proposal=proposal),
        revision_workspace=SimpleNamespace(latest_revision=None),
    )
    current_digest = initial_draft_queue.snapshot_initial_draft_context_digest(
        snapshot, proposal
    )
    current = CodexRun(
        id="current-run",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="started",
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
        initial_draft_context_digest=current_digest,
        initial_draft_base_revision_id=None,
        used_endpoints=["/api/content/work-items/work/initial-draft"],
        started_at=now - timedelta(seconds=10),
    )
    stale = current.model_copy(
        update={
            "id": "later-stale-run",
            "initial_draft_context_digest": "0" * 64,
            "started_at": now - timedelta(seconds=5),
        }
    )

    class LocalState:
        def list_codex_runs(self):
            return [current, stale]

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return proposal

        def latest_for_service(self, _work_item_id: str, _service_card_id: str | None):
            return proposal

    class WorkflowStore:
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

    response = content_initial_draft._read_initial_draft_status(
        "work",
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    assert response.status == "generating"
    assert response.run_id == current.id


def test_status_follows_snapshot_proposal_for_a_context_bound_run(monkeypatch) -> None:
    persisted = SimpleNamespace(
        proposal_id="persisted-proposal",
        planning_digest="0" * 64,
        planning_input_digest="1" * 64,
        generation_status="codex_generated",
        service_card_id=None,
    )
    current_proposal = SimpleNamespace(
        proposal_id="snapshot-proposal",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        generation_status="codex_generated",
        service_card_id=None,
    )
    snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(proposal=current_proposal),
        revision_workspace=SimpleNamespace(latest_revision=None),
    )
    run = CodexRun(
        id="current-context-run",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="started",
        proposal_id=current_proposal.proposal_id,
        planning_digest=current_proposal.planning_digest,
        planning_input_digest=current_proposal.planning_input_digest,
        initial_draft_context_digest=(
            initial_draft_queue.snapshot_initial_draft_context_digest(
                snapshot,
                current_proposal,
            )
        ),
        initial_draft_base_revision_id=None,
        used_endpoints=["/api/content/work-items/work/initial-draft"],
    )

    class LocalState:
        def list_codex_runs(self):
            return [run]

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return persisted

        def latest_for_service(self, _work_item_id: str, _service_card_id: str | None):
            return persisted

    class WorkflowStore:
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

    response = content_initial_draft._read_initial_draft_status(
        "work",
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    assert response.status == "generating"
    assert response.proposal_id == current_proposal.proposal_id
    assert response.run_id == run.id


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
    assert response.json()["blockers"][0]["code"] == "planning_not_ready"
    assert "Wygeneruj aktualny plan" in response.json()["safe_next_step"]
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
    assert response.json()["blockers"][0]["code"] == "planning_not_ready"


def test_initial_draft_status_marks_a_current_generated_plan_as_not_started(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return SimpleNamespace(
                proposal_id="current-proposal",
                planning_input_digest="1" * 64,
                generation_status="codex_generated",
            )

    class WorkflowStore:
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
    assert response.json()["blockers"][0]["code"] == "draft_not_started"
    assert "Przygotuj pełny tekst" in response.json()["safe_next_step"]


def test_initial_draft_status_does_not_expose_non_generated_latest_proposal(monkeypatch) -> None:
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


def test_initial_draft_status_uses_latest_generated_plan(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    current = SimpleNamespace(
        proposal_id="approved-plan-proposal",
        planning_input_digest="1" * 64,
        generation_status="codex_generated",
        service_card_id="service-bdo",
    )
    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest_for_planning_digest(self, _work_item_id: str, planning_digest: str):
            return current if planning_digest == "a" * 64 else None

        def latest(self, _work_item_id: str):
            return current

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


def test_initial_draft_status_terminalizes_a_stalled_current_run(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    stale_run = CodexRun(
        id="stalled-initial-draft",
        hook="content_initial_full_draft",
        status="started",
        started_at=datetime.now(UTC) - timedelta(seconds=2401),
        used_endpoints=[endpoint],
        proposal_id="current-proposal",
        planning_input_digest="1" * 64,
    )
    saved: list[CodexRun] = []

    class LocalState:
        def list_codex_runs(self):
            return [stale_run]

        def save_codex_run(self, run: CodexRun) -> CodexRun:
            saved.append(run)
            return run

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return SimpleNamespace(
                proposal_id="current-proposal",
                planning_input_digest="1" * 64,
                generation_status="codex_generated",
            )

    class WorkflowStore:
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
    assert response.json()["status"] == "failed"
    assert response.json()["blockers"][0]["code"] == "runtime_failed"
    assert saved and saved[0].error == "initial_draft_timeout"


def test_initial_draft_status_blocks_old_revision_when_newer_planning_job_exists(
    monkeypatch,
) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    current = SimpleNamespace(
        proposal_id="approved-plan-proposal",
        planning_input_digest="1" * 64,
        service_card_id="service-bdo",
        generation_status="codex_generated",
    )
    newer = SimpleNamespace(planning_input_digest="2" * 64)

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return current

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


def test_initial_draft_status_blocks_old_revision_when_newer_plan_is_ready(
    monkeypatch,
) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    current = SimpleNamespace(
        proposal_id="approved-plan-proposal",
        planning_input_digest="1" * 64,
        service_card_id="service-bdo",
        generation_status="codex_generated",
    )
    newer = SimpleNamespace(
        proposal_id="new-ready-proposal",
        planning_input_digest="2" * 64,
    )

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return current

        def latest_for_planning_digest(self, _work_item_id: str, planning_digest: str):
            return current if planning_digest == "a" * 64 else None

        def latest_for_service(self, _work_item_id: str, _service_card_id: str):
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
        generation_status="codex_generated",
    )
    other_service = SimpleNamespace(planning_input_digest="2" * 64)

    class LocalState:
        def list_codex_runs(self):
            return []

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return current

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
    assert response.json()["blockers"][0]["code"] == "draft_not_started"


def test_initial_draft_status_exposes_safe_document_gate_details(monkeypatch) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    proposal = SimpleNamespace(
        proposal_id="proposal", planning_input_digest="1" * 64,
        service_card_id="service", generation_status="codex_generated",
    )
    run = SimpleNamespace(
        hook="content_initial_full_draft", used_endpoints=[endpoint],
        started_at=datetime(2026, 7, 31, tzinfo=UTC), status="blocked", id="run",
        error="document_scope_mismatch|regulatory_document_assertion:bdo_kpo:before_transport",
        proposal_id="proposal", planning_input_digest="1" * 64,
    )

    class LocalState:
        def list_codex_runs(self):
            return [run]

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return proposal

    class WorkflowStore:
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
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(AssertionError()),
    )

    body = TestClient(app).get(endpoint).json()

    assert body["blockers"][0]["code"] == "document_scope_mismatch"
    assert body["blockers"][0]["source_codes"] == [
        "regulatory_document_assertion:bdo_kpo:before_transport"
    ]


@pytest.mark.parametrize(
    ("blocker_code", "source_code"),
    [
        ("readability_gate_failed", "working_note"),
        ("readability_repair_failed", "readability_repair_turn_failed"),
    ],
)
def test_initial_draft_status_preserves_persisted_readability_blocker_identity(
    monkeypatch,
    blocker_code: str,
    source_code: str,
) -> None:
    app = FastAPI()
    endpoint = "/api/content/work-items/content_work_item_bdo/initial-draft"
    proposal = SimpleNamespace(
        proposal_id="proposal",
        planning_input_digest="1" * 64,
        service_card_id="service",
        generation_status="codex_generated",
    )
    run = SimpleNamespace(
        hook="content_initial_full_draft",
        used_endpoints=[endpoint],
        started_at=datetime(2026, 8, 12, tzinfo=UTC),
        status="blocked",
        id="readability-run",
        error=f"{blocker_code}|{source_code}",
        proposal_id="proposal",
        planning_input_digest="1" * 64,
    )

    class LocalState:
        def list_codex_runs(self):
            return [run]

    class ProposalStore:
        def latest(self, _work_item_id: str):
            return proposal

    class WorkflowStore:
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
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(AssertionError()),
    )

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", "")
        == "/api/content/work-items/{work_item_id}/initial-draft"
        and "GET" in getattr(route, "methods", set())
    )
    body = route.endpoint("content_work_item_bdo").model_dump(mode="json")

    assert body["blockers"][0]["code"] == blocker_code
    assert body["blockers"][0]["source_codes"] == [source_code]
