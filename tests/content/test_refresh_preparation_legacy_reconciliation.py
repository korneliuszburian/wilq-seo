from __future__ import annotations

from typing import Any, cast

import pytest

from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.test_classified_refresh_generation_integration import (
    BDO_SERVICE_CARD_ID,
    BDO_WORK_ITEM_ID,
    _app_client,
    _authority,
    _authorize,
    _refresh_run,
    _wait_for_plan,
)
from wilq.content.workflow.store.store import content_workflow_store


def test_legacy_unbound_same_input_refresh_plan_requires_reconciliation_not_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    main_client, runtime = configure_planning_harness(monkeypatch, tmp_path)
    initial_status = main_client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )
    assert initial_status.status_code == 200
    initial = cast(dict[str, Any], initial_status.json())
    legacy_response = main_client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": initial["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    legacy = _wait_for_plan(main_client, legacy_response)
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["status"] in {"created", "ready", "idempotent"}
    assert runtime.calls == 1

    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    client = _app_client(_authority(store))
    get_response = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals")
    ready = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    )
    assert ready.status_code == 200, ready.text
    authorization = _authorize(client)
    repeat = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": ready.json()["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )

    assert get_response.status_code == 200, get_response.text
    get_body = get_response.json()
    assert get_body["status"] == "blocked"
    assert get_body["proposal"] is None
    assert get_body["blockers"][0]["code"] == "refresh_preparation_proposal_binding_mismatch"
    assert "Nie ponawiaj" in get_body["blockers"][0]["reason"]
    assert repeat.status_code == 409, repeat.text
    assert repeat.json()["status"] == "blocked"
    assert repeat.json()["blockers"][0]["code"] == (
        "refresh_preparation_proposal_binding_mismatch"
    )
    assert "Nie ponawiaj" in repeat.json()["blockers"][0]["reason"]
    assert runtime.calls == 1
