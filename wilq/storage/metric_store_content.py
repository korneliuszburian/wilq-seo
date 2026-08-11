from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

import duckdb

from wilq.content.canonical.landing_identity import (
    landing_page_metric_legacy_base_urls,
    landing_page_metric_lookup_path,
)
from wilq.content.canonical.metric_dimensions import (
    LANDING_IDENTITY_DIMENSION,
    dimensions_with_metric_identity,
    metric_dimensions_landing_identity,
    metric_dimensions_match_landing,
)
from wilq.schemas import MetricFact
from wilq.storage.metric_store_read import (
    _DUCKDB_LOCK,
    MAX_METRIC_FACT_READ_LIMIT,
    _metric_delta,
    _metric_fact_from_row,
    _parse_dimensions,
)


class _ContentUrlMetricReadMixin:
    def _connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        raise NotImplementedError

    def _metric_fact_read_limit(self) -> int:
        raise NotImplementedError

    def list_metric_facts_for_content_url(
        self,
        connector_ids: list[str],
        content_url: str,
        *,
        content_path: str,
        limit: int = MAX_METRIC_FACT_READ_LIMIT,
    ) -> list[MetricFact]:
        if not connector_ids or not content_url or not content_path:
            return []
        bounded_limit = max(1, min(limit, self._metric_fact_read_limit()))
        # Keep one predecessor available for the publication-facing delta
        # calculation. The public limit is applied after identity filtering
        # and history enrichment, never before either of those decisions.
        candidate_limit = max(bounded_limit + 1, self._metric_fact_read_limit())
        identity_dimensions = dimensions_with_metric_identity({"page": content_url})
        landing_identity = identity_dimensions.get(LANDING_IDENTITY_DIMENSION)
        if not landing_identity:
            return []
        legacy_match = _legacy_url_matching_predicate(
            content_url, content_path, landing_identity
        )
        functional_identity, legacy_join, legacy_condition, legacy_params = legacy_match
        # Resolve legacy URL dimensions into the same private identity before
        # applying the bounded read limit. A base-path SQL predicate alone
        # would let functional-query interlopers consume the limit and only be
        # rejected by the public matcher afterwards.
        query = """
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
            {legacy_join}
            WHERE facts.connector_id = ANY(?)
              AND (
                json_extract_string(facts.dimensions_json, '$._wilq_landing_identity') = ?
                {legacy_condition}
                OR (
                  facts.connector_id = 'google_analytics_4'
                  AND (
                    lower(rtrim(split_part(
                      json_extract_string(facts.dimensions_json, '$.landing_page'), '?', 1
                    ), '/')) = lower(rtrim(?, '/'))
                    OR lower(rtrim(split_part(
                      json_extract_string(
                        facts.dimensions_json, '$.landing_page_plus_query_string'
                      ), '?', 1
                    ), '/')) = lower(rtrim(?, '/'))
                  )
                )
              )
            ORDER BY
              facts.collected_at DESC,
              facts.connector_id ASC,
              facts.metric_name ASC,
              facts.dimensions_json ASC,
              facts.evidence_id ASC
            LIMIT ?
        """.replace("{legacy_join}", legacy_join).replace(  # nosec B608
            "{legacy_condition}", legacy_condition
        )
        params: list[Any] = [
            list(dict.fromkeys(connector_ids)),
            landing_identity,
            *( [landing_identity] if functional_identity else legacy_params ),
            content_path,
            content_path,
            candidate_limit,
        ]
        with _DUCKDB_LOCK, self._connect(read_only=True) as connection:
            if functional_identity:
                _prepare_legacy_landing_identity_index(
                    connection,
                    list(dict.fromkeys(connector_ids)),
                    content_url=content_url,
                    content_path=content_path,
                )
            rows = connection.execute(query, params).fetchall()
        return _post_filter_content_metric_history(
            rows,
            content_url=content_url,
            bounded_limit=bounded_limit,
        )


def _legacy_url_matching_predicate(
    content_url: str,
    content_path: str,
    landing_identity: str,
) -> tuple[bool, str, str, list[Any]]:
    legacy_dimension_paths = [
        "$.content_url",
        "$.final_url",
        "$.landing_page",
        "$.landing_page_plus_query_string",
        "$.page",
        "$.page_location",
    ]
    legacy_url_bases = [
        base.rstrip("/").casefold()
        for base in landing_page_metric_legacy_base_urls(content_url)
    ]
    functional_identity = "?" in landing_identity
    legacy_match = ""
    legacy_params: list[Any] = []
    if (
        not functional_identity
        and landing_page_metric_lookup_path(content_url) == content_path
    ):
        legacy_match = " OR (" + " OR ".join(
            "lower(rtrim(split_part("
            "json_extract_string(facts.dimensions_json, ?), '?', 1), '/')) = ANY(?)"
            for _ in legacy_dimension_paths
        ) + ")"
        legacy_params = [
            value
            for dimension_path in legacy_dimension_paths
            for value in (dimension_path, legacy_url_bases)
        ]
    legacy_join = (
        "LEFT JOIN wilq_legacy_landing_identity legacy\n"
        "              ON facts.run_id = legacy.run_id\n"
        "             AND facts.metric_name = legacy.metric_name\n"
        "             AND facts.dimensions_json = legacy.dimensions_json"
        if functional_identity
        else ""
    )
    legacy_condition = (
        " OR legacy.landing_identity = ?"
        if functional_identity
        else legacy_match
    )
    return functional_identity, legacy_join, legacy_condition, legacy_params


def _prepare_legacy_landing_identity_index(
    connection: duckdb.DuckDBPyConnection,
    connector_ids: list[str],
    *,
    content_url: str,
    content_path: str,
) -> None:
    connection.execute(
        """
        CREATE TEMP TABLE wilq_legacy_landing_identity (
          run_id VARCHAR NOT NULL,
          metric_name VARCHAR NOT NULL,
          dimensions_json VARCHAR NOT NULL,
          landing_identity VARCHAR NOT NULL,
          PRIMARY KEY (run_id, metric_name, dimensions_json)
        )
        """
    )
    if landing_page_metric_lookup_path(content_url) != content_path:
        return

    url_bases = [
        base.rstrip("/").casefold()
        for base in landing_page_metric_legacy_base_urls(content_url)
    ]

    base_match = """
        lower(rtrim(split_part(json_extract_string(dimensions_json, ?), '?', 1), '/'))
          = ANY(?)
    """
    dimension_paths = [
        "$.content_url",
        "$.final_url",
        "$.landing_page",
        "$.landing_page_plus_query_string",
        "$.page",
        "$.page_location",
    ]
    # The repeated predicate and JSON paths are module-owned
    # literals; connector IDs and URL bases are passed as bound parameters.
    query = f"""
        SELECT DISTINCT run_id, metric_name, dimensions_json
        FROM connector_metric_facts
        WHERE connector_id = ANY(?)
          AND json_extract_string(
            dimensions_json, '$._wilq_landing_identity'
          ) IS NULL
          AND ({" OR ".join(base_match for _ in dimension_paths)})
        """  # nosec B608
    stored_rows = connection.execute(
        query,
        [
            list(dict.fromkeys(connector_ids)),
            *[
                item
                for dimension_path in dimension_paths
                for item in (dimension_path, url_bases)
            ],
        ],
    ).fetchall()
    index_rows: list[tuple[str, str, str, str]] = []
    for run_id, metric_name, dimensions_json in stored_rows:
        public_dimensions = _parse_dimensions(cast(str, dimensions_json))
        landing_identity = metric_dimensions_landing_identity(public_dimensions)
        if landing_identity:
            index_rows.append(
                (
                    cast(str, run_id),
                    cast(str, metric_name),
                    cast(str, dimensions_json),
                    landing_identity,
                )
            )
    if index_rows:
        connection.executemany(
            """
            INSERT INTO wilq_legacy_landing_identity (
              run_id, metric_name, dimensions_json, landing_identity
            ) VALUES (?, ?, ?, ?)
            """,
            index_rows,
        )


def _post_filter_content_metric_history(
    rows: list[tuple[Any, ...]],
    *,
    content_url: str,
    bounded_limit: int,
) -> list[MetricFact]:
    facts = [_metric_fact_from_row(row) for row in rows]
    filtered = [
        fact
        for fact in facts
        if metric_dimensions_match_landing(
            fact.dimensions,
            content_url,
            allow_relative_path=fact.source_connector == "google_analytics_4",
        )
    ]
    return _apply_metric_history(filtered)[:bounded_limit]


def _apply_metric_history(facts: list[MetricFact]) -> list[MetricFact]:
    """Compute deltas only after the public landing-dimension filter."""
    previous_by_group: dict[tuple[str, str], MetricFact] = {}
    enriched_by_key: dict[tuple[str, str, str, str], MetricFact] = {}
    ordered = sorted(
        facts,
        key=lambda fact: (
            fact.collected_at or datetime.min.replace(tzinfo=UTC),
            fact.evidence_id,
        ),
    )
    for fact in ordered:
        group = (fact.source_connector, fact.name)
        previous = previous_by_group.get(group)
        delta, delta_percent, trend = _metric_delta(
            fact.value,
            previous.value if previous is not None else None,
        )
        enriched = fact.model_copy(
            update={
                "previous_value": previous.value if previous is not None else None,
                "previous_evidence_id": previous.evidence_id if previous is not None else None,
                "previous_collected_at": (
                    previous.collected_at if previous is not None else None
                ),
                "delta": delta,
                "delta_percent": delta_percent,
                "trend": trend,
            }
        )
        key = (
            fact.source_connector,
            fact.name,
            fact.evidence_id,
            json.dumps(fact.dimensions, sort_keys=True, ensure_ascii=False),
        )
        enriched_by_key[key] = enriched
        previous_by_group[group] = enriched
    return [
        enriched_by_key[
            (
                fact.source_connector,
                fact.name,
                fact.evidence_id,
                json.dumps(fact.dimensions, sort_keys=True, ensure_ascii=False),
            )
        ]
        for fact in facts
    ]
