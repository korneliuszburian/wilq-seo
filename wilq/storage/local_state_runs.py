from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from typing import Protocol, cast, runtime_checkable

from pydantic import BaseModel

from wilq.codex.run_history import (
    CODEX_RUN_HISTORY_DEFAULT_LIMIT,
    CODEX_RUN_HISTORY_MAX_LIMIT,
    decode_codex_run_history_cursor,
    encode_codex_run_history_cursor,
    summarize_codex_run,
)
from wilq.jobs.models import JobRun
from wilq.schemas import CodexRun, CodexRunHistoryPage, ConnectorRefreshRun
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json as _model_json
from wilq.workflows.models import WorkflowRun


@runtime_checkable
class RunTransactionStore(Protocol):
    def run_transaction(self) -> AbstractContextManager[sqlite3.Connection]:
        ...


def supports_run_transaction(store: object) -> bool:
    return isinstance(store, RunTransactionStore)


class _RunStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    @contextmanager
    def run_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as connection:
            yield connection

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

    def get_codex_run(self, run_id: str) -> CodexRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM codex_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(CodexRun, cast(str, row["payload_json"]))

    def list_codex_run_history(
        self,
        *,
        limit: int = CODEX_RUN_HISTORY_DEFAULT_LIMIT,
        cursor: str | None = None,
    ) -> CodexRunHistoryPage:
        if not 1 <= limit <= CODEX_RUN_HISTORY_MAX_LIMIT:
            raise ValueError(
                f"Codex run history limit must be between 1 and {CODEX_RUN_HISTORY_MAX_LIMIT}"
            )

        cursor_key = decode_codex_run_history_cursor(cursor) if cursor is not None else None
        with self._connect() as connection:
            total_count = cast(
                int,
                connection.execute("SELECT COUNT(*) FROM codex_runs").fetchone()[0],
            )
            if cursor_key is None:
                rows = connection.execute(
                    """
                    SELECT id, started_at, payload_json
                    FROM codex_runs
                    ORDER BY started_at DESC, id DESC
                    LIMIT ?
                    """,
                    (limit + 1,),
                ).fetchall()
            else:
                cursor_started_at = cursor_key.started_at.isoformat()
                rows = connection.execute(
                    """
                    SELECT id, started_at, payload_json
                    FROM codex_runs
                    WHERE started_at < ? OR (started_at = ? AND id < ?)
                    ORDER BY started_at DESC, id DESC
                    LIMIT ?
                    """,
                    (
                        cursor_started_at,
                        cursor_started_at,
                        cursor_key.run_id,
                        limit + 1,
                    ),
                ).fetchall()

        page_rows = rows[:limit]
        items = [
            summarize_codex_run(
                _model_from_json(CodexRun, cast(str, row["payload_json"]))
            )
            for row in page_rows
        ]
        next_cursor = None
        if len(rows) > limit:
            last_row = page_rows[-1]
            next_cursor = encode_codex_run_history_cursor(
                started_at=datetime.fromisoformat(cast(str, last_row["started_at"])),
                run_id=cast(str, last_row["id"]),
            )

        return CodexRunHistoryPage(
            items=items,
            total_count=total_count,
            next_cursor=next_cursor,
        )

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


def _model_from_json[ModelT: BaseModel](model_type: type[ModelT], payload_json: str) -> ModelT:
    return model_type.model_validate(json.loads(payload_json))
