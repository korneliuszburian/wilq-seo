from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import apps.api.wilq_api.routers.content_planning_proposals as planning_router
from apps.api.wilq_api.routers.content_initial_draft_refresh import (
    read_authorized_refresh_initial_draft_status,
)

_WORK_ITEM_ID = "content_work_item_refresh"
_SERVICE_CARD_ID = "ekologus_service_operat_wodnoprawny"
_INPUT_DIGEST = "a" * 64


@pytest.mark.parametrize(
    "classification_state",
    [
        "refresh_stale",
        "refresh_selection",
        "refresh_blocked",
        "alias",
        "reuse",
        "write",
        "blocked",
    ],
)
def test_legacy_unbound_planning_get_never_falls_through_for_classified_states(
    monkeypatch: pytest.MonkeyPatch,
    classification_state: str,
) -> None:
    proposal = SimpleNamespace(
        service_card_id=_SERVICE_CARD_ID,
        planning_input_digest=_INPUT_DIGEST,
        refresh_preparation_binding=None,
    )
    store = SimpleNamespace(
        latest_generation_response=lambda _work_item_id: None,
        latest=lambda _work_item_id: proposal,
    )
    preview_calls: list[tuple[str, str | None]] = []
    snapshot_calls: list[str] = []

    class Authority:
        def preview(self, work_item_id: str, *, service_card_id: str | None) -> object:
            preview_calls.append((work_item_id, service_card_id))
            return SimpleNamespace(status=classification_state)

    monkeypatch.setattr(planning_router, "content_planning_proposal_store", lambda: store)
    monkeypatch.setattr(
        planning_router,
        "content_workflow_store",
        lambda: (_ for _ in ()).throw(AssertionError("workspace must not load")),
    )

    response = planning_router._get_content_work_item_planning_proposal_status(
        work_item_id=_WORK_ITEM_ID,
        snapshot_loader=lambda work_item_id: snapshot_calls.append(work_item_id),
        refresh_authority=cast(Any, Authority()),
    )

    assert response.status == "blocked"
    assert response.proposal is None
    assert response.blockers[0].code == "refresh_preparation_proposal_binding_mismatch"
    assert preview_calls == [(_WORK_ITEM_ID, _SERVICE_CARD_ID)]
    assert snapshot_calls == []


@pytest.mark.parametrize("legacy_kind", ["proposal", "revision"])
def test_initial_draft_get_blocks_unbound_legacy_refresh_artifacts_without_legacy_reader(
    legacy_kind: str,
) -> None:
    proposal = (
        SimpleNamespace(
            generation_status="codex_generated",
            proposal_id="content_planning_proposal_legacy",
            planning_input_digest=_INPUT_DIGEST,
            refresh_preparation_binding=None,
        )
        if legacy_kind == "proposal"
        else None
    )
    revision = (
        None
        if legacy_kind == "proposal"
        else SimpleNamespace(refresh_preparation_binding=None)
    )
    calls = {"authority": 0, "legacy": 0}

    class ProposalStore:
        def latest(self, _work_item_id: str) -> object | None:
            return proposal

    class WorkflowStore:
        def load_draft_revision_state(self, _work_item_id: str) -> object:
            return SimpleNamespace(latest_revision=revision)

    class Authority:
        def resolve_initial_draft(self, *_args: object, **_kwargs: object) -> object:
            calls["authority"] += 1
            raise AssertionError("unbound legacy artifact must not resolve authority")

        def initial_draft_block_response(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("unbound legacy artifact must not resolve authority")

    response = read_authorized_refresh_initial_draft_status(
        work_item_id=_WORK_ITEM_ID,
        refresh_authority=cast(Any, Authority()),
        proposal_store=cast(Any, ProposalStore()),
        workflow_store=cast(Any, WorkflowStore()),
        legacy_status_reader=lambda *_args: calls.__setitem__("legacy", calls["legacy"] + 1),
    )

    assert response is not None
    assert response.status == "blocked"
    assert response.blockers[0].code == "refresh_preparation_proposal_binding_mismatch"
    assert calls == {"authority": 0, "legacy": 0}
