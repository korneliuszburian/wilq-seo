from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from wilq.operator_labels import (
    blocked_claim_count_label,
    missing_contract_count_label,
    required_validation_count_label,
)

from ..core import (
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorStatus,
    DiagnosticDataReadiness,
    MetricFact,
    utc_now,
)
from .business import (
    AdsBusinessContextReadContract,
    AdsDerivedKpiReadContract,
    AdsDerivedKpiRow,
)
from .custom_segments import (
    AdsCustomSegmentAudienceForecastRow,
    AdsCustomSegmentCandidate,
    AdsCustomSegmentPayloadPreview,
    AdsCustomSegmentsReadContract,
)
from .diagnostics import (
    AdsAccountCurrencyReadContract,
    AdsCampaignMetricRow,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsCampaignTriageRow,
    AdsChangeHistoryReadContract,
    AdsChangeHistoryRow,
    AdsChangeImpactReadinessContract,
    AdsImpressionShareReadContract,
    AdsImpressionShareRow,
    AdsSearchTermMetricRow,
    AdsSearchTermNgramReadContract,
    AdsSearchTermNgramRow,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermSafetyRow,
    AdsSearchTermsReadContract,
)
from .negative_keywords import (
    AdsKeywordMatchContextReadContract,
    AdsKeywordMatchContextRow,
    AdsKeywordPlannerIdeaRow,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordCandidate,
    AdsNegativeKeywordPayloadPreview,
    AdsNegativeKeywordsReadContract,
)
from .optimizer import (
    AdsBudgetApplyPreview,
    AdsBudgetPacingReadContract,
    AdsBudgetPacingRow,
    AdsOptimizerReadinessContract,
    AdsRecommendationApplyPreview,
    AdsRecommendationRow,
    AdsRecommendationsReadContract,
    AdsSharedBudgetDistributionRow,
)

__all__ = [
    "AdsDiagnosticSection",
    "AdsBlockedHandoff",
    "AdsDecisionItem",
    "AdsOperatorSummary",
    "AdsFreshnessAssessment",
    "AdsAggregationContract",
    "AdsDiagnosticsResponse",
]



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
    data_readiness: DiagnosticDataReadiness
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
