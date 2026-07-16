from __future__ import annotations

from pathlib import Path

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from wilq.actions.action_blockers import ads_target_confirmation_blockers
from wilq.schemas import ActionConfirmRequest


def test_ads_target_confirmation_blockers_require_one_guardrail() -> None:
    assert ads_target_confirmation_blockers(
        ActionConfirmRequest(confirmed_by="operator", notes="brak celu")
    ) == ["target_roas_or_cpa_required"]
    assert ads_target_confirmation_blockers(
        ActionConfirmRequest(
            confirmed_by="operator",
            notes="dwa cele",
            target_roas=2.0,
            target_cpa_micros=1000000,
        )
    ) == ["exactly_one_target_guardrail_allowed"]


def test_action_confirm_requires_prior_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_without_preview.sqlite3"))
    confirm_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Operator tried to confirm without preview.",
            "preview_acknowledged": True,
        },
    )
    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is False
    assert confirmation["status"] == "blocked"
    assert confirmation["status_label"] == "zablokowany"
    assert "dry_run_preview_required" in confirmation["blockers"]
    assert "wymagany wcześniejszy podgląd zmian" in confirmation["blocker_labels"]
    assert "warunek techniczny do sprawdzenia" not in confirmation["blocker_labels"]
    assert confirmation["audit_event"]["event_type"] == "action_confirmation_blocked"
    assert confirmation["audit_event"]["event_type_label"] == "Potwierdzenie zablokowane"
    assert "dry_run_preview_required" not in confirmation["audit_event"]["summary"]
    assert "wymagany wcześniejszy podgląd zmian" in confirmation["audit_event"]["summary"]
    assert confirmation["review_gate"]["apply_allowed"] is False
    assert confirmation["review_gate"]["status_label"]
    audit_response = client.get("/api/audit/events?action_id=act_review_merchant_feed_issues")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "action_confirmation_blocked"


def test_action_confirm_records_preview_confirmation_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_after_preview.sqlite3"))
    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 2},
    )
    assert preview_response.status_code == 200
    confirm_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Operator confirms the generated preview.",
            "preview_acknowledged": True,
        },
    )
    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is True
    assert confirmation["status"] == "confirmed"
    assert confirmation["blockers"] == []
    assert confirmation["blocker_labels"] == []
    assert confirmation["audit_event"]["event_type"] == "action_apply_confirmed"
    assert confirmation["audit_event"]["actor"] == "local_operator"
    assert confirmation["audit_event"]["principal_id"] == "local_operator"
    assert confirmation["audit_event"]["trust_level"] == "local_unverified"
    assert confirmation["audit_event"]["submitted_actor_label"] == "operator_test"
    assert "Potwierdzenie podglądu zapisane" in confirmation["audit_event"]["summary"]
    assert "Audyt podglądu" not in confirmation["audit_event"]["summary"]
    assert "audit_" not in confirmation["audit_event"]["summary"]
    assert ".." not in confirmation["audit_event"]["summary"]
    assert "Audyt podglądu" not in confirmation["review_gate"]["last_confirmation_summary"]
    assert "audit_" not in confirmation["review_gate"]["last_confirmation_summary"]
    assert ".." not in confirmation["review_gate"]["last_confirmation_summary"]
    assert confirmation["review_gate"]["last_confirmation_by"] == "local_operator"
    assert confirmation["review_gate"]["apply_allowed"] is False
    assert "human_confirm_before_apply" not in confirmation["review_gate"]["apply_blockers"]
    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    assert merchant_action["latest_audit_event"]["event_type"] == "action_apply_confirmed"
    assert merchant_action["review_gate"]["last_confirmation_by"] == "local_operator"
    assert merchant_action["review_gate"]["apply_allowed"] is False


def test_action_impact_check_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "impact_without_confirm.sqlite3"))
    response = client.post(
        "/api/actions/act_review_merchant_feed_issues/impact-check",
        json={
            "checked_by": "operator_test",
            "notes": "Impact check before confirmation should block.",
            "pre_window_days": 7,
            "post_window_days": 7,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "blocked"
    assert "action_confirmation_required" in result["blockers"]
    assert "wymagane potwierdzenie podglądu zmian" in result["blocker_labels"]
    assert "warunek techniczny do sprawdzenia" not in result["blocker_labels"]
    assert result["audit_event"]["event_type"] == "action_impact_check_blocked"
    assert "status=" not in result["audit_event"]["summary"]
    assert "google_merchant_center" not in result["audit_event"]["summary"]
    assert "Porównanie sprzed zmiany" in result["audit_event"]["summary"]
    assert "Okno przed zmianą" not in result["audit_event"]["summary"]
    assert result["review_gate"]["last_impact_check_status"] == "blocked"
    assert result["review_gate"]["apply_allowed"] is False
    assert "impact_sanity_check_required" in result["review_gate"]["apply_blockers"]
    assert result["review_gate"]["apply_blocker_summary_label"]


def test_action_impact_check_records_pre_apply_sanity_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "impact_after_confirm.sqlite3"))
    action_id = "act_review_merchant_feed_issues"
    preview_response = client.post(
        f"/api/actions/{action_id}/preview",
        json={"requested_by": "operator_test", "max_items": 2},
    )
    assert preview_response.status_code == 200
    confirm_response = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Operator confirms the generated preview.",
            "preview_acknowledged": True,
        },
    )
    assert confirm_response.status_code == 200

    response = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={
            "checked_by": "operator_test",
            "notes": "Operator checks pre/post sanity before apply.",
            "pre_window_days": 7,
            "post_window_days": 14,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "checked"
    assert "status=" not in result["audit_event"]["summary"]
    assert "google_merchant_center" not in result["audit_event"]["summary"]
    assert "Porównanie sprzed zmiany: 7 dni" in result["audit_event"]["summary"]
    assert "Porównanie po zmianie: 14 dni" in result["audit_event"]["summary"]
    assert "Okno przed zmianą" not in result["audit_event"]["summary"]
    assert "Okno po zmianie" not in result["audit_event"]["summary"]
    assert result["pre_window_days"] == 7
    assert result["post_window_days"] == 14
    assert result["metric_fact_count"] > 0
    assert "google_merchant_center" in result["source_connectors"]
    assert result["source_connector_labels"] == ["Merchant Center"]
    assert (
        "dowód" in result["evidence_summary_label"]
        or "dowody" in result["evidence_summary_label"]
    )
    assert result["blocker_labels"] == []
    assert result["audit_event"]["event_type"] == "action_impact_check_completed"
    assert result["review_gate"]["last_impact_check_status"] == "checked"
    assert result["review_gate"]["last_impact_checked_by"] == "local_operator"
    assert result["review_gate"]["apply_allowed"] is False
    assert "impact_sanity_check_required" not in result["review_gate"]["apply_blockers"]
    assert result["review_gate"]["apply_blocker_summary_label"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id[action_id]
    assert merchant_action["latest_audit_event"]["event_type"] == "action_impact_check_completed"
    assert merchant_action["review_gate"]["last_impact_check_status"] == "checked"
    assert merchant_action["review_gate"]["apply_allowed"] is False

    action_response = client.get(f"/api/actions/{action_id}")
    assert action_response.status_code == 200
    action_payload = action_response.json()
    assert "Porównanie sprzed zmiany" in action_payload["review_gate"]["last_impact_check_summary"]
    assert "Okno przed zmianą" not in action_payload["review_gate"]["last_impact_check_summary"]
