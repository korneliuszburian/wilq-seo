"""Exact-revision GET contract for persisted content measurement evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.measurement import evidence as measurement_evidence
from wilq.content.measurement.aggregates import (
    MeasurementComparisonStatus,
    MeasurementConnector,
    compare_exact_page_metric_periods,
)
from wilq.content.measurement.deployment import ContentPublicDeployment
from wilq.schemas import MetricFact

ContentMeasurementReadStatus = Literal["blocked", "not_available", "available"]


class ContentMeasurementReadRow(BaseModel):
    """One connector's exact before/after comparison, including its reason."""

    model_config = ConfigDict(extra="forbid")

    source_connector: MeasurementConnector
    status: MeasurementComparisonStatus
    reason: str = Field(min_length=1)
    baseline_period: str | None = None
    observation_period: str | None = None
    metric_names: list[str] = Field(default_factory=list)
    baseline_values: dict[str, float] = Field(default_factory=dict)
    observation_values: dict[str, float] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentMeasurementReadResponse(BaseModel):
    """Measurement projection bound to one persisted revision/deployment."""

    model_config = ConfigDict(extra="forbid")

    status: ContentMeasurementReadStatus
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    deployment_id: str | None = None
    content_url: str | None = None
    publication_evidence_id: str | None = None
    publication_source_connector: str | None = None
    rows: list[ContentMeasurementReadRow] = Field(default_factory=list)
    fact_count: int = Field(default=0, ge=0)
    source_connectors: list[MeasurementConnector] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_status_lineage(self) -> ContentMeasurementReadResponse:
        deployment_fields = (
            self.deployment_id,
            self.content_url,
            self.publication_evidence_id,
            self.publication_source_connector,
        )
        if self.status == "blocked":
            if any(value is not None for value in deployment_fields):
                raise ValueError("Blocked measurement cannot claim deployment lineage.")
            if self.rows or self.fact_count or self.source_connectors:
                raise ValueError("Blocked measurement cannot claim metric evidence.")
        elif any(value is None for value in deployment_fields):
            raise ValueError("Measurable revision requires exact deployment lineage.")
        if self.status == "available" and not any(row.status == "available" for row in self.rows):
            raise ValueError("Available measurement requires an available comparison.")
        return self


def build_content_measurement_read(
    *,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
    deployment: ContentPublicDeployment | None,
) -> ContentMeasurementReadResponse:
    if deployment is None or not _deployment_matches_revision(
        deployment,
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision_digest,
    ):
        return ContentMeasurementReadResponse(
            status="blocked",
            reason=(
                "Brakuje potwierdzonego wdrożenia dokładnie tej rewizji; "
                "adres z diagnostyki nie jest dowodem publikacji."
            ),
            safe_next_step=("Potwierdź publiczne wdrożenie tej rewizji z evidence WordPress."),
            work_item_id=work_item_id,
            revision_id=revision_id,
            revision_digest=revision_digest,
        )

    facts = measurement_evidence.load_content_measurement_facts(deployment.public_url)
    comparisons = compare_exact_page_metric_periods(
        facts,
        content_url=deployment.public_url,
    )
    rows = [
        ContentMeasurementReadRow(
            source_connector=comparison.source_connector,
            status=comparison.status,
            reason=comparison.reason,
            baseline_period=comparison.baseline_period,
            observation_period=comparison.comparison_period,
            metric_names=comparison.metric_names,
            baseline_values=comparison.baseline_values,
            observation_values=comparison.comparison_values,
            evidence_ids=comparison.evidence_ids,
        )
        for comparison in comparisons
    ]
    available = any(row.status == "available" for row in rows)
    return ContentMeasurementReadResponse(
        status="available" if available else "not_available",
        reason=(
            "Co najmniej jedno źródło ma dwa dokładne okresy z niezależną lineage."
            if available
            else "Brakuje dwóch kompletnych, porównywalnych okresów dla tego wdrożenia."
        ),
        safe_next_step=(
            "Porównaj widoczne okresy i evidence przed decyzją o wyniku."
            if available
            else "Odśwież źródła po zamknięciu kolejnego dokładnego okresu."
        ),
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision_digest,
        deployment_id=deployment.deployment_id,
        content_url=deployment.public_url,
        publication_evidence_id=deployment.publication_evidence_id,
        publication_source_connector=deployment.publication_source_connector,
        rows=rows,
        fact_count=len(facts),
        source_connectors=_evidence_backed_connectors(facts),
    )


def _deployment_matches_revision(
    deployment: ContentPublicDeployment,
    *,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
) -> bool:
    return (
        deployment.work_item_id == work_item_id
        and deployment.revision_id == revision_id
        and deployment.revision_digest == revision_digest
    )


def _evidence_backed_connectors(facts: list[MetricFact]) -> list[MeasurementConnector]:
    connectors: list[MeasurementConnector] = []
    for connector in ("google_search_console", "google_analytics_4"):
        if any(fact.source_connector == connector and fact.evidence_id for fact in facts):
            connectors.append(connector)
    return connectors


__all__ = [
    "ContentMeasurementReadResponse",
    "ContentMeasurementReadRow",
    "ContentMeasurementReadStatus",
    "build_content_measurement_read",
]
