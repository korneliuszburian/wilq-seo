import json

import pytest
from pydantic import ValidationError

import wilq.actions.service as action_service
from tests._contract_support.action_safety_factory import synthetic_apply_ready_action
from tests._contract_support.api_client import client
from tests._contract_support.env import GOOGLE_ADS_TEST_ENV
from wilq.actions.service import apply_action
from wilq.schemas import (
    ActionApplyRequest,
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)


def test_google_ads_oauth_repair_action_is_explicit_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(action_service, "_google_ads_live_data_available", lambda: False)
    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    assert "act_configure_google_ads_env" in {
        action["id"] for action in actions_response.json()
    }
    response = client.get("/api/actions/act_configure_google_ads_env")
    assert response.status_code == 200
    action = response.json()
    serialized = json.dumps(action)

    assert action["title"] == "Odnow dostęp Google Ads"
    assert action["payload"]["action_type"] == "repair_google_ads_oauth"
    assert action["payload"]["oauth_scope"] == "https://www.googleapis.com/auth/adwords"
    assert "token odświeżania" in action["human_diagnosis"]
    assert "oauth_error=invalid_grant" not in action["human_diagnosis"]
    assert "credentials" not in action["human_diagnosis"]
    assert "refresh token" not in action["human_diagnosis"]
    assert "$WILQ_GOOGLE_ADS_CLIENT_SECRET_FILE" in action["payload"]["oauth_client_json_path"]
    assert "GOOGLE_ADS_REFRESH_TOKEN" in action["payload"]["required_env"]
    assert "/home/" not in serialized
    assert "marketing@rekurencja.com" not in serialized
    assert "client_secret_504856024095" not in serialized
    assert "ya29." not in serialized
    assert "refresh-token" not in serialized.lower()
    assert "client-secret-test" not in serialized


def test_apply_ready_action_blocks_without_mutation_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    action = synthetic_apply_ready_action()
    result = apply_action(action, ActionApplyRequest(confirm=True, confirmed_by="operator_test"))
    assert result.applied is False
    assert result.status == "blocked"
    assert result.audit_event.event_type == "apply_blocked"
    assert result.mutation_audit.status == "blocked"
    assert result.mutation_audit.mutation_attempted is False
    assert result.mutation_audit.mutation_adapter is None
    assert "vendor_mutation_adapter_required" in action.review_gate.apply_blockers
    assert action.review_gate.apply_allowed is False


def test_apply_ready_action_blocks_when_adapter_executor_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    monkeypatch.setattr(
        action_service,
        "_supported_mutation_adapter",
        lambda _action: "synthetic_google_ads_adapter",
    )
    action = synthetic_apply_ready_action("act_synthetic_apply_ready_with_adapter")
    result = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="operator_test"),
    )
    assert result.applied is False
    assert result.status == "blocked"
    assert result.audit_event.event_type == "apply_blocked"
    assert result.mutation_audit.status == "blocked"
    assert result.mutation_audit.mutation_attempted is False
    assert result.mutation_audit.mutation_adapter == "synthetic_google_ads_adapter"
    assert result.adapter_result is None
    assert "synthetic_google_ads_adapter nie ma implementacji wykonania" in str(
        result.model_dump(mode="json")
    )


def test_action_apply_requires_validation(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "audit_state.sqlite3"))
    response = client.post("/api/actions/act_configure_google_ads_env/apply")
    assert response.status_code == 409
    body = response.json()["detail"]
    serialized = json.dumps(body, ensure_ascii=False)
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert body["mutation_audit"]["mutation_adapter"] is None
    assert "Wymagane jest jawne potwierdzenie zapisu zmian" in serialized
    assert "Przed zapisem zmian" in serialized
    audit_response = client.get("/api/audit/events?action_id=act_configure_google_ads_env")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "apply_confirmation_missing"
    mutation_response = client.get(
        "/api/action-mutation-audits?action_id=act_configure_google_ads_env"
    )
    assert mutation_response.status_code == 200
    mutation_audits = mutation_response.json()
    assert len(mutation_audits) == 1
    assert mutation_audits[0]["status"] == "blocked"
    assert mutation_audits[0]["mutation_attempted"] is False
    assert mutation_audits[0]["audit_event_id"] == body["audit_event"]["id"]
    action_response = client.get("/api/actions/act_configure_google_ads_env")
    review_gate = action_response.json()["review_gate"]
    assert review_gate["last_mutation_audit_status"] == "blocked"
    assert review_gate["last_mutation_audit_status_label"] == "zablokowany"
    assert review_gate["last_mutation_attempted"] is False
    assert review_gate["last_mutation_adapter"] is None
    assert review_gate["last_mutation_audit_trace_label"] == "ślad bezpieczeństwa zapisany"


def test_action_requires_evidence_id() -> None:
    with pytest.raises(ValidationError):
        ActionObject(
            id="bad",
            title="Bad action",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.apply,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=[],
            human_diagnosis="No evidence.",
            recommended_reason="Should fail.",
            payload={"action_type": "bad"},
            validation_status="not_validated",
            created_by="test",
        )


def test_action_apply_requires_explicit_confirmation_actor(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_audit_state.sqlite3"))
    response = client.post(
        "/api/actions/act_configure_google_ads_env/apply", json={"confirm": True}
    )
    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "blocked"
    assert "Brakuje osoby potwierdzającej zapis zmian" in str(body)
    assert body["audit_event"]["event_type"] == "apply_confirmation_missing"
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["actor"] == "wilq_api"


def test_action_apply_confirmed_prepare_action_still_blocks_with_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirmed_prepare_audit.sqlite3"))
    validate_response = client.post("/api/actions/act_configure_google_ads_env/validate")
    assert validate_response.status_code == 200
    response = client.post(
        "/api/actions/act_configure_google_ads_env/apply",
        json={"confirm": True, "confirmed_by": "operator_test"},
    )
    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "blocked"
    assert body["audit_event"]["event_type"] == "apply_blocked"
    assert body["audit_event"]["actor"] == "operator_test"
    assert body["mutation_audit"]["actor"] == "operator_test"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert "Akcja nie ma trybu zapisu zmian w zewnętrznym systemie" in str(body)
