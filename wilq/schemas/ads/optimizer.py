from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    blocked_claim_label,
    evidence_count_label,
    missing_contract_count_label,
    required_validation_count_label,
    source_contract_count_label,
)

from ..actions import ActionPreviewCardViewModel
from ..core import (
    ActionRisk,
    MetricFact,
)

__all__ = [
    "AdsBudgetApplySafetyReview",
    "AdsBudgetApplyPreview",
    "AdsBudgetPacingRow",
    "AdsSharedBudgetCampaignShare",
    "AdsSharedBudgetDistributionRow",
    "AdsBudgetPacingReadContract",
    "AdsRecommendationApplyPreview",
    "AdsRecommendationRow",
    "AdsRecommendationsReadContract",
    "AdsOptimizerReadinessItem",
    "AdsOptimizerReadinessContract",
]



class AdsBudgetApplySafetyReview(BaseModel):
    id: str
    budget_preview_id: str
    safety_contract: Literal["campaign_budget_apply_safety_v1"] = "campaign_budget_apply_safety_v1"
    status: Literal["blocked"] = "blocked"
    status_label: str = ""
    reason: str
    max_allowed_delta_percent: float = 0.3
    current_budget_amount_micros: int | None = None
    proposed_budget_amount_micros: int | None = None
    proposed_delta_percent: float | None = None
    missing_requirements: list[str] = Field(default_factory=list)
    missing_requirement_labels: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsBudgetApplyPreview(BaseModel):
    id: str
    campaign_id: str | None = None
    campaign_name: str
    campaign_budget_id: str | None = None
    campaign_budget_name: str | None = None
    operation_type: Literal["CampaignBudgetOperation"] = "CampaignBudgetOperation"
    operation_type_label: str = ""
    current_budget_amount_micros: int | None = None
    proposed_budget_amount_micros: int | None = None
    proposed_budget_delta_micros: int | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    safety_review: AdsBudgetApplySafetyReview
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsBudgetPacingRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    budget_id: str | None = None
    budget_name: str | None = None
    budget_period: str | None = None
    budget_period_label: str = ""
    budget_status: str | None = None
    budget_status_label: str = ""
    budget_amount_micros: int | None = None
    cost_micros_7d: int | None = None
    seven_day_budget_micros: int | None = None
    spend_to_budget_ratio_7d: float | None = None
    has_recommended_budget: bool | None = None
    recommended_budget_amount_micros: int | None = None
    recommended_budget_delta_micros: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    payload_preview: AdsBudgetApplyPreview | None = None
    preview_card: ActionPreviewCardViewModel | None = None
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsBudgetPacingRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsSharedBudgetCampaignShare(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    cost_micros_7d: int | None = None
    spend_share_7d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class AdsSharedBudgetDistributionRow(BaseModel):
    budget_id: str
    budget_name: str | None = None
    campaign_count: int
    budget_amount_micros: int | None = None
    seven_day_budget_micros: int | None = None
    total_cost_micros_7d: int | None = None
    spend_to_budget_ratio_7d: float | None = None
    campaign_shares: list[AdsSharedBudgetCampaignShare] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsSharedBudgetDistributionRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsBudgetPacingReadContract(BaseModel):
    id: str = "ads_budget_pacing_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    empty_state_message: str = ""
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    budget_rows: list[AdsBudgetPacingRow] = Field(default_factory=list)
    shared_budget_distribution_rows: list[AdsSharedBudgetDistributionRow] = Field(
        default_factory=list
    )
    payload_preview: list[AdsBudgetApplyPreview] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsRecommendationApplyPreview(BaseModel):
    id: str
    recommendation_id: str | None = None
    recommendation_resource_name: str | None = None
    recommendation_type: str
    recommendation_type_label: str = ""
    campaign_id: str | None = None
    campaign_budget_id: str | None = None
    operation_type: Literal["ApplyRecommendationOperation"] = "ApplyRecommendationOperation"
    operation_type_label: str = ""
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsRecommendationRow(BaseModel):
    recommendation_id: str | None = None
    recommendation_resource_name: str | None = None
    recommendation_type: str
    recommendation_type_label: str = ""
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "normalne"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    human_review_gate_summary_label: str = ""
    dismissed: bool = False
    campaign_id: str | None = None
    campaign_budget_id: str | None = None
    campaign_count: int | None = None
    impact_available: bool = False
    base_clicks: int | None = None
    potential_clicks: int | None = None
    delta_clicks: int | None = None
    base_impressions: int | None = None
    potential_impressions: int | None = None
    delta_impressions: int | None = None
    base_cost_micros: int | None = None
    potential_cost_micros: int | None = None
    delta_cost_micros: int | None = None
    base_conversions: float | None = None
    potential_conversions: float | None = None
    delta_conversions: float | None = None
    base_conversion_value: float | None = None
    potential_conversion_value: float | None = None
    delta_conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    payload_preview: AdsRecommendationApplyPreview | None = None
    preview_card: ActionPreviewCardViewModel | None = None
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsRecommendationRow:
        if not self.human_review_gate_summary_label:
            self.human_review_gate_summary_label = required_validation_count_label(
                self.human_review_gate_labels or self.human_review_gates
            )
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsRecommendationsReadContract(BaseModel):
    id: str = "ads_recommendations_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    recommendation_rows: list[AdsRecommendationRow] = Field(default_factory=list)
    payload_preview: list[AdsRecommendationApplyPreview] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsOptimizerReadinessItem(BaseModel):
    id: str
    label: str = ""
    title: str
    status: Literal["ready", "blocked"]
    status_label: str = ""
    summary: str
    next_step: str
    source_contract_ids: list[str] = Field(default_factory=list)
    source_contract_summary_label: str = ""
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    risk: ActionRisk = ActionRisk.medium
    risk_label: str = ""

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsOptimizerReadinessItem:
        if not self.source_contract_summary_label:
            self.source_contract_summary_label = source_contract_count_label(
                self.source_contract_ids
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsOptimizerReadinessContract(BaseModel):
    id: str = "ads_optimizer_readiness_contract"
    status: Literal["review_ready", "blocked"]
    status_label: str = ""
    mode: Literal["review_only"] = "review_only"
    mode_label: str = ""
    title: str
    summary: str
    ready_area_count: int = 0
    blocked_area_count: int = 0
    readiness_items: list[AdsOptimizerReadinessItem] = Field(default_factory=list)
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsOptimizerReadinessContract:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self
