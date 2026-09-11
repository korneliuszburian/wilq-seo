from __future__ import annotations

import pytest

from tests.content.test_refresh_preparation_authority import (
    DECISION_DIGEST,
    INPUT_DIGEST,
    ROW_DIGEST,
    RUN_DIGEST,
    SERVICE_CARD_ID,
    WORK_ITEM_ID,
    _authority,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorizationRequest,
)


@pytest.mark.parametrize(
    ("planning_input_updates", "expected_code"),
    [
        ({"work_item_id": "content_work_item_foreign"}, "refresh_preparation_authorization_stale"),
        (
            {"final_canonical_url": "https://www.ekologus.pl/inny-adres/"},
            "refresh_preparation_authorization_stale",
        ),
        (
            {"confirmed_service_card_id": "ekologus_service_foreign"},
            "refresh_preparation_authorization_service_mismatch",
        ),
        ({"planning_input_digest": "e" * 64}, "refresh_preparation_authorization_input_mismatch"),
    ],
)
def test_authorization_rejects_a_mismatched_rebuilt_input_without_writing(
    monkeypatch: pytest.MonkeyPatch,
    planning_input_updates: dict[str, object],
    expected_code: str,
) -> None:
    authority, store, _calls, _snapshot = _authority(
        monkeypatch,
        planning_input_updates=planning_input_updates,
    )
    request = ContentRefreshPreparationAuthorizationRequest(
        expected_production_classification_run_digest=RUN_DIGEST,
        expected_production_classification_decision_set_digest=DECISION_DIGEST,
        expected_production_classification_source_packet_row_digest=ROW_DIGEST,
        expected_planning_input_digest=INPUT_DIGEST,
        service_card_id=SERVICE_CARD_ID,
        authorized_by="wilku",
        acknowledged_classification_blocker_codes=["lineage_needs_review"],
    )

    response = authority.authorize(WORK_ITEM_ID, request)

    assert response.status == "conflict"
    assert response.blockers[0].code == expected_code
    assert store.record_calls == 0
    assert store.authorizations == {}
