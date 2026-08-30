from __future__ import annotations

from types import SimpleNamespace

import pytest

from wilq.content.drafts import initial_draft_queue
from wilq.content.drafts.initial_draft_persistence import InitialDraftPrePersistenceGuardError
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)

WORK_ITEM_ID = "content_work_item_refresh"
SERVICE_CARD_ID = "ekologus_service_operat_wodnoprawny"
INPUT_DIGEST = "d" * 64


def test_planning_worker_checks_refresh_authority_before_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ContentPlanningProposalRequest(
        service_card_id=SERVICE_CARD_ID,
        expected_planning_input_digest=INPUT_DIGEST,
        requested_by="wilku",
    )
    blocked = ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=WORK_ITEM_ID,
        service_card_id=SERVICE_CARD_ID,
        blockers=[
            ContentPlanningProposalBlocker(
                code="refresh_preparation_authorization_missing",
                label="Brakuje autoryzacji",
                reason="Brak exact receipt.",
                next_step="Autoryzuj refresh.",
            )
        ],
        safe_next_step="Autoryzuj refresh.",
    )
    terminal: list[object] = []
    model_called = False

    class Store:
        def save_terminal_response(self, response: object, **_kwargs: object) -> str:
            terminal.append(response)
            return "saved"

    class Claims:
        def finish(self, **_kwargs: object) -> None:
            return None

    def model_bomb(**_kwargs: object) -> object:
        nonlocal model_called
        model_called = True
        raise AssertionError("worker reached model after refresh authority blocked")

    monkeypatch.setattr(
        planning_generation_queue, "content_planning_proposal_store", lambda: Store()
    )
    monkeypatch.setattr(planning_generation_queue, "generate_content_planning_proposal", model_bomb)

    result = planning_generation_queue.run_queued_planning_generation(
        WORK_ITEM_ID,
        request,
        lambda _work_item_id: (_ for _ in ()).throw(AssertionError("snapshot should not load")),
        Claims(),  # type: ignore[arg-type]
        "claim-owner",
        1,
        generation_guard=lambda: blocked,
    )

    assert result is blocked
    assert terminal == [blocked]
    assert model_called is False


def test_initial_draft_worker_and_append_guard_stop_before_model_or_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ContentInitialDraftRequest(
        expected_proposal_id="content_planning_proposal_test",
        expected_planning_digest="e" * 64,
        expected_planning_input_digest=INPUT_DIGEST,
        requested_by="wilku",
    )
    blocked = ContentInitialDraftResponse(
        status="conflict",
        work_item_id=WORK_ITEM_ID,
        proposal_id=request.expected_proposal_id,
        blockers=[
            ContentInitialDraftBlocker(
                code="refresh_preparation_authorization_stale",
                label="Autoryzacja nieaktualna",
                reason="Źródła zmieniły się.",
                next_step="Odśwież przygotowanie.",
            )
        ],
        safe_next_step="Odśwież przygotowanie.",
    )
    terminal: list[object] = []
    model_called = False
    base_append_called = False

    def model_bomb(**_kwargs: object) -> object:
        nonlocal model_called
        model_called = True
        raise AssertionError("initial worker reached model after refresh authority blocked")

    monkeypatch.setattr(initial_draft_queue, "generate_initial_full_draft", model_bomb)
    monkeypatch.setattr(
        initial_draft_queue,
        "_persist_terminal_preflight_run",
        lambda **kwargs: terminal.append(kwargs["result"]),
    )
    initial_draft_queue.run_queued_initial_draft(
        WORK_ITEM_ID,
        request,
        SimpleNamespace(),
        "run-id",
        lambda _work_item_id: SimpleNamespace(),
        pre_generation_guard=lambda: blocked,
    )

    class BaseStore:
        def append_draft_revision(self, *_args: object, **_kwargs: object) -> object:
            nonlocal base_append_called
            base_append_called = True
            raise AssertionError("append should not execute after refresh guard")

    guarded_store = initial_draft_queue._ContextCheckedWorkflowStore(  # noqa: SLF001
        BaseStore(),  # type: ignore[arg-type]
        lambda _work_item_id: SimpleNamespace(),
        WORK_ITEM_ID,
        pre_persistence_guard=lambda: blocked,
    )

    with pytest.raises(InitialDraftPrePersistenceGuardError):
        guarded_store.append_draft_revision(SimpleNamespace())  # type: ignore[arg-type]
    assert terminal == [blocked]
    assert model_called is False
    assert base_append_called is False
