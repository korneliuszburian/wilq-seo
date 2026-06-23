from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from apps.api.wilq_api.main import app
from wilq.cli import app as cli_app
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.evidence.registry import get_evidence
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.metric_store import _connect_with_retry, metric_store

client = TestClient(app)


def test_connector_refresh_persists_metric_facts_to_duckdb(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    for key in (
        "AHREFS_API_TOKEN",
        "AHREFS_API_KEY",
    ):
        monkeypatch.setenv(key, "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "domain_rating": 24.0,
                "ahrefs_rank": 6433882,
                "target_source": "repo_env",
            },
        ),
    )

    response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "metric store contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["metric_summary"]["domain_rating"] == 24.0

    facts = metric_store().list_metric_facts(connector_id="ahrefs")
    facts_by_name = {fact.name: fact for fact in facts}
    assert facts_by_name["domain_rating"].value == 24
    assert facts_by_name["ahrefs_rank"].value == 6433882
    assert facts_by_name["target_source"].value == "repo_env"
    assert facts_by_name["domain_rating"].source_connector == "ahrefs"
    assert facts_by_name["domain_rating"].evidence_id.startswith("ev_refresh_")


def test_metrics_api_exposes_metric_store_status_and_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("AHREFS_API_TOKEN", "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 31.0},
        ),
    )

    refresh_response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "metrics API contract test"},
    )
    assert refresh_response.status_code == 200

    status_response = client.get("/api/metrics/status")
    assert status_response.status_code == 200
    assert status_response.json()["metric_fact_count"] == 1
    assert status_response.json()["backend"] == "duckdb"

    metrics_response = client.get("/api/metrics?connector_id=ahrefs")
    assert metrics_response.status_code == 200
    facts = metrics_response.json()
    assert facts == [
        {
            "name": "domain_rating",
            "value": 31,
            "period": "connector_refresh",
            "source_connector": "ahrefs",
            "evidence_id": refresh_response.json()["evidence_ids"][-1],
            "dimensions": {},
            "unit": None,
            "collected_at": refresh_response.json()["completed_at"],
            "previous_value": None,
            "delta": None,
            "delta_percent": None,
            "trend": "unknown",
            "freshness_state": "fresh",
            "freshness_label": "odświeżone mniej niż godzinę temu",
        }
    ]


def test_metric_store_exposes_previous_value_delta_and_freshness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(minutes=5)
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_ga4_delta_old",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=older,
            completed_at=older,
            evidence_ids=["ev_refresh_refresh_ga4_delta_old"],
            metric_summary={"active_users": 10, "traffic_source": "organic"},
            summary="Older GA4 metric facts.",
        )
    )
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_ga4_delta_new",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=newer,
            completed_at=newer,
            evidence_ids=["ev_refresh_refresh_ga4_delta_new"],
            metric_summary={"active_users": 15, "traffic_source": "organic"},
            summary="Newer GA4 metric facts.",
        )
    )

    facts = metric_store().list_metric_facts(connector_id="google_analytics_4")
    latest_facts_by_name: dict[str, MetricFact] = {}
    for fact in facts:
        latest_facts_by_name.setdefault(fact.name, fact)

    active_users = latest_facts_by_name["active_users"]
    assert active_users.value == 15
    assert active_users.previous_value == 10
    assert active_users.delta == 5
    assert active_users.delta_percent == 50
    assert active_users.trend == "up"
    assert active_users.freshness_state == "fresh"
    assert active_users.freshness_label == "odświeżone mniej niż godzinę temu"
    assert active_users.collected_at is not None

    traffic_source = latest_facts_by_name["traffic_source"]
    assert traffic_source.value == "organic"
    assert traffic_source.previous_value == "organic"
    assert traffic_source.delta is None
    assert traffic_source.trend == "unknown"


def test_metric_store_lists_metric_facts_by_connector_in_one_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(minutes=5)
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_batch_ga4_old",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=older,
            completed_at=older,
            evidence_ids=["ev_refresh_batch_ga4_old"],
            metric_summary={"active_users": 10},
            summary="Older GA4 metric facts.",
        )
    )
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_batch_ga4_new",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=newer,
            completed_at=newer,
            evidence_ids=["ev_refresh_batch_ga4_new"],
            metric_summary={"active_users": 15},
            summary="Newer GA4 metric facts.",
        )
    )
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_batch_gsc",
            connector_id="google_search_console",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=newer,
            completed_at=newer,
            evidence_ids=["ev_refresh_batch_gsc"],
            metric_summary={"clicks": 4, "impressions": 100},
            summary="GSC metric facts.",
        )
    )

    facts_by_connector = metric_store().list_metric_facts_by_connector(
        ["google_analytics_4", "google_search_console", "missing_connector"],
        limit_per_connector=1,
    )

    assert set(facts_by_connector) == {
        "google_analytics_4",
        "google_search_console",
        "missing_connector",
    }
    assert len(facts_by_connector["google_analytics_4"]) == 1
    ga4_fact = facts_by_connector["google_analytics_4"][0]
    assert ga4_fact.name == "active_users"
    assert ga4_fact.value == 15
    assert ga4_fact.previous_value == 10
    assert ga4_fact.delta == 5
    gsc_facts = facts_by_connector["google_search_console"]
    assert {fact.name for fact in gsc_facts} == {"clicks", "impressions"}
    assert all(fact.source_connector == "google_search_console" for fact in gsc_facts)
    assert facts_by_connector["missing_connector"] == []


def test_metric_store_lists_latest_metric_facts_by_connector_without_delta_cost(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(minutes=5)
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_latest_ga4_old",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=older,
            completed_at=older,
            evidence_ids=["ev_refresh_latest_ga4_old"],
            metric_summary={"active_users": 10},
            summary="Older GA4 metric facts.",
        )
    )
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_latest_ga4_new",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=newer,
            completed_at=newer,
            evidence_ids=["ev_refresh_latest_ga4_new"],
            metric_summary={"active_users": 15, "sessions": 20},
            summary="Newer GA4 metric facts.",
        )
    )

    facts_by_connector = metric_store().list_latest_metric_facts_by_connector(
        ["google_analytics_4", "missing_connector"],
        limit_per_connector=1,
    )

    assert set(facts_by_connector) == {"google_analytics_4", "missing_connector"}
    facts = facts_by_connector["google_analytics_4"]
    assert {fact.name for fact in facts} == {"active_users", "sessions"}
    assert {fact.evidence_id for fact in facts} == {"ev_refresh_latest_ga4_new"}
    assert all(fact.previous_value is None for fact in facts)
    assert facts_by_connector["missing_connector"] == []


def test_connector_refresh_persists_detailed_metric_facts_with_dimensions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("AHREFS_API_TOKEN", "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 24.0},
            metric_facts=[
                VendorMetricFact(
                    name="referring_domains",
                    value=12,
                    dimensions={"competitor_domain": "example.pl", "market": "PL"},
                )
            ],
        ),
    )

    response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "dimension contract test"},
    )

    assert response.status_code == 200
    facts = metric_store().list_metric_facts(connector_id="ahrefs")
    detailed = next(fact for fact in facts if fact.name == "referring_domains")
    assert detailed.value == 12
    assert detailed.dimensions == {"competitor_domain": "example.pl", "market": "PL"}
    assert detailed.period == "connector_refresh"
    assert detailed.evidence_id == response.json()["evidence_ids"][-1]


def test_metric_fact_evidence_ids_are_resolvable_without_refresh_run_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))

    run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_detached",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_merchant_center_detached"],
        metric_summary={"active_products": 12, "disapproved_products": 3},
        summary="Detached Merchant metric facts retained in DuckDB.",
    )
    metric_store().save_connector_refresh_metrics(run)

    evidence = get_evidence("ev_refresh_refresh_google_merchant_center_detached")

    assert evidence is not None
    assert evidence.source_connector == "google_merchant_center"
    assert evidence.source_type == "metric_fact_store"
    assert "active_products" in evidence.summary
    assert evidence.raw_ref == "metric_facts:ev_refresh_refresh_google_merchant_center_detached"


def test_wilq_cli_status_and_metrics_list_do_not_print_secret_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "gho_cli_secretvalue1234567890")
    runner = CliRunner()

    status_result = runner.invoke(cli_app, ["status"])
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["metric_store"]["backend"] == "duckdb"
    assert "gho_cli_secretvalue1234567890" not in status_result.stdout

    metrics_result = runner.invoke(cli_app, ["metrics", "list", "--limit", "5"])
    assert metrics_result.exit_code == 0
    assert json.loads(metrics_result.stdout) == []


def test_metric_store_retries_duckdb_conflicting_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = 0
    original_connect = duckdb.connect

    def flaky_connect(path: str, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise duckdb.IOException("IO Error: Conflicting lock is held by another process")
        return original_connect(path, read_only=read_only)

    monkeypatch.setattr("wilq.storage.metric_store.duckdb.connect", flaky_connect)
    monkeypatch.setattr("wilq.storage.metric_store.DUCKDB_CONNECT_RETRY_SECONDS", 0)

    connection = _connect_with_retry(tmp_path / "metrics.duckdb")
    try:
        assert calls == 2
    finally:
        connection.close()
