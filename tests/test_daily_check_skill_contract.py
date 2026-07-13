from scripts.daily_check_skill_contract import compact_daily_check


def test_daily_check_skill_contract_preserves_traceability_and_blockers() -> None:
    payload = {
        "status": "blocked",
        "freshness": {"state": "fresh", "last_success_at": "2026-07-12T00:31:59Z"},
        "checked_connectors": [{"connector_id": "google_analytics_4"}],
        "source_connectors": ["google_analytics_4"],
        "evidence_ids": ["ev_ga4"],
        "expert_rules_used": ["ga4_platform_traps_v1"],
        "blocked_recommendations": [
            {
                "id": "daily_check_ga4",
                "status": "blocked",
                "title": "GA4",
                "source_connectors": ["google_analytics_4"],
                "evidence_ids": ["ev_ga4"],
                "expert_rule_ids": ["ga4_platform_traps_v1"],
                "freshness": {"state": "fresh"},
                "next_step": "Sprawdź zdarzenia.",
                "false_positive_guards": ["missing_conversion"],
            }
        ],
        "safe_next_actions": [],
        "opportunities": [],
    }

    result = compact_daily_check(payload, "wilq-ga4-analyst")

    assert result["status"] == "blocked"
    assert result["evidence_ids"] == ["ev_ga4"]
    assert result["expert_rule_ids"] == ["ga4_platform_traps_v1"]
    assert result["items"][0]["false_positive_guards"] == ["missing_conversion"]
