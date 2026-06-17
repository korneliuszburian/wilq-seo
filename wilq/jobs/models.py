from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from wilq.schemas import ConnectorRefreshMode, utc_now


class ScheduledJob(BaseModel):
    id: str
    label: str
    description: str
    connector_ids: list[str] = Field(default_factory=list)
    refresh_mode: ConnectorRefreshMode
    schedule: Literal["manual", "interval"]
    interval_minutes: int | None = None
    enabled: bool = True
    output_contract: str
    safety_notes: list[str] = Field(default_factory=list)


class JobRunRequest(BaseModel):
    reason: str | None = None


class JobRun(BaseModel):
    id: str
    job_id: str
    status: Literal["completed", "blocked", "failed"]
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    connector_refresh_run_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    redacted: bool = True

