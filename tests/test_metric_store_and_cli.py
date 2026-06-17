from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from apps.api.wilq_api.main import app
from wilq.cli import app as cli_app
from wilq.connectors.vendor import VendorReadResult
from wilq.schemas import ConnectorRefreshStatus
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
            "unit": None,
        }
    ]


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

    def flaky_connect(path: str) -> duckdb.DuckDBPyConnection:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise duckdb.IOException("IO Error: Conflicting lock is held by another process")
        return original_connect(path)

    monkeypatch.setattr("wilq.storage.metric_store.duckdb.connect", flaky_connect)
    monkeypatch.setattr("wilq.storage.metric_store.DUCKDB_CONNECT_RETRY_SECONDS", 0)

    connection = _connect_with_retry(tmp_path / "metrics.duckdb")
    try:
        assert calls == 2
    finally:
        connection.close()
