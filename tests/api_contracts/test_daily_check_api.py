"""API proof that daily-check is an operator-ready typed projection."""

from tests._contract_support.api_client import client


def test_daily_check_returns_traceable_operator_queue() -> None:
    response = client.get("/api/marketing/daily-check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == "ekologus"
    assert payload["status"] in {"ready", "review_ready", "blocked", "degraded"}
    assert payload["checked_connectors"] or payload["skipped_connectors"]
    assert payload["freshness"]["state"] in {"fresh", "stale", "missing", "unknown"}
    assert payload["expert_rules_used"]
    assert payload["source_connectors"]
    assert payload["evidence_ids"]
    assert payload["safe_next_actions"] or payload["blocked_recommendations"]
    for item in [
        *payload["safe_next_actions"],
        *payload["blocked_recommendations"],
        *payload["opportunities"],
    ]:
        assert item["source_connectors"]
        assert item["evidence_ids"]
        assert item["expert_rule_ids"]
        assert item["false_positive_guards"]
        assert item["freshness"]["state"] != "unknown"
        assert item["next_step"]
    ga4_items = [
        item
        for item in [*payload["safe_next_actions"], *payload["blocked_recommendations"]]
        if "ga4_platform_traps_v1" in item["expert_rule_ids"]
    ]
    if ga4_items:
        assert any(
            guard in {"conversion_readiness_ready", "missing_conversion"}
            for item in ga4_items
            for guard in item["false_positive_guards"]
        )
    if payload["do_not_touch"]:
        assert all(item["status"] == "blocked" for item in payload["do_not_touch"])
