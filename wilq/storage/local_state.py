from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from wilq.schemas import AuditEvent, CodexRun, ConnectorRefreshRun
from wilq.security.redaction import redact_mapping
from wilq.workflows.models import WorkflowRun

DEFAULT_STATE_DB = Path(".local-lab/state/wilq.sqlite3")


def state_db_path() -> Path:
    configured_path = os.getenv("WILQ_STATE_DB")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_STATE_DB


def local_state_store() -> LocalStateStore:
    return LocalStateStore(state_db_path())


class LocalStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def status(self) -> dict[str, Any]:
        return {
            "backend": "sqlite",
            "enabled": True,
            "codex_runs": self._count_with_query(
                "SELECT COUNT(*) AS count FROM codex_runs"
            ),
            "workflow_runs": self._count_with_query(
                "SELECT COUNT(*) AS count FROM workflow_runs"
            ),
            "audit_events": self._count_with_query(
                "SELECT COUNT(*) AS count FROM audit_events"
            ),
            "connector_refresh_runs": self._count_with_query(
                "SELECT COUNT(*) AS count FROM connector_refresh_runs"
            ),
        }

    def save_codex_run(self, run: CodexRun) -> CodexRun:
        redacted = CodexRun.model_validate(redact_mapping(run.model_dump(mode="json")))
        payload_json = _model_json(redacted)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO codex_runs (id, started_at, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  started_at = excluded.started_at,
                  payload_json = excluded.payload_json
                """,
                (redacted.id, redacted.started_at.isoformat(), payload_json),
            )
        return redacted

    def list_codex_runs(self) -> list[CodexRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM codex_runs ORDER BY started_at DESC, id DESC"
            ).fetchall()
        return [_model_from_json(CodexRun, cast(str, row["payload_json"])) for row in rows]

    def save_workflow_run(self, run: WorkflowRun) -> WorkflowRun:
        redacted = WorkflowRun.model_validate(redact_mapping(run.model_dump(mode="json")))
        payload_json = _model_json(redacted)
        updated_at = redacted.completed_at or redacted.started_at
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_runs (id, workflow_id, status, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  workflow_id = excluded.workflow_id,
                  status = excluded.status,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.id,
                    redacted.workflow_id,
                    redacted.status,
                    updated_at.isoformat(),
                    payload_json,
                ),
            )
        return redacted

    def list_workflow_runs(self) -> list[WorkflowRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM workflow_runs ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_model_from_json(WorkflowRun, cast(str, row["payload_json"])) for row in rows]

    def get_workflow_run(self, run_id: str) -> WorkflowRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM workflow_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(WorkflowRun, cast(str, row["payload_json"]))

    def save_connector_refresh_run(self, run: ConnectorRefreshRun) -> ConnectorRefreshRun:
        redacted = ConnectorRefreshRun.model_validate(redact_mapping(run.model_dump(mode="json")))
        payload_json = _model_json(redacted)
        updated_at = redacted.completed_at or redacted.started_at
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO connector_refresh_runs (
                  id, connector_id, status, updated_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  connector_id = excluded.connector_id,
                  status = excluded.status,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.id,
                    redacted.connector_id,
                    redacted.status,
                    updated_at.isoformat(),
                    payload_json,
                ),
            )
        return redacted

    def list_connector_refresh_runs(
        self,
        connector_id: str | None = None,
    ) -> list[ConnectorRefreshRun]:
        with self._connect() as connection:
            if connector_id is None:
                rows = connection.execute(
                    """
                    SELECT payload_json FROM connector_refresh_runs
                    ORDER BY updated_at DESC, id DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT payload_json FROM connector_refresh_runs
                    WHERE connector_id = ?
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (connector_id,),
                ).fetchall()
        return [
            _model_from_json(ConnectorRefreshRun, cast(str, row["payload_json"]))
            for row in rows
        ]

    def get_connector_refresh_run(self, run_id: str) -> ConnectorRefreshRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM connector_refresh_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(ConnectorRefreshRun, cast(str, row["payload_json"]))

    def save_audit_event(self, event: AuditEvent) -> AuditEvent:
        redacted = AuditEvent.model_validate(redact_mapping(event.model_dump(mode="json")))
        payload_json = _model_json(redacted)
        with self._connect() as connection:
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

    def _count_with_query(self, query: str) -> int:
        with self._connect() as connection:
            row = connection.execute(query).fetchone()
        return cast(int, row["count"])

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        self._ensure_schema(connection)
        return connection

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_runs (
              id TEXT PRIMARY KEY,
              workflow_id TEXT NOT NULL,
              status TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY,
              action_id TEXT,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS connector_refresh_runs (
              id TEXT PRIMARY KEY,
              connector_id TEXT NOT NULL,
              status TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            """
        )


def _model_json(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _model_from_json[ModelT: BaseModel](model_type: type[ModelT], payload_json: str) -> ModelT:
    return model_type.model_validate(json.loads(payload_json))
