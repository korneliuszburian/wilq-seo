from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import missing_contract_count_label

from .core import (
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorStatus,
    DiagnosticDataReadiness,
    MetricFact,
    utc_now,
)
from .diagnostic_readiness import build_diagnostic_data_readiness


class LocaloAccessProbe(BaseModel):
    status: Literal["access_ready", "access_blocked", "unknown"]
    status_label: str = ""
    source_run_id: str | None = None
    mcp_initialize_status: int | None = None
    access_check_label: str = ""
    authorization_code_supported: bool | None = None
    authorization_code_supported_label: str = ""
    authorization_readiness_label: str = ""
    pkce_s256_supported: bool | None = None
    pkce_s256_supported_label: str = ""
    secure_readiness_label: str = ""
    access_token_present: bool | None = None
    access_token_present_label: str = ""
    credential_readiness_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    summary: str


class LocaloDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class LocaloReadContractStatus(BaseModel):
    id: Literal[
        "place_inventory",
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
        "local_tasks",
    ]
    id_label: str = ""
    status: Literal["ready", "missing"]
    status_label: str = ""
    evidence_kind: str
    metric_fact_names: list[str] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    next_step: str


class LocaloDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "access_ready_wait_for_visibility_facts",
        "fix_access",
        "review_local_visibility",
        "block_visibility_claims",
    ]
    decision_type_label: str = ""
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    rationale: str
    next_step: str
    access_status: Literal["access_ready", "access_blocked", "unknown"]
    access_status_label: str = ""
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_evidence: list[str] = Field(default_factory=list)
    allowed_evidence_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    read_contract_statuses: list[LocaloReadContractStatus] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    action_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class LocaloOperatorSummary(BaseModel):
    id: Literal["localo_operator_summary"] = "localo_operator_summary"
    title: str
    summary: str
    next_step: str
    review_card_label: str = "Karta review Localo"
    review_decision_after_review: str
    review_question_for_operator: str
    review_next_safe_click: str
    review_action_ids: list[str] = Field(default_factory=list)
    top_decision_ids: list[str] = Field(default_factory=list)
    access_status: Literal["access_ready", "access_blocked", "unknown"]
    access_status_label: str = ""
    visibility_fact_count: int = 0
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    read_contract_statuses: list[LocaloReadContractStatus] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_operator_summary_labels(self) -> LocaloOperatorSummary:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        return self


class LocaloDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    access_probe: LocaloAccessProbe
    live_data_available: bool
    data_readiness: DiagnosticDataReadiness | None = None
    visibility_fact_count: int = 0
    read_contract_statuses: list[LocaloReadContractStatus] = Field(default_factory=list)
    operator_summary: LocaloOperatorSummary
    decision_queue: list[LocaloDecisionItem] = Field(default_factory=list)
    sections: list[LocaloDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0

    @model_validator(mode="after")
    def build_data_readiness(self) -> LocaloDiagnosticsResponse:
        if self.data_readiness is None:
            facts = [fact for section in self.sections for fact in section.metric_facts]
            self.data_readiness = build_diagnostic_data_readiness(
                connector=self.connector,
                latest_refresh=self.latest_refresh,
                factual_metrics=facts[:12] if self.live_data_available else [],
                factual_metric_count=len(facts) if self.live_data_available else 0,
                evidence_ids=self.evidence_ids,
                partial=bool(
                    self.live_data_available
                    and any(item.status == "missing" for item in self.read_contract_statuses)
                ),
                stale=self.connector.freshness.state == "stale",
                partial_coverage_label="Pokazane metryki obejmują tylko odczytane obszary Localo.",
            )
        return self
