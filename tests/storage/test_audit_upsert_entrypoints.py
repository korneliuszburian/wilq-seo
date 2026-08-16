from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

import wilq.storage.local_state_audit as local_state_audit
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.store.store_queries import (
    upsert_action_mutation_audit,
    upsert_audit_event,
)
from wilq.schemas import ActionMutationAuditRecord, AuditEvent
from wilq.storage.local_state import LocalStateStore


@pytest.mark.parametrize("kind", ["event", "mutation"])
def test_audit_entrypoints_write_byte_identical_rows(kind: str, tmp_path: Path) -> None:
    path = tmp_path / "shared-audit.sqlite3"
    local_store = LocalStateStore(path)
    workflow_store = ContentWorkflowStore(path)
    created_at = datetime(2026, 8, 16, 10, tzinfo=UTC)
    if kind == "event":
        value = AuditEvent(
            id="audit-entrypoint",
            action_id="action-entrypoint",
            event_type="created",
            actor="operator",
            created_at=created_at,
            summary="Entry point test",
        )
        local_store.save_audit_event(value)
        with workflow_store._connect() as connection:
            upsert_audit_event(connection, value)
        rows = local_store.list_audit_events("action-entrypoint")
    else:
        value = ActionMutationAuditRecord(
            id="mutation-entrypoint",
            action_id="action-entrypoint",
            connector="wordpress_ekologus",
            status="blocked",
            actor="operator",
            created_at=created_at,
            audit_event_id="audit-entrypoint",
            summary="Entry point test",
        )
        local_store.save_action_mutation_audit(value)
        with workflow_store._connect() as connection:
            upsert_action_mutation_audit(connection, value)
        rows = local_store.list_action_mutation_audits("action-entrypoint")

    assert len(rows) == 1
    assert rows[0] == value


def test_apply_audit_pair_commits_both_rows_together(tmp_path: Path) -> None:
    local_store = LocalStateStore(tmp_path / "atomic-audit.sqlite3")
    event = AuditEvent(
        id="atomic-audit-event",
        action_id="atomic-action",
        event_type="apply_blocked",
        actor="operator",
        summary="Atomic apply test",
    )
    mutation_audit = ActionMutationAuditRecord(
        id="atomic-mutation-audit",
        action_id=event.action_id,
        connector="wordpress_ekologus",
        status="blocked",
        actor="operator",
        audit_event_id=event.id,
        summary="Atomic apply test",
    )

    persisted_event, persisted_mutation_audit = local_store.save_apply_audit_pair(
        event, mutation_audit
    )

    assert persisted_event == event
    assert persisted_mutation_audit == mutation_audit
    assert local_store.list_audit_events(event.action_id) == [event]
    assert local_store.list_action_mutation_audits(event.action_id) == [mutation_audit]


def test_apply_audit_pair_rolls_back_when_second_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_store = LocalStateStore(tmp_path / "atomic-audit-rollback.sqlite3")
    event = AuditEvent(
        id="rollback-audit-event",
        action_id="rollback-action",
        event_type="apply_blocked",
        actor="operator",
        summary="Atomic rollback test",
    )
    mutation_audit = ActionMutationAuditRecord(
        id="rollback-mutation-audit",
        action_id=event.action_id,
        connector="wordpress_ekologus",
        status="blocked",
        actor="operator",
        audit_event_id=event.id,
        summary="Atomic rollback test",
    )

    def fail_second_insert(*args, **kwargs):
        raise RuntimeError("simulated mutation audit insert failure")

    monkeypatch.setattr(local_state_audit, "upsert_action_mutation_audit", fail_second_insert)

    with pytest.raises(RuntimeError, match="simulated mutation audit insert failure"):
        local_store.save_apply_audit_pair(event, mutation_audit)

    assert local_store.list_audit_events(event.action_id) == []
    assert local_store.list_action_mutation_audits(event.action_id) == []
