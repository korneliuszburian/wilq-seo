from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from apps.api.wilq_api.routers.content_planning_proposals import (
    _legacy_unbound_refresh_reconciliation_status,
)
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
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationClassificationBinding,
)
from wilq.content.workflow.store.store import content_workflow_store


def test_legacy_unbound_same_input_refresh_plan_requires_reconciliation_not_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    client = _app_client(_authority(store))
    initial_status = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )
    assert initial_status.status_code == 200
    initial = cast(dict[str, Any], initial_status.json())
    legacy_response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": initial["content_kind"],
            "service_card_id": initial.get("service_card_id"),
            "expected_planning_input_digest": initial["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    legacy = _wait_for_plan(client, legacy_response)
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["status"] in {"created", "ready", "idempotent"}, legacy.json().get(
        "blockers", legacy.json()
    )
    assert runtime.calls == 1
    store.record_production_classification(_refresh_run())
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


def test_blocked_editorial_subject_still_does_not_reconcile_legacy_service() -> None:
    legacy = SimpleNamespace(
        refresh_preparation_binding=None,
        proposal=None,
        service_card_id=BDO_SERVICE_CARD_ID,
        planning_input_digest="a" * 64,
    )
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id="classification",
        classification_run_digest="a" * 64,
        decision_set_digest="b" * 64,
        source_packet_row_digest="c" * 64,
        current_work_item_id=BDO_WORK_ITEM_ID,
        canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
        public_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
    )
    service_mismatch = ContentRefreshPreparationBlocker(
        code="refresh_preparation_authorization_service_mismatch",
        label="Editorial nie przyjmuje usługi",
        reason="Bieżący subject jest editorial.",
        next_step="Użyj editorial subject.",
    )
    blocked = ContentRefreshPreparationBlocked(
        status="blocked",
        work_item_id=BDO_WORK_ITEM_ID,
        classification=classification,
        blockers=[service_mismatch],
        safe_next_step=service_mismatch.next_step,
    )
    authority = SimpleNamespace(
        preview=lambda _work_item_id, *, service_card_id: (
            SimpleNamespace() if service_card_id is None else blocked
        )
    )

    assert (
        _legacy_unbound_refresh_reconciliation_status(
            store=SimpleNamespace(
                latest_generation_response=lambda _work_item_id: legacy
            ),
            work_item_id=BDO_WORK_ITEM_ID,
            authority=authority,
            inventory_binding_loader=lambda _work_item_id: SimpleNamespace(
                content_kind="editorial"
            ),
        )
        is None
    )


def test_legacy_service_plan_does_not_shadow_current_editorial_subject() -> None:
    legacy = SimpleNamespace(
        refresh_preparation_binding=None,
        proposal=None,
        service_card_id=BDO_SERVICE_CARD_ID,
        planning_input_digest="a" * 64,
    )
    store = SimpleNamespace(latest_generation_response=lambda _work_item_id: legacy)
    authority = SimpleNamespace(
        preview=lambda _work_item_id, *, service_card_id: SimpleNamespace(
            content_kind="editorial" if service_card_id is None else None
        )
    )

    assert (
        _legacy_unbound_refresh_reconciliation_status(
            store=store,
            work_item_id=BDO_WORK_ITEM_ID,
            authority=authority,
            inventory_binding_loader=lambda _work_item_id: SimpleNamespace(
                content_kind="editorial"
            ),
        )
        is None
    )
