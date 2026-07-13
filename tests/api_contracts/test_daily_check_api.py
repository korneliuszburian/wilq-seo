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
    dossier = payload["workspace_dossier"]
    assert dossier["id"] == "workspace_dossier:ekologus"
    assert dossier["workspace_id"] == "ekologus"
    assert dossier["exclusions"]
    assert dossier["known_false_positives"]
    assert dossier["open_blockers"]
    assert all("payload" not in entry["summary"].lower() for entry in dossier["open_blockers"])
    assert any(
        entry["id"] == "blocker:content_candidate_density"
        for entry in dossier["open_blockers"]
    )
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
    content_items = [
        item
        for item in [*payload["safe_next_actions"], *payload["blocked_recommendations"]]
        if "gsc_platform_traps_v1" in item["expert_rule_ids"]
    ]
    if content_items:
        assert any(
            guard in {"date_window_ready", "date_window"}
            for item in content_items
            for guard in item["false_positive_guards"]
        )
        content_queue_items = [
            item
            for item in content_items
            if item["id"] == "daily_check_decision_prepare_content_refresh_queue"
        ]
        if content_queue_items:
            assert any(
                guard in {"multi_source_ready", "multi_source_required"}
                for item in content_queue_items
                for guard in item["false_positive_guards"]
            )
            assert any(
                guard in {"measurement_baseline_ready", "missing_measurement_baseline"}
                for item in content_queue_items
                for guard in item["false_positive_guards"]
            )
            assert all(
                item["evidence_ids"] for item in content_queue_items
            )
            queue_response = client.get("/api/content/work-items/queue")
            assert queue_response.status_code == 200
            queue = queue_response.json()
            if any(
                blocker["code"] == "not_enough_actionable_candidates"
                for blocker in queue["blockers"]
            ):
                progress = (
                    f'{queue["actionable_candidate_count"]} z '
                    f'{queue["minimum_actionable_candidate_count"]} tematów gotowych do pracy'
                )
                assert all(
                    "Pełna kolejka pozostaje zablokowana" in item["summary"]
                    and progress in item["summary"]
                    and progress in item["next_step"]
                    for item in content_queue_items
                )
    if payload["do_not_touch"]:
        assert all(item["status"] == "blocked" for item in payload["do_not_touch"])


def test_daily_check_recommendation_log_is_redacted_and_read_back() -> None:
    record = {
        "id": "recommendation_test_daily_check_content",
        "workspace_id": "ekologus",
        "recommendation_id": "daily_check_decision_prepare_content_refresh_queue",
        "status": "made",
        "reason": "Kolejka wymaga review źródeł.",
        "follow_up": "Odśwież źródła i wróć do kolejki.",
        "evidence_ids": ["ev_test_daily_check"],
        "source_connectors": ["google_search_console"],
        "expert_rule_ids": ["gsc_platform_traps_v1"],
        "action_ids": [],
        "recorded_by": "operator_test",
    }
    response = client.post("/api/marketing/daily-check/recommendations", json=record)
    assert response.status_code == 200
    assert response.json()["redacted"] is True

    daily_check = client.get("/api/marketing/daily-check")
    assert daily_check.status_code == 200
    history = daily_check.json()["recommendation_history"]
    saved = next(item for item in history if item["id"] == record["id"])
    assert saved["evidence_ids"] == ["ev_test_daily_check"]
    assert "payload" not in saved["reason"].lower()
