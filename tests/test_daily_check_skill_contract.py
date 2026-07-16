from scripts import daily_check_skill_contract
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


def test_daily_check_content_operator_reads_checked_connectors_not_decision_items() -> None:
    payload = {
        "status": "blocked",
        "freshness": {"state": "fresh"},
        "checked_connectors": [
            {"connector_id": "google_search_console"},
            {"connector_id": "wordpress_ekologus"},
        ],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "evidence_ids": ["ev_gsc", "ev_wordpress"],
        "blocked_recommendations": [{"id": "density", "connector_id": None}],
        "safe_next_actions": [],
        "opportunities": [],
    }

    result = compact_daily_check(payload, "wilq-content-operator")

    assert result["source_connectors"] == [
        "google_search_console",
        "wordpress_ekologus",
    ]


def test_daily_check_request_waits_for_explicit_runtime_prewarm(monkeypatch) -> None:
    prewarm = {
        "status": "blocked",
        "blocked_recommendations": [{"id": "daily_check_runtime_prewarm"}],
    }
    ready = {
        "status": "blocked",
        "blocked_recommendations": [],
        "checked_connectors": [{"connector_id": "google_search_console"}],
    }
    responses = iter([prewarm, ready])
    monkeypatch.setattr(
        daily_check_skill_contract,
        "_request_once",
        lambda _api_base: next(responses),
    )
    monkeypatch.setattr(daily_check_skill_contract.time, "sleep", lambda _seconds: None)

    assert daily_check_skill_contract._request("http://127.0.0.1:8000") is ready
