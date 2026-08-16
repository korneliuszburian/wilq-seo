from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, cast

from wilq.schemas import ActionMutationAuditRecord, AuditEvent
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state_runs import _model_from_json
from wilq.storage.model_json import model_json as _model_json


def upsert_audit_event(connection: sqlite3.Connection, event: AuditEvent) -> AuditEvent:
    redacted = AuditEvent.model_validate(redact_mapping(event.model_dump(mode="json")))
    payload_json = _model_json(redacted)
    connection.execute(
        """
        INSERT INTO audit_events (id, action_id, created_at, payload_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          action_id = excluded.action_id,
          created_at = excluded.created_at,
          payload_json = excluded.payload_json
        """,
        (redacted.id, redacted.action_id, redacted.created_at.isoformat(), payload_json),
    )
    return redacted


def upsert_action_mutation_audit(
    connection: sqlite3.Connection,
    record: ActionMutationAuditRecord,
) -> ActionMutationAuditRecord:
    redacted = ActionMutationAuditRecord.model_validate(
        redact_mapping(record.model_dump(mode="json"))
    )
    payload_json = _model_json(redacted)
    connection.execute(
        """
        INSERT INTO action_mutation_audits (
          id, action_id, status, created_at, payload_json
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          action_id = excluded.action_id,
          status = excluded.status,
          created_at = excluded.created_at,
          payload_json = excluded.payload_json
        """,
        (
            redacted.id,
            redacted.action_id,
            redacted.status,
            redacted.created_at.isoformat(),
            payload_json,
        ),
    )
    return redacted


class _AuditStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_audit_event(self, event: AuditEvent) -> AuditEvent:
        with self._connect() as connection:
            return upsert_audit_event(connection, event)

    def list_audit_events(self, action_id: str | None = None) -> list[AuditEvent]:
        with self._connect() as connection:
            if action_id is None:
                rows = connection.execute(
                    "SELECT payload_json FROM audit_events ORDER BY created_at DESC, id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT payload_json FROM audit_events
                    WHERE action_id = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (action_id,),
                ).fetchall()
        return [_model_from_json(AuditEvent, cast(str, row["payload_json"])) for row in rows]

    def save_action_mutation_audit(
        self,
        record: ActionMutationAuditRecord,
    ) -> ActionMutationAuditRecord:
        with self._connect() as connection:
            return upsert_action_mutation_audit(connection, record)

    def list_action_mutation_audits(
        self,
        action_id: str | None = None,
    ) -> list[ActionMutationAuditRecord]:
        with self._connect() as connection:
            if action_id is None:
                rows = connection.execute(
                    """
                    SELECT payload_json FROM action_mutation_audits
                    ORDER BY created_at DESC, id DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT payload_json FROM action_mutation_audits
                    WHERE action_id = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (action_id,),
                ).fetchall()
        return [
            _model_from_json(ActionMutationAuditRecord, cast(str, row["payload_json"]))
            for row in rows
        ]

    def save_action_validation_state(
        self,
        *,
        action_id: str,
        status: str,
        validation_status: str,
    ) -> None:
        updated_at = datetime.now(UTC).isoformat()
        payload_json = json.dumps(
            {
                "action_id": action_id,
                "status": status,
                "validation_status": validation_status,
                "updated_at": updated_at,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO action_validation_states (
                  action_id, status, validation_status, updated_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                  status = excluded.status,
                  validation_status = excluded.validation_status,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (action_id, status, validation_status, updated_at, payload_json),
            )

    def get_action_validation_state(self, action_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM action_validation_states WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(cast(str, row["payload_json"]))
        return payload if isinstance(payload, dict) else None
