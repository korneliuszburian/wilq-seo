from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from wilq.actions import audit_store
from wilq.schemas import ActionMutationAuditRecord, ActionObject, AuditEvent


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


def test_audit_event_operator_projection_uses_store_owned_summary_and_labels() -> None:
    event = AuditEvent(
        id="audit_preview_test",
        event_type="action_preview_generated",
        actor="system",
        summary="preview pozycje=2, blocked",
        details={"checked_items": ["reviewed_url"]},
    )

    projected = audit_store.audit_event_with_operator_label(
        event,
        string_list=lambda value: value if isinstance(value, list) else [],
        review_summary_item=lambda item: f"review:{item}",
        review_blocker_label=lambda item: f"blocker:{item}",
    )

    assert projected.event_type_label == "Podgląd zmian wygenerowany"
    assert "zapis zmian pozostaje zablokowany" in projected.summary
    assert projected.details["checked_items"] == ["review:reviewed_url"]


def test_mutation_audit_record_keeps_redacted_write_attempt_flags() -> None:
    action = ActionObject.model_construct(
        id="act_test_mutation",
        connector="wordpress_ekologus",
        payload={"action_type": "create_wordpress_draft"},
        evidence_ids=["ev_test"],
    )
    event = AuditEvent(
        id="audit_apply_blocked",
        event_type="action_apply_blocked",
        actor="operator",
        summary="blocked",
    )

    audit = audit_store.action_mutation_audit_record(
        action=action,
        audit_event=event,
        actor="operator",
        errors=["missing_confirmation_audit"],
        mutation_adapter="wordpress_draft_execution_boundary",
        adapter_result=None,
    )

    assert audit.status == "blocked"
    assert audit.adapter_reached is False
    assert audit.external_write_attempted is False
    assert audit.evidence_ids == ["ev_test"]
    assert "before any vendor API call" in audit.summary


def test_apply_audit_event_type_distinguishes_confirmation_and_other_blockers() -> None:
    assert audit_store.apply_audit_event_type([]) == "apply_succeeded"
    assert (
        audit_store.apply_audit_event_type(["Brakuje osoby potwierdzającej zapis zmian."])
        == "apply_confirmation_missing"
    )
    assert audit_store.apply_audit_event_type(["inny blocker"]) == "apply_blocked"


def test_build_apply_audit_event_owns_event_type_summary_and_evidence() -> None:
    action = ActionObject.model_construct(
        id="act_apply_audit_builder",
        evidence_ids=["ev_apply_builder"],
    )

    event = audit_store.build_apply_audit_event(
        action=action,
        audit_id="audit_apply_builder",
        actor="operator",
        errors=["Brakuje osoby potwierdzającej zapis zmian."],
    )

    assert event.id == "audit_apply_builder"
    assert event.event_type == "apply_confirmation_missing"
    assert event.event_type_label == "Zapis zmian zablokowany"
    assert event.actor == "operator"
    assert event.evidence_ids == ["ev_apply_builder"]


def test_build_human_review_audit_event_owns_review_event_metadata() -> None:
    action = ActionObject.model_construct(
        id="act_review_audit_builder",
        evidence_ids=["ev_review_builder"],
    )

    event = audit_store.build_human_review_audit_event(
        action=action,
        reviewed_by="operator",
        outcome="approved_for_prepare",
        summary="Review zaakceptowany.",
        details={"checked_items": ["public_url"]},
    )

    assert event.id.startswith("audit_act_review_audit_builder_human_review_")
    assert event.event_type == "human_review_approved_for_prepare"
    assert event.event_type_label == "Przegląd operatora zapisany"
    assert event.actor == "operator"
    assert event.evidence_ids == ["ev_review_builder"]
    assert event.details == {"checked_items": ["public_url"]}


def test_build_preview_audit_event_stays_dry_run_and_keeps_evidence() -> None:
    action = ActionObject.model_construct(
        id="act_preview_audit_builder",
        evidence_ids=["ev_preview_builder"],
    )

    event = audit_store.build_preview_audit_event(
        action=action,
        actor="operator",
        summary="Podgląd zmian gotowy.",
    )

    assert event.id.startswith("audit_act_preview_audit_builder_preview_")
    assert event.event_type == "action_preview_generated"
    assert event.event_type_label == "Podgląd zmian wygenerowany"
    assert event.actor == "operator"
    assert event.summary == "Podgląd zmian gotowy."
    assert event.evidence_ids == ["ev_preview_builder"]


def test_build_confirmation_audit_event_keeps_review_only_semantics() -> None:
    action = ActionObject.model_construct(
        id="act_confirmation_audit_builder",
        evidence_ids=["ev_confirmation_builder"],
    )

    event = audit_store.build_confirmation_audit_event(
        action=action,
        actor="operator",
        event_type="action_confirmation_blocked",
        summary="Potwierdzenie zablokowane.",
    )

    assert event.id.startswith("audit_act_confirmation_audit_builder_confirm_")
    assert event.event_type == "action_confirmation_blocked"
    assert event.event_type_label == "Potwierdzenie zablokowane"
    assert event.actor == "operator"
    assert event.summary == "Potwierdzenie zablokowane."
    assert event.evidence_ids == ["ev_confirmation_builder"]


def test_build_impact_check_audit_event_keeps_measurement_evidence() -> None:
    action = ActionObject.model_construct(id="act_impact_audit_builder")

    event = audit_store.build_impact_check_audit_event(
        action=action,
        actor="operator",
        event_type="action_impact_check_blocked",
        summary="Sprawdzenie efektu zablokowane.",
        evidence_ids=["ev_impact_builder", "ev_metric_builder"],
    )

    assert event.id.startswith("audit_act_impact_audit_builder_impact_")
    assert event.event_type == "action_impact_check_blocked"
    assert event.event_type_label == "Sprawdzenie efektu zablokowane"
    assert event.actor == "operator"
    assert event.summary == "Sprawdzenie efektu zablokowane."
    assert event.evidence_ids == ["ev_impact_builder", "ev_metric_builder"]
