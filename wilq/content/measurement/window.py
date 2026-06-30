from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.workflow.models import ContentMeasurementWindowStatus, ContentWorkItem

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
    success_claim_allowed: bool = False


class ContentMeasurementWindowBlocker(BaseModel):
    code: ContentMeasurementWindowBlockerCode
    label: str
    reason: str
    next_step: str


class ContentMeasurementWindowBuildResult(BaseModel):
    window: ContentMeasurementWindow | None = None
    blockers: list[ContentMeasurementWindowBlocker] = Field(default_factory=list)


def build_content_measurement_window(
    *,
    item: ContentWorkItem,
    handoff: ContentWordPressDraftHandoff | None,
    baseline_period: ContentDateRange,
    observation_period: ContentDateRange,
    allowed_metrics: list[ContentMeasurementMetric],
    source_connectors: list[str],
) -> ContentMeasurementWindowBuildResult:
    blockers = content_measurement_window_blockers(
        item=item,
        allowed_metrics=allowed_metrics,
        source_connectors=source_connectors,
    )
    if blockers:
        return ContentMeasurementWindowBuildResult(blockers=blockers)

    assert item.final_canonical_url is not None
    evidence_ids = _unique(
        [
            *item.evidence_ids,
            *([] if handoff is None else handoff.evidence_ids),
        ]
    )
    return ContentMeasurementWindowBuildResult(
        window=ContentMeasurementWindow(
            id=f"measurement_window_{item.id}",
            work_item_id=item.id,
            content_url=item.final_canonical_url,
            baseline_period=baseline_period,
            observation_period=observation_period,
            earliest_verdict_date=observation_period.end + timedelta(days=1),
            allowed_metrics=allowed_metrics,
            source_connectors=_unique(source_connectors),
            evidence_ids=evidence_ids,
            handoff_id=None if handoff is None else handoff.id,
        )
    )


def content_measurement_window_blockers(
    *,
    item: ContentWorkItem,
    allowed_metrics: list[ContentMeasurementMetric],
    source_connectors: list[str],
) -> list[ContentMeasurementWindowBlocker]:
    blockers: list[ContentMeasurementWindowBlocker] = []
    if item.canonical_status != "resolved" or not item.final_canonical_url:
        blockers.append(
            _blocker(
                "missing_final_canonical",
                "Brakuje finalnego adresu",
                "Measurement window musi mierzyć publiczny final canonical URL.",
                "Ustal publiczny final_canonical_url przed planem pomiaru.",
            )
        )
    elif content_url_host(item.final_canonical_url) not in CONTENT_SOURCE_SITE_HOSTS:
        blockers.append(
            _blocker(
                "invalid_final_canonical",
                "Adres podglądu nie może być mierzonym canonical",
                "Dev albo preview URL nie może być podstawą oceny efektu contentu.",
                "Ustaw content_url na publiczny adres Ekologus.",
            )
        )
    if not allowed_metrics:
        blockers.append(
            _blocker(
                "missing_allowed_metrics",
                "Brakuje metryk do obserwacji",
                "WILQ musi wiedzieć, które metryki wolno oceniać po publikacji.",
                "Dodaj metryki z GSC, GA4, Ahrefs albo innych źródeł.",
            )
        )
    if not source_connectors:
        blockers.append(
            _blocker(
                "missing_source_connector",
                "Brakuje źródeł pomiaru",
                "Measurement window musi wskazywać connector, który dostarczy dane.",
                "Dodaj source connectors dla pomiaru, np. GSC i GA4.",
            )
        )
    return blockers


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


def apply_content_measurement_window_to_work_item(
    item: ContentWorkItem,
    window: ContentMeasurementWindow,
) -> ContentWorkItem:
    return item.model_copy(
        update={
            "measurement_window_status": window.status,
            "measurement_window_id": window.id,
        }
    )


def _unique(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values


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
