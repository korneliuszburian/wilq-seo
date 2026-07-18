from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import (
    action_count_label,
    ads_campaign_status_label,
    ads_channel_type_label,
    blocked_claim_count_label,
    blocked_claim_label,
    evidence_count_label,
    missing_contract_count_label,
    policy_count_label,
    required_validation_count_label,
    source_contract_count_label,
)

from .actions import ActionPreviewCardViewModel, ActionReviewOutcome
from .core import ActionRisk, ConnectorRefreshRun, ConnectorStatus, MetricFact, utc_now


class AdsDiagnosticSection(BaseModel):
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
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class AdsBlockedHandoff(BaseModel):
    id: str = "ads_oauth_blocked_handoff"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    marketer_message: str
    repair_steps: list[str] = Field(default_factory=list)
    allowed_demo_claims: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""


class AdsCampaignMetricRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    clicks: int | None = None
    clicks_label: str = ""
    impressions: int | None = None
    impressions_label: str = ""
    cost_micros: int | None = None
    cost_label: str = ""
    conversions: float | None = None
    conversions_label: str = ""
    conversion_value: float | None = None
    conversion_value_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak celu"
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "niski sygnał"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str = ""
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    human_review_gate_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsCampaignMetricRow:
        if not self.campaign_status_label:
            self.campaign_status_label = ads_campaign_status_label(self.campaign_status)
        if not self.advertising_channel_type_label:
            self.advertising_channel_type_label = ads_channel_type_label(
                self.advertising_channel_type
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.clicks_label:
            self.clicks_label = _operator_number_label(
                self.clicks,
                missing_label="brak odczytu kliknięć Ads",
            )
        if not self.impressions_label:
            self.impressions_label = _operator_number_label(
                self.impressions,
                missing_label="brak odczytu wyświetleń Ads",
            )
        if not self.cost_label:
            self.cost_label = _operator_micros_label(
                self.cost_micros,
                missing_label="brak odczytu kosztu Ads",
            )
        if not self.conversions_label:
            self.conversions_label = _operator_number_label(
                self.conversions,
                missing_label="brak odczytu konwersji Ads",
            )
        if not self.conversion_value_label:
            self.conversion_value_label = _operator_number_label(
                self.conversion_value,
                missing_label="brak odczytu wartości konwersji Ads",
            )
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        if not self.human_review_gate_summary_label:
            self.human_review_gate_summary_label = required_validation_count_label(
                self.human_review_gate_labels or self.human_review_gates
            )
        return self


def _operator_number_label(
    value: int | float | None,
    *,
    missing_label: str,
    max_fraction_digits: int = 2,
) -> str:
    if value is None:
        return missing_label
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    text = f"{value:,.{max_fraction_digits}f}".rstrip("0").rstrip(".")
    return text.replace(",", " ").replace(".", ",")


def _operator_micros_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{_operator_number_label(value / 1_000_000, missing_label=missing_label)} jedn. konta"


def _operator_percent_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{_operator_number_label(value * 100, missing_label=missing_label)}%"


class AdsCampaignReadContract(BaseModel):
    id: str = "ads_campaign_activity_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    next_step: str


class AdsAccountCurrencyReadContract(BaseModel):
    id: str = "ads_account_currency_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    currency_code: str | None = None
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    next_step: str


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


class AdsImpressionShareRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    search_impression_share: float | None = None
    search_budget_lost_impression_share: float | None = None
    search_rank_lost_impression_share: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsImpressionShareRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsImpressionShareReadContract(BaseModel):
    id: str = "ads_impression_share_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    empty_state_message: str = ""
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    impression_share_rows: list[AdsImpressionShareRow] = Field(default_factory=list)
    next_step: str


class AdsCampaignTriageRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str | None = None
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str | None = None
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "niski sygnał"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    next_step: str
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak celu"
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    ctr: float | None = None
    average_cpc_micros: float | None = None
    conversion_rate: float | None = None
    cost_per_conversion_micros: float | None = None
    roas: float | None = None
    spend_to_budget_ratio_7d: float | None = None
    search_budget_lost_impression_share: float | None = None
    recommendation_count: int = 0
    recommendation_types: list[str] = Field(default_factory=list)
    has_budget_apply_preview: bool = False
    has_recommendation_apply_preview: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    source_metric_names: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    human_review_gate_summary_label: str = ""

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsCampaignTriageRow:
        if not self.campaign_status_label:
            self.campaign_status_label = ads_campaign_status_label(self.campaign_status)
        if not self.advertising_channel_type_label:
            self.advertising_channel_type_label = ads_channel_type_label(
                self.advertising_channel_type
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        if not self.human_review_gate_summary_label:
            self.human_review_gate_summary_label = required_validation_count_label(
                self.human_review_gate_labels or self.human_review_gates
            )
        return self


class AdsCampaignTriageReadContract(BaseModel):
    id: str = "ads_campaign_triage_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    triage_rows: list[AdsCampaignTriageRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
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


class AdsChangeHistoryRow(BaseModel):
    change_event_id: str | None = None
    change_date_time: str | None = None
    change_resource_id: str | None = None
    change_resource_type: str | None = None
    change_resource_type_label: str = ""
    change_resource_label: str = ""
    resource_change_operation: str | None = None
    resource_change_operation_label: str = ""
    client_type: str | None = None
    client_type_label: str = ""
    campaign_id: str | None = None
    campaign_label: str = ""
    changed_field_count: int | None = None
    changed_fields: list[str] = Field(default_factory=list)
    changed_field_labels: list[str] = Field(default_factory=list)
    changed_field_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsChangeHistoryRow:
        if not self.change_resource_label:
            self.change_resource_label = _ads_change_resource_display_label(
                self.change_resource_type_label,
                self.change_resource_id,
            )
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(None, self.campaign_id)
        if not self.changed_field_summary_label:
            if self.changed_field_labels:
                self.changed_field_summary_label = ", ".join(self.changed_field_labels[:4])
            else:
                self.changed_field_summary_label = f"{self.changed_field_count or 0} pól"
        return self


class AdsChangeHistoryReadContract(BaseModel):
    id: str = "ads_change_history_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    allowed_metric_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    change_history_rows: list[AdsChangeHistoryRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsChangeImpactReadinessRow(BaseModel):
    change_event_id: str | None = None
    change_event_label: str = ""
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    change_date_time: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    changed_field_labels: list[str] = Field(default_factory=list)
    current_campaign_metrics_available: bool = False
    pre_window_available: bool = False
    post_window_available: bool = False
    current_clicks: int | None = None
    current_impressions: int | None = None
    current_cost_micros: int | None = None
    current_conversions: float | None = None
    current_conversion_value: float | None = None
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsChangeImpactReadinessRow:
        if not self.change_event_label:
            self.change_event_label = _ads_change_event_display_label(self.change_event_id)
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsChangeImpactReadinessContract(BaseModel):
    id: str = "ads_change_impact_readiness_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    allowed_metric_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    readiness_rows: list[AdsChangeImpactReadinessRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsChangeImpactReadinessContract:
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


def _ads_campaign_display_label(
    campaign_name: str | None,
    campaign_id: str | None,
) -> str:
    name = (campaign_name or "").strip()
    if name:
        return name
    if campaign_id:
        return "kampania do sprawdzenia w szczegółach technicznych"
    return "brak kampanii w odczycie"


def _ads_change_event_display_label(change_event_id: str | None) -> str:
    if change_event_id:
        return "zmiana do sprawdzenia w szczegółach technicznych"
    return "brak identyfikatora zmiany w odczycie"


def _ads_change_resource_display_label(
    resource_type_label: str | None,
    change_resource_id: str | None,
) -> str:
    resource = (resource_type_label or "").strip() or "zasób zmiany"
    if change_resource_id:
        return f"{resource} do sprawdzenia w szczegółach technicznych"
    return f"{resource} bez identyfikatora w odczycie"


def _ads_ad_group_display_label(
    ad_group_name: str | None,
    ad_group_id: str | None,
) -> str:
    name = (ad_group_name or "").strip()
    if name:
        return name
    if ad_group_id:
        return "grupa reklam do sprawdzenia w szczegółach technicznych"
    return "brak grupy reklam w odczycie"


class AdsSearchTermMetricRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    search_term_status: str | None = None
    landing_mapping_status: str | None = None
    landing_identity_sha256: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermMetricRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermCoverage(BaseModel):
    """Bounded coverage contract shared by search-term-derived decisions."""

    window: Literal["last_30_days", "search_term_safety_90d"]
    window_label: str
    requested_row_limit: int | None = None
    returned_row_count: int = Field(default=0, ge=0)
    connector_cap: int | None = None
    cap_applied: bool = False
    coverage_status: Literal["bounded_sample", "empty", "blocked"]
    privacy_omission_caveat: str


class AdsSearchTermsReadContract(BaseModel):
    id: str = "ads_search_terms_read_contract"
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
    coverage: list[AdsSearchTermCoverage] = Field(default_factory=list)
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    next_step: str


class AdsSearchTermReviewRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    search_term_status: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermReviewRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermCampaignReviewRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    search_term_count: int = 0
    zero_conversion_search_term_count: int = 0
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermCampaignReviewRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermReviewSummaryContract(BaseModel):
    id: str = "ads_search_term_review_summary_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: list[AdsSearchTermCoverage] = Field(default_factory=list)
    total_search_term_count: int = 0
    zero_conversion_search_term_count: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    total_cost_micros: int = 0
    total_conversions: float = 0.0
    top_cost_search_terms: list[AdsSearchTermReviewRow] = Field(default_factory=list)
    campaign_review_rows: list[AdsSearchTermCampaignReviewRow] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsSearchTermReviewSummaryContract:
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


class AdsSearchTermNgramRow(BaseModel):
    ngram: str
    ngram_size: int = Field(ge=1, le=3)
    source_search_term_count: int = 0
    sample_search_terms: list[str] = Field(default_factory=list)
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsSearchTermNgramRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermNgramReadContract(BaseModel):
    id: str = "ads_search_term_ngram_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: list[AdsSearchTermCoverage] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    ngram_rows: list[AdsSearchTermNgramRow] = Field(default_factory=list)
    next_step: str


class AdsSearchTermSafetyRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    search_term_status: str | None = None
    clicks_90d: int | None = None
    impressions_90d: int | None = None
    cost_micros_90d: int | None = None
    conversions_90d: float | None = None
    conversion_value_90d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermSafetyRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermSafetyReadContract(BaseModel):
    id: str = "ads_search_term_safety_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: list[AdsSearchTermCoverage] = Field(default_factory=list)
    safety_rows: list[AdsSearchTermSafetyRow] = Field(default_factory=list)
    next_step: str


class AdsKeywordMatchContextRow(BaseModel):
    keyword_text: str
    match_type: str
    match_type_label: str = ""
    criterion_id: str | None = None
    criterion_status: str | None = None
    criterion_status_label: str = ""
    negative: bool | None = None
    negative_label: str = ""
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsKeywordMatchContextRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsKeywordMatchContextReadContract(BaseModel):
    id: str = "ads_keyword_match_context_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    context_rows: list[AdsKeywordMatchContextRow] = Field(default_factory=list)
    next_step: str


class AdsCustomSegmentTargetingPreview(BaseModel):
    id: str
    custom_segment_preview_id: str
    target_scope: Literal["campaign_context_review"] = "campaign_context_review"
    campaign_id: str | None = None
    campaign_name: str | None = None
    operation_type: Literal["custom_segment_targeting_review"] = "custom_segment_targeting_review"
    reason: str
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentApplySafetyReview(BaseModel):
    id: str
    custom_segment_preview_id: str
    safety_contract: Literal["custom_segment_apply_safety_v1"] = "custom_segment_apply_safety_v1"
    status: Literal["blocked"] = "blocked"
    status_label: str = "zablokowane"
    reason: str
    missing_requirements: list[str] = Field(default_factory=list)
    missing_requirement_labels: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    audit_required: bool = True
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentPayloadPreview(BaseModel):
    id: str
    custom_segment_name: str
    member_type: Literal["KEYWORD"] = "KEYWORD"
    member_type_label: str = "słowa kluczowe"
    source_terms: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    campaign_name: str | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    targeting_preview: list[AdsCustomSegmentTargetingPreview] = Field(default_factory=list)
    safety_review: AdsCustomSegmentApplySafetyReview
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentAudienceForecastRow(BaseModel):
    id: str
    candidate_id: str
    custom_segment_name: str
    status: Literal["ready", "missing_forecast"] = "missing_forecast"
    forecast_available: bool = False
    audience_size: int | None = None
    source_terms: list[str] = Field(default_factory=list)
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsCustomSegmentAudienceForecastRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsCustomSegmentAudienceForecastReadContract(BaseModel):
    id: str = "ads_custom_segment_audience_forecast_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    checked_candidate_count: int = 0
    forecast_row_count: int = 0
    forecast_rows: list[AdsCustomSegmentAudienceForecastRow] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    next_step: str

    @model_validator(mode="after")
    def fill_operator_labels(self) -> AdsCustomSegmentAudienceForecastReadContract:
        if not self.status_label:
            self.status_label = _ads_read_contract_status_label(self.status)
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


def default_ads_custom_segment_audience_forecast_contract() -> (
    AdsCustomSegmentAudienceForecastReadContract
):
    return AdsCustomSegmentAudienceForecastReadContract(
        status="blocked",
        title="Prognoza i rozmiar odbiorców segmentów",
        summary=("Brak propozycji segmentów do sprawdzenia prognozy albo rozmiaru odbiorców."),
        missing_read_contracts=["custom_segment_candidates", "forecast_or_audience_size"],
        operator_review_gates=["forecast_or_audience_size", "human_confirm_before_apply"],
        blocked_claims=[
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
        ],
        next_step=("Najpierw zbuduj propozycje segmentów z realnych wyszukiwanych haseł."),
    )


class AdsKeywordPlannerIdeaRow(BaseModel):
    idea_text: str
    avg_monthly_searches: int | None = None
    competition: str | None = None
    competition_index: int | None = None
    low_top_of_page_bid_micros: int | None = None
    high_top_of_page_bid_micros: int | None = None
    source_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsKeywordPlannerReadContract(BaseModel):
    id: str = "ads_keyword_planner_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    idea_rows: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_operator_labels(self) -> AdsKeywordPlannerReadContract:
        if not self.status_label:
            self.status_label = _ads_read_contract_status_label(self.status)
        return self


class AdsCustomSegmentSourceQuality(BaseModel):
    total_terms: int = 0
    accepted_terms: int = 0
    rejected_terms: int = 0
    missing_metric_terms: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    rejection_reason_labels: dict[str, int] = Field(default_factory=dict)


class AdsCustomSegmentCandidate(BaseModel):
    id: str
    name: str
    intent: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "normalne"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    source_terms: list[str] = Field(default_factory=list)
    rejected_terms: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    source_quality: AdsCustomSegmentSourceQuality = Field(
        default_factory=AdsCustomSegmentSourceQuality
    )
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
    confidence_label: str = "niska"
    validation_status: Literal["pending_validation", "blocked"] = "pending_validation"
    validation_status_label: str = "do sprawdzenia"
    payload_preview: AdsCustomSegmentPayloadPreview | None = None
    preview_card: ActionPreviewCardViewModel | None = None
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsCustomSegmentCandidate:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsCustomSegmentsReadContract(BaseModel):
    id: str = "ads_custom_segments_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    candidates: list[AdsCustomSegmentCandidate] = Field(default_factory=list)
    payload_preview: list[AdsCustomSegmentPayloadPreview] = Field(default_factory=list)
    audience_forecast_read_contract: AdsCustomSegmentAudienceForecastReadContract = Field(
        default_factory=default_ads_custom_segment_audience_forecast_contract
    )
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_summary_label: str = ""
    next_step: str

    @model_validator(mode="after")
    def fill_operator_labels(self) -> AdsCustomSegmentsReadContract:
        if not self.status_label:
            self.status_label = _ads_read_contract_status_label(self.status)
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
                self.operator_review_gates
            )
        return self


def _ads_read_contract_status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
    }
    return labels.get(status, "status do sprawdzenia")


class AdsNegativeKeywordPayloadPreview(BaseModel):
    id: str
    search_term: str
    negative_keyword_text: str
    match_type: Literal["EXACT"]
    match_type_label: str = ""
    level: Literal["ad_group", "campaign_review_required"]
    level_label: str = ""
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    safety_evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsNegativeKeywordPayloadPreview:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        return self


class AdsNegativeKeywordCandidate(BaseModel):
    id: str
    search_term: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "normalne"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    clicks_90d: int | None = None
    impressions_90d: int | None = None
    cost_micros_90d: int | None = None
    conversions_90d: float | None = None
    conversion_value_90d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    safety_evidence_ids: list[str] = Field(default_factory=list)
    keyword_context_evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    safety_metric_facts: list[MetricFact] = Field(default_factory=list)
    keyword_context_rows: list[AdsKeywordMatchContextRow] = Field(default_factory=list)
    payload_preview: AdsNegativeKeywordPayloadPreview | None = None
    preview_card: ActionPreviewCardViewModel | None = None
    required_checks: list[str] = Field(default_factory=list)
    required_check_labels: list[str] = Field(default_factory=list)
    safety_status: Literal[
        "needs_90_day_review",
        "read_ready_needs_human_review",
        "blocked",
    ] = "needs_90_day_review"
    safety_status_label: str = ""
    validation_status: Literal["pending_validation", "blocked"] = "pending_validation"
    validation_status_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsNegativeKeywordCandidate:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        return self


class AdsNegativeKeywordsReadContract(BaseModel):
    id: str = "ads_negative_keywords_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    candidates: list[AdsNegativeKeywordCandidate] = Field(default_factory=list)
    payload_preview: list[AdsNegativeKeywordPayloadPreview] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: list[AdsSearchTermCoverage] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsNegativeKeywordsReadContract:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_campaign_activity",
        "review_business_context",
        "review_derived_kpi",
        "review_budget_context",
        "review_recommendations",
        "review_impression_share",
        "review_change_history",
        "review_search_term_safety",
        "review_search_terms",
        "review_search_term_ngrams",
        "review_negative_keyword_safety",
        "prepare_custom_segments",
        "block_write_actions",
        "fix_ads_access",
        "review_campaign_triage",
    ]
    status: Literal["ready", "blocked"]
    status_label: str = ""
    decision_type_label: str = ""
    title: str
    summary: str
    start_here_summary: str = ""
    measurement_plan: str = ""
    rationale: str
    next_step: str
    priority: int = Field(default=50, ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    campaign_triage_rows: list[AdsCampaignTriageRow] = Field(default_factory=list)
    derived_kpi_rows: list[AdsDerivedKpiRow] = Field(default_factory=list)
    budget_rows: list[AdsBudgetPacingRow] = Field(default_factory=list)
    shared_budget_distribution_rows: list[AdsSharedBudgetDistributionRow] = Field(
        default_factory=list
    )
    budget_apply_preview: list[AdsBudgetApplyPreview] = Field(default_factory=list)
    recommendation_rows: list[AdsRecommendationRow] = Field(default_factory=list)
    recommendation_apply_preview: list[AdsRecommendationApplyPreview] = Field(default_factory=list)
    impression_share_rows: list[AdsImpressionShareRow] = Field(default_factory=list)
    change_history_rows: list[AdsChangeHistoryRow] = Field(default_factory=list)
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    search_term_ngram_rows: list[AdsSearchTermNgramRow] = Field(default_factory=list)
    search_term_safety_rows: list[AdsSearchTermSafetyRow] = Field(default_factory=list)
    keyword_match_context_rows: list[AdsKeywordMatchContextRow] = Field(default_factory=list)
    keyword_planner_idea_rows: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    custom_segment_candidates: list[AdsCustomSegmentCandidate] = Field(default_factory=list)
    custom_segment_payload_preview: list[AdsCustomSegmentPayloadPreview] = Field(
        default_factory=list
    )
    custom_segment_audience_forecast_rows: list[AdsCustomSegmentAudienceForecastRow] = Field(
        default_factory=list
    )
    negative_keyword_candidates: list[AdsNegativeKeywordCandidate] = Field(default_factory=list)
    negative_keyword_payload_preview: list[AdsNegativeKeywordPayloadPreview] = Field(
        default_factory=list
    )
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    risk_label: str = ""
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsDecisionItem:
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


class AdsOperatorSummary(BaseModel):
    id: Literal["ads_operator_summary"] = "ads_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    campaign_count: int = 0
    search_term_count: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    total_cost_micros: int = 0
    total_conversions: float = 0.0
    total_conversion_value: float = 0.0
    ready_area_count: int = 0
    blocked_area_count: int = 0
    allowed_metrics: list[str] = Field(default_factory=list)
    allowed_metric_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    top_blocked_claim_labels: list[str] = Field(default_factory=list)
    top_blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsOperatorSummary:
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
        if not self.top_blocked_claim_labels:
            self.top_blocked_claim_labels = list(self.blocked_claim_labels or self.blocked_claims)
        if not self.top_blocked_claim_summary_label:
            self.top_blocked_claim_summary_label = blocked_claim_count_label(
                self.top_blocked_claim_labels
            )
        return self


class AdsFreshnessAssessment(BaseModel):
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


class AdsAggregationContract(BaseModel):
    """Make Ads window, compaction and money semantics visible to operators."""

    id: str = "ads_aggregation_contract_v1"
    view: Literal["full", "summary"]
    campaign_window: str = "LAST_7_DAYS"
    search_term_windows: list[str] = Field(default_factory=list)
    summary_row_limit: int = 5
    campaign_rows_returned: int = 0
    campaign_rows_available: int | None = None
    search_term_rows_returned: int = 0
    search_term_rows_available: int | None = None
    is_exhaustive: bool = False
    summary_scope: str
    pacing_basis: str = "daily_context_from_last_7_days"
    currency_code: str | None = None
    currency_status: Literal["ready", "blocked", "missing"] = "missing"
    money_aggregation_allowed: bool = False
    caveats: list[str] = Field(default_factory=list)


class AdsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    live_data_status_label: str = ""
    live_data_available: bool
    freshness_assessment: AdsFreshnessAssessment
    aggregation_contract: AdsAggregationContract = Field(
        default_factory=lambda: AdsAggregationContract(
            view="full",
            summary_scope="unknown_until_view_assembly",
        )
    )
    campaign_read_contract: AdsCampaignReadContract
    account_currency_read_contract: AdsAccountCurrencyReadContract
    business_context_read_contract: AdsBusinessContextReadContract
    derived_kpi_read_contract: AdsDerivedKpiReadContract
    budget_pacing_read_contract: AdsBudgetPacingReadContract
    recommendations_read_contract: AdsRecommendationsReadContract
    impression_share_read_contract: AdsImpressionShareReadContract
    campaign_triage_read_contract: AdsCampaignTriageReadContract
    optimizer_readiness_contract: AdsOptimizerReadinessContract
    change_history_read_contract: AdsChangeHistoryReadContract
    change_impact_readiness_contract: AdsChangeImpactReadinessContract
    search_terms_read_contract: AdsSearchTermsReadContract
    search_term_review_summary_contract: AdsSearchTermReviewSummaryContract
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract
    keyword_planner_read_contract: AdsKeywordPlannerReadContract
    custom_segments_read_contract: AdsCustomSegmentsReadContract
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract
    operator_summary: AdsOperatorSummary
    decision_queue: list[AdsDecisionItem] = Field(default_factory=list)
    sections: list[AdsDiagnosticSection] = Field(default_factory=list)
    blocked_handoff: AdsBlockedHandoff | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0


class DemandGenAdGroupAdRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_id: str | None = None
    ad_type: str | None = None
    ad_status: str | None = None
    final_url_count: int = 0
    asset_reference_count: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenAdGroupAdRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class DemandGenCreativeAssetRow(BaseModel):
    asset_id: str | None = None
    asset_type: str | None = None
    field_type: str | None = None
    impressions: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenCreativeAssetRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class DemandGenLandingQualityRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    landing_page: str
    landing_page_label: str = ""
    source_medium: str | None = None
    source_medium_label: str = ""
    active_users: int | None = None
    active_users_label: str = ""
    sessions: int | None = None
    sessions_label: str = ""
    engagement_rate: float | None = None
    engagement_rate_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenLandingQualityRow:
        if not self.landing_page_label:
            self.landing_page_label = self.landing_page or "brak strony wejścia w raporcie"
        if not self.source_medium_label:
            self.source_medium_label = self.source_medium or "brak źródła ruchu"
        if not self.active_users_label:
            self.active_users_label = _operator_number_label(
                self.active_users,
                missing_label="brak odczytu aktywnych użytkowników GA4",
            )
        if not self.sessions_label:
            self.sessions_label = _operator_number_label(
                self.sessions,
                missing_label="brak odczytu sesji GA4",
            )
        if not self.engagement_rate_label:
            self.engagement_rate_label = _operator_percent_label(
                self.engagement_rate,
                missing_label="brak odczytu zaangażowania GA4",
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class DemandGenCampaignModeReviewRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    review_required: bool = False
    review_status_label: str = ""
    reason: str
    reason_label: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenCampaignModeReviewRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self
