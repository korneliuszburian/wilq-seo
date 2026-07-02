from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]

from wilq.connectors.refresh import run_connector_refresh
from wilq.jobs.models import JobRun, JobRunRequest, ScheduledJob
from wilq.jobs.registry import get_job, list_jobs
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus, utc_now
from wilq.storage.local_state import local_state_store


def scheduler_status() -> dict[str, Any]:
    jobs = list_jobs()
    return {
        "backend": "apscheduler",
        "autostart": False,
        "configured_jobs": len(jobs),
        "enabled_jobs": sum(1 for job in jobs if job.enabled),
        "notes": [
            "Goal 001 exposes deterministic job definitions and manual run endpoints.",
            "The background scheduler is not auto-started by the API process.",
        ],
    }


def build_background_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    for job in list_jobs():
        if job.schedule == "interval" and job.interval_minutes is not None:
            scheduler.add_job(
                lambda job_id=job.id: run_job(job_id, JobRunRequest(reason="scheduled")),
                "interval",
                minutes=job.interval_minutes,
                id=job.id,
                replace_existing=True,
                max_instances=1,
            )
    return scheduler


def run_job(job_id: str, request: JobRunRequest | None = None) -> JobRun | None:
    job = get_job(job_id)
    if job is None:
        return None
    started_at = utc_now()
    reason = request.reason if request else None
    connector_refresh_run_ids: list[str] = []
    evidence_ids: list[str] = []
    errors: list[str] = []
    statuses: list[ConnectorRefreshStatus] = []

    for connector_id in job.connector_ids:
        try:
            refresh = run_connector_refresh(
                connector_id,
                ConnectorRefreshRequest(
                    mode=job.refresh_mode,
                    reason=reason or f"job:{job.id}",
                ),
            )
        except Exception as error:
            errors.append(f"{connector_id}: connector_refresh_failed:{type(error).__name__}")
            statuses.append(ConnectorRefreshStatus.failed)
            continue
        if refresh is None:
            errors.append(f"Unknown connector: {connector_id}")
            statuses.append(ConnectorRefreshStatus.failed)
            continue
        connector_refresh_run_ids.append(refresh.id)
        evidence_ids.extend(refresh.evidence_ids)
        errors.extend(refresh.errors)
        statuses.append(refresh.status)

    run = JobRun(
        id=f"jobrun_{job.id}_{uuid4().hex[:10]}",
        job_id=job.id,
        status=_job_status(job, statuses),
        started_at=started_at,
        completed_at=utc_now(),
        connector_refresh_run_ids=connector_refresh_run_ids,
        evidence_ids=sorted(set(evidence_ids)),
        errors=errors,
    )
    return local_state_store().save_job_run(run)


def list_job_runs() -> list[JobRun]:
    return local_state_store().list_job_runs()


def get_job_run(run_id: str) -> JobRun | None:
    return local_state_store().get_job_run(run_id)


def _job_status(
    job: ScheduledJob,
    statuses: list[ConnectorRefreshStatus],
) -> Literal["completed", "blocked", "failed"]:
    if not statuses or ConnectorRefreshStatus.failed in statuses:
        return "failed"
    if ConnectorRefreshStatus.blocked in statuses:
        return "blocked"
    if len(statuses) != len(job.connector_ids):
        return "blocked"
    return "completed"
