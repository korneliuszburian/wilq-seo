from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    evidence_count_label,
    missing_contract_count_label,
)

from .content import ContentAhrefsCandidateRow
from .core import ActionRisk, ConnectorRefreshRun, ConnectorStatus, MetricFact, utc_now


class AhrefsDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsDiagnosticSection:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AhrefsDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_authority_context",
        "review_gap_records",
        "run_authority_read",
        "block_gap_claims",
    ]
    status: Literal["ready", "blocked"]
    status_label: str = ""
    decision_type_label: str = ""
    title: str
    summary: str
    rationale: str
    next_step: str
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_evidence: list[str] = Field(default_factory=list)
    allowed_evidence_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsDecisionItem:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AhrefsGapRecord(BaseModel):
    id: str
    gap_type: Literal[
        "competitor_page",
        "content_gap",
        "backlink_gap",
        "organic_keyword_gap",
        "top_page_gap",
    ]
    gap_type_label: str = ""
    title: str
    summary: str
    source_url: str | None = None
    referenced_public_url: str | None = None
    competitor_domain: str | None = None
    keyword: str | None = None
    snapshot_date: str | None = None
    mapping_status: Literal["unbound", "review_required", "exact"] = "unbound"
    derived_method: str = ""
    coverage_summary: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium


class AhrefsGapReadContract(BaseModel):
    id: Literal["ahrefs_gap_read_contract"] = "ahrefs_gap_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    allowed_evidence: list[str] = Field(default_factory=list)
    allowed_evidence_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    gap_records: list[AhrefsGapRecord] = Field(default_factory=list)
    gap_record_count: int = 0
    coverage_summary: str = ""
    cross_check_status: Literal["api_backed", "manual_required", "missing"] = "missing"
    cross_check_status_label: str = ""
    cross_check_summary: str = ""
    cross_check_next_step: str = ""
    cross_check_gsc_match_count: int = 0
    cross_check_wordpress_match_count: int = 0
    cross_check_source_connectors: list[str] = Field(default_factory=list)
    cross_check_evidence_ids: list[str] = Field(default_factory=list)
    cross_check_candidates: list[ContentAhrefsCandidateRow] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsGapReadContract:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(self.blocked_claims)
        return self


class AhrefsOperatorSummary(BaseModel):
    id: Literal["ahrefs_operator_summary"] = "ahrefs_operator_summary"
    title: str
    summary: str
    next_step: str
    review_card_label: str = "Karta review Ahrefs"
    review_decision_after_review: str = ""
    review_question_for_operator: str = ""
    review_next_safe_click: str = ""
    review_action_ids: list[str] = Field(default_factory=list)
    top_decision_ids: list[str] = Field(default_factory=list)
    gap_read_status: Literal["ready", "blocked"]
    gap_read_status_label: str = ""
    authority_fact_count: int = 0
    gap_fact_count: int = 0
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsOperatorSummary:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AhrefsRequestBudgetStage(BaseModel):
    id: Literal[
        "domain_rating",
        "organic_competitors",
        "top_pages_by_competitor",
        "organic_keywords_by_url",
        "content_gap",
        "backlink_gap",
    ]
    label: str = Field(min_length=1)
    status: Literal["completed", "failed", "skipped", "not_run"]
    status_label: str = Field(min_length=1)
    requested_calls: int = Field(ge=0)
    rows: int = Field(ge=0)
    summary: str = ""


class AhrefsRequestBudget(BaseModel):
    estimated_calls: int = 0
    failed_stages: int = 0
    partial: bool = False
    summary: str = ""
    stages: list[AhrefsRequestBudgetStage] = Field(default_factory=list)


class AhrefsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    request_budget: AhrefsRequestBudget = Field(default_factory=AhrefsRequestBudget)
    live_data_status_label: str = ""
    live_data_available: bool
    authority_fact_count: int = 0
    gap_fact_count: int = 0
    gap_read_contract: AhrefsGapReadContract
    operator_summary: AhrefsOperatorSummary
    decision_queue: list[AhrefsDecisionItem] = Field(default_factory=list)
    sections: list[AhrefsDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsDiagnosticsResponse:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self
