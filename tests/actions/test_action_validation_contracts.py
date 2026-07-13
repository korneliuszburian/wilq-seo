from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from wilq.actions.payloads import validate_action_payload
from wilq.schemas import ActionMode, ActionObject, ActionRisk, ActionStatus, OpportunityDomain


@pytest.mark.parametrize(
    ("connector_id", "payload"),
    [
        (
            "google_ads",
            {"action_type": "google_ads_recommendation_review", "connector": "google_ads"},
        ),
        ("google_ads", {"action_type": "campaign_change_review", "connector": "google_ads"}),
        (
            "google_ads",
            {"action_type": "negative_keyword_candidate", "connector": "google_ads"},
        ),
        (
            "google_ads",
            {
                "action_type": "custom_segment_candidate",
                "connector": "google_ads",
                "invented_terms": True,
            },
        ),
        (
            "google_ads",
            {
                "action_type": "google_ads_change_history_impact_review",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {
                "action_type": "google_ads_search_term_ngram_review",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {
                "action_type": "google_ads_demand_gen_readiness_review",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {
                "action_type": "configure_google_ads_keyword_planner_access",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {"action_type": "configure_ads_business_context", "connector": "google_ads"},
        ),
        (
            "google_ads",
            {"action_type": "confirm_ads_target_guardrails", "connector": "google_ads"},
        ),
        (
            "google_ads",
            {"action_type": "record_ads_strategy_review", "connector": "google_ads"},
        ),
        (
            "google_analytics_4",
            {"action_type": "ga4_tracking_gap", "connector": "google_analytics_4"},
        ),
        ("localo", {"action_type": "local_visibility_task", "connector": "localo"}),
    ],
)
def test_action_payload_validation_errors_are_operator_readable(
    connector_id: str,
    payload: dict[str, Any],
) -> None:
    errors = validate_action_payload(connector_id, payload)
    assert errors
    joined = " ".join(errors)
    forbidden_fragments = [
        "payload",
        "requires",
        "must ",
        "connector=",
        "mode=",
        "apply_allowed",
        "api_mutation_ready",
        "destructive=false",
        "payload_preview",
        "evidence IDs",
        "required_validation",
        "source_connectors",
        "missing_read_contracts",
        "not supported",
        "is only valid",
        "non-destructive",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in joined


def test_metric_backed_prepare_actions_validate_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    for action_id in (
        "act_review_merchant_feed_issues",
        "act_review_ga4_tracking_quality",
        "act_prepare_content_refresh_queue",
        "act_prepare_linkedin_social_drafts",
        "act_prepare_facebook_social_drafts",
    ):
        validate_response = client.post(f"/api/actions/{action_id}/validate")
        assert validate_response.status_code == 200
        validation = validate_response.json()
        assert validation["valid"] is True
        assert validation["errors"] == []

        apply_response = client.post(f"/api/actions/{action_id}/apply")
        assert apply_response.status_code == 409
        apply_detail = apply_response.json()["detail"]
        assert apply_detail["status"] == "blocked"
        assert apply_detail["applied"] is False
        assert apply_detail["audit_event"]["event_type"] == "apply_confirmation_missing"


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
    assert "ten typ działania nie jest wspierany" in " ".join(result.errors)


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
