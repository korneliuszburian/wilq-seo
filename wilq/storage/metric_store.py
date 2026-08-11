from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, cast

import duckdb

from wilq.connectors.vendor import VendorMetricFact
from wilq.content.canonical.metric_dimensions import dimensions_with_metric_identity
from wilq.schemas import ConnectorRefreshRun
from wilq.storage.metric_store_content import _ContentUrlMetricReadMixin
from wilq.storage.metric_store_latest import _MetricFactLatestReadMixin
from wilq.storage.metric_store_read import _DUCKDB_LOCK as _DUCKDB_LOCK
from wilq.storage.metric_store_read import (
    MAX_METRIC_FACT_READ_LIMIT as MAX_METRIC_FACT_READ_LIMIT,
)
from wilq.storage.metric_store_read import _metric_fact_from_row as _metric_fact_from_row
from wilq.storage.metric_store_read import _MetricFactHistoryReadMixin
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_duckdb_schema_version,
    reject_newer_duckdb_schema,
)

DEFAULT_METRIC_DB = Path(".local-lab/state/wilq.duckdb")
DUCKDB_CONNECT_ATTEMPTS = 5
DUCKDB_CONNECT_RETRY_SECONDS = 0.2
METRIC_INSERT_SEQUENCE_NAME = "connector_metric_facts_insert_sequence"


def metric_store_path() -> Path:
    configured_path = os.getenv("WILQ_METRIC_DB")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_METRIC_DB


def metric_store() -> DuckDbMetricStore:
    return DuckDbMetricStore(metric_store_path())


class DuckDbMetricStore(
    _MetricFactHistoryReadMixin,
    _MetricFactLatestReadMixin,
    _ContentUrlMetricReadMixin,
):
    def __init__(self, path: Path) -> None:
        self.path = path

    def _metric_fact_read_limit(self) -> int:
        return MAX_METRIC_FACT_READ_LIMIT

    def status(self) -> dict[str, Any]:
        with _DUCKDB_LOCK, self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  COUNT(*) AS metric_fact_count,
                  COUNT(DISTINCT connector_id) AS connector_count,
                  COUNT(DISTINCT run_id) AS refresh_run_count
                FROM connector_metric_facts
                """
            ).fetchone()
            version_row = connection.execute(
                "SELECT version FROM wilq_schema_metadata WHERE store_key = 'metric_store'"
            ).fetchone()
        if row is None:
            raise RuntimeError("DuckDB metric store status query returned no row")
        if version_row is None:
            raise RuntimeError("DuckDB metric store schema version is missing")
        return {
            "backend": "duckdb",
            "enabled": True,
            "schema_version": int(version_row[0]),
            "path_configured": bool(os.getenv("WILQ_METRIC_DB")),
            "metric_fact_count": int(row[0]),
            "connector_count": int(row[1]),
            "refresh_run_count": int(row[2]),
        }

    def save_connector_refresh_metrics(
        self,
        run: ConnectorRefreshRun,
        detailed_facts: list[VendorMetricFact] | None = None,
    ) -> int:
        if not run.metric_summary and not detailed_facts:
            return 0
        with _DUCKDB_LOCK, self._connect() as connection:
            connection.execute("BEGIN TRANSACTION")
            try:
                sequence_row = connection.execute(
                    f"SELECT nextval('{METRIC_INSERT_SEQUENCE_NAME}')"
                ).fetchone()
                if sequence_row is None:
                    raise RuntimeError("DuckDB metric insert sequence returned no value")
                insert_sequence = int(sequence_row[0])
                rows = [
                    _metric_row(run, name, value, insert_sequence=insert_sequence)
                    for name, value in run.metric_summary.items()
                ]
                rows.extend(
                    _detailed_metric_row(run, fact, insert_sequence=insert_sequence)
                    for fact in detailed_facts or []
                )
                rows = _deduplicate_metric_rows(rows)
                connection.execute(
                    "DELETE FROM connector_metric_facts WHERE run_id = ?", [run.id]
                )
                connection.executemany(
                    """
                    INSERT INTO connector_metric_facts (
                      run_id,
                      connector_id,
                      metric_name,
                      metric_value_double,
                      metric_value_text,
                      value_kind,
                      period,
                      unit,
                      dimensions_json,
                      mode,
                      status,
                      collected_at,
                      insert_sequence,
                      evidence_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            except Exception:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
        return len(rows)

    def _connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_METRIC_DB,
        )
        if read_only and self.path.exists():
            return _connect_with_retry(self.path, read_only=True)
        connection = _connect_with_retry(self.path)
        self.path.chmod(0o600)
        try:
            self._ensure_schema(connection)
        except Exception:
            connection.close()
            raise
        return connection

    def _ensure_schema(self, connection: duckdb.DuckDBPyConnection) -> None:
        connection.execute("BEGIN TRANSACTION")
        try:
            reject_newer_duckdb_schema(connection)
            self._migrate_schema(connection)
            _ensure_metric_insert_sequence(connection)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS connector_metric_facts (
                  run_id VARCHAR NOT NULL,
                  connector_id VARCHAR NOT NULL,
                  metric_name VARCHAR NOT NULL,
                  metric_value_double DOUBLE,
                  metric_value_text VARCHAR,
                  value_kind VARCHAR NOT NULL,
                  period VARCHAR NOT NULL,
                  unit VARCHAR,
                  dimensions_json VARCHAR NOT NULL,
                  mode VARCHAR NOT NULL,
                  status VARCHAR NOT NULL,
                  collected_at TIMESTAMP NOT NULL,
                  insert_sequence BIGINT NOT NULL,
                  evidence_id VARCHAR NOT NULL,
                  PRIMARY KEY (run_id, metric_name, dimensions_json)
                )
                """
            )
            ensure_duckdb_schema_version(connection)
        except Exception:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")

    def _migrate_schema(self, connection: duckdb.DuckDBPyConnection) -> None:
        if not _table_exists(connection, "connector_metric_facts"):
            return
        columns = _table_columns(connection, "connector_metric_facts")
        required_columns = {"period", "unit", "dimensions_json"}
        if not required_columns.issubset(columns):
            _migrate_legacy_metric_facts_table(connection)
        _add_metric_insert_sequence_column(connection)


def _connect_with_retry(path: Path, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    last_error: Exception | None = None
    for attempt in range(DUCKDB_CONNECT_ATTEMPTS):
        try:
            return duckdb.connect(str(path), read_only=read_only)
        except duckdb.Error as exc:
            last_error = exc
            message = str(exc)
            is_retryable = "Conflicting lock" in message or "Unique file handle conflict" in message
            if not is_retryable or attempt == DUCKDB_CONNECT_ATTEMPTS - 1:
                raise
            time.sleep(DUCKDB_CONNECT_RETRY_SECONDS * (attempt + 1))
    raise RuntimeError("DuckDB connection retry exhausted") from last_error


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and row[0])


def _table_columns(connection: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {cast(str, row[1]) for row in rows}


def _migrate_legacy_metric_facts_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("DROP TABLE IF EXISTS connector_metric_facts_v2")
    connection.execute(
        """
        CREATE TABLE connector_metric_facts_v2 (
          run_id VARCHAR NOT NULL,
          connector_id VARCHAR NOT NULL,
          metric_name VARCHAR NOT NULL,
          metric_value_double DOUBLE,
          metric_value_text VARCHAR,
          value_kind VARCHAR NOT NULL,
          period VARCHAR NOT NULL,
          unit VARCHAR,
          dimensions_json VARCHAR NOT NULL,
          mode VARCHAR NOT NULL,
          status VARCHAR NOT NULL,
          collected_at TIMESTAMP NOT NULL,
          insert_sequence BIGINT NOT NULL,
          evidence_id VARCHAR NOT NULL,
          PRIMARY KEY (run_id, metric_name, dimensions_json)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO connector_metric_facts_v2 (
          run_id,
          connector_id,
          metric_name,
          metric_value_double,
          metric_value_text,
          value_kind,
          period,
          unit,
          dimensions_json,
          mode,
          status,
          collected_at,
          insert_sequence,
          evidence_id
        )
        SELECT
          run_id,
          connector_id,
          metric_name,
          metric_value_double,
          metric_value_text,
          value_kind,
          'connector_refresh',
          NULL,
          '{}',
          mode,
          status,
          collected_at,
          ROW_NUMBER() OVER (ORDER BY collected_at ASC, rowid ASC),
          evidence_id
        FROM connector_metric_facts
        """
    )
    connection.execute("DROP TABLE connector_metric_facts")
    connection.execute(
        "ALTER TABLE connector_metric_facts_v2 RENAME TO connector_metric_facts"
    )


def _add_metric_insert_sequence_column(connection: duckdb.DuckDBPyConnection) -> None:
    if "insert_sequence" in _table_columns(connection, "connector_metric_facts"):
        return
    connection.execute(
        """
        ALTER TABLE connector_metric_facts
        ADD COLUMN insert_sequence BIGINT DEFAULT 0
        """
    )
    connection.execute(
        """
        ALTER TABLE connector_metric_facts
        ALTER COLUMN insert_sequence SET NOT NULL
        """
    )
    connection.execute(
        """
        ALTER TABLE connector_metric_facts
        ALTER COLUMN insert_sequence DROP DEFAULT
        """
    )
    connection.execute(
        """
        UPDATE connector_metric_facts AS facts
        SET insert_sequence = numbered.insert_sequence
        FROM (
          SELECT
            rowid AS metric_rowid,
            ROW_NUMBER() OVER (
              ORDER BY collected_at ASC, rowid ASC
            ) AS insert_sequence
          FROM connector_metric_facts
        ) AS numbered
        WHERE facts.rowid = numbered.metric_rowid
        """
    )


def _ensure_metric_insert_sequence(connection: duckdb.DuckDBPyConnection) -> None:
    next_insert_sequence = 1
    if _table_exists(connection, "connector_metric_facts"):
        row = connection.execute(
            "SELECT COALESCE(MAX(insert_sequence), 0) + 1 FROM connector_metric_facts"
        ).fetchone()
        if row is not None:
            next_insert_sequence = int(row[0])
    connection.execute(
        f"""
        CREATE SEQUENCE IF NOT EXISTS {METRIC_INSERT_SEQUENCE_NAME}
        START {next_insert_sequence}
        """  # nosec B608
    )


MetricRow = tuple[
    str,
    str,
    str,
    float | None,
    str | None,
    str,
    str,
    str | None,
    str,
    str,
    str,
    str,
    int,
    str,
]


def _metric_row(
    run: ConnectorRefreshRun,
    name: str,
    value: float | int | str,
    *,
    insert_sequence: int,
) -> MetricRow:
    return _metric_row_from_parts(
        run=run,
        name=name,
        value=value,
        period="connector_refresh",
        unit=None,
        dimensions={},
        insert_sequence=insert_sequence,
    )


def _detailed_metric_row(
    run: ConnectorRefreshRun,
    fact: VendorMetricFact,
    *,
    insert_sequence: int,
) -> MetricRow:
    period = fact.period
    if period == "connector_refresh" and run.connector_id == "google_search_console":
        date_start = run.metric_summary.get("date_start")
        date_end = run.metric_summary.get("date_end")
        if isinstance(date_start, str) and isinstance(date_end, str):
            period = f"{date_start}/{date_end}"
    return _metric_row_from_parts(
        run=run,
        name=fact.name,
        value=fact.value,
        period=period,
        unit=fact.unit,
        dimensions=fact.dimensions,
        insert_sequence=insert_sequence,
    )


def _metric_row_from_parts(
    *,
    run: ConnectorRefreshRun,
    name: str,
    value: float | int | str,
    period: str,
    unit: str | None,
    dimensions: dict[str, str],
    insert_sequence: int,
) -> MetricRow:
    numeric_value: float | None = None
    text_value: str | None = None
    if isinstance(value, bool):
        numeric_value = 1.0 if value else 0.0
        value_kind = "bool"
    elif isinstance(value, int | float):
        numeric_value = float(value)
        value_kind = "number"
    else:
        text_value = value
        value_kind = "text"
    evidence_id = run.evidence_ids[-1] if run.evidence_ids else f"ev_refresh_{run.id}"
    collected_at = (run.completed_at or run.started_at).isoformat()
    return (
        run.id,
        run.connector_id,
        name,
        numeric_value,
        text_value,
        value_kind,
        period,
        unit,
        _dimensions_json(dimensions),
        run.mode.value,
        run.status.value,
        collected_at,
        insert_sequence,
        evidence_id,
    )


def _dimensions_json(dimensions: dict[str, str]) -> str:
    enriched = dimensions_with_metric_identity(dimensions)
    return json.dumps(enriched, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _deduplicate_metric_rows(rows: list[MetricRow]) -> list[MetricRow]:
    deduplicated: dict[tuple[str, str, str], MetricRow] = {}
    for row in rows:
        key = (row[0], row[2], row[8])
        deduplicated[key] = row
    return list(deduplicated.values())
