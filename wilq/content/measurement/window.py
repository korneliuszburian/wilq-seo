from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.content.workflow.models import ContentMeasurementWindowStatus

ContentMeasurementMetric = Literal[
    "gsc_clicks",
    "gsc_impressions",
    "gsc_ctr",
    "gsc_average_position",
    "ga4_sessions",
    "ga4_engaged_sessions",
    "ga4_engagement_rate",
    "ga4_key_events",
    "ahrefs_keywords",
    "ads_assisted_queries",
    "merchant_product_context",
    "localo_visibility",
]
ContentMeasurementWindowBlockerCode = Literal[
    "missing_final_canonical",
    "invalid_final_canonical",
    "missing_allowed_metrics",
    "missing_source_connector",
    "missing_publication_event",
    "missing_metric_evidence",
    "measurement_window_not_ready",
]


class ContentDateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> ContentDateRange:
        if self.end < self.start:
            raise ValueError("date range end must be on or after start")
        return self


class ContentMeasurementWindow(BaseModel):
    id: str
    work_item_id: str
    content_url: str
    baseline_period: ContentDateRange
    observation_period: ContentDateRange
    earliest_verdict_date: date
    allowed_metrics: list[ContentMeasurementMetric]
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    status: ContentMeasurementWindowStatus = "planned"
    handoff_id: str | None = None
    publication_evidence_id: str | None = None
    publication_refresh_run_id: str | None = None
    publication_source_connector: str | None = None
    wordpress_post_id: str | None = None
    deployment_id: str | None = None
    deployed_revision_id: str | None = None
    deployed_revision_digest: str | None = None
    success_claim_allowed: bool = False


class ContentMeasurementWindowBlocker(BaseModel):
    code: ContentMeasurementWindowBlockerCode
    label: str
    reason: str
    next_step: str


class ContentMeasurementWindowBuildResult(BaseModel):
    window: ContentMeasurementWindow | None = None
    blockers: list[ContentMeasurementWindowBlocker] = Field(default_factory=list)


def mark_content_measurement_window_ready(
    window: ContentMeasurementWindow,
    *,
    as_of: date,
) -> ContentMeasurementWindow:
    if as_of < window.earliest_verdict_date:
        return window
    return window.model_copy(
        update={
            "status": "ready_for_review",
            "success_claim_allowed": True,
        }
    )


def content_measurement_window_outcome_allowed(
    window: ContentMeasurementWindow,
    *,
    as_of: date,
) -> bool:
    return (
        window.status in {"ready_for_review", "closed"}
        and window.success_claim_allowed
        and as_of >= window.earliest_verdict_date
    )


def content_measurement_window_outcome_blockers(
    window: ContentMeasurementWindow,
) -> list[ContentMeasurementWindowBlocker]:
    if window.status in {"ready_for_review", "closed"} and window.success_claim_allowed:
        return []
    return [
        _blocker(
            "measurement_window_not_ready",
            "Nie wolno jeszcze oceniać efektu",
            "WILQ może zbierać dane, ale nie może claimować sukcesu albo porażki przed "
            "końcem okna obserwacji.",
            "Wróć do oceny po dacie earliest_verdict_date.",
        )
    ]


def _blocker(
    code: ContentMeasurementWindowBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentMeasurementWindowBlocker:
    return ContentMeasurementWindowBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
