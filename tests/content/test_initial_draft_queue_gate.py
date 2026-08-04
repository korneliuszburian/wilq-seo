from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from apps.api.wilq_api.routers import content_initial_draft
from apps.api.wilq_api.routers.content_initial_draft import _can_queue_initial_draft
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def _request() -> ContentInitialDraftRequest:
    return ContentInitialDraftRequest(
        expected_proposal_id="proposal-1",
        expected_planning_digest="a" * 64,
        expected_planning_input_digest="b" * 64,
        requested_by="wilku",
    )


def _snapshot(
    *, latest_revision: object | None, context_current: bool = True, scope_current: bool = True
) -> SimpleNamespace:
    return SimpleNamespace(
        planning_workspace=SimpleNamespace(
            scope_current=scope_current,
            section_map_current=True,
            proposal=SimpleNamespace(
                proposal_id="proposal-1",
                planning_digest="a" * 64,
                planning_input_digest="b" * 64,
            ),
        ),
        revision_workspace=SimpleNamespace(
            latest_revision=latest_revision,
            context_current=context_current,
        ),
    )


def test_existing_revision_never_enters_async_initial_draft_queue() -> None:
    assert _can_queue_initial_draft(
        _snapshot(latest_revision=object()),
        _request(),
    ) is False


def test_currently_approved_plan_without_revision_can_enter_queue() -> None:
    assert _can_queue_initial_draft(
        _snapshot(latest_revision=None),
        _request(),
    ) is True


def test_generated_plan_without_human_plan_approval_can_enter_queue() -> None:
    assert _can_queue_initial_draft(
        _snapshot(latest_revision=None, scope_current=False),
        _request(),
    ) is True


def test_stale_revision_can_enter_refresh_queue_without_overwriting_history() -> None:
    assert _can_queue_initial_draft(
        _snapshot(latest_revision=object(), context_current=False),
        _request(),
    ) is True


def test_preflight_blocker_from_async_queue_is_persisted_for_status_read(monkeypatch) -> None:
    class Store:
        def __init__(self) -> None:
            self.runs = []

        def list_codex_runs(self):
            return self.runs

        def save_codex_run(self, run):
            self.runs.append(run)
            return run

    store = Store()
    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: store)
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(item=SimpleNamespace(id="item-1"))
    )
    result = ContentInitialDraftResponse(
        status="blocked",
        work_item_id="item-1",
        proposal_id="proposal-1",
        blockers=[
            ContentInitialDraftBlocker(
                code="stale_planning_input",
                label="Nieaktualne wejście",
                reason="Źródło wymaga odświeżenia.",
                next_step="Odśwież źródło.",
            )
        ],
        safe_next_step="Odśwież źródło.",
    )

    content_initial_draft._persist_terminal_preflight_run(
        snapshot=snapshot,
        request=_request(),
        result=result,
        run_id="run-1",
    )

    assert len(store.runs) == 1
    assert store.runs[0].status == "blocked"
    assert store.runs[0].error == "stale_planning_input"


def test_initial_draft_queue_claim_is_durable_and_exact(tmp_path, monkeypatch) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    submitted = []
    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: store)
    monkeypatch.setattr(
        content_initial_draft,
        "_INITIAL_DRAFT_EXECUTOR",
        SimpleNamespace(submit=lambda fn, *args: submitted.append((fn, args))),
    )
    snapshot = _snapshot(latest_revision=None)
    client = StdioCodexAppServerClient()

    first = content_initial_draft._queue_initial_draft(
        "work",
        _request(),
        client,
        lambda _work_item_id: snapshot,
        snapshot,
    )
    second = content_initial_draft._queue_initial_draft(
        "work",
        _request(),
        client,
        lambda _work_item_id: snapshot,
        snapshot,
    )

    assert first.run_id == second.run_id
    assert len(submitted) == 1
    runs = [run for run in store.list_codex_runs() if run.status == "started"]
    assert len(runs) == 1
    assert runs[0].proposal_id == "proposal-1"
    assert runs[0].planning_digest == "a" * 64
    assert runs[0].planning_input_digest == "b" * 64


def test_initial_draft_queue_ignores_started_run_from_another_proposal(
    tmp_path, monkeypatch
) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    endpoint = "/api/content/work-items/work/initial-draft"
    store.save_codex_run(
        CodexRun(
            id="old-run",
            hook="content_initial_full_draft",
            source="wilq_api",
            status="started",
            proposal_id="proposal-old",
            planning_digest="c" * 64,
            planning_input_digest="1" * 64,
            used_endpoints=[endpoint],
        )
    )
    submitted = []
    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: store)
    monkeypatch.setattr(
        content_initial_draft,
        "_INITIAL_DRAFT_EXECUTOR",
        SimpleNamespace(submit=lambda fn, *args: submitted.append((fn, args))),
    )
    snapshot = _snapshot(latest_revision=None)
    response = content_initial_draft._queue_initial_draft(
        "work",
        _request(),
        StdioCodexAppServerClient(),
        lambda _work_item_id: snapshot,
        snapshot,
    )

    assert response.run_id != "old-run"
    assert response.proposal_id == "proposal-1"
    assert len(submitted) == 1


def test_expired_exact_claim_is_replaced_without_get(tmp_path) -> None:
    from wilq.content.drafts.initial_draft_run import claim_initial_draft_run

    store = LocalStateStore(tmp_path / "state.sqlite3")
    store.save_codex_run(
        CodexRun(
            id="expired-run",
            hook="content_initial_full_draft",
            source="wilq_api",
            status="started",
            proposal_id="proposal-1",
            planning_digest="a" * 64,
            planning_input_digest="b" * 64,
            used_endpoints=["/api/content/work-items/work/initial-draft"],
            started_at=datetime.now(UTC) - timedelta(seconds=901),
            deadline_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    claim = claim_initial_draft_run(
        store,
        work_item_id="work",
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        evidence_ids=["ev"],
        timeout_seconds=900,
    )
    assert claim.newly_claimed is True
    assert claim.run.id != "expired-run"
    old = next(run for run in store.list_codex_runs() if run.id == "expired-run")
    assert old.status == "failed"
    assert old.error == "initial_draft_timeout"


def test_queue_persists_proposal_evidence_ids(tmp_path, monkeypatch) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    submitted = []
    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: store)
    monkeypatch.setattr(
        content_initial_draft,
        "_INITIAL_DRAFT_EXECUTOR",
        SimpleNamespace(submit=lambda fn, *args: submitted.append(args)),
    )
    snapshot = _snapshot(latest_revision=None)
    snapshot.planning_workspace.proposal.evidence_ids = ["ev-b", "ev-a", "ev-b"]
    content_initial_draft._queue_initial_draft(
        "work", _request(), StdioCodexAppServerClient(), lambda _: snapshot, snapshot
    )
    run = store.list_codex_runs()[0]
    assert run.evidence_ids == ["ev-b", "ev-a"]


def test_expired_initial_draft_cannot_complete_atomic_append(tmp_path) -> None:
    import pytest

    from wilq.content.workflow.codex_revision_commit import codex_completion_state

    store = LocalStateStore(tmp_path / "state.sqlite3")
    now = datetime.now(UTC)
    started = CodexRun(
        id="expired-append",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="started",
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        used_endpoints=["/api/content/work-items/work/initial-draft"],
        started_at=now - timedelta(seconds=901),
        deadline_at=now - timedelta(seconds=1),
    )
    store.save_codex_run(started)
    completed = started.model_copy(update={"status": "completed", "completed_at": now})
    with store._connect() as connection, pytest.raises(ValueError, match="deadline"):
        connection.execute("BEGIN IMMEDIATE")
        codex_completion_state(connection, completed)
