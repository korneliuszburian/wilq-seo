"""Typed evidence contracts for bounded measurement decisions."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MetricSampleEvidence(BaseModel):
    """One source-backed sample-size observation for a bounded decision."""

    metric_name: str
    period: str
    sample_size: int = Field(ge=0)
    minimum_sample_size: int = Field(ge=1)
    source_connector: str
    evidence_ids: list[str] = Field(min_length=1)


class SourceComparisonValue(BaseModel):
    """A comparable value with explicit source and evidence lineage."""

    source_connector: str
    value: float | int | str
    evidence_ids: list[str] = Field(min_length=1)


class SourceComparisonEvidence(BaseModel):
    """Values that must be compared before a cross-source conclusion."""

    metric_name: str
    period: str
    values: list[SourceComparisonValue] = Field(min_length=2)

    @model_validator(mode="after")
    def require_distinct_sources(self) -> SourceComparisonEvidence:
        sources = [item.source_connector for item in self.values]
        if len(set(sources)) != len(sources):
            raise ValueError("Source comparison requires distinct source connectors.")
        return self
