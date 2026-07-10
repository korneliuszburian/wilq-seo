from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import reported_issue_occurrence_count_label

from .actions import ActionPreviewCardViewModel
from .core import ActionRisk, ConnectorRefreshRun, ConnectorStatus, MetricFact, utc_now
from .marketing import TacticalQueueItem, _marketing_priority_label


class MerchantDiagnosticSection(BaseModel):
    id: str
    label: str = ""
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
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""


class MerchantIssueCluster(BaseModel):
    id: str
    issue_type: str
    issue_type_label: str | None = None
    severity: str
    severity_label: str | None = None
    resolution: str | None = None
    resolution_label: str | None = None
    affected_attribute: str | None = None
    affected_attribute_label: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    reporting_context_label: str
    product_count: int = 0
    reported_issue_summary_label: str = ""
    count_semantics: Literal["reported_issue_occurrences"] = "reported_issue_occurrences"
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_titles: list[str] = Field(default_factory=list)
    sample_unavailable_reason: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    action_id: str | None = None
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""
    next_step: str

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> MerchantIssueCluster:
        if not self.reported_issue_summary_label:
            self.reported_issue_summary_label = reported_issue_occurrence_count_label(
                self.product_count
            )
        return self


class MerchantDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_issue_cluster",
        "review_feed_status",
        "review_product_state_mapping",
        "review_price_impact_readiness",
        "block_until_vendor_read",
    ]
    decision_type_label: str = ""
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    title: str
    summary: str | None = None
    cluster_id: str | None = None
    issue_cluster_ids: list[str] = Field(default_factory=list)
    issue_type: str | None = None
    issue_type_label: str | None = None
    severity: str | None = None
    severity_label: str | None = None
    resolution: str | None = None
    resolution_label: str | None = None
    affected_attribute: str | None = None
    affected_attribute_label: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    reporting_context_label: str | None = None
    product_count: int | None = None
    issue_count: int | None = None
    count_semantics: Literal["reported_issue_occurrences"] = "reported_issue_occurrences"
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_titles: list[str] = Field(default_factory=list)
    change_preview: list[dict[str, Any]] = Field(default_factory=list)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
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
    why_it_matters: str | None = None
    operator_action: str | None = None
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""

    @model_validator(mode="after")
    def fill_operator_aliases(self) -> MerchantDecisionItem:
        if not self.priority_label:
            self.priority_label = _marketing_priority_label(self.priority)
        if self.why_it_matters is None:
            self.why_it_matters = self.rationale
        if self.operator_action is None:
            self.operator_action = self.next_step
        return self


class MerchantOperatorSummary(BaseModel):
    id: Literal["merchant_operator_summary"] = "merchant_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    top_issue_cluster_ids: list[str] = Field(default_factory=list)
    top_tactical_item_ids: list[str] = Field(default_factory=list)
    reported_issue_occurrences: int = 0
    decision_source: Literal["decision_queue"] = "decision_queue"
    decision_source_label: str = "kolejka decyzji Merchant"
    drilldown_source: Literal["issue_clusters"] = "issue_clusters"
    drilldown_source_label: str = "grupy problemów pliku produktowego"
    count_semantics: Literal["reported_issue_occurrences"] = "reported_issue_occurrences"
    count_semantics_label: str = "wystąpienia problemów w raportach"
    issue_types: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantFreshnessAssessment(BaseModel):
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


class MerchantUnknownFact(BaseModel):
    id: str
    title: str
    reason: str
    impact: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantProductSampleReadiness(BaseModel):
    status: Literal["ready", "blocked"]
    status_label: str = ""
    sample_products_available: bool = False
    sample_count: int = 0
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_product_titles: list[str] = Field(default_factory=list)
    sample_summary_label: str = ""
    sample_title_labels: list[str] = Field(default_factory=list)
    current_read_contract: Literal["merchant_aggregate_product_statuses"] = (
        "merchant_aggregate_product_statuses"
    )
    required_read_contracts: list[str] = Field(default_factory=list)
    source_endpoint: str
    summary: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantProductPerformanceRow(BaseModel):
    product_id: str
    title_label: str = ""
    product_reference_label: str = ""
    sample_title: str | None = None
    issue_type: str | None = None
    issue_type_label: str | None = None
    affected_attribute: str | None = None
    affected_attribute_label: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    reporting_context_label: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    ads_product_title: str | None = None
    ads_product_status: str | None = None
    ads_product_status_label: str = ""
    ads_product_availability: str | None = None
    ads_product_availability_label: str = ""
    ads_product_price_micros: int | None = None
    ads_product_price_label: str = ""
    ads_product_currency_code: str | None = None
    ads_product_price_collected_at: datetime | None = None
    ads_product_previous_price_micros: int | None = None
    ads_product_previous_price_collected_at: datetime | None = None
    ads_product_previous_price_evidence_id: str | None = None
    ads_product_price_delta_micros: int | None = None
    ads_product_price_delta_percent: float | None = None
    ads_clicks: int | None = None
    ads_clicks_label: str = ""
    ads_cost_micros: int | None = None
    ads_cost_label: str = ""
    ads_conversions: float | None = None
    ads_conversions_label: str = ""
    ads_conversion_value: float | None = None
    ads_conversion_value_label: str = ""
    ga4_ecommerce_purchases: float | None = None
    ga4_ecommerce_purchases_label: str = ""
    ga4_purchase_revenue: float | None = None
    ga4_purchase_revenue_label: str = ""
    missing_metrics: list[str] = Field(default_factory=list)
    missing_metric_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantProductPerformanceReadiness(BaseModel):
    id: Literal["merchant_product_performance_readiness"] = "merchant_product_performance_readiness"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    joined_product_count: int = 0
    merchant_sample_count: int = 0
    ads_product_fact_count: int = 0
    ga4_product_fact_count: int = 0
    current_read_contracts: list[str] = Field(default_factory=list)
    required_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    join_key_candidates: list[str] = Field(default_factory=list)
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_product_summary_label: str = ""
    performance_rows: list[MerchantProductPerformanceRow] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    summary: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantPriceImpactReadiness(BaseModel):
    id: Literal["merchant_price_impact_readiness"] = "merchant_price_impact_readiness"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    products_with_current_price: int = 0
    products_with_previous_price: int = 0
    products_with_price_change: int = 0
    products_with_unchanged_price_history: int = 0
    products_with_performance_metrics: int = 0
    current_read_contracts: list[str] = Field(default_factory=list)
    required_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    change_preview: list[dict[str, Any]] = Field(default_factory=list)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    summary: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    live_data_available: bool
    live_data_status_label: str = ""
    product_count: int | None = None
    issue_count: int | None = None
    freshness_assessment: MerchantFreshnessAssessment
    unknowns: list[MerchantUnknownFact] = Field(default_factory=list)
    product_sample_readiness: MerchantProductSampleReadiness
    product_performance_readiness: MerchantProductPerformanceReadiness
    price_impact_readiness: MerchantPriceImpactReadiness
    operator_summary: MerchantOperatorSummary
    issue_clusters: list[MerchantIssueCluster] = Field(default_factory=list)
    decision_queue: list[MerchantDecisionItem] = Field(default_factory=list)
    sections: list[MerchantDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0
