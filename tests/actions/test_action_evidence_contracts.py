import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import wilq.actions.service as action_service
from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.action_safety_factory import synthetic_apply_ready_action
from tests._contract_support.api_client import client
from tests._contract_support.env import GOOGLE_ADS_TEST_ENV
from wilq.actions.service import apply_action
from wilq.schemas import (
    ActionApplyRequest,
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)


def test_google_ads_oauth_repair_action_is_explicit_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(action_service, "_google_ads_live_data_available", lambda: False)
    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    assert "act_configure_google_ads_env" in {
        action["id"] for action in actions_response.json()
    }
    response = client.get("/api/actions/act_configure_google_ads_env")
    assert response.status_code == 200
    action = response.json()
    serialized = json.dumps(action)

    assert action["title"] == "Odnow dostęp Google Ads"
    assert action["payload"]["action_type"] == "repair_google_ads_oauth"
    assert action["payload"]["oauth_scope"] == "https://www.googleapis.com/auth/adwords"
    assert "token odświeżania" in action["human_diagnosis"]
    assert "oauth_error=invalid_grant" not in action["human_diagnosis"]
    assert "credentials" not in action["human_diagnosis"]
    assert "refresh token" not in action["human_diagnosis"]
    assert "$WILQ_GOOGLE_ADS_CLIENT_SECRET_FILE" in action["payload"]["oauth_client_json_path"]
    assert "GOOGLE_ADS_REFRESH_TOKEN" in action["payload"]["required_env"]
    assert "/home/" not in serialized
    assert "marketing@rekurencja.com" not in serialized
    assert "client_secret_504856024095" not in serialized
    assert "ya29." not in serialized
    assert "refresh-token" not in serialized.lower()
    assert "client-secret-test" not in serialized


def test_apply_ready_action_blocks_without_mutation_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    action = synthetic_apply_ready_action()
    result = apply_action(action, ActionApplyRequest(confirm=True, confirmed_by="operator_test"))
    assert result.applied is False
    assert result.status == "blocked"
    assert result.audit_event.event_type == "apply_blocked"
    assert result.mutation_audit.status == "blocked"
    assert result.mutation_audit.mutation_attempted is False
    assert result.mutation_audit.mutation_adapter is None
    assert "vendor_mutation_adapter_required" in action.review_gate.apply_blockers
    assert action.review_gate.apply_allowed is False


def test_apply_ready_action_blocks_when_adapter_executor_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    monkeypatch.setattr(
        action_service,
        "_supported_mutation_adapter",
        lambda _action: "synthetic_google_ads_adapter",
    )
    action = synthetic_apply_ready_action("act_synthetic_apply_ready_with_adapter")
    result = action_service.apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="operator_test"),
    )
    assert result.applied is False
    assert result.status == "blocked"
    assert result.audit_event.event_type == "apply_blocked"
    assert result.mutation_audit.status == "blocked"
    assert result.mutation_audit.mutation_attempted is False
    assert result.mutation_audit.mutation_adapter == "synthetic_google_ads_adapter"
    assert result.adapter_result is None
    assert "synthetic_google_ads_adapter nie ma implementacji wykonania" in str(
        result.model_dump(mode="json")
    )


def test_action_apply_requires_validation(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "audit_state.sqlite3"))
    response = client.post("/api/actions/act_configure_google_ads_env/apply")
    assert response.status_code == 409
    body = response.json()["detail"]
    serialized = json.dumps(body, ensure_ascii=False)
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert body["mutation_audit"]["mutation_adapter"] is None
    assert "Wymagane jest jawne potwierdzenie zapisu zmian" in serialized
    assert "Przed zapisem zmian" in serialized
    audit_response = client.get("/api/audit/events?action_id=act_configure_google_ads_env")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "apply_confirmation_missing"
    mutation_response = client.get(
        "/api/action-mutation-audits?action_id=act_configure_google_ads_env"
    )
    assert mutation_response.status_code == 200
    mutation_audits = mutation_response.json()
    assert len(mutation_audits) == 1
    assert mutation_audits[0]["status"] == "blocked"
    assert mutation_audits[0]["mutation_attempted"] is False
    assert mutation_audits[0]["audit_event_id"] == body["audit_event"]["id"]
    action_response = client.get("/api/actions/act_configure_google_ads_env")
    review_gate = action_response.json()["review_gate"]
    assert review_gate["last_mutation_audit_status"] == "blocked"
    assert review_gate["last_mutation_audit_status_label"] == "zablokowany"
    assert review_gate["last_mutation_attempted"] is False
    assert review_gate["last_mutation_adapter"] is None
    assert review_gate["last_mutation_audit_trace_label"] == "ślad bezpieczeństwa zapisany"


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


def test_action_apply_requires_explicit_confirmation_actor(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_audit_state.sqlite3"))
    response = client.post(
        "/api/actions/act_configure_google_ads_env/apply", json={"confirm": True}
    )
    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "blocked"
    assert "Brakuje osoby potwierdzającej zapis zmian" in str(body)
    assert body["audit_event"]["event_type"] == "apply_confirmation_missing"
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["actor"] == "wilq_api"


def test_action_apply_confirmed_prepare_action_still_blocks_with_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirmed_prepare_audit.sqlite3"))
    validate_response = client.post("/api/actions/act_configure_google_ads_env/validate")
    assert validate_response.status_code == 200
    response = client.post(
        "/api/actions/act_configure_google_ads_env/apply",
        json={"confirm": True, "confirmed_by": "operator_test"},
    )
    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "blocked"
    assert body["audit_event"]["event_type"] == "apply_blocked"
    assert body["audit_event"]["actor"] == "operator_test"
    assert body["mutation_audit"]["actor"] == "operator_test"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert "Akcja nie ma trybu zapisu zmian w zewnętrznym systemie" in str(body)
def test_metric_backed_prepare_actions_are_evidence_grounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/actions")
    assert response.status_code == 200
    actions = {action["id"]: action for action in response.json()}

    expected_actions = {
        "act_review_merchant_feed_issues": {
            "connector": "google_merchant_center",
            "action_type": "merchant_feed_issue",
            "metric_names": {"issue_product_count"},
        },
        "act_review_ga4_tracking_quality": {
            "connector": "google_analytics_4",
            "action_type": "ga4_tracking_gap",
            "metric_names": {"active_users", "sessions"},
        },
        "act_prepare_content_refresh_queue": {
            "connector": "wordpress_ekologus",
            "action_type": "wordpress_content_refresh",
            "metric_names": {"content_object_count", "clicks", "domain_rating"},
        },
        "act_prepare_wordpress_draft_handoff": {
            "connector": "wordpress_ekologus",
            "action_type": "wordpress_draft_handoff",
            "metric_names": {"content_object_count", "clicks", "domain_rating"},
        },
        "act_prepare_linkedin_social_drafts": {
            "connector": "linkedin",
            "action_type": "linkedin_post_candidate",
            "metric_names": {"clicks", "impressions", "issue_product_count"},
        },
        "act_prepare_facebook_social_drafts": {
            "connector": "facebook",
            "action_type": "facebook_post_candidate",
            "metric_names": {"clicks", "impressions", "issue_product_count"},
        },
    }

    for action_id, expected in expected_actions.items():
        action = actions[action_id]
        assert action["mode"] == "prepare"
        assert action["status"] == "needs_validation"
        assert action["connector"] == expected["connector"]
        assert action["payload"]["action_type"] == expected["action_type"]
        assert action["payload"]["mode"] == "prepare_only"
        assert action["payload"]["destructive"] is False
        assert action["review_gate"]["status"] == "pending_validation"
        assert action["review_gate"]["confirmation_required"] is True
        assert action["review_gate"]["apply_allowed"] is False
        assert "action_validation_required" in action["review_gate"]["apply_blockers"]
        assert "payload_apply_allowed_false" in action["review_gate"]["apply_blockers"]
        assert "wymagane sprawdzenie w WILQ" in action["review_gate"]["apply_blocker_labels"]
        assert "podgląd zmian nie pozwala na zapis" in action["review_gate"]["apply_blocker_labels"]
        assert action["review_gate"]["apply_blocker_summary_label"]
        assert action["evidence_ids"]
        for preview_key in (
            "payload_preview",
            "budget_payload_preview",
            "content_brief_preview",
            "wordpress_draft_payload_preview",
        ):
            preview_items = action["payload"].get(preview_key)
            if isinstance(preview_items, dict):
                preview_items = [preview_items]
            if not isinstance(preview_items, list):
                continue
            for preview in preview_items:
                if not isinstance(preview, dict) or not preview.get("required_validation"):
                    continue
                assert preview.get("required_validation_labels"), (
                    action_id,
                    preview_key,
                    preview.get("required_validation"),
                )
                assert not any(
                    "_" in label
                    for label in preview["required_validation_labels"]
                    if isinstance(label, str)
                )
                assert (
                    "warunek techniczny do sprawdzenia" not in preview["required_validation_labels"]
                )
                assert "brak opisu w kontrakcie WILQ" not in preview["required_validation_labels"]
        if action_id.startswith("act_prepare_") and "social_drafts" in action_id:
            assert action["domain"] == "social"
            assert action["payload"]["source_inputs"]
            assert "candidate_inputs" not in action["payload"]
            preview_cards = action["preview_cards"]
            assert preview_cards
            assert {card["kind"] for card in preview_cards} == {"social_draft_input_review"}
            preview_text = json.dumps(
                [
                    {
                        "title_label": card["title_label"],
                        "subtitle_label": card["subtitle_label"],
                        "status_label": card["status_label"],
                        "rows": card["rows"],
                    }
                    for card in preview_cards
                ],
                ensure_ascii=False,
            )
            assert "Google Search Console" in preview_text
            assert "Merchant Center" in preview_text
            assert "kliknięcia" in preview_text
            assert "zgłoszenia problemów" in preview_text
            assert "google_search_console" not in preview_text
            assert "google_merchant_center" not in preview_text
            assert "clicks" not in preview_text
            assert "issue_product_count" not in preview_text
            assert (
                "no_publishing_without_connector_credentials"
                in action["payload"]["draft_constraints"]
            )
            assert (
                "require_social_history_duplicate_review" in action["payload"]["draft_constraints"]
            )
            assert "brak powtórzeń historycznych postów" in action["payload"]["blocked_claims"]
            assert {"ev_connector_linkedin_status", "ev_connector_facebook_status"}.issubset(
                set(action["evidence_ids"])
            )
        if action_id == "act_prepare_content_refresh_queue":
            content_payload = action["payload"]
            assert content_payload["preview_contract"] == "content_brief_preview_v1"
            content_cards = action["preview_cards"]
            assert content_cards
            assert "content_brief_review" in {card["kind"] for card in content_cards}
            if content_payload.get("wordpress_draft_payload_preview"):
                assert "wordpress_draft_payload_review" in {card["kind"] for card in content_cards}
            content_card_text = json.dumps(
                [
                    {
                        "title_label": card["title_label"],
                        "subtitle_label": card["subtitle_label"],
                        "status_label": card["status_label"],
                        "rows": card["rows"],
                    }
                    for card in content_cards
                ],
                ensure_ascii=False,
            )
            assert "Plan treści do sprawdzenia" in content_card_text
            if content_payload.get("wordpress_draft_payload_preview"):
                assert "Szkic WordPress do sprawdzenia" in content_card_text
            assert "URL publiczny" in content_card_text
            assert "content_brief_" not in content_card_text
            assert "content_brief_preview_v1" not in content_card_text
            assert "wordpress_draft_payload_preview_v1" not in content_card_text
            assert "target_site" not in content_card_text
            assert "mapping_review" not in content_card_text
            assert content_payload["apply_allowed"] is False
            assert content_payload["api_mutation_ready"] is False
            assert "target_site_mapping_review_contract" not in content_payload
            url_contract = content_payload["content_url_review_contract"]
            assert url_contract["contract"] == "content_url_preflight_review_v1"
            assert url_contract["scope"] == "review_only"
            assert "confirm_final_canonical_url" in url_contract["allowed_outcomes"]
            assert "potwierdź finalny URL kanoniczny" in url_contract["allowed_outcome_labels"]
            assert "docelowy URL publiczny" in url_contract["required_field_labels"]
            assert "wordpress_publish" in url_contract["blocked_outputs"]
            assert "publikacja WordPress" in url_contract["blocked_output_labels"]
            assert "obietnica braku duplikacji" in url_contract["blocked_output_labels"]
            assert "content_url_preflight_review" in content_payload["required_validation"]
            assert "target_site_mapping_review" not in content_payload["required_validation"]
            assert "content_brief_preview" in content_payload
            assert len(content_payload["content_brief_preview"]) >= 2
            gsc_preview = next(
                item
                for item in content_payload["content_brief_preview"]
                if item["source_type"] == "gsc_query_page"
            )
            assert gsc_preview["mode"] == "refresh"
            assert gsc_preview["wordpress_inventory_match"] == "present"
            assert gsc_preview["metric_snapshot"]["clicks"] == 12
            assert gsc_preview["metric_snapshot"]["impressions"] == 120
            assert gsc_preview["apply_allowed"] is False
            assert "gwarancja pozycji" in gsc_preview["blocked_claims"]
            assert "human_confirm_before_wordpress_write" in gsc_preview["required_validation"]
            ahrefs_preview = next(
                item
                for item in content_payload["content_brief_preview"]
                if item["source_type"] == "ahrefs_gap_review"
            )
            serialized_content_preview = json.dumps(
                content_payload["content_brief_preview"],
                ensure_ascii=False,
            )
        if action_id == "act_prepare_wordpress_draft_handoff":
            wordpress_draft_payload = action["payload"]
            assert wordpress_draft_payload["preview_contract"] == (
                "wordpress_draft_handoff_preview_v1"
            )
            handoff_cards = action["preview_cards"]
            assert handoff_cards
            assert {card["kind"] for card in handoff_cards} == {"wordpress_draft_handoff_review"}
            handoff_card_text = json.dumps(
                [
                    {
                        "title_label": card["title_label"],
                        "subtitle_label": card["subtitle_label"],
                        "status_label": card["status_label"],
                        "rows": card["rows"],
                    }
                    for card in handoff_cards
                ],
                ensure_ascii=False,
            )
            assert "Szkic WordPress do sprawdzenia" in handoff_card_text
            assert "URL publiczny" in handoff_card_text
            assert "URL kanoniczny" in handoff_card_text
            assert "Szkic WordPress" in handoff_card_text
            assert "candidate_id" not in handoff_card_text
            assert "content_brief_" not in handoff_card_text
            assert "wordpress_draft_handoff_preview_v1" not in handoff_card_text
            assert "wordpress_draft_handoff_review" not in handoff_card_text
            assert wordpress_draft_payload["depends_on_action_id"] == (
                "act_prepare_content_refresh_queue"
            )
            assert (
                "content_draft_readiness_review_v1"
                in wordpress_draft_payload["required_input_contracts"]
            )
            assert (
                "post_publication_measurement_plan_v1"
                in wordpress_draft_payload["required_input_contracts"]
            )
            assert wordpress_draft_payload["apply_allowed"] is False
            assert wordpress_draft_payload["api_mutation_ready"] is False
            assert (
                "wordpress_draft_preview_review" in wordpress_draft_payload["required_validation"]
            )
            assert (
                "wordpress_draft_payload_preview"
                not in wordpress_draft_payload["required_validation"]
            )
            assert "wordpress_publish" in wordpress_draft_payload["blocked_claims"]
            assert len(wordpress_draft_payload["payload_preview"]) >= 1
            first_wordpress_draft_preview = wordpress_draft_payload["payload_preview"][0]
            assert first_wordpress_draft_preview["preview_contract"] == (
                "wordpress_draft_handoff_preview_v1"
            )
            assert first_wordpress_draft_preview["operation_type"] == (
                "wordpress_draft_handoff_review"
            )
            assert first_wordpress_draft_preview["apply_allowed"] is False
            assert first_wordpress_draft_preview["api_mutation_ready"] is False
            assert first_wordpress_draft_preview["final_canonical_url"]
            assert "selected_target_url" not in first_wordpress_draft_preview
            assert "mapping_review_status" not in first_wordpress_draft_preview
            assert not any(
                key.startswith("target_site_")
                or key.startswith("mapping_review_")
                or key.startswith("transition_candidate")
                for key in first_wordpress_draft_preview
            )
            wordpress_draft_measurement_plan = first_wordpress_draft_preview[
                "post_publication_measurement_plan"
            ]
            assert (
                wordpress_draft_measurement_plan["contract_version"]
                == "post_publication_measurement_plan_v1"
            )
            assert wordpress_draft_measurement_plan["scope"] == "blocked_preview_only"
            assert (
                "wordpress_ekologus"
                in wordpress_draft_measurement_plan["required_source_connectors"]
            )
            assert "obietnica wzrostu leadów" in wordpress_draft_measurement_plan["blocked_outputs"]
            assert first_wordpress_draft_preview["canonical_gate_status_label"]
            assert first_wordpress_draft_preview["duplicate_gate_status_label"]
            assert (
                "stan przekazania do WordPress: zablokowany do przejścia kontroli szkicu"
                in first_wordpress_draft_preview["wordpress_draft_handoff_summary"]
            )
            assert "status:" not in " ".join(
                [
                    *first_wordpress_draft_preview["wordpress_draft_handoff_summary"],
                    *first_wordpress_draft_preview["post_publication_measurement_summary"],
                ]
            )
            assert (
                first_wordpress_draft_preview["required_next_action_label"]
                == "zapis szkicu WordPress"
            )
            assert (
                "potwierdzenie publicznego URL-a"
                in first_wordpress_draft_preview["required_validation_labels"]
            )
            assert "publikacja WordPress" in first_wordpress_draft_preview["blocked_claim_labels"]
            assert "blokuje: obietnica wzrostu pozycji" in (
                " ".join(first_wordpress_draft_preview["post_publication_measurement_summary"])
            )
            assert ahrefs_preview["mode"] == "review"
            assert ahrefs_preview["topic"] == "audyt środowiskowy"
            assert ahrefs_preview["gsc_demand"] == "unknown"
            assert ahrefs_preview["apply_allowed"] is False
            assert "gsc_demand_check" in ahrefs_preview["required_validation"]
            assert ahrefs_preview["evidence_ids"] == ["ev_refresh_refresh_ahrefs_action_test"]
            assert "cuk.pl" not in serialized_content_preview
        metric_names = {str(metric["name"]) for metric in action["metrics"]}
        assert metric_names.issuperset(expected["metric_names"])
        assert "prepare" in json.dumps(action["payload"])
    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert "active_products=12" not in serialized
    assert "disapproved_products=3" not in serialized
    assert "active_users=20" not in serialized
    assert "sessions=30" not in serialized
