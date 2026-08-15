from __future__ import annotations

import json
import sqlite3
from typing import cast

from pydantic import BaseModel

from wilq.jobs.models import JobRun
from wilq.schemas import CodexRun, ConnectorRefreshRun
from wilq.security.redaction import redact_mapping
from wilq.workflows.models import WorkflowRun


class _RunStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

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
                    redacted.updated_at.isoformat(),
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
            _model_from_json(ConnectorRefreshRun, cast(str, row["payload_json"])) for row in rows
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

    def save_job_run(self, run: JobRun) -> JobRun:
        redacted = JobRun.model_validate(redact_mapping(run.model_dump(mode="json")))
        payload_json = _model_json(redacted)
        updated_at = redacted.completed_at or redacted.started_at
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO job_runs (id, job_id, status, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  job_id = excluded.job_id,
                  status = excluded.status,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.id,
                    redacted.job_id,
                    redacted.status,
                    updated_at.isoformat(),
                    payload_json,
                ),
            )
        return redacted

    def list_job_runs(self) -> list[JobRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM job_runs ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_model_from_json(JobRun, cast(str, row["payload_json"])) for row in rows]

    def get_job_run(self, run_id: str) -> JobRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM job_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(JobRun, cast(str, row["payload_json"]))


def _model_json(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _model_from_json[ModelT: BaseModel](model_type: type[ModelT], payload_json: str) -> ModelT:
    return model_type.model_validate(json.loads(payload_json))
