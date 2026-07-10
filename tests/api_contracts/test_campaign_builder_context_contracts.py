from __future__ import annotations

import json

from tests._contract_support.api_client import client


def test_codex_context_pack_scopes_campaign_builder_payload() -> None:
    content_response = client.get("/api/content/diagnostics")
    assert content_response.status_code == 200
    content_payload = content_response.json()

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-campaign-builder"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-campaign-builder"
    assert set(data["context_scope"]["source_connectors"]) == {
        "google_ads",
        "google_analytics_4",
        "google_search_console",
    }
    assert "ads_diagnostics" in data
    assert "content_landing_context" in data
    assert "command_center" not in data
    assert "merchant_diagnostics" not in data
    assert "content_diagnostics" not in data
    action_ids = {action["id"] for action in data["active_action_objects"]}
    assert action_ids == {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
    }
    assert data["content_landing_context"]["source_connectors"] == ["google_search_console"]
    assert (
        data["content_landing_context"]["context_pack_compaction"]["full_endpoint"]
        == "/api/content/diagnostics"
    )
    assert (
        data["content_landing_context"]["context_pack_compaction"]["purpose"] == "landing_context"
    )
    if content_payload["query_page_count"] > 0:
        assert data["content_landing_context"]["live_data_available"] is True
        assert data["content_landing_context"]["query_page_candidates"]
        first_candidate = data["content_landing_context"]["query_page_candidates"][0]
        assert first_candidate["page"]
        assert first_candidate["query"]
        assert first_candidate["evidence_ids"]
    if data["content_landing_context"]["live_data_available"]:
        assert data["content_landing_context"]["query_page_candidates"]
        first_candidate = data["content_landing_context"]["query_page_candidates"][0]
        assert first_candidate["page"]
        assert first_candidate["query"]
        assert first_candidate["evidence_ids"]
    assert data["ads_diagnostics"]["context_pack_compaction"]["metric_facts_removed"] is True
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000
