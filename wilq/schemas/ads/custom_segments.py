from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from wilq.operator_labels import (
    action_count_label,
    evidence_count_label,
    missing_contract_count_label,
    required_validation_count_label,
)

from ..actions import ActionPreviewCardViewModel
from ..core import MetricFact
from .diagnostics import AdsSearchTermMetricRow
from .labels import _ads_read_contract_status_label
from .negative_keywords import AdsKeywordPlannerIdeaRow

__all__ = [
    "AdsCustomSegmentTargetingPreview",
    "AdsCustomSegmentApplySafetyReview",
    "AdsCustomSegmentPayloadPreview",
    "AdsCustomSegmentAudienceForecastRow",
    "AdsCustomSegmentAudienceForecastReadContract",
    "default_ads_custom_segment_audience_forecast_contract",
    "AdsCustomSegmentSourceQuality",
    "AdsCustomSegmentCandidate",
    "AdsCustomSegmentsReadContract",
]



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
