from __future__ import annotations

from datetime import datetime
from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    blocked_claim_label,
    missing_contract_count_label,
    policy_count_label,
    required_validation_count_label,
)

from ..actions import ActionReviewOutcome

__all__ = [
    "AdsBusinessTargetInterpretation",
    "AdsStrategyReviewReadinessContract",
    "AdsBusinessContextReadContract",
    "AdsDerivedKpiRow",
    "AdsDerivedKpiReadContract",
]



class AdsBusinessTargetInterpretation(BaseModel):
    id: str = "ads_business_target_interpretation"
    interpretation_contract: Literal["ads_business_target_interpretation_v1"] = (
        "ads_business_target_interpretation_v1"
    )
    status: Literal["ready", "preliminary", "blocked"]
    status_label: str = ""
    summary: str
    allowed_uses: list[str] = Field(default_factory=list)
    allowed_use_labels: list[str] = Field(default_factory=list)
    blocked_uses: list[str] = Field(default_factory=list)
    blocked_use_labels: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    missing_requirement_labels: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    policy_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    apply_allowed: bool = False
    destructive: bool = False

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsBusinessTargetInterpretation:
        if not self.policy_summary_label:
            self.policy_summary_label = policy_count_label(self.policy_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AdsStrategyReviewReadinessContract(BaseModel):
    id: str = "ads_strategy_review_readiness_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    latest_review_status: Literal[
        "missing",
        "approved_for_prepare",
        "needs_changes",
        "rejected",
        "deferred",
    ] = "missing"
    latest_review_status_label: str = ""
    latest_review_outcome: ActionReviewOutcome | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    current_context: dict[str, Any] = Field(default_factory=dict)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    required_validation_summary_label: str = ""
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    apply_allowed: bool = False
    destructive: bool = False
    next_step: str

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsStrategyReviewReadinessContract:
        if not self.required_validation_summary_label:
            self.required_validation_summary_label = required_validation_count_label(
                self.required_validation
            )
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsBusinessContextReadContract(BaseModel):
    id: str = "ads_business_context_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    profit_margin: float | None = None
    business_goal: str | None = None
    budget_goal: str | None = None
    target_roas: float | None = None
    target_cpa_micros: int | None = None
    strategy_review_status: Literal[
        "missing",
        "approved_for_prepare",
        "needs_changes",
        "rejected",
        "deferred",
    ] = "missing"
    strategy_reviewed_by: str | None = None
    strategy_reviewed_at: datetime | None = None
    strategy_review_summary: str | None = None
    configured_sources: list[str] = Field(default_factory=list)
    business_policy_ids: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    target_interpretation: AdsBusinessTargetInterpretation
    strategy_review_readiness_contract: AdsStrategyReviewReadinessContract
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    next_step: str


class AdsDerivedKpiRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    ctr: float | None = None
    average_cpc_micros: float | None = None
    conversion_rate: float | None = None
    cost_per_conversion_micros: float | None = None
    roas: float | None = None
    value_per_conversion: float | None = None
    target_roas: float | None = None
    roas_vs_target: float | None = None
    target_cpa_micros: int | None = None
    cpa_vs_target_micros: float | None = None
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak celu"
    target_review_priority: int = 90
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsDerivedKpiRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsDerivedKpiReadContract(BaseModel):
    id: str = "ads_derived_kpi_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    kpi_rows: list[AdsDerivedKpiRow] = Field(default_factory=list)
    next_step: str
