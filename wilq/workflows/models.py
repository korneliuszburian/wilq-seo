from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    blocked_claim_labels,
    evidence_count_label,
    missing_contract_count_label,
    missing_contract_labels,
    source_connector_labels,
    source_connector_summary_label,
    workflow_error_count_label,
)
from wilq.schemas import ActionRisk, utc_now


class WorkflowInput(BaseModel):
    connector_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowOutput(BaseModel):
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_summary_label: str = ""
    error_summary_label: str = ""

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> WorkflowOutput:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.error_summary_label:
            self.error_summary_label = workflow_error_count_label(self.errors)
        return self


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
    source_connector_labels: list[str] = Field(default_factory=list)
    source_connector_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    missing_contracts: list[str] = Field(default_factory=list)
    missing_contract_labels: list[str] = Field(default_factory=list)
    missing_contract_summary_label: str = ""
    missing_contract_detail_label: str = ""
    risk: ActionRisk = ActionRisk.low
    risk_label: str | None = None

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> Workflow:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        if not self.source_connector_summary_label:
            self.source_connector_summary_label = source_connector_summary_label(
                self.source_connectors
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = blocked_claim_labels(self.blocked_claims)
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(self.blocked_claims)
        if not self.missing_contract_labels:
            self.missing_contract_labels = missing_contract_labels(self.missing_contracts)
        if not self.missing_contract_summary_label:
            self.missing_contract_summary_label = missing_contract_count_label(
                self.missing_contracts
            )
        if not self.missing_contract_detail_label:
            self.missing_contract_detail_label = (
                ", ".join(self.missing_contract_labels)
                if self.missing_contract_labels
                else "Dane kompletne dla tego procesu"
            )
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
    def hydrate_labels(self) -> WorkflowRun:
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
