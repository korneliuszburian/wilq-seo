from __future__ import annotations

import json
from pathlib import Path

import pytest

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
