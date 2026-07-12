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


def test_audit_event_labels_keep_operator_copy_and_safe_fallback() -> None:
    from wilq.actions.audit_store import audit_event_label

    assert audit_event_label("action_preview_generated") == "Podgląd zmian wygenerowany"
    assert audit_event_label("unknown_event") == "Zdarzenie audytu"


def test_operator_payload_labels_keep_nested_action_copy_polish() -> None:
    from wilq.actions.operator_labels import payload_with_operator_labels

    payload = {
        "status": "blocked_apply",
        "required_validation": ["human_review_before_apply"],
        "recommendation_type": "TARGET_ROAS_OPT_IN",
        "preview": [{"post_status": "draft", "match_type": "EXACT", "level": "ad_group"}],
    }

    enriched = payload_with_operator_labels(payload)

    assert enriched["status_label"] == "zapis zmian zablokowany"
    assert enriched["required_validation_labels"] == ["sprawdzenie przez człowieka przed zapisem"]
    assert enriched["recommendation_type_label"] == "strategia zwrotu z reklam"
    assert enriched["preview"][0]["post_status_label"] == "szkic"
    assert enriched["preview"][0]["match_type_label"] == "dopasowanie ścisłe"
    assert enriched["preview"][0]["level_label"] == "grupa reklam"


def test_review_gate_operator_projection_keeps_mutation_safety_labels() -> None:
    from wilq.actions.operator_labels import review_gate_with_operator_labels
    from wilq.schemas import ActionReviewGate

    gate = ActionReviewGate(
        status="blocked_apply",
        apply_blockers=["action_validation_required"],
        last_review_outcome="approved_for_prepare",
        last_impact_check_status="blocked",
        last_mutation_audit_status="blocked",
        last_mutation_attempted=False,
        last_mutation_adapter_reached=False,
        last_external_write_attempted=False,
        last_mutation_adapter="wordpress_draft",
        last_mutation_audit_event_id="audit_1",
    )

    projected = review_gate_with_operator_labels(
        gate,
        review_outcome_label=lambda value: f"review:{value}",
        blocker_count_label=lambda values: f"blokady:{len(values)}",
    )

    assert projected.status_label == "zapis zmian zablokowany"
    assert projected.apply_blocker_summary_label == "blokady:1"
    assert projected.last_review_outcome_label == "review:approved_for_prepare"
    assert projected.last_impact_check_status_label == "zablokowany"
    assert projected.last_mutation_attempted_label == "nie próbowano zapisu w systemie zewnętrznym"
    assert projected.last_mutation_audit_trace_label == "ślad bezpieczeństwa zapisany"


def test_review_gate_builders_keep_required_checks_and_checklist_fallbacks() -> None:
    from wilq.actions.review_gate import action_operator_checklist, action_required_checks

    payload = {
        "payload_preview": [
            {"required_validation": ["one", "two", "one"]},
        ],
    }
    def string_list(value: object) -> list[str]:
        return value if isinstance(value, list) else []

    def preview_items(value: dict[str, object]) -> list[dict[str, object]]:
        rows = value.get("payload_preview", [])
        return rows if isinstance(rows, list) else []

    def unique_values(values: object) -> list[str]:
        return list(dict.fromkeys(values)) if isinstance(values, list) else []

    required = action_required_checks(
        payload,
        string_list=string_list,
        preview_items=preview_items,
        unique_values=unique_values,
    )
    checklist = action_operator_checklist(
        payload,
        string_list=string_list,
        required_checks=lambda: required,
    )

    assert required == ["one", "two"]
    assert checklist == ["one", "two"]


def test_latest_google_ads_vendor_read_ignores_non_vendor_runs_and_tiebreaks_id() -> None:
    from wilq.actions.google_ads.business_context import latest_google_ads_vendor_read
    from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus

    started_at = datetime.fromisoformat("2026-07-12T10:00:00+00:00")
    runs = [
        ConnectorRefreshRun(
            id="status_probe",
            connector_id="google_ads",
            mode=ConnectorRefreshMode.status_probe,
            status=ConnectorRefreshStatus.completed,
            started_at=started_at,
            summary="probe",
        ),
        ConnectorRefreshRun(
            id="vendor_a",
            connector_id="google_ads",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=started_at,
            summary="read",
        ),
        ConnectorRefreshRun(
            id="vendor_b",
            connector_id="google_ads",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=started_at,
            summary="read",
        ),
    ]

    latest = latest_google_ads_vendor_read(runs)

    assert latest is not None and latest.id == "vendor_b"


def test_latest_google_ads_metric_facts_require_completed_vendor_read_and_source() -> None:
    from wilq.actions.google_ads.business_context import latest_google_ads_metric_facts
    from wilq.schemas import (
        ConnectorRefreshMode,
        ConnectorRefreshRun,
        ConnectorRefreshStatus,
        MetricFact,
    )

    run = ConnectorRefreshRun(
        id="vendor_facts",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        vendor_data_collected=True,
        evidence_ids=["ev_ads"],
        summary="read",
    )
    ads_fact = MetricFact(
        name="clicks",
        value=3,
        period="30d",
        source_connector="google_ads",
        evidence_id="ev_ads",
    )
    ga4_fact = ads_fact.model_copy(update={"source_connector": "google_analytics_4"})

    facts = latest_google_ads_metric_facts(
        run,
        metric_facts_by_evidence_ids=lambda evidence_ids: [ads_fact, ga4_fact]
        if evidence_ids == ["ev_ads"]
        else [],
    )

    assert facts == [ads_fact]


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
