from __future__ import annotations

import json
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Literal, cast

import duckdb

from wilq.schemas import MetricFact

MAX_METRIC_FACT_READ_LIMIT = 5000
_DUCKDB_LOCK = RLock()


class _MetricFactHistoryReadMixin:
    def _connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        raise NotImplementedError

    def _metric_fact_read_limit(self) -> int:
        raise NotImplementedError

    def list_metric_facts(
        self,
        connector_id: str | None = None,
        limit: int = 100,
    ) -> list[MetricFact]:
        bounded_limit = max(1, min(limit, self._metric_fact_read_limit()))
        # Only fixed SQL fragments above are interpolated; all
        # connector, URL, path and identity values remain bound parameters.
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
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_metric_value_double,
              LAG(metric_value_text) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_metric_value_text,
              LAG(value_kind) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_value_kind,
              LAG(evidence_id) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_evidence_id,
              LAG(collected_at) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_collected_at
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
              previous_value_kind,
              previous_evidence_id,
              previous_collected_at
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
        bounded_group_limit = max(
            1,
            min(limit_per_connector, self._metric_fact_read_limit()),
        )
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
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_metric_value_double,
              LAG(metric_value_text) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_metric_value_text,
              LAG(value_kind) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_value_kind,
              LAG(evidence_id) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_evidence_id,
              LAG(collected_at) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_collected_at
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
              facts.previous_value_kind,
              facts.previous_evidence_id,
              facts.previous_collected_at
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
        return _group_metric_facts_by_connector(rows, unique_connector_ids)

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
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_metric_value_double,
              LAG(metric_value_text) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_metric_value_text,
              LAG(value_kind) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_value_kind,
              LAG(evidence_id) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_evidence_id,
              LAG(collected_at) OVER (
                PARTITION BY connector_id, metric_name, dimensions_json
                ORDER BY collected_at ASC, insert_sequence ASC
              ) AS previous_collected_at
            FROM connector_metric_facts
            WHERE connector_id = ANY(?)
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
              previous_value_kind,
              previous_evidence_id,
              previous_collected_at
            FROM metric_facts_with_previous
            WHERE evidence_id = ANY(?)
            ORDER BY
              evidence_id ASC,
              connector_id ASC,
              metric_name ASC,
              dimensions_json ASC
        """
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            connector_rows = connection.execute(
                """
                SELECT DISTINCT connector_id
                FROM connector_metric_facts
                WHERE evidence_id = ANY(?)
                """,
                [unique_evidence_ids],
            ).fetchall()
            rows = connection.execute(
                query,
                [
                    [cast(str, row[0]) for row in connector_rows],
                    unique_evidence_ids,
                ],
            ).fetchall()
        return [_metric_fact_from_row(row) for row in rows]


def _group_metric_facts_by_connector(
    rows: list[tuple[Any, ...]],
    connector_ids: list[str],
) -> dict[str, list[MetricFact]]:
    facts_by_connector: dict[str, list[MetricFact]] = {
        connector_id: [] for connector_id in connector_ids
    }
    for row in rows:
        fact = _metric_fact_from_row(row)
        facts_by_connector.setdefault(fact.source_connector, []).append(fact)
    return facts_by_connector


def _metric_fact_from_row(row: tuple[Any, ...]) -> MetricFact:
    value_kind = cast(str, row[3])
    value = _metric_value(value_kind, row[1], row[2])
    previous_value_kind = cast(str | None, row[12])
    previous_value: float | int | str | None = None
    if previous_value_kind:
        previous_value = _metric_value(previous_value_kind, row[10], row[11])
    previous_evidence_id = cast(str | None, row[13])
    previous_collected_at = _coerce_datetime(row[14])
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
        previous_evidence_id=previous_evidence_id,
        previous_collected_at=previous_collected_at,
        delta=delta,
        delta_percent=delta_percent,
        trend=trend,
        freshness_state=freshness_state,
        freshness_label=freshness_label,
    )


def _parse_dimensions(value: str) -> dict[str, str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in parsed.items()
        if item is not None and not str(key).startswith("_wilq_")
    }


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
