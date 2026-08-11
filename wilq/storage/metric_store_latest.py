from __future__ import annotations

from typing import Any

import duckdb

from wilq.schemas import MetricFact
from wilq.storage.metric_store_read import (
    _DUCKDB_LOCK,
    _group_metric_facts_by_connector,
)


class _MetricFactLatestReadMixin:
    def _connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        raise NotImplementedError

    def _metric_fact_read_limit(self) -> int:
        raise NotImplementedError

    def list_latest_metric_facts_by_connector(
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
            connector_id: max(1, min(limit, self._metric_fact_read_limit()))
            for connector_id, limit in connector_limits.items()
        }
        query = """
            WITH connector_limits(connector_id, connector_limit) AS (
              SELECT unnest(?) AS connector_id, unnest(?) AS connector_limit
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
              NULL AS previous_value_kind,
              NULL AS previous_evidence_id,
              NULL AS previous_collected_at
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
            list(unique_connector_limits.keys()),
            list(unique_connector_limits.values()),
        ]
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            rows = connection.execute(query, params).fetchall()
        return _group_metric_facts_by_connector(
            rows,
            list(unique_connector_limits),
        )
