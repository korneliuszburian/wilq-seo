"""Public GET measurement contract: real page metrics with before/after periods."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.measurement.aggregates import compare_exact_page_metric_periods
from wilq.content.measurement.evidence import load_content_measurement_facts
from wilq.content.measurement.window import ContentDateRange
from wilq.schemas import MetricFact


class ContentMeasurementReadRow(BaseModel):
    """One source connector's exact before/after period comparison."""

    model_config = ConfigDict(extra="forbid")

    source_connector: str
    status: str
    baseline_period: str | None = None
    observation_period: str | None = None
    metric_names: list[str] = Field(default_factory=list)
    baseline_values: dict[str, float] = Field(default_factory=dict)
    observation_values: dict[str, float] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentMeasurementReadResponse(BaseModel):
    """Real, evidence-traceable page metrics with before/after comparison."""

    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    content_url: str
    baseline_period: ContentDateRange | None = None
    observation_period: ContentDateRange | None = None
    rows: list[ContentMeasurementReadRow] = Field(default_factory=list)
    fact_count: int = 0
    source_connectors: list[str] = Field(default_factory=list)


def _fact_date_range(facts: list[MetricFact]) -> ContentDateRange | None:
    dates = []
    for fact in facts:
        collected_at = getattr(fact, "collected_at", None)
        if collected_at is not None:
            dates.append(collected_at.date())
    if not dates:
        return None
    return ContentDateRange(start=min(dates), end=max(dates))


def build_content_measurement_read(
    *,
    work_item_id: str,
    content_url: str,
) -> ContentMeasurementReadResponse:
    facts = load_content_measurement_facts(content_url)
    comparisons = (
        [] if not facts else compare_exact_page_metric_periods(facts, content_url=content_url)
    )
    rows = [
        ContentMeasurementReadRow(
            source_connector=comparison.source_connector,
            status=comparison.status,
            baseline_period=comparison.baseline_period,
            observation_period=comparison.comparison_period,
            metric_names=comparison.metric_names,
            baseline_values=comparison.baseline_values,
            observation_values=comparison.comparison_values,
            evidence_ids=comparison.evidence_ids,
        )
        for comparison in comparisons
    ]
    connectors = sorted({row.source_connector for row in rows if row.source_connector})
    return ContentMeasurementReadResponse(
        work_item_id=work_item_id,
        content_url=content_url,
        baseline_period=(
            _fact_date_range(
                [fact for fact in facts if getattr(fact, "collected_at", None) is not None]
            )
        ),
        observation_period=None,
        rows=rows,
        fact_count=len(facts),
        source_connectors=connectors,
    )


__all__ = [
    "ContentMeasurementReadRow",
    "ContentMeasurementReadResponse",
    "build_content_measurement_read",
]
