from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import source_connector_labels

from .core import (
    ActionRisk,
    ConnectorCoveredWindow,
    ConnectorQualityState,
    ConnectorRefreshRun,
    ConnectorSettlementState,
    ConnectorStatus,
    MetricFact,
    utc_now,
)
from .marketing import TacticalQueueItem


class ContentDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
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


class ContentAhrefsCrossCheck(BaseModel):
    strength: Literal["exact", "weak", "missing"] = "missing"
    label: str = "brak potwierdzonego dopasowania"
    matching_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @classmethod
    def missing(cls) -> ContentAhrefsCrossCheck:
        return cls()


class ContentAhrefsCandidateRow(BaseModel):
    id: str
    topic: str
    gap_type: str
    gap_type_label: str = ""
    relevance_status: Literal["relevant", "review", "off_topic"]
    relevance_status_label: str = ""
    relevance_score: int
    business_relevance_reasons: list[str] = Field(default_factory=list)
    business_relevance_reason_labels: list[str] = Field(default_factory=list)
    gsc_demand: Literal["present", "missing"]
    gsc_demand_label: str = ""
    gsc_cross_check: ContentAhrefsCrossCheck = Field(
        default_factory=ContentAhrefsCrossCheck.missing
    )
    wordpress_inventory_match: Literal["present", "missing"]
    wordpress_inventory_match_label: str = ""
    wordpress_cross_check: ContentAhrefsCrossCheck = Field(
        default_factory=ContentAhrefsCrossCheck.missing
    )
    gsc_overlap_terms: list[str] = Field(default_factory=list)
    wordpress_overlap_urls: list[str] = Field(default_factory=list)
    keyword: str | None = None
    competitor_domain: str | None = None
    source_url: str | None = None
    referenced_public_url: str | None = None
    metric_name: str
    metric_value: int | float | str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    next_step: str


class ContentDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "block_until_vendor_read",
        "refresh_or_merge",
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
        "block_as_tracking_not_content",
        "review_ahrefs_gap_records",
    ]
    status: Literal["ready", "blocked"] = "ready"
    decision_type_label: str = ""
    title: str
    summary: str | None = None
    priority: int = 50
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    page: str | None = None
    normalized_page_path: str | None = None
    queries: list[str] = Field(default_factory=list)
    query_count: int = 0
    primary_query: str | None = None
    total_clicks: int | None = None
    total_impressions: int | None = None
    aggregate_ctr: float | None = None
    best_average_position: float | None = None
    wordpress_match: str | None = None
    wordpress_match_label: str | None = None
    wordpress_match_confidence: str | None = None
    wordpress_match_confidence_label: str | None = None
    wordpress_title_or_h1: str | None = None
    wordpress_inventory_source: str | None = None
    wordpress_modified_gmt: str | None = None
    wordpress_section_headings: list[str] = Field(default_factory=list)
    wordpress_section_count: int | None = None
    wordpress_section_inventory_status: Literal["available", "missing"] = "missing"
    wordpress_content_summary: str | None = None
    wordpress_content_text: str | None = None
    wordpress_content_source_kind: str | None = None
    wordpress_content_extraction_region: str | None = None
    wordpress_content_material_confidence: str | None = None
    wordpress_content_source_field_lineage: list[str] = Field(default_factory=list)
    wordpress_content_word_count: int | None = None
    wordpress_content_inventory_status: Literal["available", "missing"] = "missing"
    wordpress_content_inventory_note: str | None = None
    wordpress_block_names: list[str] = Field(default_factory=list)
    wordpress_block_count: int | None = None
    wordpress_acf_section_inventory_status: Literal["available", "missing"] = "missing"
    wordpress_acf_section_inventory_note: str | None = None
    wordpress_acf_section_headings: list[str] = Field(default_factory=list)
    wordpress_acf_section_count: int | None = None
    source_public_url: str | None = None
    preview_url: str | None = None
    intended_final_url: str | None = None
    final_canonical_url: str | None = None
    inventory_gate_status: str | None = None
    inventory_gate_status_label: str | None = None
    canonical_gate_status: str | None = None
    canonical_gate_status_label: str | None = None
    duplicate_gate_status: str | None = None
    duplicate_gate_status_label: str | None = None
    content_gate_summary: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    ahrefs_candidate_rows: list[ContentAhrefsCandidateRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentDecisionItem:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentOperatorSummary(BaseModel):
    id: Literal["content_operator_summary"] = "content_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    confirmed_wordpress_count: int = 0
    missing_wordpress_count: int = 0
    current_site_match_count: int = 0
    decision_type_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentOperatorSummary:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentMarketerDecision(BaseModel):
    id: str
    technical_decision_id: str
    status: Literal["ready", "blocked"]
    decision: str
    mode_label: str
    why_it_matters: str
    safe_next_action: str
    review_card_label: str = "Karta decyzji dla Wilka"
    review_decision_after_review: str
    review_question_for_wilku: str
    review_next_safe_click: str
    review_action_ids: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    content_angle: str | None = None
    h1_direction: str | None = None
    h2_direction: list[str] = Field(default_factory=list)
    faq_direction: list[str] = Field(default_factory=list)
    cta_direction: str | None = None
    source_facts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    evidence_summary: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    measurement_plan: str
    source_public_url: str | None = None
    preview_url: str | None = None
    intended_final_url: str | None = None
    final_canonical_url: str | None = None

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentMarketerDecision:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentPreflightItem(BaseModel):
    id: str
    technical_decision_id: str
    recommended_mode: Literal["preserve", "refresh", "merge", "create", "block"]
    recommended_mode_label: str = ""
    status: Literal["allowed", "review_required", "blocked"]
    status_label: str = ""
    create_allowed: bool = False
    draft_allowed: bool = False
    wordpress_draft_allowed: bool = False
    sales_brief_allowed: bool = False
    source_public_url: str | None = None
    preview_url: str | None = None
    intended_final_url: str | None = None
    final_canonical_url: str | None = None
    inventory_gate_status: str | None = None
    inventory_gate_status_label: str | None = None
    canonical_gate_status: str | None = None
    canonical_gate_status_label: str | None = None
    duplicate_gate_status: str | None = None
    duplicate_gate_status_label: str | None = None
    claim_gate_status: str
    claim_gate_status_label: str = ""
    service_fit_status: str
    service_fit_status_label: str = ""
    similar_existing_urls: list[str] = Field(default_factory=list)
    query_overlap_summary: str
    blocked_claims: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentPreflightItem:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentPreflightResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    primary_item: ContentPreflightItem | None = None
    items: list[ContentPreflightItem] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    blocker_count: int = 0

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentPreflightResponse:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentGscSearchAnalyticsContract(BaseModel):
    source_connector: Literal["google_search_console"] = "google_search_console"
    evidence_ids: list[str] = Field(default_factory=list)
    data_availability_checked: bool = False
    date_availability_status: str = ""
    expected_data_delay_days_min: int = 2
    expected_data_delay_days_max: int = 3
    availability_date_start: str | None = None
    availability_date_end: str | None = None
    detail_date_start: str | None = None
    detail_date_end: str | None = None
    latest_available_detail_date: str | None = None
    search_type: str = ""
    detail_dimensions: str = ""
    detail_data_completeness: str = ""
    read_granularity: Literal["single_day_latest_available"] = "single_day_latest_available"
    api_recommended_page_size: int = 25000
    api_daily_row_cap_per_search_type: int = 50000
    query_page_row_limit: int | None = None
    query_page_max_rows: int | None = None
    query_page_rows_truncated: bool = False
    aggregate_date_start: str | None = None
    aggregate_date_end: str | None = None
    aggregate_dimensions: str = ""
    aggregate_aggregation_type: str = ""
    aggregate_data_completeness: str = ""
    aggregate_row_count: int | None = None
    aggregate_clicks: int | None = None
    aggregate_impressions: int | None = None
    aggregate_ctr: float | None = None
    aggregate_average_position: float | None = None
    aggregate_summary_label: str = ""
    summary_label: str = ""
    partial_detail_warning_label: str = ""
    paging_label: str = ""
    official_limits_label: str = ""
    wilq_internal_cap_label: str = ""


class ContentFreshnessAssessment(BaseModel):
    state: Literal["fresh", "stale", "missing", "blocked"]
    state_label: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    stale_after_hours: int = 48
    requires_refresh: bool
    missing_connector_ids: list[str] = Field(default_factory=list)
    blocked_connector_ids: list[str] = Field(default_factory=list)
    stale_connector_ids: list[str] = Field(default_factory=list)
    connector_labels_requiring_refresh: list[str] = Field(default_factory=list)
    connector_refresh_run_ids: dict[str, str] = Field(default_factory=dict)
    connector_covered_windows: dict[str, ConnectorCoveredWindow] = Field(default_factory=dict)
    connector_settlement_states: dict[str, ConnectorSettlementState] = Field(default_factory=dict)
    connector_quality_states: dict[str, ConnectorQualityState] = Field(default_factory=dict)
    connector_quality_caveats: dict[str, list[str]] = Field(default_factory=dict)
    summary: str
    next_step: str


class ContentDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connectors: list[ConnectorStatus]
    latest_refreshes: list[ConnectorRefreshRun] = Field(default_factory=list)
    live_data_available: bool
    live_data_status_label: str = ""
    freshness_assessment: ContentFreshnessAssessment
    gsc_search_analytics_contract: ContentGscSearchAnalyticsContract | None = None
    query_page_count: int = 0
    matched_inventory_count: int = 0
    operator_summary: ContentOperatorSummary
    marketer_decision: ContentMarketerDecision | None = None
    decision_queue: list[ContentDecisionItem] = Field(default_factory=list)
    sections: list[ContentDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0
