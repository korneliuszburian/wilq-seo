from __future__ import annotations

from wilq.connectors.registry import list_connector_statuses
from wilq.jobs.models import ScheduledJob
from wilq.schemas import ConnectorRefreshMode

VENDOR_READ_CONNECTOR_IDS = {
    "google_ads",
    "google_search_console",
    "google_analytics_4",
    "google_merchant_center",
    "ahrefs",
    "localo",
    "wordpress_ekologus",
    "wordpress_sklep",
}


def list_jobs() -> list[ScheduledJob]:
    connector_ids = [connector.id for connector in list_connector_statuses()]
    return [
        ScheduledJob(
            id="connector_status_probe_all",
            label="Connector status probe",
            description="Probe local credential/config readiness for every connector.",
            connector_ids=connector_ids,
            refresh_mode=ConnectorRefreshMode.status_probe,
            schedule="interval",
            interval_minutes=60,
            output_contract=(
                "Persist one redacted connector refresh run per connector with evidence IDs, "
                "missing credential names and sanitized errors only."
            ),
            safety_notes=[
                "Does not call vendor APIs.",
                "Does not print or persist secret values.",
            ],
        ),
        ScheduledJob(
            id="configured_vendor_read_refresh",
            label="Configured vendor read refresh",
            description="Run read-only vendor refreshes for connectors that are configured.",
            connector_ids=[
                connector.id
                for connector in list_connector_statuses()
                if (
                    connector.configured
                    and connector.capabilities.read
                    and connector.id in VENDOR_READ_CONNECTOR_IDS
                )
            ],
            refresh_mode=ConnectorRefreshMode.vendor_read,
            schedule="manual",
            output_contract=(
                "Persist redacted aggregate refresh runs and DuckDB metric facts for configured "
                "read-only connectors. Missing or blocked vendors must return blocked state."
            ),
            safety_notes=[
                "Read-only vendor adapters only.",
                "No raw response bodies, query/page/user dumps or credential paths.",
                "No ActionObject write/apply path.",
            ],
        ),
    ]


def get_job(job_id: str) -> ScheduledJob | None:
    for job in list_jobs():
        if job.id == job_id:
            return job
    return None
