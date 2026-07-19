from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.wilq_api.context_compaction import connector_readiness_for_context
from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client


def test_codex_context_pack_contains_no_metric_invention_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CODEX_API_KEY",
        "sk-supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert "Codex nie może podawać metryk" in serialized
    assert "Brak dowodu w WILQ" in serialized
    assert "must not invent metrics" not in serialized
    assert "No evidence ID" not in serialized
    assert "sk-supersecretvalue1234567890" not in serialized


def test_connector_consumer_readiness_fails_closed_for_missing_source() -> None:
    payload = connector_readiness_for_context(
        [
            {
                "id": "example_missing",
                "label": "Przykładowe źródło",
                "status": "missing_credentials",
                "configured": False,
                "missing_credentials": ["EXAMPLE_TOKEN"],
                "freshness": {"state": "missing"},
                "capabilities": {"read": True},
            }
        ]
    )

    assert payload["contract"] == "connector_consumer_readiness_v1"
    assert payload["blocked"] == 1
    assert payload["blocked_connector_ids"] == ["example_missing"]
    row = payload["rows"][0]
    assert row["status"] == "blocked"
    assert row["blocker_code"] == "missing_credentials"
    assert "zablokowane" in row["effect"]


def test_connector_consumer_readiness_excludes_runtime_connector_from_blockers() -> None:
    payload = connector_readiness_for_context(
        [
            {
                "id": "openai_codex",
                "label": "Codex runtime",
                "status": "configured",
                "configured": True,
                "product_scope": "runtime",
                "active_for_daily_work": False,
                "freshness": {"state": "unknown"},
                "capabilities": {"read": True},
            }
        ]
    )

    assert payload["blocked"] == 0
    assert payload["ready"] == 0
    assert payload["not_applicable"] == 1
    assert payload["rows"][0]["status"] == "not_applicable"


def test_connector_consumer_readiness_excludes_disabled_optional_connector() -> None:
    payload = connector_readiness_for_context(
        [
            {
                "id": "google_sheets",
                "label": "Google Sheets",
                "status": "disabled",
                "configured": False,
                "product_scope": "optional_disabled",
                "active_for_daily_work": False,
                "freshness": {"state": "missing"},
                "capabilities": {"read": True},
            }
        ]
    )

    assert payload["blocked"] == 0
    assert payload["not_applicable"] == 1
    assert payload["rows"][0]["status"] == "not_applicable"


def test_daily_context_pack_uses_daily_decisions_for_action_summaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})

    assert response.status_code == 200
    payload = response.json()
    assert len(json.dumps(payload, ensure_ascii=False).encode()) < 180_000
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    ga4_action = actions_by_id["act_review_ga4_tracking_quality"]
    assert merchant_action["decision_id"]
    assert merchant_action["decision_id"] != "[REDACTED]"
    assert merchant_action["decision_id"].startswith("decision_")
    assert merchant_action["metric_tiles"]
    assert ga4_action["decision_id"]
    assert ga4_action["decision_id"] != "[REDACTED]"
    assert ga4_action["decision_id"].startswith("decision_")
    assert ga4_action["metric_tiles"]
    assert all("payload_keys" not in action for action in payload["active_action_objects"])
    serialized = json.dumps(payload, ensure_ascii=False)
    serialized_actions = json.dumps(payload["active_action_objects"], ensure_ascii=False)
    assert "payload_preview" not in serialized_actions
    assert "payload_apply_allowed_false" not in serialized_actions
    assert "active_products=12" not in serialized
    assert "disapproved_products=3" not in serialized
    assert "active_users=20" not in serialized
    assert "sessions=30" not in serialized


def test_daily_context_pack_preserves_action_review_gates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})

    assert response.status_code == 200
    payload = response.json()
    actions = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions["act_review_merchant_feed_issues"]
    assert merchant_action["review_gate"]["status"] == "pending_validation"
    assert merchant_action["review_gate"]["apply_allowed"] is False
    assert "apply_blockers" not in merchant_action["review_gate"]
    assert merchant_action["review_gate"]["apply_blockers_total"] >= 2
    assert "wymagane sprawdzenie w WILQ" in merchant_action["review_gate"]["apply_blocker_labels"]
    assert (
        "podgląd zmian nie pozwala na zapis"
        in merchant_action["review_gate"]["apply_blocker_labels"]
    )
    assert "payload_apply_allowed_false" not in json.dumps(
        merchant_action["review_gate"], ensure_ascii=False
    )
    assert "last_mutation_adapter" not in merchant_action["review_gate"]


def test_daily_context_pack_preserves_action_preview_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "preview_context_state.sqlite3"))
    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 2},
    )
    assert preview_response.status_code == 200

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )

    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    latest_audit_event = merchant_action["latest_audit_event"]
    assert latest_audit_event["event_type"] == "action_preview_generated"
    assert (
        "Szczegóły techniczne są dostępne w szczegółach akcji WILQ"
        in latest_audit_event["summary"]
    )
    assert "details_keys" not in latest_audit_event
    assert merchant_action["review_gate"]["apply_allowed"] is False


def test_daily_context_pack_preserves_human_review_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "human_review_context_state.sqlite3"))
    review_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/review",
        json={
            "outcome": "needs_changes",
            "reviewed_by": "operator_test",
            "notes": "Brakuje podglądu zmian do zapisu.",
            "checked_items": ["prepare_feed_fix_preview"],
            "blockers": ["payload_apply_allowed_false"],
        },
    )
    assert review_response.status_code == 200

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )

    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    assert merchant_action["review_gate"]["last_review_outcome"] == "needs_changes"
    assert merchant_action["review_gate"]["last_reviewed_by"] == "local_operator"
    assert merchant_action["review_gate"]["apply_allowed"] is False
    serialized = json.dumps(merchant_action, ensure_ascii=False)
    assert "[REDACTED]" not in serialized
    assert "Brakuje podglądu zmian" not in serialized
    assert merchant_action["latest_audit_event"]["event_type"] == "human_review_needs_changes"
    assert (
        "Szczegóły techniczne są dostępne w szczegółach akcji WILQ"
        in merchant_action["latest_audit_event"]["summary"]
    )
