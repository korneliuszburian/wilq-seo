from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from apps.api.wilq_api.main import app
from wilq.cli import app as cli_app
from wilq.connectors.refresh import get_connector_refresh_run, run_connector_refresh
from wilq.jobs.registry import list_jobs
from wilq.jobs.scheduler import run_job
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRequest

client = TestClient(app)

FAKE_JOBS_API_SECRET = "sk-jobs-api-redaction-test"  # pragma: allowlist secret
FAKE_JOBS_CLI_SECRET = "sk-jobs-cli-redaction-test"  # pragma: allowlist secret


def test_configured_vendor_read_job_only_includes_implemented_vendor_adapters() -> None:
    jobs = {job.id: job for job in list_jobs()}
    job = jobs["configured_vendor_read_refresh"]

    assert "google_ads" in job.connector_ids
    assert "google_search_console" in job.connector_ids
    assert "google_analytics_4" in job.connector_ids
    assert "google_merchant_center" in job.connector_ids
    assert "ahrefs" in job.connector_ids
    assert "localo" in job.connector_ids
    assert "wordpress_ekologus" in job.connector_ids
    assert "wordpress_sklep" in job.connector_ids
    assert "openai_codex" not in job.connector_ids


def test_jobs_api_runs_connector_status_probe_without_secret_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", FAKE_JOBS_API_SECRET)

    status_response = client.get("/api/jobs/status")
    assert status_response.status_code == 200
    assert status_response.json()["backend"] == "apscheduler"
    assert status_response.json()["autostart"] is False

    jobs_response = client.get("/api/jobs")
    assert jobs_response.status_code == 200
    jobs = {job["id"]: job for job in jobs_response.json()}
    assert jobs["connector_status_probe_all"]["refresh_mode"] == "status_probe"
    assert jobs["connector_status_probe_all"]["schedule"] == "interval"

    run_response = client.post(
        "/api/jobs/connector_status_probe_all/run",
        json={"reason": "jobs API contract test"},
    )

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["job_id"] == "connector_status_probe_all"
    assert run["status"] == "completed"
    assert len(run["connector_refresh_run_ids"]) >= 10
    assert "[REDACTED]" not in run["connector_refresh_run_ids"]
    assert FAKE_JOBS_API_SECRET not in run_response.text

    runs_response = client.get("/api/job-runs")
    assert runs_response.status_code == 200
    assert runs_response.json()[0]["id"] == run["id"]

    system_status_response = client.get("/api/system/status")
    assert system_status_response.status_code == 200
    assert system_status_response.json()["local_state"]["job_runs"] == 1


def test_connector_refresh_marks_run_failed_when_metric_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))

    class BrokenMetricStore:
        def save_connector_refresh_metrics(self, *args: object, **kwargs: object) -> int:
            raise RuntimeError("duckdb lock path should stay sanitized")

    monkeypatch.setattr("wilq.connectors.refresh.metric_store", lambda: BrokenMetricStore())

    run = run_connector_refresh(
        "google_ads",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.status_probe, reason="test"),
    )

    assert run is not None
    assert run.status == "failed"
    assert run.metrics_persisted is False
    assert "metric_persistence_failed:RuntimeError" in run.errors
    assert "duckdb lock path" not in " ".join(run.errors)

    persisted = get_connector_refresh_run(run.id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.metrics_persisted is False


def test_job_run_persists_failed_status_when_connector_refresh_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))

    def broken_refresh(*args: object, **kwargs: object) -> None:
        raise RuntimeError("vendor payload should stay sanitized")

    monkeypatch.setattr("wilq.jobs.scheduler.run_connector_refresh", broken_refresh)

    run = run_job("connector_status_probe_all")

    assert run is not None
    assert run.status == "failed"
    assert run.connector_refresh_run_ids == []
    assert run.errors
    assert all("connector_refresh_failed:RuntimeError" in error for error in run.errors)
    assert "vendor payload" not in " ".join(run.errors)


def test_wilq_cli_jobs_run_persists_redacted_job_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", FAKE_JOBS_CLI_SECRET)
    runner = CliRunner()

    status_result = runner.invoke(cli_app, ["jobs", "status"])
    assert status_result.exit_code == 0
    assert json.loads(status_result.stdout)["backend"] == "apscheduler"

    run_result = runner.invoke(
        cli_app,
        ["jobs", "run", "connector_status_probe_all", "--reason", "cli job contract test"],
    )

    assert run_result.exit_code == 0
    run = json.loads(run_result.stdout)
    assert run["job_id"] == "connector_status_probe_all"
    assert run["status"] == "completed"
    assert "[REDACTED]" not in run["connector_refresh_run_ids"]
    assert FAKE_JOBS_CLI_SECRET not in run_result.stdout

    runs_result = runner.invoke(cli_app, ["jobs", "runs"])
    assert runs_result.exit_code == 0
    runs = json.loads(runs_result.stdout)
    assert runs[0]["id"] == run["id"]
