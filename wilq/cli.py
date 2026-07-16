from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.google_ads.oauth import (
    DEFAULT_REDIRECT_URI,
    exchange_google_ads_oauth_code,
    google_ads_oauth_authorization_url,
)
from wilq.connectors.localo.oauth import (
    DEFAULT_LOCALO_REDIRECT_URI,
    exchange_localo_oauth_code,
    localo_oauth_authorization_url,
)
from wilq.connectors.refresh import run_connector_refresh
from wilq.connectors.registry import list_connector_statuses
from wilq.connectors.wordpress.client import WordPressDraftReadError, read_wordpress_draft_post
from wilq.content.workflow.store import (
    WordPressRevisionApplyClaimFinalStatus,
    content_workflow_store,
)
from wilq.credentials.runtime import credential_runtime_status
from wilq.jobs.models import JobRunRequest
from wilq.jobs.registry import list_jobs
from wilq.jobs.scheduler import list_job_runs, run_job, scheduler_status
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRequest
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store
from wilq.storage.recovery import copy_storage_pair

app = typer.Typer(help="WILQ local operator CLI for API-backed runtime checks.")
connectors_app = typer.Typer(help="Connector readiness and refresh commands.")
metrics_app = typer.Typer(help="DuckDB analytics metric store commands.")
jobs_app = typer.Typer(help="Local job orchestration commands.")
google_ads_app = typer.Typer(help="Google Ads OAuth and operator setup commands.")
localo_app = typer.Typer(help="Localo MCP OAuth setup commands.")
wordpress_apply_app = typer.Typer(help="Recovery of interrupted WordPress draft applies.")
storage_app = typer.Typer(help="Non-destructive local pilot storage recovery commands.")
app.add_typer(connectors_app, name="connectors")
app.add_typer(metrics_app, name="metrics")
app.add_typer(jobs_app, name="jobs")
app.add_typer(google_ads_app, name="google-ads")
app.add_typer(localo_app, name="localo")
app.add_typer(wordpress_apply_app, name="wordpress-apply")
app.add_typer(storage_app, name="storage")


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


@storage_app.command("backup")
def storage_backup(
    sqlite_source: Annotated[Path, typer.Option("--sqlite-source")],
    duckdb_source: Annotated[Path, typer.Option("--duckdb-source")],
    sqlite_destination: Annotated[Path, typer.Option("--sqlite-destination")],
    duckdb_destination: Annotated[Path, typer.Option("--duckdb-destination")],
) -> None:
    """Copy both stores to new alternate paths and report recovery proof."""
    _copy_storage_pair(
        sqlite_source=sqlite_source,
        duckdb_source=duckdb_source,
        sqlite_destination=sqlite_destination,
        duckdb_destination=duckdb_destination,
    )


@storage_app.command("restore")
def storage_restore(
    sqlite_backup: Annotated[Path, typer.Option("--sqlite-backup")],
    duckdb_backup: Annotated[Path, typer.Option("--duckdb-backup")],
    sqlite_destination: Annotated[Path, typer.Option("--sqlite-destination")],
    duckdb_destination: Annotated[Path, typer.Option("--duckdb-destination")],
) -> None:
    """Restore a backup into new alternate paths and report recovery proof."""
    _copy_storage_pair(
        sqlite_source=sqlite_backup,
        duckdb_source=duckdb_backup,
        sqlite_destination=sqlite_destination,
        duckdb_destination=duckdb_destination,
    )


def _copy_storage_pair(
    *,
    sqlite_source: Path,
    duckdb_source: Path,
    sqlite_destination: Path,
    duckdb_destination: Path,
) -> None:
    proof = copy_storage_pair(
        sqlite_source=sqlite_source,
        duckdb_source=duckdb_source,
        sqlite_destination=sqlite_destination,
        duckdb_destination=duckdb_destination,
    )
    _print_json(
        {
            "destination_mode": "alternative_paths_only",
            "proof": proof,
        }
    )


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


@google_ads_app.command("oauth-url")
def google_ads_oauth_url(
    redirect_uri: Annotated[
        str,
        typer.Option("--redirect-uri", help="Loopback redirect URI configured for OAuth."),
    ] = DEFAULT_REDIRECT_URI,
    client_secret_file: Annotated[
        Path | None,
        typer.Option("--client-secret-file", help="OAuth desktop client JSON path."),
    ] = None,
) -> None:
    """Print a Google Ads OAuth consent URL without secret values."""
    _print_json(
        google_ads_oauth_authorization_url(
            redirect_uri=redirect_uri,
            client_secret_file=client_secret_file,
        )
    )


@google_ads_app.command("oauth-exchange")
def google_ads_oauth_exchange(
    redirect_url: Annotated[
        str | None,
        typer.Option("--redirect-url", help="Final localhost redirect URL containing ?code=."),
    ] = None,
    code: Annotated[
        str | None,
        typer.Option("--code", help="OAuth authorization code if copied separately."),
    ] = None,
    redirect_uri: Annotated[
        str,
        typer.Option("--redirect-uri", help="Same redirect URI used by oauth-url."),
    ] = DEFAULT_REDIRECT_URI,
    write_env: Annotated[
        bool,
        typer.Option("--write-env", help="Write GOOGLE_ADS_REFRESH_TOKEN to local .env."),
    ] = False,
    client_secret_file: Annotated[
        Path | None,
        typer.Option("--client-secret-file", help="OAuth desktop client JSON path."),
    ] = None,
) -> None:
    """Exchange Google Ads OAuth code and optionally update local .env."""
    _print_json(
        exchange_google_ads_oauth_code(
            code=code,
            redirect_url=redirect_url,
            redirect_uri=redirect_uri,
            write_env=write_env,
            client_secret_file=client_secret_file,
        )
    )


@localo_app.command("oauth-url")
def localo_oauth_url(
    redirect_uri: Annotated[
        str,
        typer.Option("--redirect-uri", help="Loopback redirect URI for Localo OAuth."),
    ] = DEFAULT_LOCALO_REDIRECT_URI,
) -> None:
    """Print a Localo MCP OAuth consent URL without credential values."""
    _print_json(localo_oauth_authorization_url(redirect_uri=redirect_uri))


@localo_app.command("oauth-exchange")
def localo_oauth_exchange(
    code_verifier: Annotated[
        str,
        typer.Option("--code-verifier", help="PKCE code_verifier from localo oauth-url."),
    ],
    redirect_url: Annotated[
        str | None,
        typer.Option("--redirect-url", help="Final localhost redirect URL containing ?code=."),
    ] = None,
    code: Annotated[
        str | None,
        typer.Option("--code", help="OAuth authorization code if copied separately."),
    ] = None,
    redirect_uri: Annotated[
        str,
        typer.Option("--redirect-uri", help="Same redirect URI used by oauth-url."),
    ] = DEFAULT_LOCALO_REDIRECT_URI,
    write_env: Annotated[
        bool,
        typer.Option("--write-env", help="Write LOCALO_ACCESS_TOKEN to local .env."),
    ] = False,
) -> None:
    """Exchange Localo OAuth code and optionally update local .env."""
    _print_json(
        exchange_localo_oauth_code(
            code=code,
            redirect_url=redirect_url,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            write_env=write_env,
        )
    )


@wordpress_apply_app.command("reconcile")
def wordpress_apply_reconcile(
    work_item_id: Annotated[
        str,
        typer.Option("--work-item-id", help="Work item with one unresolved apply claim."),
    ],
    outcome: Annotated[
        str,
        typer.Option("--outcome", help="Explicit result: applied or failed."),
    ],
    confirmed_by: Annotated[
        str,
        typer.Option("--confirmed-by", help="Local operator attribution."),
    ],
    notes: Annotated[
        str,
        typer.Option("--notes", help="What was checked in WordPress."),
    ],
    wordpress_post_id: Annotated[
        str | None,
        typer.Option("--wordpress-post-id", help="Required for an applied draft."),
    ] = None,
    confirm_inspection: Annotated[
        bool,
        typer.Option(
            "--confirm-inspection",
            help="Confirm that WordPress was inspected and no write should be retried.",
        ),
    ] = False,
) -> None:
    """Resolve a crashed apply after WordPress inspection, without retrying the write."""
    normalized_outcome = outcome.strip().lower()
    if normalized_outcome not in {"applied", "failed"}:
        raise typer.BadParameter("--outcome musi mieć wartość applied albo failed.")
    if not confirmed_by.strip() or not notes.strip():
        raise typer.BadParameter("Wymagane są --confirmed-by i niepusta --notes.")
    if not confirm_inspection:
        raise typer.BadParameter(
            "Wymagane jest --confirm-inspection po ręcznym sprawdzeniu WordPress."
        )
    if normalized_outcome == "applied":
        if not wordpress_post_id:
            raise typer.BadParameter("Applied wymaga --wordpress-post-id.")
        try:
            readback = read_wordpress_draft_post(wordpress_post_id)
        except WordPressDraftReadError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if readback.status != "draft":
            raise typer.BadParameter("Wskazany wpis WordPress nie ma statusu draft.")
    elif wordpress_post_id is not None:
        raise typer.BadParameter("Failed nie może wskazywać WordPress post ID.")

    resolved_outcome = cast(WordPressRevisionApplyClaimFinalStatus, normalized_outcome)
    try:
        audit = content_workflow_store().reconcile_wordpress_revision_apply_claim(
            work_item_id=work_item_id,
            outcome=resolved_outcome,
            reconciled_by=confirmed_by.strip(),
            notes=notes.strip(),
            wordpress_post_id=wordpress_post_id,
        )
    except (RuntimeError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    _print_json(
        {
            "status": "reconciled",
            "work_item_id": work_item_id,
            "outcome": normalized_outcome,
            "wordpress_post_id": wordpress_post_id,
            "audit_event_id": audit.id,
            "external_write_retried": False,
            "actor_contract": "local_operator_attribution_only",
        }
    )


def _print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    app()
