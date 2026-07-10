from __future__ import annotations

import json

import pytest

from tests._contract_support.api_client import client


def test_evidence_registry_exposes_connector_status_without_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "gho_supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.get("/api/evidence")
    assert response.status_code == 200
    evidence = response.json()
    evidence_ids = {item["id"] for item in evidence}
    assert "ev_connector_google_ads_status" in evidence_ids
    google_ads_evidence = next(
        item for item in evidence if item["id"] == "ev_connector_google_ads_status"
    )
    assert google_ads_evidence["title_label"] == "Dowód z Google Ads"
    assert google_ads_evidence["source_connector_label"] == "Google Ads"
    assert google_ads_evidence["source_type_label"] == "status źródła danych"
    assert google_ads_evidence["trace_summary_label"]
    serialized = json.dumps(evidence)
    assert "gho_supersecretvalue1234567890" not in serialized
