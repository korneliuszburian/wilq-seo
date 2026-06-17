from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, cast

import duckdb

from wilq.schemas import ConnectorRefreshRun, MetricFact

DEFAULT_METRIC_DB = Path(".local-lab/state/wilq.duckdb")
DUCKDB_CONNECT_ATTEMPTS = 5
DUCKDB_CONNECT_RETRY_SECONDS = 0.2


def metric_store_path() -> Path:
    configured_path = os.getenv("WILQ_METRIC_DB")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_METRIC_DB


def metric_store() -> DuckDbMetricStore:
    return DuckDbMetricStore(metric_store_path())


class DuckDbMetricStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                  COUNT(*) AS metric_fact_count,
                  COUNT(DISTINCT connector_id) AS connector_count,
                  COUNT(DISTINCT run_id) AS refresh_run_count
                FROM connector_metric_facts
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("DuckDB metric store status query returned no row")
        return {
            "backend": "duckdb",
            "enabled": True,
            "path_configured": bool(os.getenv("WILQ_METRIC_DB")),
            "metric_fact_count": int(row[0]),
            "connector_count": int(row[1]),
            "refresh_run_count": int(row[2]),
        }

    def save_connector_refresh_metrics(self, run: ConnectorRefreshRun) -> int:
        if not run.metric_summary:
            return 0
        rows = [_metric_row(run, name, value) for name, value in run.metric_summary.items()]
        with self._connect() as connection:
            connection.execute("DELETE FROM connector_metric_facts WHERE run_id = ?", [run.id])
            connection.executemany(
                """
                INSERT INTO connector_metric_facts (
                  run_id,
                  connector_id,
                  metric_name,
                  metric_value_double,
                  metric_value_text,
                  value_kind,
                  mode,
                  status,
                  collected_at,
                  evidence_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def list_metric_facts(
        self,
        connector_id: str | None = None,
        limit: int = 100,
    ) -> list[MetricFact]:
        bounded_limit = max(1, min(limit, 500))
        query = """
            SELECT
              metric_name,
              metric_value_double,
              metric_value_text,
              value_kind,
              connector_id,
              evidence_id,
              collected_at
            FROM connector_metric_facts
        """
        params: list[Any] = []
        if connector_id:
            query += " WHERE connector_id = ?"
            params.append(connector_id)
        query += " ORDER BY collected_at DESC, connector_id ASC, metric_name ASC LIMIT ?"
        params.append(bounded_limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_metric_fact_from_row(row) for row in rows]

    def _connect(self) -> duckdb.DuckDBPyConnection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = _connect_with_retry(self.path)
        self._ensure_schema(connection)
        return connection

    def _ensure_schema(self, connection: duckdb.DuckDBPyConnection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS connector_metric_facts (
              run_id VARCHAR NOT NULL,
              connector_id VARCHAR NOT NULL,
              metric_name VARCHAR NOT NULL,
              metric_value_double DOUBLE,
              metric_value_text VARCHAR,
              value_kind VARCHAR NOT NULL,
              mode VARCHAR NOT NULL,
              status VARCHAR NOT NULL,
              collected_at TIMESTAMP NOT NULL,
              evidence_id VARCHAR NOT NULL,
              PRIMARY KEY (run_id, metric_name)
            )
            """
        )


def _connect_with_retry(path: Path) -> duckdb.DuckDBPyConnection:
    last_error: Exception | None = None
    for attempt in range(DUCKDB_CONNECT_ATTEMPTS):
        try:
            return duckdb.connect(str(path))
        except duckdb.IOException as exc:
            last_error = exc
            if "Conflicting lock" not in str(exc) or attempt == DUCKDB_CONNECT_ATTEMPTS - 1:
                raise
            time.sleep(DUCKDB_CONNECT_RETRY_SECONDS * (attempt + 1))
    raise RuntimeError("DuckDB connection retry exhausted") from last_error


def _metric_row(
    run: ConnectorRefreshRun,
    name: str,
    value: float | int | str,
) -> tuple[str, str, str, float | None, str | None, str, str, str, str, str]:
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
        run.mode.value,
        run.status.value,
        collected_at,
        evidence_id,
    )


def _metric_fact_from_row(row: tuple[Any, ...]) -> MetricFact:
    value_kind = cast(str, row[3])
    value: float | int | str
    if value_kind in {"number", "bool"}:
        value = cast(float, row[1])
        if value.is_integer():
            value = int(value)
    else:
        value = cast(str, row[2])
    return MetricFact(
        name=cast(str, row[0]),
        value=value,
        period="connector_refresh",
        source_connector=cast(str, row[4]),
        evidence_id=cast(str, row[5]),
    )
