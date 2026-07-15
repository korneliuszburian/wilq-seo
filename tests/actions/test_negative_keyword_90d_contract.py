from __future__ import annotations

from pathlib import Path

import pytest

from tests._contract_support.ads_review_seed import seed_google_ads_live_review_metric_facts
from tests._contract_support.api_client import client
from wilq.actions.google_ads.negative_keywords import (
    negative_keyword_action_from_metric_facts,
    validate_negative_keyword_payload,
)
from wilq.schemas import MetricFact


def _search_term_fact(
    name: str,
    value: int | float,
    evidence_id: str,
    *,
    campaign_id: str = "101",
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="search_term_safety_90d" if name.startswith("search_term_90d_") else "last_30_days",
        source_connector="google_ads",
        evidence_id=evidence_id,
        dimensions={
            "search_term": "odpady cena",
            "campaign_id": campaign_id,
            "campaign_name": "Brand Search",
            "ad_group_id": "202",
            "ad_group_name": "BDO",
        },
    )


def test_negative_keyword_public_contract_blocks_preview_without_matched_90d_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    diagnostics_response = client.get("/api/ads/diagnostics")
    actions_response = client.get("/api/actions")

    assert diagnostics_response.status_code == 200
    assert actions_response.status_code == 200
    contract = diagnostics_response.json()["negative_keywords_read_contract"]
    candidate = contract["candidates"][0]
    assert candidate["safety_status"] == "needs_90_day_review"
    assert candidate["payload_preview"] is None
    assert contract["payload_preview"] == []
    assert contract["action_ids"] == []
    assert "90_day_safety_check" in contract["missing_read_contracts"]
    assert "act_prepare_negative_keyword_review_queue" not in {
        action["id"] for action in actions_response.json()
    }


def test_negative_keyword_action_requires_exact_matched_90d_evidence(
) -> None:
    current_facts = [
        _search_term_fact("search_term_clicks", 6, "ev_30d"),
        _search_term_fact("search_term_conversions", 0, "ev_30d"),
    ]
    mismatched_90d = _search_term_fact(
        "search_term_90d_clicks",
        10,
        "ev_90d_wrong_campaign",
        campaign_id="999",
    )
    assert negative_keyword_action_from_metric_facts([*current_facts, mismatched_90d]) is None

    matched_90d = _search_term_fact("search_term_90d_clicks", 10, "ev_90d")
    action = negative_keyword_action_from_metric_facts([*current_facts, matched_90d])

    assert action is not None
    preview = action.payload["payload_preview"][0]
    assert preview["safety_evidence_ids"] == ["ev_90d"]
    assert set(preview["safety_evidence_ids"]).issubset(preview["evidence_ids"])
    assert action.payload["apply_allowed"] is False
    assert preview["apply_allowed"] is False
    assert validate_negative_keyword_payload(action.payload) == []

    preview["safety_evidence_ids"] = []
    errors = validate_negative_keyword_payload(action.payload)
    assert any("pasującego dowodu z ostatnich 90 dni" in error for error in errors)
