from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from tests._contract_support.api_client import client


def test_content_review_details_keep_allowed_fields_and_ignore_unknown_values() -> None:
    from wilq.actions.content_review_details import (
        content_url_review_details,
        draft_readiness_review_details,
    )

    checked_items = [
        "candidate: candidate_1",
        "reviewed_url: https://www.ekologus.pl/usluga",
        "draft_readiness_outcome: ready_for_review",
        "unknown: should_be_ignored",
        "review_notes: operator checked canonical URL",
    ]

    assert content_url_review_details(checked_items) == {
        "candidate": "candidate_1",
        "reviewed_url": "https://www.ekologus.pl/usluga",
        "review_notes": "operator checked canonical URL",
    }
    assert draft_readiness_review_details(checked_items) == {
        "candidate": "candidate_1",
        "draft_readiness_outcome": "ready_for_review",
    }


def test_review_outcome_projection_keeps_latest_human_event() -> None:
    from wilq.actions.review_gate import (
        latest_human_review_event,
        review_outcome_from_event,
        review_outcome_label,
    )
    from wilq.schemas import AuditEvent

    events = [
        AuditEvent(
            id="audit_old",
            event_type="human_review_needs_changes",
            actor="operator",
            created_at=datetime.fromisoformat("2026-07-12T04:00:00+00:00"),
            summary="old",
        ),
        AuditEvent(
            id="audit_new",
            event_type="human_review_approved_for_prepare",
            actor="operator",
            created_at=datetime.fromisoformat("2026-07-12T05:00:00+00:00"),
            summary="new",
        ),
        AuditEvent(
            id="audit_preview",
            event_type="action_preview_generated",
            actor="system",
            created_at=datetime.fromisoformat("2026-07-12T06:00:00+00:00"),
            summary="preview",
        ),
    ]

    latest = latest_human_review_event(events)
    assert latest is not None and latest.id == "audit_new"
    assert review_outcome_from_event(latest) == "approved_for_prepare"
    assert review_outcome_label("approved_for_prepare") == "zatwierdzone do dalszego przygotowania"


def test_action_review_records_human_outcome_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "human_review_state.sqlite3"))
    review_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": "Sprawdzono kolejkę pliku produktowego; można kontynuować przygotowanie.",
            "checked_items": ["group_issue_reasons", "prepare_feed_fix_preview"],
            "blockers": ["payload_apply_allowed_false"],
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["status"] == "recorded"
    assert review_payload["status_label"] == "zapisane"
    assert review_payload["audit_event"]["event_type"] == "human_review_approved_for_prepare"
    assert review_payload["audit_event"]["event_type_label"] == "Przegląd operatora zapisany"
    assert review_payload["audit_event"]["actor"] == "operator_test"
    assert review_payload["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert (
        review_payload["review_gate"]["last_review_outcome_label"]
        == "zatwierdzone do dalszego przygotowania"
    )
    assert review_payload["review_gate"]["status_label"]
    assert review_payload["review_gate"]["apply_allowed"] is False
    assert "zmian w zewnętrznych systemach" in review_payload["audit_event"]["summary"]
    audit_response = client.get("/api/audit/events?action_id=act_review_merchant_feed_issues")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "human_review_approved_for_prepare"
    action_response = client.get("/api/actions/act_review_merchant_feed_issues")
    assert action_response.status_code == 200
    action = action_response.json()
    assert action["connector_label"] == "Google Merchant Center"
    assert action["mode_label"] == "przygotowanie"
    assert action["status_label"]
    assert action["risk_label"]
    assert action["validation_status_label"]
    assert action["audit_events"][0]["event_type"] == "human_review_approved_for_prepare"
    assert action["audit_events"][0]["event_type_label"] == "Przegląd operatora zapisany"
    assert action["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert (
        action["review_gate"]["last_review_outcome_label"]
        == "zatwierdzone do dalszego przygotowania"
    )
    assert action["review_gate"]["last_reviewed_by"] == "operator_test"
    assert action["review_gate"]["apply_allowed"] is False
