from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from wilq.content.canonical.urls import content_normalized_path, content_normalized_url
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftExecutionResult
from wilq.content.measurement.outcome import ContentMeasurementObservedMetric
from wilq.content.measurement.window import (
    ContentDateRange,
    ContentMeasurementMetric,
    ContentMeasurementWindow,
    ContentMeasurementWindowBlocker,
    ContentMeasurementWindowBuildResult,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.schemas import MetricFact
from wilq.storage.metric_store import metric_store

MEASUREMENT_CONNECTORS = [
    "wordpress_ekologus",
    "google_search_console",
    "google_analytics_4",
]
METRIC_NAMES: dict[tuple[str, str], ContentMeasurementMetric] = {
    ("google_search_console", "clicks"): "gsc_clicks",
    ("google_search_console", "impressions"): "gsc_impressions",
    ("google_search_console", "ctr"): "gsc_ctr",
    ("google_search_console", "average_position"): "gsc_average_position",
    ("google_analytics_4", "sessions"): "ga4_sessions",
    ("google_analytics_4", "engaged_sessions"): "ga4_engaged_sessions",
    ("google_analytics_4", "engagement_rate"): "ga4_engagement_rate",
    ("google_analytics_4", "key_events"): "ga4_key_events",
}
CONTENT_URL_DIMENSIONS = {
    "content_url",
    "page",
    "page_location",
    "landing_page",
    "landing_page_plus_query_string",
}


def load_content_measurement_facts(content_url: str | None) -> list[MetricFact]:
    store = metric_store()
    normalized_url = content_normalized_url(content_url)
    normalized_path = content_normalized_path(content_url)
    return [
        fact
        for connector_id in MEASUREMENT_CONNECTORS
        for fact in store.list_metric_facts_for_content_url(
            [connector_id],
            normalized_url,
            content_path=normalized_path,
        )
    ]


def build_publication_bound_measurement_window(
    *,
    item: ContentWorkItem,
    handoff: ContentWordPressDraftHandoff | None,
    execution: ContentWordPressDraftExecutionResult | None,
    metric_facts: list[MetricFact],
) -> ContentMeasurementWindowBuildResult:
    publication_fact = _publication_fact(item, execution, metric_facts)
    if publication_fact is None:
        return ContentMeasurementWindowBuildResult(
            blockers=[
                _blocker(
                    "missing_publication_event",
                    "Brakuje potwierdzonej publikacji",
                    "Szkic WordPress nie jest publikacją. WILQ musi zobaczyć ten sam wpis "
                    "i adres jako opublikowany w odczycie WordPress.",
                    "Opublikuj zatwierdzony szkic poza WILQ, odśwież WordPress i wróć do pomiaru.",
                )
            ]
        )
    measurement_facts = [
        fact
        for fact in metric_facts
        if _measurement_metric(fact) is not None
        and _fact_matches_url(fact, item.final_canonical_url)
        and _fact_is_page_aggregate(fact)
    ]
    allowed_metrics = list(
        dict.fromkeys(
            cast(ContentMeasurementMetric, _measurement_metric(fact))
            for fact in measurement_facts
        )
    )
    if not allowed_metrics:
        return ContentMeasurementWindowBuildResult(
            blockers=[
                _blocker(
                    "missing_metric_evidence",
                    "Brakuje metryk dla opublikowanego adresu",
                    "WILQ potwierdził publikację, ale nie ma exact-URL danych GSC ani GA4.",
                    "Odśwież GSC lub GA4 po publikacji i wróć do pomiaru.",
                )
            ]
        )
    observed_at = _required_collected_at(publication_fact)
    if execution is None or execution.wordpress_post_id is None:
        raise RuntimeError("Publication fact passed without a bound WordPress execution")
    publication_date = observed_at.date()
    baseline_period = ContentDateRange(
        start=publication_date - timedelta(days=28),
        end=publication_date - timedelta(days=1),
    )
    observation_period = ContentDateRange(
        start=publication_date,
        end=publication_date + timedelta(days=27),
    )
    return ContentMeasurementWindowBuildResult(
        window=ContentMeasurementWindow(
            id=f"measurement_window_{item.id}_{publication_fact.evidence_id}",
            work_item_id=item.id,
            content_url=cast(str, item.final_canonical_url),
            baseline_period=baseline_period,
            observation_period=observation_period,
            earliest_verdict_date=observation_period.end + timedelta(days=1),
            allowed_metrics=allowed_metrics,
            source_connectors=list(
                dict.fromkeys(fact.source_connector for fact in measurement_facts)
            ),
            evidence_ids=list(
                dict.fromkeys(
                    [
                        *item.evidence_ids,
                        *([] if handoff is None else handoff.evidence_ids),
                        publication_fact.evidence_id,
                        *(fact.evidence_id for fact in measurement_facts),
                    ]
                )
            ),
            handoff_id=None if handoff is None else handoff.id,
            publication_evidence_id=publication_fact.evidence_id,
            publication_refresh_run_id=_refresh_run_id(publication_fact.evidence_id),
            wordpress_post_id=execution.wordpress_post_id,
        )
    )


def observed_metrics_from_store(
    window: ContentMeasurementWindow,
    metric_facts: list[MetricFact],
) -> list[ContentMeasurementObservedMetric]:
    observed: list[ContentMeasurementObservedMetric] = []
    for metric in window.allowed_metrics:
        candidates = [
            fact
            for fact in metric_facts
            if _measurement_metric(fact) == metric
            and _fact_matches_url(fact, window.content_url)
            and _fact_is_page_aggregate(fact)
            and _fact_covers_period(fact, window.baseline_period)
            and isinstance(fact.value, (int, float))
            and fact.collected_at is not None
        ]
        baseline = _latest_period_fact(candidates, window.baseline_period)
        observation = _latest_period_fact(
            [
                fact
                for fact in metric_facts
                if _measurement_metric(fact) == metric
                and _fact_matches_url(fact, window.content_url)
                and _fact_is_page_aggregate(fact)
                and _fact_covers_period(fact, window.observation_period)
                and isinstance(fact.value, (int, float))
                and fact.collected_at is not None
            ],
            window.observation_period,
        )
        if baseline is None or observation is None:
            continue
        evidence_ids = list(dict.fromkeys([baseline.evidence_id, observation.evidence_id]))
        observed.append(
            ContentMeasurementObservedMetric(
                metric=metric,
                baseline_value=float(baseline.value),
                observation_value=float(observation.value),
                source_connector=observation.source_connector,
                evidence_ids=evidence_ids,
                metric_fact_ids=[
                    _metric_fact_locator(baseline),
                    _metric_fact_locator(observation),
                ],
                refresh_run_ids=list(
                    dict.fromkeys(_refresh_run_id(evidence) for evidence in evidence_ids)
                ),
                work_item_id=window.work_item_id,
                measurement_window_id=window.id,
                content_url=window.content_url,
            )
        )
    return observed


def _publication_fact(
    item: ContentWorkItem,
    execution: ContentWordPressDraftExecutionResult | None,
    metric_facts: list[MetricFact],
) -> MetricFact | None:
    if (
        execution is None
        or execution.status != "created"
        or execution.mode != "live"
        or not execution.wordpress_post_id
        or execution.payload is None
        or content_normalized_url(execution.payload.final_canonical_url)
        != content_normalized_url(item.final_canonical_url)
    ):
        return None
    matches = [
        fact
        for fact in metric_facts
        if fact.source_connector == "wordpress_ekologus"
        and fact.name == "content_object_seen"
        and fact.dimensions.get("object_id") == execution.wordpress_post_id
        and fact.dimensions.get("status") == "publish"
        and _fact_matches_url(fact, item.final_canonical_url)
        and fact.collected_at is not None
    ]
    return min(matches, key=lambda fact: _required_collected_at(fact), default=None)


def _measurement_metric(fact: MetricFact) -> ContentMeasurementMetric | None:
    return METRIC_NAMES.get((fact.source_connector, fact.name))


def _fact_matches_url(fact: MetricFact, content_url: str | None) -> bool:
    expected = content_normalized_url(content_url)
    expected_path = content_normalized_path(content_url)
    return bool(expected) and (
        any(
            content_normalized_url(fact.dimensions.get(key)) == expected
            for key in ("content_url", "page", "page_location")
        )
        or any(
            content_normalized_path(fact.dimensions.get(key)) == expected_path
            for key in (
                "landing_page",
                "landing_page_plus_query_string",
            )
        )
    )


def _latest_period_fact(
    facts: list[MetricFact],
    period: ContentDateRange,
) -> MetricFact | None:
    matches = [fact for fact in facts if _fact_covers_period(fact, period)]
    return max(matches, key=lambda fact: _required_collected_at(fact), default=None)


def _fact_covers_period(fact: MetricFact, period: ContentDateRange) -> bool:
    return fact.period == f"{period.start.isoformat()}/{period.end.isoformat()}"


def _fact_is_page_aggregate(fact: MetricFact) -> bool:
    return bool(fact.dimensions) and set(fact.dimensions) <= CONTENT_URL_DIMENSIONS


def _required_collected_at(fact: MetricFact) -> datetime:
    if fact.collected_at is None:
        raise RuntimeError("Measurement fact passed a collected_at gate without a timestamp")
    value = fact.collected_at
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _refresh_run_id(evidence_id: str) -> str:
    return evidence_id.removeprefix("ev_refresh_")


def _metric_fact_locator(fact: MetricFact) -> str:
    return f"{fact.evidence_id}:{fact.source_connector}:{fact.name}"


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
) -> ContentMeasurementWindowBlocker:
    return ContentMeasurementWindowBlocker.model_validate(
        {"code": code, "label": label, "reason": reason, "next_step": next_step}
    )
