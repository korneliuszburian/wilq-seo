from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from wilq.schemas import ActionRisk, utc_now


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
    status: Literal["ready", "blocked", "planned"] = "planned"
    status_label: str | None = None
    route: str | None = None
    route_label: str | None = None
    skill_id: str | None = None
    safe_next_step: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    missing_contracts: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low
    risk_label: str | None = None


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    status: Literal["queued", "running", "completed", "failed", "blocked"]
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    input: WorkflowInput = Field(default_factory=WorkflowInput)
    output: WorkflowOutput = Field(default_factory=WorkflowOutput)


class WorkflowRunCreateRequest(BaseModel):
    id: str | None = None
    input: WorkflowInput = Field(default_factory=WorkflowInput)


class WorkflowEvidence(BaseModel):
    workflow_run_id: str
    evidence_ids: list[str] = Field(default_factory=list)


class WorkflowActionObject(BaseModel):
    workflow_run_id: str
    action_ids: list[str] = Field(default_factory=list)
