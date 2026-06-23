from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Literal, cast

import duckdb

from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import ConnectorRefreshRun, MetricFact

DEFAULT_METRIC_DB = Path(".local-lab/state/wilq.duckdb")
DUCKDB_CONNECT_ATTEMPTS = 5
DUCKDB_CONNECT_RETRY_SECONDS = 0.2
MAX_METRIC_FACT_READ_LIMIT = 5000
_DUCKDB_LOCK = RLock()


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

    def save_connector_refresh_metrics(
        self,
        run: ConnectorRefreshRun,
        detailed_facts: list[VendorMetricFact] | None = None,
    ) -> int:
        if not run.metric_summary and not detailed_facts:
            return 0
        rows = [_metric_row(run, name, value) for name, value in run.metric_summary.items()]
        rows.extend(_detailed_metric_row(run, fact) for fact in detailed_facts or [])
        rows = _deduplicate_metric_rows(rows)
        with _DUCKDB_LOCK, self._connect() as connection:
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
                  period,
                  unit,
                  dimensions_json,
                  mode,
                  status,
                  collected_at,
                  evidence_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def list_metric_facts(
        self,
        connector_id: str | None = None,
        limit: int = 100,
    ) -> list[MetricFact]:
        bounded_limit = max(1, min(limit, MAX_METRIC_FACT_READ_LIMIT))
        query = """
            WITH metric_facts_with_previous AS (
            SELECT
              metric_name,
              metric_value_double,
              metric_value_text,
              value_kind,
              connector_id,
              evidence_id,
              collected_at,
              period,
              unit,
              dimensions_json,
              LAG(metric_value_double) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_metric_value_double,
              LAG(metric_value_text) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_metric_value_text,
              LAG(value_kind) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_value_kind
            FROM connector_metric_facts
            )
            SELECT
              metric_name,
              metric_value_double,
              metric_value_text,
              value_kind,
              connector_id,
              evidence_id,
              collected_at,
              period,
              unit,
              dimensions_json,
              previous_metric_value_double,
              previous_metric_value_text,
              previous_value_kind
            FROM metric_facts_with_previous
        """
        params: list[Any] = []
        if connector_id:
            query += " WHERE connector_id = ?"
            params.append(connector_id)
        query += """
            ORDER BY
              collected_at DESC,
              connector_id ASC,
              metric_name ASC,
              dimensions_json ASC,
              evidence_id ASC
            LIMIT ?
        """
        params.append(bounded_limit)
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            rows = connection.execute(query, params).fetchall()
        return [_metric_fact_from_row(row) for row in rows]

    def list_metric_facts_by_connector(
        self,
        connector_ids: list[str],
        limit_per_connector: int = 100,
    ) -> dict[str, list[MetricFact]]:
        if not connector_ids:
            return {}
        unique_connector_ids = list(dict.fromkeys(connector_ids))
        bounded_group_limit = max(1, min(limit_per_connector, MAX_METRIC_FACT_READ_LIMIT))
        query = """
            WITH metric_facts_with_previous AS (
            SELECT
              metric_name,
              metric_value_double,
              metric_value_text,
              value_kind,
              connector_id,
              evidence_id,
              collected_at,
              period,
              unit,
              dimensions_json,
              LAG(metric_value_double) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_metric_value_double,
              LAG(metric_value_text) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_metric_value_text,
              LAG(value_kind) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_value_kind
            FROM connector_metric_facts
            WHERE connector_id = ANY(?)
            ),
            ranked_metric_fact_groups AS (
            SELECT
              connector_id,
              evidence_id,
              dimensions_json,
              MAX(collected_at) AS group_collected_at,
              ROW_NUMBER() OVER (
                PARTITION BY connector_id
                ORDER BY
                  MAX(collected_at) DESC,
                  connector_id ASC,
                  dimensions_json ASC,
                  evidence_id ASC
              ) AS connector_group_rank
            FROM metric_facts_with_previous
            GROUP BY connector_id, evidence_id, dimensions_json
            )
            SELECT
              facts.metric_name,
              facts.metric_value_double,
              facts.metric_value_text,
              facts.value_kind,
              facts.connector_id,
              facts.evidence_id,
              facts.collected_at,
              facts.period,
              facts.unit,
              facts.dimensions_json,
              facts.previous_metric_value_double,
              facts.previous_metric_value_text,
              facts.previous_value_kind
            FROM metric_facts_with_previous facts
            INNER JOIN ranked_metric_fact_groups groups
              ON facts.connector_id = groups.connector_id
             AND facts.evidence_id = groups.evidence_id
             AND facts.dimensions_json = groups.dimensions_json
            WHERE groups.connector_group_rank <= ?
            ORDER BY
              facts.connector_id ASC,
              groups.connector_group_rank ASC,
              facts.metric_name ASC,
              facts.dimensions_json ASC,
              facts.evidence_id ASC
        """
        params: list[Any] = [unique_connector_ids, bounded_group_limit]
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            rows = connection.execute(query, params).fetchall()
        facts_by_connector: dict[str, list[MetricFact]] = {
            connector_id: [] for connector_id in unique_connector_ids
        }
        for row in rows:
            fact = _metric_fact_from_row(row)
            facts_by_connector.setdefault(fact.source_connector, []).append(fact)
        return facts_by_connector

    def list_latest_metric_facts_by_connector(
        self,
        connector_ids: list[str],
        limit_per_connector: int = 100,
    ) -> dict[str, list[MetricFact]]:
        if not connector_ids:
            return {}
        unique_connector_ids = list(dict.fromkeys(connector_ids))
        bounded_group_limit = max(1, min(limit_per_connector, MAX_METRIC_FACT_READ_LIMIT))
        connector_limits = {
            connector_id: bounded_group_limit for connector_id in unique_connector_ids
        }
        return self.list_latest_metric_facts_by_connector_limits(connector_limits)

    def list_latest_metric_facts_by_connector_limits(
        self,
        connector_limits: dict[str, int],
    ) -> dict[str, list[MetricFact]]:
        if not connector_limits:
            return {}
        unique_connector_limits = {
            connector_id: max(1, min(limit, MAX_METRIC_FACT_READ_LIMIT))
            for connector_id, limit in connector_limits.items()
        }
        values_placeholders = ", ".join("(?, ?)" for _ in unique_connector_limits)
        query = f"""
            WITH connector_limits(connector_id, connector_limit) AS (
              VALUES {values_placeholders}
            ),
            ranked_metric_fact_groups AS (
            SELECT
              facts.connector_id,
              facts.evidence_id,
              facts.dimensions_json,
              MAX(facts.collected_at) AS group_collected_at,
              ROW_NUMBER() OVER (
                PARTITION BY facts.connector_id
                ORDER BY
                  MAX(facts.collected_at) DESC,
                  facts.connector_id ASC,
                  facts.dimensions_json ASC,
                  facts.evidence_id ASC
              ) AS connector_group_rank
            FROM connector_metric_facts facts
            INNER JOIN connector_limits limits
              ON facts.connector_id = limits.connector_id
            GROUP BY facts.connector_id, facts.evidence_id, facts.dimensions_json
            )
            SELECT
              facts.metric_name,
              facts.metric_value_double,
              facts.metric_value_text,
              facts.value_kind,
              facts.connector_id,
              facts.evidence_id,
              facts.collected_at,
              facts.period,
              facts.unit,
              facts.dimensions_json,
              NULL AS previous_metric_value_double,
              NULL AS previous_metric_value_text,
              NULL AS previous_value_kind
            FROM connector_metric_facts facts
            INNER JOIN ranked_metric_fact_groups groups
              ON facts.connector_id = groups.connector_id
             AND facts.evidence_id = groups.evidence_id
             AND facts.dimensions_json = groups.dimensions_json
            INNER JOIN connector_limits limits
              ON facts.connector_id = limits.connector_id
            WHERE groups.connector_group_rank <= limits.connector_limit
            ORDER BY
              facts.connector_id ASC,
              groups.connector_group_rank ASC,
              facts.metric_name ASC,
              facts.dimensions_json ASC,
              facts.evidence_id ASC
        """
        params: list[Any] = [
            value
            for connector_id, connector_limit in unique_connector_limits.items()
            for value in (connector_id, connector_limit)
        ]
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            rows = connection.execute(query, params).fetchall()
        facts_by_connector: dict[str, list[MetricFact]] = {
            connector_id: [] for connector_id in unique_connector_limits
        }
        for row in rows:
            fact = _metric_fact_from_row(row)
            facts_by_connector.setdefault(fact.source_connector, []).append(fact)
        return facts_by_connector

    def list_metric_facts_by_evidence_ids(
        self,
        evidence_ids: list[str],
    ) -> list[MetricFact]:
        if not evidence_ids:
            return []
        unique_evidence_ids = list(dict.fromkeys(evidence_ids))
        query = """
            WITH metric_facts_with_previous AS (
            SELECT
              metric_name,
              metric_value_double,
              metric_value_text,
              value_kind,
              connector_id,
              evidence_id,
              collected_at,
              period,
              unit,
              dimensions_json,
              LAG(metric_value_double) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_metric_value_double,
              LAG(metric_value_text) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_metric_value_text,
              LAG(value_kind) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, evidence_id ASC
              ) AS previous_value_kind
            FROM connector_metric_facts
            WHERE evidence_id = ANY(?)
            )
            SELECT
              metric_name,
              metric_value_double,
              metric_value_text,
              value_kind,
              connector_id,
              evidence_id,
              collected_at,
              period,
              unit,
              dimensions_json,
              previous_metric_value_double,
              previous_metric_value_text,
              previous_value_kind
            FROM metric_facts_with_previous
            ORDER BY
              evidence_id ASC,
              connector_id ASC,
              metric_name ASC,
              dimensions_json ASC
        """
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            rows = connection.execute(query, [unique_evidence_ids]).fetchall()
        return [_metric_fact_from_row(row) for row in rows]

    def _connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if read_only and self.path.exists():
            return _connect_with_retry(self.path, read_only=True)
        connection = _connect_with_retry(self.path)
        self._ensure_schema(connection)
        return connection

    def _ensure_schema(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._migrate_schema(connection)
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
              evidence_id VARCHAR NOT NULL,
              PRIMARY KEY (run_id, metric_name, dimensions_json)
            )
            """
        )

    def _migrate_schema(self, connection: duckdb.DuckDBPyConnection) -> None:
        if not _table_exists(connection, "connector_metric_facts"):
            return
        columns = _table_columns(connection, "connector_metric_facts")
        required_columns = {"period", "unit", "dimensions_json"}
        if required_columns.issubset(columns):
            return
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
              evidence_id
            FROM connector_metric_facts
            """
        )
        connection.execute("DROP TABLE connector_metric_facts")
        connection.execute("ALTER TABLE connector_metric_facts_v2 RENAME TO connector_metric_facts")


def _connect_with_retry(path: Path, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    last_error: Exception | None = None
    for attempt in range(DUCKDB_CONNECT_ATTEMPTS):
        try:
            return duckdb.connect(str(path), read_only=read_only)
        except duckdb.Error as exc:
            last_error = exc
            message = str(exc)
            is_retryable = (
                "Conflicting lock" in message
                or "Unique file handle conflict" in message
            )
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
    str,
]


def _metric_row(
    run: ConnectorRefreshRun,
    name: str,
    value: float | int | str,
) -> MetricRow:
    return _metric_row_from_parts(
        run=run,
        name=name,
        value=value,
        period="connector_refresh",
        unit=None,
        dimensions={},
    )


def _detailed_metric_row(
    run: ConnectorRefreshRun,
    fact: VendorMetricFact,
) -> MetricRow:
    return _metric_row_from_parts(
        run=run,
        name=fact.name,
        value=fact.value,
        period=fact.period,
        unit=fact.unit,
        dimensions=fact.dimensions,
    )


def _metric_row_from_parts(
    *,
    run: ConnectorRefreshRun,
    name: str,
    value: float | int | str,
    period: str,
    unit: str | None,
    dimensions: dict[str, str],
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
        evidence_id,
    )


def _metric_fact_from_row(row: tuple[Any, ...]) -> MetricFact:
    value_kind = cast(str, row[3])
    value = _metric_value(value_kind, row[1], row[2])
    previous_value_kind = cast(str | None, row[12])
    previous_value: float | int | str | None = None
    if previous_value_kind:
        previous_value = _metric_value(previous_value_kind, row[10], row[11])
    delta, delta_percent, trend = _metric_delta(value, previous_value)
    collected_at = _coerce_datetime(row[6])
    freshness_state, freshness_label = _metric_freshness(collected_at)
    return MetricFact(
        name=cast(str, row[0]),
        value=value,
        period=cast(str, row[7]),
        source_connector=cast(str, row[4]),
        evidence_id=cast(str, row[5]),
        dimensions=_parse_dimensions(cast(str, row[9])),
        unit=cast(str | None, row[8]),
        collected_at=collected_at,
        previous_value=previous_value,
        delta=delta,
        delta_percent=delta_percent,
        trend=trend,
        freshness_state=freshness_state,
        freshness_label=freshness_label,
    )


def _dimensions_json(dimensions: dict[str, str]) -> str:
    cleaned = {
        str(key): str(value)
        for key, value in dimensions.items()
        if str(key).strip() and str(value).strip()
    }
    return json.dumps(cleaned, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _parse_dimensions(value: str) -> dict[str, str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(item) for key, item in parsed.items() if item is not None}


def _deduplicate_metric_rows(rows: list[MetricRow]) -> list[MetricRow]:
    deduplicated: dict[tuple[str, str, str], MetricRow] = {}
    for row in rows:
        key = (row[0], row[2], row[8])
        deduplicated[key] = row
    return list(deduplicated.values())


def _metric_value(value_kind: str, numeric_value: Any, text_value: Any) -> float | int | str:
    if value_kind in {"number", "bool"}:
        value = cast(float, numeric_value)
        if value.is_integer():
            return int(value)
        return value
    return cast(str, text_value)


def _metric_delta(
    value: float | int | str,
    previous_value: float | int | str | None,
) -> tuple[float | int | None, float | None, Literal["up", "down", "flat", "unknown"]]:
    if not isinstance(value, int | float) or not isinstance(previous_value, int | float):
        return None, None, "unknown"
    delta_value = value - previous_value
    if isinstance(delta_value, float) and delta_value.is_integer():
        delta: float | int = int(delta_value)
    else:
        delta = delta_value
    trend: Literal["up", "down", "flat", "unknown"]
    if delta_value > 0:
        trend = "up"
    elif delta_value < 0:
        trend = "down"
    else:
        trend = "flat"
    delta_percent = None
    if previous_value != 0:
        delta_percent = (delta_value / previous_value) * 100
    return delta, delta_percent, trend


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def _metric_freshness(
    collected_at: datetime | None,
) -> tuple[Literal["fresh", "stale", "unknown"], str | None]:
    if collected_at is None:
        return "unknown", None
    age_hours = max(0.0, (datetime.now(UTC) - collected_at).total_seconds() / 3600)
    if age_hours < 1:
        label = "odświeżone mniej niż godzinę temu"
    else:
        label = f"odświeżone {age_hours:.0f}h temu"
    if age_hours <= 24:
        return "fresh", label
    return "stale", label
