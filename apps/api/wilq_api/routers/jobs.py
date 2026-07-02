from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException

from wilq.jobs.models import JobRun, JobRunRequest, ScheduledJob
from wilq.jobs.registry import get_job, list_jobs
from wilq.jobs.scheduler import get_job_run, list_job_runs, run_job, scheduler_status


def create_jobs_router(clear_api_view_model_caches: Callable[[], None]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/jobs", response_model=list[ScheduledJob])
    def jobs() -> list[ScheduledJob]:
        return list_jobs()


    @router.get("/api/jobs/status")
    def jobs_status() -> dict[str, Any]:
        return scheduler_status()


    @router.get("/api/jobs/{job_id}", response_model=ScheduledJob)
    def job_detail(job_id: str) -> ScheduledJob:
        job = get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
        return job


    @router.post("/api/jobs/{job_id}/run", response_model=JobRun)
    def run_job_endpoint(job_id: str, request: JobRunRequest | None = None) -> JobRun:
        run = run_job(job_id, request)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
        clear_api_view_model_caches()
        return run


    @router.get("/api/job-runs", response_model=list[JobRun])
    def job_runs() -> list[JobRun]:
        return list_job_runs()


    @router.get("/api/job-runs/{run_id}", response_model=JobRun)
    def job_run_detail(run_id: str) -> JobRun:
        run = get_job_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Unknown job run: {run_id}")
        return run

    return router
