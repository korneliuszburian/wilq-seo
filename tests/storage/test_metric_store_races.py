from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import duckdb
import pytest

from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
)
from wilq.storage import metric_store as metric_store_module
from wilq.storage.metric_store import DuckDbMetricStore, metric_store
from wilq.storage.schema_versions import DUCKDB_SCHEMA_VERSION


def test_metric_store_rolls_back_delete_and_partial_insert_on_insert_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metric_db = tmp_path / "metrics.duckdb"
    monkeypatch.setenv("WILQ_METRIC_DB", str(metric_db))
    collected_at = datetime.now(UTC) - timedelta(minutes=5)
    store = metric_store()
    store.save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_atomic_replace",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=collected_at,
            completed_at=collected_at,
            evidence_ids=["ev_refresh_atomic_replace_original"],
            metric_summary={"active_users": 10, "sessions": 20},
            summary="Original metric batch.",
        )
    )
    original_metric_row = metric_store_module._metric_row

    def invalid_metric_row(
        run: ConnectorRefreshRun,
        name: str,
        value: float | int | str,
        *,
        insert_sequence: int,
    ) -> metric_store_module.MetricRow:
        row = original_metric_row(
            run,
            name,
            value,
            insert_sequence=insert_sequence,
        )
        if name != "sessions":
            return row
        invalid_row = list(row)
        invalid_row[3] = "not-a-double"
        return cast(metric_store_module.MetricRow, tuple(invalid_row))

    monkeypatch.setattr(metric_store_module, "_metric_row", invalid_metric_row)

    with pytest.raises(duckdb.Error):
        store.save_connector_refresh_metrics(
            ConnectorRefreshRun(
                id="refresh_atomic_replace",
                connector_id="google_analytics_4",
                mode=ConnectorRefreshMode.vendor_read,
                status=ConnectorRefreshStatus.completed,
                started_at=collected_at,
                completed_at=collected_at,
                evidence_ids=["ev_refresh_atomic_replace_failed"],
                metric_summary={"active_users": 11, "sessions": 21},
                summary="Injected failed replacement batch.",
            )
        )

    with duckdb.connect(str(metric_db), read_only=True) as connection:
        stored_rows = connection.execute(
            """
            SELECT metric_name, metric_value_double, evidence_id, insert_sequence
            FROM connector_metric_facts
            WHERE run_id = 'refresh_atomic_replace'
            ORDER BY metric_name
            """
        ).fetchall()
    assert stored_rows == [
        ("active_users", 10.0, "ev_refresh_atomic_replace_original", 1),
        ("sessions", 20.0, "ev_refresh_atomic_replace_original", 1),
    ]


def test_metric_store_orders_same_timestamp_history_by_insert_sequence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metric_db = tmp_path / "metrics.duckdb"
    monkeypatch.setenv("WILQ_METRIC_DB", str(metric_db))
    collected_at = datetime(2026, 8, 7, 10, 30, tzinfo=UTC)
    store = metric_store()
    for run_id, evidence_id, value in (
        ("refresh_same_time_first", "ev_z_first", 10),
        ("refresh_same_time_second", "ev_a_second", 15),
    ):
        store.save_connector_refresh_metrics(
            ConnectorRefreshRun(
                id=run_id,
                connector_id="google_analytics_4",
                mode=ConnectorRefreshMode.vendor_read,
                status=ConnectorRefreshStatus.completed,
                started_at=collected_at,
                completed_at=collected_at,
                evidence_ids=[evidence_id],
                metric_summary={"active_users": value},
                summary="Same-timestamp metric history.",
            )
        )

    facts = {
        fact.evidence_id: fact
        for fact in store.list_metric_facts_by_evidence_ids(
            ["ev_z_first", "ev_a_second"]
        )
    }
    with duckdb.connect(str(metric_db), read_only=True) as connection:
        insert_order = connection.execute(
            """
            SELECT run_id, insert_sequence
            FROM connector_metric_facts
            ORDER BY insert_sequence
            """
        ).fetchall()

    assert insert_order == [
        ("refresh_same_time_first", 1),
        ("refresh_same_time_second", 2),
    ]
    assert facts["ev_z_first"].previous_value is None
    assert facts["ev_a_second"].previous_value == 10
    assert facts["ev_a_second"].previous_evidence_id == "ev_z_first"


def test_metric_store_migrates_insert_sequence_without_data_loss(tmp_path: Path) -> None:
    metric_path = tmp_path / "version_1.duckdb"
    with duckdb.connect(str(metric_path)) as connection:
        connection.execute(
            """
            CREATE TABLE connector_metric_facts (
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
            INSERT INTO connector_metric_facts VALUES
              ('run_first', 'gsc', 'clicks', 1, NULL, 'number', 'connector_refresh',
               NULL, '{}', 'vendor_read', 'completed', TIMESTAMP '2026-08-07 10:30:00',
               'ev_z_first'),
              ('run_second', 'gsc', 'clicks', 2, NULL, 'number', 'connector_refresh',
               NULL, '{}', 'vendor_read', 'completed', TIMESTAMP '2026-08-07 10:30:00',
               'ev_a_second')
            """
        )
        connection.execute(
            """
            CREATE TABLE wilq_schema_metadata (
              store_key VARCHAR PRIMARY KEY,
              version INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO wilq_schema_metadata VALUES ('metric_store', 1)"
        )

    status = DuckDbMetricStore(metric_path).status()

    with duckdb.connect(str(metric_path), read_only=True) as connection:
        migrated_rows = connection.execute(
            """
            SELECT run_id, evidence_id, insert_sequence
            FROM connector_metric_facts
            ORDER BY insert_sequence
            """
        ).fetchall()
        columns = {
            row[1]: row[3]
            for row in connection.execute(
                "PRAGMA table_info('connector_metric_facts')"
            ).fetchall()
        }
    assert status["schema_version"] == DUCKDB_SCHEMA_VERSION
    assert status["metric_fact_count"] == 2
    assert migrated_rows == [
        ("run_first", "ev_z_first", 1),
        ("run_second", "ev_a_second", 2),
    ]
    assert columns["insert_sequence"] is True
