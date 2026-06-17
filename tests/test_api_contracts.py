from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.main import app
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    Opportunity,
    OpportunityDomain,
)

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_connector_registry_contains_required_connectors() -> None:
    response = client.get("/api/connectors")
    assert response.status_code == 200
    connector_ids = {item["id"] for item in response.json()}
    assert {
        "google_ads",
        "google_search_console",
        "google_analytics_4",
        "google_merchant_center",
        "google_sheets",
        "ahrefs",
        "localo",
        "wordpress_ekologus",
        "wordpress_sklep",
        "linkedin",
        "facebook",
        "openai_codex",
    }.issubset(connector_ids)


def test_connector_status_does_not_expose_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "gho_supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.get("/api/connectors")
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "gho_supersecretvalue1234567890" not in serialized
    assert "GOOGLE_ADS_DEVELOPER_TOKEN" in serialized


def test_system_status_does_not_expose_access_pack_paths_or_filenames() -> None:
    response = client.get("/api/system/status")
    assert response.status_code == 200
    access_pack = response.json()["access_pack"]
    assert "path" not in access_pack
    assert "credential_files_present" not in access_pack
    assert "manifest_files" not in access_pack


def test_codex_run_redacts_token_like_error_values() -> None:
    response = client.post(
        "/api/codex/runs",
        json={
            "id": "codex_redaction_test",
            "status": "failed",
            "source": "test",
            "error": "failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
        },
    )
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "sk-testsecretvalue1234567890" not in serialized
    assert "[REDACTED]" in serialized


def test_api_is_local_only_by_default() -> None:
    remote_client = TestClient(app, base_url="http://example.com")
    response = remote_client.get("/api/health")
    assert response.status_code == 403


def test_opportunity_requires_source_connector() -> None:
    with pytest.raises(ValidationError):
        Opportunity(
            id="bad",
            type="bad",
            title="Bad",
            domain=OpportunityDomain.google_ads,
            source_connectors=[],
            evidence_ids=["ev_1"],
            human_diagnosis="Missing source connector should fail.",
            recommended_action="Fix schema.",
        )


def test_opportunity_requires_evidence_id() -> None:
    with pytest.raises(ValidationError):
        Opportunity(
            id="bad",
            type="bad",
            title="Bad",
            domain=OpportunityDomain.google_ads,
            source_connectors=["google_ads"],
            evidence_ids=[],
            human_diagnosis="Missing evidence should fail.",
            recommended_action="Fix schema.",
        )


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


def test_action_apply_requires_validation() -> None:
    response = client.post("/api/actions/act_configure_google_ads_access_pack/apply")
    assert response.status_code == 409
    assert "validated before apply" in json.dumps(response.json())


def test_action_validation_rejects_unsupported_payload_action_type() -> None:
    action = ActionObject(
        id="bad_payload",
        title="Bad payload",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_1"],
        human_diagnosis="Invalid payload action should fail.",
        recommended_reason="Unsupported connector action.",
        payload={"action_type": "not_supported_by_google_ads", "connector": "google_ads"},
        validation_status="not_validated",
        created_by="test",
    )

    from wilq.actions.service import validate_action

    result = validate_action(action)
    assert not result.valid
    assert "not supported by connector google_ads" in " ".join(result.errors)


def test_command_center_returns_valid_shape() -> None:
    response = client.get("/api/dashboard/command-center")
    assert response.status_code == 200
    data = response.json()
    assert data["strict_instruction"]
    assert data["connector_summary"]["total"] >= 12
    assert "todays_moves" in data["sections"]


def test_codex_context_pack_contains_no_metric_invention_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CODEX_API_KEY",
        "sk-supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "must not invent metrics" in serialized
    assert "sk-supersecretvalue1234567890" not in serialized
