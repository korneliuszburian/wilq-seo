from __future__ import annotations

from types import SimpleNamespace

from apps.api.wilq_api.routers import content_initial_draft
from apps.api.wilq_api.routers.content_initial_draft import _can_queue_initial_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)


def _request() -> ContentInitialDraftRequest:
    return ContentInitialDraftRequest(
        expected_proposal_id="proposal-1",
        expected_planning_digest="a" * 64,
        expected_planning_input_digest="b" * 64,
        requested_by="wilku",
    )


def _snapshot(
    *, latest_revision: object | None, context_current: bool = True
) -> SimpleNamespace:
    return SimpleNamespace(
        planning_workspace=SimpleNamespace(
            scope_current=True,
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
