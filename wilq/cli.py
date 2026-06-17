from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.refresh import run_connector_refresh
from wilq.connectors.registry import list_connector_statuses
from wilq.credentials.runtime import credential_runtime_status
from wilq.jobs.models import JobRunRequest
from wilq.jobs.registry import list_jobs
from wilq.jobs.scheduler import list_job_runs, run_job, scheduler_status
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRequest
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

app = typer.Typer(help="WILQ local operator CLI for API-backed runtime checks.")
connectors_app = typer.Typer(help="Connector readiness and refresh commands.")
metrics_app = typer.Typer(help="DuckDB analytics metric store commands.")
jobs_app = typer.Typer(help="Local job orchestration commands.")
app.add_typer(connectors_app, name="connectors")
app.add_typer(metrics_app, name="metrics")
app.add_typer(jobs_app, name="jobs")


@app.command()
def status() -> None:
    """Print local WILQ runtime status without secret values."""
    _print_json(
        {
            "credential_runtime": credential_runtime_status(detailed=False),
            "codex_runtime": codex_runtime_status(),
            "job_scheduler": scheduler_status(),
            "local_state": local_state_store().status(),
            "metric_store": metric_store().status(),
        }
    )


@connectors_app.command("status")
def connectors_status() -> None:
    """Print connector readiness without credential values."""
    _print_json([connector.model_dump(mode="json") for connector in list_connector_statuses()])


@connectors_app.command("refresh")
def connector_refresh(
    connector_id: Annotated[str, typer.Argument(help="Connector ID, for example google_ads.")],
    mode: Annotated[
        ConnectorRefreshMode,
        typer.Option("--mode", help="Refresh mode."),
    ] = ConnectorRefreshMode.status_probe,
    reason: Annotated[str | None, typer.Option("--reason", help="Operator reason.")] = None,
) -> None:
    """Run a connector refresh and persist redacted state plus metric facts."""
    run = run_connector_refresh(
        connector_id,
        ConnectorRefreshRequest(mode=mode, reason=reason),
    )
    if run is None:
        raise typer.BadParameter(f"Unknown connector: {connector_id}")
    _print_json(run.model_dump(mode="json"))


@metrics_app.command("status")
def metrics_status() -> None:
    """Print DuckDB metric store status."""
    _print_json(metric_store().status())


@metrics_app.command("list")
def metrics_list(
    connector_id: Annotated[
        str | None,
        typer.Option("--connector-id", help="Optional connector ID filter."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 100,
) -> None:
    """Print stored connector metric facts."""
    facts = metric_store().list_metric_facts(connector_id, limit)
    _print_json([fact.model_dump(mode="json") for fact in facts])


@jobs_app.command("status")
def jobs_status() -> None:
    """Print local job scheduler status."""
    _print_json(scheduler_status())


@jobs_app.command("list")
def jobs_list() -> None:
    """Print configured local jobs."""
    _print_json([job.model_dump(mode="json") for job in list_jobs()])


@jobs_app.command("run")
def jobs_run(
    job_id: Annotated[str, typer.Argument(help="Job ID, for example connector_status_probe_all.")],
    reason: Annotated[str | None, typer.Option("--reason", help="Operator reason.")] = None,
) -> None:
    """Run a local job and persist redacted job/refresh state."""
    run = run_job(job_id, JobRunRequest(reason=reason))
    if run is None:
        raise typer.BadParameter(f"Unknown job: {job_id}")
    _print_json(run.model_dump(mode="json"))


@jobs_app.command("runs")
def jobs_runs() -> None:
    """Print persisted local job runs."""
    _print_json([run.model_dump(mode="json") for run in list_job_runs()])


def _print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    app()
