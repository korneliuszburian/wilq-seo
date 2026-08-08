from __future__ import annotations

from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    model_serializer,
    model_validator,
)

from wilq.operator_labels import (
    action_count_label,
    ads_campaign_status_label,
    ads_channel_type_label,
    blocked_claim_count_label,
    blocked_claim_label,
    evidence_count_label,
    missing_contract_count_label,
    required_validation_count_label,
)

from ..core import MetricFact
from .labels import (
    _ads_ad_group_display_label,
    _ads_campaign_display_label,
    _ads_change_event_display_label,
    _ads_change_resource_display_label,
    _operator_micros_label,
    _operator_number_label,
)

__all__ = [
    "AdsCampaignMetricRow",
    "AdsCampaignReadContract",
    "AdsAccountCurrencyReadContract",
    "AdsImpressionShareRow",
    "AdsImpressionShareReadContract",
    "AdsCampaignTriageRow",
    "AdsCampaignTriageReadContract",
    "AdsChangeHistoryRow",
    "AdsChangeHistoryReadContract",
    "AdsChangeImpactReadinessRow",
    "AdsChangeImpactReadinessContract",
    "AdsLandingServiceBinding",
    "AdsSearchTermMetricRow",
    "AdsSearchTermCoverage",
    "AdsSearchTermsReadContract",
    "AdsSearchTermReviewRow",
    "AdsSearchTermCampaignReviewRow",
    "AdsSearchTermReviewSummaryContract",
    "AdsSearchTermNgramRow",
    "AdsSearchTermNgramReadContract",
    "AdsSearchTermSafetyRow",
    "AdsSearchTermSafetyReadContract",
]



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


class AdsLandingServiceBinding(BaseModel):
    """Hash-only page-to-service join for review-only Ads context."""

    status: Literal["unbound", "ambiguous", "review_required", "approved_current"]
    inventory_work_item_id: str | None = None
    service_candidate_ids: list[str] = Field(default_factory=list)
    service_candidate_labels: list[str] = Field(default_factory=list)
    service_lifecycle_statuses: list[str] = Field(default_factory=list)
    reason: str
    next_step: str


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
    landing_service_binding: AdsLandingServiceBinding | None = None
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

    @model_serializer(mode="wrap")
    def _serialize_without_unset_context(self, handler: Any) -> dict[str, Any]:
        """Keep optional landing context absent until an exact hash is available."""

        return {key: value for key, value in handler(self).items() if value is not None}

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
