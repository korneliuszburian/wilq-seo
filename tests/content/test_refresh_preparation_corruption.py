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
)
from wilq.content.workflow.store.store import content_workflow_store


@pytest.mark.parametrize("corruption", ["payload", "scalar"])
def test_corrupt_refresh_authorization_is_typed_stale_without_model_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    corruption: str,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    client = _app_client(_authority(store))
    authorization = _authorize(client)
    ready = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()
    with cast(Any, store)._connect() as connection:
        if corruption == "payload":
            connection.execute(
                """
                UPDATE content_refresh_preparation_authorizations
                SET payload_json = '{}'
                WHERE authorization_id = ?
                """,
                (authorization["authorization_id"],),
            )
        else:
            connection.execute(
                """
                UPDATE content_refresh_preparation_authorizations
                SET authorized_by = 'inna_osoba'
                WHERE authorization_id = ?
                """,
                (authorization["authorization_id"],),
            )

    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    )
    planning = client.post(
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

    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "blocked"
    assert preview.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert planning.status_code == 409, planning.text
    assert planning.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert runtime.calls == 0
