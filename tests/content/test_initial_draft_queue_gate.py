from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Event
from types import SimpleNamespace

import pytest

from apps.api.wilq_api.routers import content_initial_draft
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts import initial_draft_queue
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
    assert initial_draft_queue.can_queue_initial_draft(
        _snapshot(latest_revision=object()),
        _request(),
    ) is False


def test_currently_approved_plan_without_revision_can_enter_queue() -> None:
    assert initial_draft_queue.can_queue_initial_draft(
        _snapshot(latest_revision=None),
        _request(),
    ) is True


def test_generated_plan_without_human_plan_approval_can_enter_queue() -> None:
    assert initial_draft_queue.can_queue_initial_draft(
        _snapshot(latest_revision=None, scope_current=False),
        _request(),
    ) is True


def test_stale_revision_can_enter_refresh_queue_without_overwriting_history() -> None:
    assert initial_draft_queue.can_queue_initial_draft(
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
    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
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
    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
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


def test_authorized_refresh_queue_claim_has_one_exact_context_and_submission(
    tmp_path,
    monkeypatch,
) -> None:
    from wilq.content.workflow.refresh_preparation_contracts import (
        ContentRefreshPreparationBinding,
    )

    store = LocalStateStore(tmp_path / "state.sqlite3")
    submitted = []
    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
    monkeypatch.setattr(
        content_initial_draft,
        "_INITIAL_DRAFT_EXECUTOR",
        SimpleNamespace(submit=lambda fn, *args: submitted.append((fn, args))),
    )
    snapshot = _snapshot(latest_revision=None)
    proposal = snapshot.planning_workspace.proposal
    proposal.service_card_id = "ekologus_service_bdo_reporting"
    proposal.refresh_preparation_binding = ContentRefreshPreparationBinding(
        authorization_id="content_refresh_preparation_authorization_" + "c" * 24,
        authorization_digest="c" * 64,
        classification_run_id="content_production_classification_test",
        classification_run_digest="d" * 64,
        decision_set_digest="e" * 64,
        source_packet_row_digest="f" * 64,
        current_work_item_id="work",
        canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
        public_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        service_card_id="ekologus_service_bdo_reporting",
        planning_input_digest="b" * 64,
    )
    snapshot.preflight = SimpleNamespace(
        item=SimpleNamespace(
            final_canonical_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
            intended_final_url=None,
        )
    )
    request = _request().model_copy(
        update={
            "refresh_preparation_authorization_id": (
                proposal.refresh_preparation_binding.authorization_id
            ),
            "expected_refresh_preparation_authorization_digest": (
                proposal.refresh_preparation_binding.authorization_digest
            ),
        }
    )

    first = content_initial_draft._queue_initial_draft(
        "work",
        request,
        StdioCodexAppServerClient(),
        lambda _work_item_id: snapshot,
        snapshot,
    )
    repeated = content_initial_draft._queue_initial_draft(
        "work",
        request,
        StdioCodexAppServerClient(),
        lambda _work_item_id: snapshot,
        snapshot,
    )

    assert first.run_id == repeated.run_id
    assert len(submitted) == 1
    assert store.list_codex_runs()[0].initial_draft_context_digest == (
        initial_draft_queue.snapshot_initial_draft_context_digest(snapshot, proposal)
    )


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
    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
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


def test_bounded_initial_draft_executor_rejects_when_worker_capacity_is_full() -> None:
    executor = content_initial_draft.BoundedInitialDraftExecutor(max_workers=1)
    started = Event()
    release = Event()

    def hold_worker() -> None:
        started.set()
        assert release.wait(timeout=5)

    future = executor.submit(hold_worker)
    assert started.wait(timeout=5)
    try:
        with pytest.raises(content_initial_draft.InitialDraftQueueFullError):
            executor.submit(lambda: None)
    finally:
        release.set()
        future.result(timeout=5)
        executor.shutdown()


def test_initial_draft_queue_full_returns_explicit_blocker_and_terminal_run(
    tmp_path,
    monkeypatch,
) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")

    class FullExecutor:
        def submit(self, *_args, **_kwargs):
            raise content_initial_draft.InitialDraftQueueFullError

    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
    monkeypatch.setattr(content_initial_draft, "_INITIAL_DRAFT_EXECUTOR", FullExecutor())
    snapshot = _snapshot(latest_revision=None)

    response = content_initial_draft._queue_initial_draft(
        "work",
        _request(),
        StdioCodexAppServerClient(),
        lambda _work_item_id: snapshot,
        snapshot,
    )

    assert response.status == "blocked"
    assert response.blockers[0].code == "initial_draft_queue_full"
    assert response.blockers[0].retry_after_seconds == 5
    assert response.run_id is not None
    persisted = next(run for run in store.list_codex_runs() if run.id == response.run_id)
    assert persisted.status == "blocked"
    assert persisted.error == "initial_draft_queue_full"


def test_expired_exact_claim_is_replaced_without_get(tmp_path) -> None:
    from wilq.content.drafts.initial_draft_run import (
        InitialDraftClaimContext,
        claim_initial_draft_run,
    )

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
            initial_draft_context_digest="c" * 64,
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
        context_digest="c" * 64,
        expected_base_revision_id=None,
        current_context=lambda: InitialDraftClaimContext(
            proposal_id="proposal-1",
            planning_digest="a" * 64,
            planning_input_digest="b" * 64,
            context_digest="c" * 64,
            base_revision_id=None,
            context_current=True,
        ),
    )
    assert claim.newly_claimed is True
    assert claim.run.id != "expired-run"
    old = next(run for run in store.list_codex_runs() if run.id == "expired-run")
    assert old.status == "failed"
    assert old.error == "initial_draft_timeout"


def test_different_initial_draft_contexts_do_not_share_claim(tmp_path) -> None:
    from wilq.content.drafts.initial_draft_run import (
        InitialDraftClaimContext,
        claim_initial_draft_run,
    )

    store = LocalStateStore(tmp_path / "state.sqlite3")
    common = {
        "work_item_id": "work",
        "proposal_id": "proposal-1",
        "planning_digest": "a" * 64,
        "planning_input_digest": "b" * 64,
        "evidence_ids": ["ev"],
        "timeout_seconds": 900,
    }
    def context(digest: str) -> InitialDraftClaimContext:
        return InitialDraftClaimContext(
            proposal_id="proposal-1",
            planning_digest="a" * 64,
            planning_input_digest="b" * 64,
            context_digest=digest,
            base_revision_id=None,
            context_current=False,
        )

    first = claim_initial_draft_run(
        store,
        context_digest="1" * 64,
        expected_base_revision_id=None,
        current_context=lambda: context("1" * 64),
        **common,
    )
    second = claim_initial_draft_run(
        store,
        context_digest="2" * 64,
        expected_base_revision_id=None,
        current_context=lambda: context("2" * 64),
        **common,
    )
    assert first.run.id != second.run.id
    assert first.newly_claimed is True
    assert second.newly_claimed is True


def test_delayed_context_cannot_create_a_shadow_initial_draft_run(tmp_path) -> None:
    from wilq.content.drafts.initial_draft_run import (
        InitialDraftClaimContext,
        claim_initial_draft_run,
    )

    store = LocalStateStore(tmp_path / "state.sqlite3")
    common = {
        "work_item_id": "work",
        "proposal_id": "proposal-1",
        "planning_digest": "a" * 64,
        "planning_input_digest": "b" * 64,
        "evidence_ids": ["ev"],
        "timeout_seconds": 900,
        "expected_base_revision_id": "revision-0",
    }
    current_context = InitialDraftClaimContext(
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        context_digest="1" * 64,
        base_revision_id="revision-0",
        context_current=False,
    )
    current = claim_initial_draft_run(
        store,
        context_digest="1" * 64,
        current_context=lambda: current_context,
        **common,
    )
    delayed = claim_initial_draft_run(
        store,
        context_digest="0" * 64,
        current_context=lambda: current_context,
        **common,
    )

    assert current.run is not None
    assert delayed.run is None
    assert delayed.newly_claimed is False
    persisted = next(run for run in store.list_codex_runs() if run.id == current.run.id)
    assert persisted.status == "started"
    assert all(run.initial_draft_context_digest != "0" * 64 for run in store.list_codex_runs())


def test_queue_rejects_a_snapshot_that_changes_before_its_durable_claim(
    tmp_path, monkeypatch
) -> None:
    from wilq.content.drafts.initial_draft_run import (
        InitialDraftClaimContext,
        claim_initial_draft_run,
    )

    store = LocalStateStore(tmp_path / "state.sqlite3")
    current_context = InitialDraftClaimContext(
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        context_digest="1" * 64,
        base_revision_id=None,
        context_current=False,
    )
    current = claim_initial_draft_run(
        store,
        work_item_id="work",
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        evidence_ids=["ev"],
        timeout_seconds=900,
        context_digest=current_context.context_digest,
        expected_base_revision_id=None,
        current_context=lambda: current_context,
    )
    assert current.run is not None

    stale_snapshot = _snapshot(latest_revision=None)
    stale_snapshot.context_digest = "0" * 64
    current_snapshot = _snapshot(latest_revision=None)
    current_snapshot.context_digest = current_context.context_digest
    snapshots = iter([stale_snapshot, current_snapshot])
    submitted = []
    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
    monkeypatch.setattr(
        content_initial_draft,
        "_INITIAL_DRAFT_EXECUTOR",
        SimpleNamespace(submit=lambda fn, *args: submitted.append((fn, args))),
    )
    monkeypatch.setattr(
        initial_draft_queue,
        "snapshot_initial_draft_context_digest",
        lambda snapshot, _proposal: snapshot.context_digest,
    )

    response = content_initial_draft._queue_initial_draft(
        "work",
        _request(),
        StdioCodexAppServerClient(),
        lambda _work_item_id: next(snapshots),
        stale_snapshot,
    )

    assert response.status == "blocked"
    assert response.blockers[0].code == "stale_initial_draft_context"
    assert submitted == []
    persisted = store.list_codex_runs()
    assert [run.id for run in persisted] == [current.run.id]
    assert persisted[0].initial_draft_context_digest == current_context.context_digest


def test_queue_persists_proposal_evidence_ids(tmp_path, monkeypatch) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    submitted = []
    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: store)
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

    from wilq.content.workflow.documents.codex_revision_commit import codex_completion_state

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


def test_completed_initial_draft_replay_is_idempotent_after_deadline(tmp_path) -> None:
    from wilq.content.workflow.documents.codex_revision_commit import codex_completion_state

    store = LocalStateStore(tmp_path / "state.sqlite3")
    now = datetime.now(UTC)
    completed = CodexRun(
        id="completed-replay",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="completed",
        proposal_id="proposal-1",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        used_endpoints=["/api/content/work-items/work/initial-draft"],
        started_at=now - timedelta(seconds=901),
        deadline_at=now - timedelta(seconds=1),
        completed_at=now - timedelta(seconds=2),
    )
    store.save_codex_run(completed)
    with store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert codex_completion_state(connection, completed) == "completed"


def test_worker_terminal_write_cannot_overwrite_polling_failure(tmp_path) -> None:
    from wilq.content.drafts.initial_draft_run import (
        finish_initial_draft_run,
        transition_initial_draft_run_if_status,
    )

    store = LocalStateStore(tmp_path / "state.sqlite3")
    started = CodexRun(
        id="cas-worker",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="started",
        used_endpoints=["/api/content/work-items/work/initial-draft"],
    )
    store.save_codex_run(started)
    assert transition_initial_draft_run_if_status(
        store, started, status="failed", error="initial_draft_timeout"
    ) is not None
    assert finish_initial_draft_run(
        store, started, status="blocked", error="document_scope_mismatch"
    ) is None
    persisted = next(run for run in store.list_codex_runs() if run.id == started.id)
    assert persisted.status == "failed"
    assert persisted.error == "initial_draft_timeout"
