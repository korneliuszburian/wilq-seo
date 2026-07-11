from __future__ import annotations

from types import SimpleNamespace

from wilq.actions import audit_store


class _FakeAuditStore:
    def list_audit_events(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(action_id="action_a", sequence=index) for index in range(12)
        ] + [SimpleNamespace(action_id="action_b", sequence=1)]

    def list_action_mutation_audits(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(action_id="action_a", sequence=index) for index in range(12)
        ] + [SimpleNamespace(action_id="action_b", sequence=1)]


def test_audit_history_projections_filter_and_bound_per_action(monkeypatch) -> None:
    monkeypatch.setattr(audit_store, "local_state_store", lambda: _FakeAuditStore())

    events = audit_store.persisted_audit_events_by_action_id({"action_a", "action_missing"})
    mutation_audits = audit_store.persisted_mutation_audits_by_action_id({"action_a"})

    assert set(events) == {"action_a", "action_missing"}
    assert len(events["action_a"]) == 10
    assert events["action_missing"] == []
    assert len(mutation_audits["action_a"]) == 10
    assert audit_store.persisted_audit_events_by_action_id(set()) == {}
    assert audit_store.persisted_mutation_audits_by_action_id(set()) == {}
