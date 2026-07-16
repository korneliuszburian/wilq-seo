from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from wilq.jobs.models import JobRun
from wilq.schemas import (
    ActionMutationAuditRecord,
    AdsStrategyReviewRecord,
    AdsTargetGuardrailConfirmation,
    AuditEvent,
    CodexRun,
    ConnectorRefreshRun,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.private_paths import prepare_private_store_path
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
            "codex_runs": self._count_with_query("SELECT COUNT(*) AS count FROM codex_runs"),
            "workflow_runs": self._count_with_query("SELECT COUNT(*) AS count FROM workflow_runs"),
            "audit_events": self._count_with_query("SELECT COUNT(*) AS count FROM audit_events"),
            "action_mutation_audits": self._count_with_query(
                "SELECT COUNT(*) AS count FROM action_mutation_audits"
            ),
            "action_validation_states": self._count_with_query(
                "SELECT COUNT(*) AS count FROM action_validation_states"
            ),
            "connector_refresh_runs": self._count_with_query(
                "SELECT COUNT(*) AS count FROM connector_refresh_runs"
            ),
            "job_runs": self._count_with_query("SELECT COUNT(*) AS count FROM job_runs"),
            "ads_target_guardrail_confirmations": self._count_with_query(
                "SELECT COUNT(*) AS count FROM ads_target_guardrail_confirmations"
            ),
            "ads_strategy_reviews": self._count_with_query(
                "SELECT COUNT(*) AS count FROM ads_strategy_reviews"
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

    def save_action_mutation_audit(
        self,
        record: ActionMutationAuditRecord,
    ) -> ActionMutationAuditRecord:
        redacted = ActionMutationAuditRecord.model_validate(
            redact_mapping(record.model_dump(mode="json"))
        )
        payload_json = _model_json(redacted)
        with self._connect() as connection:
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

    def save_ads_target_guardrail_confirmation(
        self,
        confirmation: AdsTargetGuardrailConfirmation,
    ) -> AdsTargetGuardrailConfirmation:
        payload_json = _model_json(confirmation)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ads_target_guardrail_confirmations (
                  id, connector_id, created_at, payload_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  connector_id = excluded.connector_id,
                  created_at = excluded.created_at,
                  payload_json = excluded.payload_json
                """,
                (
                    confirmation.id,
                    confirmation.connector_id,
                    confirmation.created_at.isoformat(),
                    payload_json,
                ),
            )
        return confirmation

    def latest_ads_target_guardrail_confirmation(
        self,
    ) -> AdsTargetGuardrailConfirmation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM ads_target_guardrail_confirmations
                WHERE connector_id = 'google_ads'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(
            AdsTargetGuardrailConfirmation,
            cast(str, row["payload_json"]),
        )

    def save_ads_strategy_review(
        self,
        review: AdsStrategyReviewRecord,
    ) -> AdsStrategyReviewRecord:
        payload_json = _model_json(review)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ads_strategy_reviews (
                  id, connector_id, created_at, payload_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  connector_id = excluded.connector_id,
                  created_at = excluded.created_at,
                  payload_json = excluded.payload_json
                """,
                (
                    review.id,
                    review.connector_id,
                    review.created_at.isoformat(),
                    payload_json,
                ),
            )
        return review

    def latest_ads_strategy_review(self) -> AdsStrategyReviewRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM ads_strategy_reviews
                WHERE connector_id = 'google_ads'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(AdsStrategyReviewRecord, cast(str, row["payload_json"]))

    def _count_with_query(self, query: str) -> int:
        with self._connect() as connection:
            row = connection.execute(query).fetchone()
        return cast(int, row["count"])

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
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

            CREATE TABLE IF NOT EXISTS action_mutation_audits (
              id TEXT PRIMARY KEY,
              action_id TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS action_validation_states (
              action_id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              validation_status TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS connector_refresh_runs (
              id TEXT PRIMARY KEY,
              connector_id TEXT NOT NULL,
              status TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_runs (
              id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL,
              status TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ads_target_guardrail_confirmations (
              id TEXT PRIMARY KEY,
              connector_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ads_strategy_reviews (
              id TEXT PRIMARY KEY,
              connector_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            """
        )


def _model_json(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _model_from_json[ModelT: BaseModel](model_type: type[ModelT], payload_json: str) -> ModelT:
    return model_type.model_validate(json.loads(payload_json))
