from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import missing_contract_count_label

from .core import ActionRisk, ConnectorRefreshRun, ConnectorStatus, MetricFact, utc_now
from .marketing import TacticalQueueItem


class Ga4TrackingQualityPayloadPreview(BaseModel):
    id: str
    preview_contract: Literal["ga4_tracking_quality_review_v1"]
    operation_type: Literal["tracking_quality_review"]
    operation_type_label: str = ""
    landing_page: str | None = None
    landing_page_label: str = ""
    source_medium: str | None = None
    source_medium_label: str = ""
    campaign_name: str | None = None
    campaign_name_label: str = ""
    tracking_dimension_gaps: list[Literal["landing_page", "source_medium", "campaign_name"]] = (
        Field(default_factory=list)
    )
    tracking_dimension_gap_labels: list[str] = Field(default_factory=list)
    metric_snapshot: dict[str, float | int | str] = Field(default_factory=dict)
    metric_snapshot_labels: dict[str, str] = Field(default_factory=dict)
    reason: str
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class Ga4DiagnosticSection(BaseModel):
    id: str
    label: str = ""
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
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""


class Ga4DecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "fix_measurement",
        "review_traffic_quality",
        "review_landing_mapping",
    ]
    decision_type_label: str = ""
    title: str
    status: Literal["ready", "blocked"] = "ready"
    status_label: str = ""
    priority: int = Field(default=50, ge=1, le=100)
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    landing_page: str | None = None
    landing_page_label: str = ""
    source_medium: str | None = None
    source_medium_label: str = ""
    campaign_name: str | None = None
    campaign_name_label: str = ""
    wordpress_match: str | None = None
    wordpress_match_label: str | None = None
    wordpress_match_confidence: str | None = None
    wordpress_match_confidence_label: str | None = None
    wordpress_content_url: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""


class Ga4ConversionReadinessContract(BaseModel):
    id: Literal["ga4_conversion_readiness_contract"] = "ga4_conversion_readiness_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    conversion_like_metric_count: int = 0
    dimensioned_behavior_metric_count: int = 0
    landing_group_count: int = 0
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> Ga4ConversionReadinessContract:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        return self


class Ga4FreshnessAssessment(BaseModel):
    state: Literal["fresh", "stale", "missing", "blocked"]
    state_label: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    latest_refresh_id: str | None = None
    latest_refresh_completed_at: datetime | None = None
    age_hours: float | None = None
    stale_after_hours: int = 48
    requires_refresh: bool
    summary: str
    next_step: str


class Ga4OperatorSummary(BaseModel):
    id: Literal["ga4_operator_summary"] = "ga4_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    measurement_issue_count: int = 0
    wordpress_missing_count: int = 0
    conversion_readiness_status: Literal["ready", "blocked"]
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class Ga4DiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str = ""
    live_data_available: bool
    live_data_status_label: str = ""
    landing_group_count: int = 0
    low_engagement_count: int = 0
    wordpress_match_count: int = 0
    freshness_assessment: Ga4FreshnessAssessment
    conversion_readiness_contract: Ga4ConversionReadinessContract
    operator_summary: Ga4OperatorSummary
    decision_queue: list[Ga4DecisionItem] = Field(default_factory=list)
    sections: list[Ga4DiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0
    decision_blocker_count: int = 0
