from __future__ import annotations

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from wilq.operator_labels import evidence_count_label

from .labels import (
    _operator_number_label,
    _operator_percent_label,
)

__all__ = [
    "DemandGenAdGroupAdRow",
    "DemandGenCreativeAssetRow",
    "DemandGenLandingQualityRow",
    "DemandGenCampaignModeReviewRow",
]



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
