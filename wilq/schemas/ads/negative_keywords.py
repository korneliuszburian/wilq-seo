from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from wilq.operator_labels import (
    blocked_claim_count_label,
    evidence_count_label,
    missing_contract_count_label,
)

from ..actions import ActionPreviewCardViewModel
from ..core import MetricFact
from .diagnostics import AdsSearchTermCoverage
from .labels import (
    _ads_ad_group_display_label,
    _ads_campaign_display_label,
    _ads_read_contract_status_label,
)

__all__ = [
    "AdsKeywordMatchContextRow",
    "AdsKeywordMatchContextReadContract",
    "AdsKeywordPlannerIdeaRow",
    "AdsKeywordPlannerReadContract",
    "AdsNegativeKeywordPayloadPreview",
    "AdsNegativeKeywordCandidate",
    "AdsNegativeKeywordsReadContract",
]



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
