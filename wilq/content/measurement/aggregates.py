from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.canonical.metric_dimensions import (
    METRIC_LANDING_URL_DIMENSIONS,
    metric_dimensions_match_landing,
)
from wilq.schemas import MetricFact

MeasurementAggregateExclusionCode = Literal[
    "wrong_period",
    "ambiguous_source_lineage",
    "insufficient_values",
    "missing_denominator",
    "unrecognized_detail_metric",
]

MeasurementComparisonStatus = Literal["available", "not_available", "ambiguous"]
MeasurementConnector = Literal["google_search_console", "google_analytics_4"]


class MeasurementAggregateExclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: MeasurementAggregateExclusionCode
    source_connector: str
    metric_name: str
    period: str
    evidence_ids: list[str] = Field(default_factory=list)


class MeasurementAggregateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[MetricFact] = Field(default_factory=list)
    exclusions: list[MeasurementAggregateExclusion] = Field(default_factory=list)


class MeasurementPeriodComparison(BaseModel):
    """A bounded, page-scoped comparison with explicit period lineage."""

    model_config = ConfigDict(extra="forbid")

    source_connector: Literal["google_search_console", "google_analytics_4"]
    status: MeasurementComparisonStatus
    baseline_period: str | None = None
    comparison_period: str | None = None
    metric_names: list[str] = Field(default_factory=list)
    baseline_values: dict[str, float] = Field(default_factory=dict)
    comparison_values: dict[str, float] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str


_DETAIL_METRICS = {
    "google_search_console": {
        "clicks",
        "impressions",
        "ctr",
        "average_position",
    },
    "google_analytics_4": {
        "sessions",
        "engaged_sessions",
        "engagement_rate",
        "key_events",
    },
}
_SUM_METRICS = {
    "clicks",
    "impressions",
    "sessions",
    "engaged_sessions",
    "key_events",
}


def aggregate_exact_page_metric_facts(
    facts: list[MetricFact],
    *,
    content_url: str,
) -> MeasurementAggregateResult:
    """Aggregate connector detail rows only when exact period and lineage agree."""
    grouped: dict[tuple[str, str], list[MetricFact]] = defaultdict(list)
    passthrough: list[MetricFact] = []
    exclusions: list[MeasurementAggregateExclusion] = []
    for fact in facts:
        if not metric_dimensions_match_landing(fact.dimensions, content_url):
            continue
        if fact.source_connector not in _DETAIL_METRICS:
            passthrough.append(fact)
            continue
        if set(fact.dimensions) <= METRIC_LANDING_URL_DIMENSIONS:
            passthrough.append(fact)
            continue
        if not _is_exact_period(fact.period):
            exclusions.append(
                _row_exclusion("wrong_period", fact, metric_name=fact.name)
            )
            continue
        if fact.name not in _DETAIL_METRICS[fact.source_connector]:
            exclusions.append(
                _row_exclusion(
                    "unrecognized_detail_metric", fact, metric_name=fact.name
                )
            )
            continue
        grouped[(fact.source_connector, fact.period)].append(fact)

    _prefer_newest_evidence_per_group(grouped)

    derived: list[MetricFact] = []
    for (connector, period), rows in grouped.items():
        group_derived, group_exclusions = _aggregate_detail_group(
            connector, period, rows, content_url=content_url
        )
        derived.extend(group_derived)
        exclusions.extend(group_exclusions)
    passthrough_keys = {
        (fact.source_connector, fact.name, fact.period) for fact in passthrough
    }
    return MeasurementAggregateResult(
        facts=[
            *passthrough,
            *[
                fact
                for fact in derived
                if (fact.source_connector, fact.name, fact.period) not in passthrough_keys
            ],
        ],
        exclusions=_deduplicate_exclusions(exclusions),
    )


def _prefer_newest_evidence_per_group(
    grouped: dict[tuple[str, str], list[MetricFact]],
) -> None:
    """Prefer the newest complete evidence per connector/period pair.

    A repeated refresh can cover the same period.  Only equal-timestamp
    lineage remains ambiguous and is kept for the typed blocker below.
    """
    for key, rows in list(grouped.items()):
        by_evidence: dict[str, list[MetricFact]] = defaultdict(list)
        for row in rows:
            by_evidence[row.evidence_id].append(row)
        if len(by_evidence) <= 1:
            continue
        evidence_collected_at = {
            evidence_id: max(
                (row.collected_at for row in evidence_rows if row.collected_at is not None),
                default=None,
            )
            for evidence_id, evidence_rows in by_evidence.items()
        }
        timestamp_values = [
            value for value in evidence_collected_at.values() if value is not None
        ]
        # Missing collection timestamps cannot establish a winner.  Keep all
        # lineages so the aggregate below emits the typed ambiguity blocker;
        # never let an incomplete legacy row crash the measurement read.
        newest = max(timestamp_values) if timestamp_values else None
        newest_evidence = [
            evidence_id
            for evidence_id, collected_at in evidence_collected_at.items()
            if collected_at == newest
        ]
        if newest is None or len(newest_evidence) != 1:
            continue
        grouped[key] = by_evidence[newest_evidence[0]]


def _aggregate_detail_group(
    connector: str,
    period: str,
    rows: list[MetricFact],
    *,
    content_url: str,
) -> tuple[list[MetricFact], list[MeasurementAggregateExclusion]]:
    """Aggregate one connector/period group into derived facts and blockers."""
    evidence_ids = sorted({row.evidence_id for row in rows if row.evidence_id})
    if len(evidence_ids) != 1:
        exclusions: list[MeasurementAggregateExclusion] = [
            _group_exclusion("ambiguous_source_lineage", connector, period, evidence_ids)
        ]
        return [], exclusions
    by_name: dict[str, list[MetricFact]] = defaultdict(list)
    for row in rows:
        by_name[row.name].append(row)
    required_detail_metrics = (
        {"clicks", "impressions"}
        if connector == "google_search_console"
        else {"sessions", "engaged_sessions"}
    )
    if not required_detail_metrics.issubset(by_name):
        return [], [
            _group_exclusion("insufficient_values", connector, period, evidence_ids)
        ]
    if connector == "google_search_console" and {
        "clicks",
        "impressions",
    }.issubset(by_name):
        by_name.setdefault("ctr", [])
    if connector == "google_analytics_4" and {
        "sessions",
        "engaged_sessions",
    }.issubset(by_name):
        by_name.setdefault("engagement_rate", [])
    impressions = _numeric_sum(by_name.get("impressions", []))
    derived: list[MetricFact] = []
    exclusions = []
    for metric_name, metric_rows in by_name.items():
        value = _derived_metric_value(
            metric_name, by_name, impressions
        )
        if value is None:
            if metric_name in {"ctr", "engagement_rate", "average_position"}:
                reason: MeasurementAggregateExclusionCode = "missing_denominator"
            else:
                reason = "insufficient_values"
            exclusions.append(
                _group_exclusion(
                    reason, connector, period, evidence_ids, metric_name=metric_name
                )
            )
            continue
        url_dimension = "page" if connector == "google_search_console" else "landing_page"
        derived.append(
            MetricFact(
                name=metric_name,
                value=value,
                period=period,
                source_connector=connector,
                evidence_id=evidence_ids[0],
                dimensions={url_dimension: content_url},
                unit=(
                    metric_rows[0].unit
                    if metric_rows
                    else "ratio"
                    if metric_name in {"ctr", "engagement_rate"}
                    else None
                ),
                collected_at=max(
                    (row.collected_at for row in metric_rows if row.collected_at is not None),
                    default=None,
                ),
            )
        )
    return derived, exclusions


def _derived_metric_value(
    metric_name: str,
    by_name: dict[str, list[MetricFact]],
    impressions: float | None,
) -> float | None:
    """Compute one derived metric; ``None`` means the row cannot be derived."""
    if metric_name in _SUM_METRICS:
        return _numeric_sum(by_name.get(metric_name, []))
    if metric_name in {"ctr", "engagement_rate"}:
        denominator = impressions if metric_name == "ctr" else _numeric_sum(
            by_name.get("sessions", [])
        )
        numerator = (
            _numeric_sum(by_name.get("clicks", []))
            if metric_name == "ctr"
            else _numeric_sum(by_name.get("engaged_sessions", []))
        )
        if denominator is None or denominator == 0 or numerator is None:
            return None
        return numerator / denominator
    if metric_name == "average_position":
        return _weighted_average(
            by_name.get(metric_name, []), by_name.get("impressions", [])
        )
    return None


def _row_exclusion(
    code: MeasurementAggregateExclusionCode,
    fact: MetricFact,
    *,
    metric_name: str,
) -> MeasurementAggregateExclusion:
    return MeasurementAggregateExclusion(
        code=code,
        source_connector=fact.source_connector,
        metric_name=metric_name,
        period=fact.period,
        evidence_ids=[fact.evidence_id],
    )


def _group_exclusion(
    code: MeasurementAggregateExclusionCode,
    connector: str,
    period: str,
    evidence_ids: list[str],
    *,
    metric_name: str = "*",
) -> MeasurementAggregateExclusion:
    return MeasurementAggregateExclusion(
        code=code,
        source_connector=connector,
        metric_name=metric_name,
        period=period,
        evidence_ids=evidence_ids,
    )


def compare_exact_page_metric_periods(
    facts: list[MetricFact],
    *,
    content_url: str,
) -> list[MeasurementPeriodComparison]:
    """Return only comparisons backed by two exact, complete page periods.

    A previous adjacent row or a single collected snapshot is not a comparison.
    The aggregate seam first resolves repeated refresh lineage, then requires
    the connector's minimum metric set in each of the two latest periods.
    """
    aggregate = aggregate_exact_page_metric_facts(facts, content_url=content_url)
    required: dict[MeasurementConnector, set[str]] = {
        "google_search_console": {"clicks", "impressions"},
        "google_analytics_4": {"sessions", "engaged_sessions"},
    }
    by_connector_period: dict[
        tuple[MeasurementConnector, str], list[MetricFact]
    ] = defaultdict(list)
    for fact in aggregate.facts:
        if fact.source_connector in required and _is_exact_period(fact.period):
            by_connector_period[(fact.source_connector, fact.period)].append(fact)

    comparisons: list[MeasurementPeriodComparison] = []
    for connector, required_names in required.items():
        periods = sorted(
            {
                period
                for source, period in by_connector_period
                if source == connector
            },
            key=lambda value: value.split("/", 1)[0],
        )
        if len(periods) < 2:
            comparisons.append(
                MeasurementPeriodComparison(
                    source_connector=connector,
                    status="not_available",
                    reason=(
                        "Brakuje dwóch odrębnych, dokładnych okresów tego samego "
                        "adresu; pojedynczy snapshot nie jest trendem."
                    ),
                )
            )
            continue
        baseline_period, comparison_period = periods[-2:]
        baseline_rows = by_connector_period[(connector, baseline_period)]
        comparison_rows = by_connector_period[(connector, comparison_period)]
        baseline_names = {row.name for row in baseline_rows}
        comparison_names = {row.name for row in comparison_rows}
        if not required_names <= baseline_names or not required_names <= comparison_names:
            comparisons.append(
                MeasurementPeriodComparison(
                    source_connector=connector,
                    status="not_available",
                    baseline_period=baseline_period,
                    comparison_period=comparison_period,
                    reason="Jeden z porównywanych okresów nie ma kompletu wymaganych metryk.",
                )
            )
            continue
        evidence_ids = sorted(
            {
                row.evidence_id
                for row in [*baseline_rows, *comparison_rows]
                if row.evidence_id
            }
        )
        baseline_values = {
            row.name: float(row.value)
            for row in baseline_rows
            if row.name in required_names and isinstance(row.value, (int, float))
        }
        comparison_values = {
            row.name: float(row.value)
            for row in comparison_rows
            if row.name in required_names and isinstance(row.value, (int, float))
        }
        if len(evidence_ids) < 2:
            comparisons.append(
                MeasurementPeriodComparison(
                    source_connector=connector,
                    status="ambiguous",
                    baseline_period=baseline_period,
                    comparison_period=comparison_period,
                    metric_names=sorted(required_names),
                    baseline_values=baseline_values,
                    comparison_values=comparison_values,
                    evidence_ids=evidence_ids,
                    reason="Dwa okresy nie mają niezależnej, rozróżnialnej lineage evidence.",
                )
            )
            continue
        comparisons.append(
            MeasurementPeriodComparison(
                source_connector=connector,
                status="available",
                baseline_period=baseline_period,
                comparison_period=comparison_period,
                metric_names=sorted(required_names),
                baseline_values=baseline_values,
                comparison_values=comparison_values,
                evidence_ids=evidence_ids,
                reason="Dwa dokładne okresy tego samego adresu mają kompletną lineage.",
            )
        )
    return comparisons


def _is_exact_period(period: str) -> bool:
    try:
        start_text, end_text = period.split("/", 1)
        return date.fromisoformat(start_text) <= date.fromisoformat(end_text)
    except ValueError:
        return False


def _numeric_sum(rows: list[MetricFact]) -> float | None:
    values = [float(row.value) for row in rows if isinstance(row.value, (int, float))]
    return sum(values) if values and len(values) == len(rows) else None


def _weighted_average(
    rows: list[MetricFact],
    impression_rows: list[MetricFact],
) -> float | None:
    denominator = _numeric_sum(impression_rows)
    if denominator is None or denominator == 0 or len(rows) != len(impression_rows):
        return None
    weighted = [
        float(row.value) * float(weight.value)
        for row, weight in zip(rows, impression_rows, strict=True)
        if isinstance(row.value, (int, float)) and isinstance(weight.value, (int, float))
    ]
    if len(weighted) != len(rows) or denominator is None or denominator == 0:
        return None
    return sum(weighted) / denominator


def _deduplicate_exclusions(
    exclusions: list[MeasurementAggregateExclusion],
) -> list[MeasurementAggregateExclusion]:
    """Collapse repeated row-level exclusions without dropping lineage."""
    merged: dict[tuple[str, str, str, str], MeasurementAggregateExclusion] = {}
    for exclusion in exclusions:
        key = (
            exclusion.code,
            exclusion.source_connector,
            exclusion.metric_name,
            exclusion.period,
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = exclusion.model_copy(
                update={"evidence_ids": sorted(set(exclusion.evidence_ids))}
            )
            continue
        merged[key] = existing.model_copy(
            update={
                "evidence_ids": sorted(
                    set(existing.evidence_ids) | set(exclusion.evidence_ids)
                )
            }
        )
    return list(merged.values())


__all__ = [
    "MeasurementAggregateExclusion",
    "MeasurementAggregateResult",
    "MeasurementPeriodComparison",
    "aggregate_exact_page_metric_facts",
    "compare_exact_page_metric_periods",
]
