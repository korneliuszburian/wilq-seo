from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from wilq.actions import audit_store
from wilq.schemas import ActionMutationAuditRecord, AuditEvent


class _FakeAuditStore:
    def list_audit_events(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(action_id="action_a", sequence=index) for index in range(12)
        ] + [SimpleNamespace(action_id="action_b", sequence=1)]

    def list_action_mutation_audits(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(action_id="action_a", sequence=index) for index in range(12)
        ] + [SimpleNamespace(action_id="action_b", sequence=1)]


def test_audit_history_projections_filter_and_bound_per_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit_store, "local_state_store", lambda: _FakeAuditStore())

    events = audit_store.persisted_audit_events_by_action_id({"action_a", "action_missing"})
    mutation_audits = audit_store.persisted_mutation_audits_by_action_id({"action_a"})

    assert set(events) == {"action_a", "action_missing"}
    assert len(events["action_a"]) == 10
    assert events["action_missing"] == []
    assert len(mutation_audits["action_a"]) == 10
    assert audit_store.persisted_audit_events_by_action_id(set()) == {}
    assert audit_store.persisted_mutation_audits_by_action_id(set()) == {}


def test_audit_event_selectors_keep_latest_relevant_event_and_mutation_audit() -> None:
    old = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
    new = datetime(2026, 7, 12, 11, 0, tzinfo=UTC)
    events = [
        AuditEvent(
            id="audit_preview_old",
            event_type="action_preview_generated",
            actor="system",
            created_at=old,
            summary="old",
        ),
        AuditEvent(
            id="audit_preview_new",
            event_type="action_preview_generated",
            actor="system",
            created_at=new,
            summary="new",
        ),
        AuditEvent(
            id="audit_confirm",
            event_type="action_apply_confirmed",
            actor="operator",
            created_at=old,
            summary="confirm",
        ),
    ]
    audits = [
        ActionMutationAuditRecord(
            id="mutation_old",
            action_id="action_a",
            action_type="test",
            connector="localo",
            status="blocked",
            adapter_reached=False,
            external_write_attempted=False,
            mutation_attempted=False,
            actor="system",
            created_at=old,
            audit_event_id="audit_old",
            summary="old",
        ),
        ActionMutationAuditRecord(
            id="mutation_new",
            action_id="action_a",
            action_type="test",
            connector="localo",
            status="blocked",
            adapter_reached=False,
            external_write_attempted=False,
            mutation_attempted=False,
            actor="system",
            created_at=new,
            audit_event_id="audit_new",
            summary="new",
        ),
    ]

    latest_preview = audit_store.latest_preview_event(events)
    latest_confirmation = audit_store.latest_action_confirmation_event(events)
    latest_mutation = audit_store.latest_mutation_audit(audits)
    assert latest_preview is not None and latest_preview.id == "audit_preview_new"
    assert latest_confirmation is not None and latest_confirmation.id == "audit_confirm"
    assert audit_store.latest_action_impact_check_event(events) is None
    assert latest_mutation is not None and latest_mutation.id == "mutation_new"


def test_audit_details_for_operator_redacts_raw_contracts_and_labels_review_fields() -> None:
    details = audit_store.audit_details_for_operator(
        {
            "checked_items": ["reviewed_url", "draft_readiness_notes"],
            "blockers": ["human_confirm_before_apply"],
            "payload_preview": "raw payload should stay hidden",
            "nested": {"safe": "ok", "mapping_secret": "hide"},
        },
        string_list=lambda value: value if isinstance(value, list) else [],
        review_summary_item=lambda item: f"review:{item}",
        review_blocker_label=lambda item: f"blocker:{item}",
    )

    assert details["checked_items"] == [
        "review:reviewed_url",
        "review:draft_readiness_notes",
    ]
    assert details["blockers"] == ["blocker:human_confirm_before_apply"]
    assert "payload_preview" not in details
    assert details["nested"] == {"safe": "ok"}
