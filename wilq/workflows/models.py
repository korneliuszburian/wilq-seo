from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from wilq.schemas import utc_now


class WorkflowInput(BaseModel):
    connector_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowOutput(BaseModel):
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    id: str
    label: str
    required_connectors: list[str] = Field(default_factory=list)
    output_contract: str


class Workflow(BaseModel):
    id: str
    label: str
    description: str
    steps: list[WorkflowStep]


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    status: Literal["queued", "running", "completed", "failed", "blocked"]
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    input: WorkflowInput = Field(default_factory=WorkflowInput)
    output: WorkflowOutput = Field(default_factory=WorkflowOutput)


class WorkflowEvidence(BaseModel):
    workflow_run_id: str
    evidence_ids: list[str] = Field(default_factory=list)


class WorkflowActionObject(BaseModel):
    workflow_run_id: str
    action_ids: list[str] = Field(default_factory=list)
