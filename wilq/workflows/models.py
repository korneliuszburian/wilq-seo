from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import missing_contract_labels
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
    missing_contract_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low
    risk_label: str | None = None

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> "Workflow":
        if not self.missing_contract_labels:
            self.missing_contract_labels = missing_contract_labels(self.missing_contracts)
        return self


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    status: Literal["queued", "running", "completed", "failed", "blocked"]
    status_label: str = ""
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    input: WorkflowInput = Field(default_factory=WorkflowInput)
    output: WorkflowOutput = Field(default_factory=WorkflowOutput)

    @model_validator(mode="after")
    def hydrate_labels(self) -> "WorkflowRun":
        if not self.status_label:
            self.status_label = _workflow_run_status_label(self.status)
        return self


class WorkflowRunCreateRequest(BaseModel):
    id: str | None = None
    input: WorkflowInput = Field(default_factory=WorkflowInput)


class WorkflowEvidence(BaseModel):
    workflow_run_id: str
    evidence_ids: list[str] = Field(default_factory=list)


class WorkflowActionObject(BaseModel):
    workflow_run_id: str
    action_ids: list[str] = Field(default_factory=list)


def _workflow_run_status_label(status: str) -> str:
    labels = {
        "queued": "czeka na uruchomienie",
        "running": "w trakcie",
        "completed": "zakończone",
        "failed": "błąd",
        "blocked": "zablokowane",
    }
    return labels.get(status, "status uruchomienia do sprawdzenia")
