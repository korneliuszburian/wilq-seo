from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from wilq.actions import action_validation
from wilq.actions import payloads as action_payloads
from wilq.actions.payloads import validate_action_payload
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionReviewGate,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)


def _current_disposition_action_for_validation() -> ActionObject:
    from wilq.content.workflow.current_disposition_authority import (
        ContentCurrentDispositionSnapshot,
        build_current_disposition_action,
        current_disposition_snapshot_digest,
    )

    snapshot = {
        "schema_version": "wilq_current_disposition_snapshot_v1",
        "current_work_item_id": "work-item-synthetic",
        "canonical_path": "/synthetic/",
        "public_url": "https://example.invalid/synthetic/",
        "classification_run_id": "classification-synthetic",
        "classification_run_digest": "a" * 64,
        "classification_decision_set_digest": "b" * 64,
        "classification_source_row_digest": "c" * 64,
        "evidence_ids": ["ev_synthetic_current_disposition"],
        "proposed_final_disposition": "keep",
        "context_digest": "0" * 64,
    }
    snapshot["context_digest"] = current_disposition_snapshot_digest(snapshot)
    return build_current_disposition_action(
        ContentCurrentDispositionSnapshot.model_validate(snapshot)
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "exact_local_authority",
        "missing_marker",
        "false_marker",
        "other_connector",
        "other_action_type",
    ],
)
def test_current_disposition_requires_unconfigured_connector_unless_exact_local_authority(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unconfigured_connector = SimpleNamespace(configured=False, supported_actions=())
    for module in (action_validation, action_payloads):
        monkeypatch.setattr(
            module,
            "get_connector_status",
            lambda _connector_id: unconfigured_connector,
        )
    monkeypatch.setattr(
        action_validation,
        "local_state_store",
        lambda: SimpleNamespace(
            save_action_validation_state=lambda **_kwargs: None,
        ),
    )

    action = _current_disposition_action_for_validation()
    if mutation == "missing_marker":
        action.payload.pop("local_authority_only")
    elif mutation == "false_marker":
        action.payload["local_authority_only"] = False
    elif mutation == "other_connector":
        action.connector = "google_ads"
        action.payload["connector"] = "google_ads"
    elif mutation == "other_action_type":
        action.payload["action_type"] = "not_current_disposition_receipt"

    result = action_validation.validate_action(
        action,
        review_gate=lambda _action: ActionReviewGate(),
        status_label=lambda status: status,
    )

    connector_error = f"Łącznik danych {action.connector} nie jest skonfigurowany."
    if mutation == "exact_local_authority":
        assert result.valid
        assert result.errors == []
    else:
        assert not result.valid
        assert connector_error in result.errors


@pytest.mark.parametrize(
    "mutation",
    [
        "exact_local_authority",
        "missing_marker",
        "false_marker",
        "other_connector",
        "unsupported_type",
        "malformed_payload",
    ],
)
def test_delivery_identity_requires_unconfigured_connector_unless_exact_local_authority(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tests.content.test_delivery_identity_authority import _ready_authority

    unconfigured_connector = SimpleNamespace(configured=False, supported_actions=())
    for module in (action_validation, action_payloads):
        monkeypatch.setattr(
            module,
            "get_connector_status",
            lambda _connector_id: unconfigured_connector,
        )
    monkeypatch.setattr(
        action_validation,
        "local_state_store",
        lambda: SimpleNamespace(
            save_action_validation_state=lambda **_kwargs: None,
        ),
    )

    _, prepared_action = _ready_authority(tmp_path)
    assert isinstance(prepared_action, ActionObject)
    action = prepared_action
    if mutation == "missing_marker":
        action.payload.pop("local_authority_only")
    elif mutation == "false_marker":
        action.payload["local_authority_only"] = False
    elif mutation == "other_connector":
        action.connector = "google_ads"
        action.payload["connector"] = "google_ads"
    elif mutation == "unsupported_type":
        action.payload["action_type"] = "unsupported_delivery_identity_action"
    elif mutation == "malformed_payload":
        action.payload["authority_mapping"] = "unsupported_mapping"

    result = action_validation.validate_action(
        action,
        review_gate=lambda _action: ActionReviewGate(),
        status_label=lambda status: status,
    )

    connector_error = f"Łącznik danych {action.connector} nie jest skonfigurowany."
    if mutation == "exact_local_authority":
        assert result.valid
        assert result.errors == []
    elif mutation == "malformed_payload":
        assert not result.valid
        assert connector_error not in result.errors
        assert "Delivery identity authority mapping is invalid." in result.errors
    else:
        assert not result.valid
        assert connector_error in result.errors
        if mutation == "unsupported_type":
            assert "ten typ działania nie jest wspierany dla źródła danych" in " ".join(
                result.errors
            )


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
