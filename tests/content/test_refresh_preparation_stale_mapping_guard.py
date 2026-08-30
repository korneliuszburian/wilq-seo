from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import wilq.content.planning.planning_generation_queue as planning_queue
from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.test_classified_refresh_generation_integration import (
    BDO_SERVICE_CARD_ID,
    BDO_WORK_ITEM_ID,
    _app_client,
    _authority,
    _authorize,
    _refresh_run,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.workflow.store.store import content_workflow_store


def test_authorized_existing_state_preserves_false_regeneration_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ContentPlanningProposalRequest(
        service_card_id=BDO_SERVICE_CARD_ID,
        expected_planning_input_digest="a" * 64,
        requested_by="wilku",
        refresh_preparation_authorization_id="content_refresh_preparation_authorization_test",
        expected_refresh_preparation_authorization_digest="b" * 64,
    )
    existing = SimpleNamespace(
        proposal_id="content_planning_proposal_legacy",
        planning_digest="c" * 64,
        planning_input_digest="a" * 64,
    )
    stale_mapping = SimpleNamespace(
        work_item_id=BDO_WORK_ITEM_ID,
        service_card_id=BDO_SERVICE_CARD_ID,
        planning_input_digest="a" * 64,
        proposal=existing,
        status="stale",
        blockers=[SimpleNamespace(label="Mapa istniejącej strony wymaga odświeżenia")],
    )
    store = SimpleNamespace(for_input=lambda *_args: existing)
    monkeypatch.setattr(
        planning_queue,
        "read_content_planning_proposal",
        lambda **_kwargs: stale_mapping,
    )

    _snapshot, effective, response = planning_queue.existing_planning_generation_state(
        work_item_id=BDO_WORK_ITEM_ID,
        request=request,
        snapshot_loader=lambda _work_item_id: SimpleNamespace(),
        store=cast(Any, store),
    )

    assert response is stale_mapping
    assert effective.regenerate_stale_mapping is False
    assert effective.regenerate_after_review is False


def test_authorized_stale_mapping_returns_reconciliation_without_model_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    client = _app_client(_authority(store))
    authorization = _authorize(client)
    captured_flags: list[bool] = []
    stale_response = ContentPlanningProposalResponse(
        status="stale",
        work_item_id=BDO_WORK_ITEM_ID,
        service_card_id=BDO_SERVICE_CARD_ID,
        blockers=[
            ContentPlanningProposalBlocker(
                code="stale_input",
                label="Mapa istniejącej strony wymaga odświeżenia",
                reason="Fixture wymusza stale mapping.",
                next_step="Nie uruchamiaj modelu.",
            )
        ],
        safe_next_step="Nie uruchamiaj modelu.",
    )

    def stale_state(**kwargs: object):
        captured_flags.append(bool(kwargs["allow_automatic_stale_mapping_regeneration"]))
        return None, kwargs["request"], stale_response

    monkeypatch.setattr(planning_queue, "existing_planning_generation_state", stale_state)
    ready = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": ready["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["blockers"][0]["code"] == (
        "refresh_preparation_proposal_binding_mismatch"
    )
    assert captured_flags == [False]
    assert runtime.calls == 0
