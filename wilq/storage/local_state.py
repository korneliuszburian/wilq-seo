from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, cast

from wilq.storage.local_state_ads import _AdsReviewStoreMixin
from wilq.storage.local_state_audit import _AuditStoreMixin
from wilq.storage.local_state_focus import _SectionFocusStoreMixin
from wilq.storage.local_state_runs import _model_from_json as _model_from_json
from wilq.storage.local_state_runs import _RunStoreMixin
from wilq.storage.local_state_stop_reconciliation import (
    _StopReconciliationStoreMixin,
    ensure_stop_reconciliation_schema,
)
from wilq.storage.local_state_stop_telemetry import _StopTelemetryStoreMixin
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    SQLITE_SCHEMA_VERSION,
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

DEFAULT_STATE_DB = Path(".local-lab/state/wilq.sqlite3")


def state_db_path() -> Path:
    configured_path = os.getenv("WILQ_STATE_DB")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_STATE_DB


def local_state_store() -> LocalStateStore:
    return LocalStateStore(state_db_path())


class LocalStateStore(
    _RunStoreMixin,
    _StopTelemetryStoreMixin,
    _StopReconciliationStoreMixin,
    _AuditStoreMixin,
    _AdsReviewStoreMixin,
    _SectionFocusStoreMixin,
):
    def __init__(self, path: Path) -> None:
        self.path = path

    def status(self) -> dict[str, Any]:
        return {
            "backend": "sqlite",
            "enabled": True,
            "schema_version": self._schema_version(),
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

    def _count_with_query(self, query: str) -> int:
        with self._connect() as connection:
            row = connection.execute(query).fetchone()
        return cast(int, row["count"])

    def _schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("PRAGMA user_version").fetchone()
        if row is None:
            raise RuntimeError("SQLite schema version is unavailable")
        return int(row[0])

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
        reject_newer_sqlite_schema(connection)
        if _local_state_schema_is_current(connection):
            return
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS codex_stop_events (
              id TEXT PRIMARY KEY,
              received_at TEXT NOT NULL,
              event_type TEXT NOT NULL CHECK (event_type = 'stop'),
              contract_version INTEGER NOT NULL CHECK (contract_version >= 1)
            );

            CREATE INDEX IF NOT EXISTS idx_codex_stop_events_received_at_id
            ON codex_stop_events (received_at, id);

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
            """
        )
        _ensure_local_state_marketing_objects(connection)
        ensure_stop_reconciliation_schema(connection)
        ensure_sqlite_schema_version(connection)


def _local_state_schema_is_current(connection: sqlite3.Connection) -> bool:
    if int(connection.execute("PRAGMA user_version").fetchone()[0]) != SQLITE_SCHEMA_VERSION:
        return False
    required_objects = {
        ("table", "codex_runs"),
        ("table", "codex_stop_events"),
        ("index", "idx_codex_stop_events_received_at_id"),
        ("table", "workflow_runs"),
        ("table", "audit_events"),
        ("table", "action_mutation_audits"),
        ("table", "action_validation_states"),
        ("table", "connector_refresh_runs"),
        ("table", "job_runs"),
        ("table", "ads_target_guardrail_confirmations"),
        ("table", "ads_strategy_reviews"),
        ("table", "content_section_focus"),
        ("table", "content_refresh_preparation_authorizations"),
        ("table", "codex_stop_reconciliation_batches"),
        ("table", "codex_stop_events_legacy"),
    }
    existing_objects = {
        (str(row[0]), str(row[1]))
        for row in connection.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'index')"
        )
    }
    return required_objects.issubset(existing_objects)


def _ensure_local_state_marketing_objects(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
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

        CREATE TABLE IF NOT EXISTS content_section_focus (
          work_item_id TEXT PRIMARY KEY,
          section_id TEXT NOT NULL,
          planning_digest TEXT,
          updated_by TEXT,
          updated_at TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS content_refresh_preparation_authorizations (
          authorization_id TEXT PRIMARY KEY,
          authorization_digest TEXT NOT NULL UNIQUE,
          work_item_id TEXT NOT NULL,
          classification_run_id TEXT NOT NULL,
          classification_run_digest TEXT NOT NULL,
          decision_set_digest TEXT NOT NULL,
          source_packet_row_digest TEXT NOT NULL,
          canonical_path TEXT NOT NULL,
          public_url TEXT NOT NULL,
          planning_input_digest TEXT NOT NULL,
          service_card_id TEXT NOT NULL,
          authorized_by TEXT NOT NULL,
          authorized_at TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          UNIQUE (
            work_item_id,
            classification_run_digest,
            decision_set_digest,
            source_packet_row_digest,
            planning_input_digest,
            service_card_id
          )
        );
        """
    )
