"""Decomposed ga4_diagnostics shared implementation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import ConnectorRefreshRun, ConnectorRefreshStatus, MetricFact, TacticalQueueItem

GA4_CONNECTOR_ID = "google_analytics_4"


GA4_METRIC_FACT_LIMIT = 2000


GA4_STALE_AFTER_HOURS = 48


GA4_CONVERSION_METRIC_NAMES = {
    "conversions",
    "ecommerce_purchases",
    "key_events",
    "purchase_revenue",
    "total_revenue",
    "transactions",
}


GA4_CONVERSION_BLOCKED_CLAIMS = [
    "współczynnik konwersji",
    "zwrot z reklam",
    "przychód",
    "opłacalność",
    "spadek konwersji",
    "diagnoza lejka",
    "ocena atrybucji",
]


GA4_KNOWLEDGE_CARD_IDS = ["card_ga4_behavior_diagnostics_playbook"]


GA4_EXPERT_RULE_IDS = ["ga4_diagnostics_v1", "ga4_platform_traps_v1"]


Ga4DecisionType = Literal[
    "fix_measurement",
    "review_traffic_quality",
    "review_landing_mapping",
]


def _ga4_metric_tiles(facts: Iterable[MetricFact]) -> dict[str, float | int | str]:
    latest_by_name: dict[str, MetricFact] = {}
    for fact in facts:
        latest_by_name.setdefault(fact.name, fact)

    tiles: dict[str, float | int | str] = {}
    for metric_name, label in (
        ("active_users", "aktywni"),
        ("sessions", "sesje"),
        ("event_count", "zdarzenia"),
        ("screen_page_views", "odsłony"),
    ):
        metric_fact = latest_by_name.get(metric_name)
        if metric_fact is None:
            continue
        value = _numeric_value(metric_fact.value)
        tiles[label] = int(value) if value.is_integer() else round(value, 2)

    engagement_fact = latest_by_name.get("engagement_rate")
    if engagement_fact is not None:
        engagement_value = _numeric_value(engagement_fact.value)
        tiles["zaangażowanie"] = _format_percent(engagement_value)
    return tiles


def _numeric_value(value: str | int | float) -> float:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except ValueError:
        return 0.0


def _format_percent(value: float) -> str:
    percent_value = value * 100 if value <= 1 else value
    formatted = f"{percent_value:.2f}".rstrip("0").rstrip(".")
    return f"{formatted}%"


def _dimensioned_ga4_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.source_connector == GA4_CONNECTOR_ID
        and {"landing_page", "source_medium", "campaign_name"}.issubset(fact.dimensions)
    ]


def _landing_group_count(facts: Iterable[MetricFact]) -> int:
    return len(
        {
            (
                fact.dimensions.get("landing_page", ""),
                fact.dimensions.get("source_medium", ""),
                fact.dimensions.get("campaign_name", ""),
            )
            for fact in _dimensioned_ga4_facts(facts)
        }
    )


def _tactical_landing_group_count(items: Iterable[TacticalQueueItem]) -> int:
    return len(
        {
            (
                item.dimensions.get("landing_page", ""),
                item.dimensions.get("source_medium", ""),
                item.dimensions.get("campaign_name", ""),
            )
            for item in items
            if item.dimensions.get("landing_page")
        }
    )


def _tactical_metric_facts(items: Iterable[TacticalQueueItem]) -> list[MetricFact]:
    facts: list[MetricFact] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        for fact in item.metric_facts:
            key = (fact.source_connector, fact.name, fact.evidence_id)
            if key in seen:
                continue
            seen.add(key)
            facts.append(fact)
    return facts


def _unique_tactical_items(items: Iterable[TacticalQueueItem]) -> list[TacticalQueueItem]:
    seen: set[str] = set()
    result: list[TacticalQueueItem] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


def _low_engagement_count(tactical_items: Iterable[TacticalQueueItem]) -> int:
    return sum(1 for item in tactical_items if item.intent == "landing_page_quality")


def _wordpress_match_count(tactical_items: Iterable[TacticalQueueItem]) -> int:
    return sum(1 for item in tactical_items if item.dimensions.get("wordpress_match") == "found")


def _ga4_blocker_reason(latest_refresh: ConnectorRefreshRun | None) -> str:
    if latest_refresh is None:
        return "Brak GA4 refresh run."
    if latest_refresh.status == ConnectorRefreshStatus.blocked:
        return f"GA4 refresh blocked: {', '.join(latest_refresh.errors) or latest_refresh.summary}"
    if latest_refresh.status == ConnectorRefreshStatus.failed:
        return f"GA4 refresh failed: {', '.join(latest_refresh.errors) or latest_refresh.summary}"
    if not latest_refresh.metrics_persisted:
        return "Ostatni GA4 refresh nie utrwalił metryk."
    if not latest_refresh.vendor_data_collected:
        return "Ostatni GA4 refresh nie zebrał vendor data."
    return latest_refresh.summary


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh and latest_refresh.evidence_ids:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(GA4_CONNECTOR_ID)]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")[:96]
