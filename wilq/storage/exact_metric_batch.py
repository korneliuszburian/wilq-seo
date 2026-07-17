from __future__ import annotations

from collections.abc import Collection

from wilq.schemas import MetricFact
from wilq.storage.metric_store import (
    _DUCKDB_LOCK,
    DuckDbMetricStore,
    _metric_fact_from_row,
)


def list_exact_metric_batch(
    store: DuckDbMetricStore,
    *,
    connector_id: str,
    evidence_id: str,
    metric_names: Collection[str],
) -> list[MetricFact]:
    """Read one evidence batch without historical LAG/window computation."""
    names = sorted(set(metric_names))
    if not names or not store.path.exists():
        return []
    query = """
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
          dimensions_json
        FROM connector_metric_facts
        WHERE connector_id = ?
          AND evidence_id = ?
          AND metric_name = ANY(?)
        ORDER BY metric_name ASC, dimensions_json ASC
    """
    with _DUCKDB_LOCK, store._connect(read_only=True) as connection:  # noqa: SLF001
        rows = connection.execute(query, [connector_id, evidence_id, names]).fetchall()
    return [
        _metric_fact_from_row((*row, None, None, None, None, None))
        for row in rows
    ]
