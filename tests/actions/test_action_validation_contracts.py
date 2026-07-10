from __future__ import annotations

from pathlib import Path

import pytest

from tests._contract_support.api_client import client


def test_validated_ready_action_copy_does_not_claim_human_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "action_validation_state.sqlite3"))

    validate_response = client.post("/api/actions/act_review_merchant_feed_issues/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    action_response = client.get("/api/actions/act_review_merchant_feed_issues")
    assert action_response.status_code == 200
    action = action_response.json()

    assert action["status"] == "ready"
    assert action["status_label"] == "gotowa do sprawdzenia"
    assert action["validation_status"] == "valid"
    assert action["validation_status_label"] == "kontrola WILQ poprawna"
    assert "sprawdzone w WILQ" not in action["validation_status_label"]
    assert action["review_gate"]["status"] == "validated_prepare_only"
    assert action["review_gate"]["status_label"] == "kontrola WILQ poprawna"
    assert "zgody operatora" in action["review_gate"]["summary"]
    assert "sprawdzone w WILQ" not in action["review_gate"]["summary"]
