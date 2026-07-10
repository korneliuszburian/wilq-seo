from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from tests._contract_support.assertions import (
    assert_preview_items_are_operator_view_models,
    preview_card_row_values,
)


def test_action_preview_generates_dry_run_audit_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "preview_state.sqlite3"))

    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 3},
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] in {"preview_ready", "blocked"}
    assert preview["status_label"] in {"podgląd gotowy", "zablokowany"}
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["audit_event"]["event_type"] == "action_preview_generated"
    assert preview["audit_event"]["event_type_label"] == "Podgląd zmian wygenerowany"
    assert preview["audit_event"]["actor"] == "operator_test"
    assert preview["preview_items_total"] >= len(preview["preview_items"])
    assert len(preview["preview_items"]) <= 3
    assert preview["preview_cards"]
    assert_preview_items_are_operator_view_models(preview["preview_items"])
    assert preview["review_gate"]["apply_allowed"] is False
    assert preview["review_gate"]["status_label"]
    assert len(preview["blocker_labels"]) == len(preview["blockers"])
    assert "warunek techniczny do sprawdzenia" not in preview["blocker_labels"]
    assert "status=" not in preview["audit_event"]["summary"]
    assert "zapis zmian=" not in preview["audit_event"]["summary"]
    assert "zapis zmian pozostaje zablokowany" in preview["audit_event"]["summary"]

    audit_response = client.get("/api/audit/events?action_id=act_review_merchant_feed_issues")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "action_preview_generated"


def test_content_action_preview_exposes_review_only_brief_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_preview_state.sqlite3"))
    preview_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/preview",
        json={"requested_by": "operator_test", "max_items": 4},
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["preview_contract"] == "content_brief_preview_v1"
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["status"] == "blocked"
    assert preview["preview_items_total"] >= 2
    assert preview["preview_cards"]
    assert_preview_items_are_operator_view_models(preview["preview_items"])
    serialized_preview_items = json.dumps(preview["preview_items"], ensure_ascii=False)
    assert "source_type" not in serialized_preview_items
    assert "preview_contract" not in serialized_preview_items
    assert "apply_allowed" not in serialized_preview_items
    assert any(
        "odśwież istniejącą treść" in preview_card_row_values(card, "Tryb")
        for card in preview["preview_cards"]
    )
    assert any(
        "kontrola prawna" in ", ".join(preview_card_row_values(card, "Blokady publikacji"))
        for card in preview["preview_cards"]
    )
    assert "action_mode_prepare_only" in preview["blockers"]
