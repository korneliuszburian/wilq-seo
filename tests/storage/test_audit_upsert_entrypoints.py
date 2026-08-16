from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

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
