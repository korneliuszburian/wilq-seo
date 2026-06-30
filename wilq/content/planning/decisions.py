from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wilq.schemas import ContentDecisionItem, MetricFact, TacticalQueueItem

ContentDecisionType = Literal[
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
    "review_ahrefs_gap_records",
]


@dataclass(frozen=True)
class ContentDecisionMetrics:
    primary_query: str | None
    total_clicks: int | None
    total_impressions: int | None
    aggregate_ctr: float | None
    best_average_position: float | None


def content_decision_metrics(
    metric_facts: list[MetricFact],
    queries: list[str],
) -> ContentDecisionMetrics:
    click_values = [
        numeric_value
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.name == "clicks"
        and (numeric_value := numeric_metric_value(fact)) is not None
    ]
    impression_values = [
        numeric_value
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.name == "impressions"
        and (numeric_value := numeric_metric_value(fact)) is not None
    ]
    position_values = [
        numeric_value
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.name == "average_position"
        and (numeric_value := numeric_metric_value(fact)) is not None
    ]
    total_clicks = int(sum(click_values)) if click_values else None
    total_impressions = int(sum(impression_values)) if impression_values else None
    return ContentDecisionMetrics(
        primary_query=primary_query(metric_facts, queries),
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        aggregate_ctr=(
            total_clicks / total_impressions
            if total_clicks is not None and total_impressions
            else None
        ),
        best_average_position=min(position_values) if position_values else None,
    )


def primary_query(metric_facts: list[MetricFact], queries: list[str]) -> str | None:
    query_scores: dict[str, tuple[float, float]] = {}
    for fact in metric_facts:
        if fact.source_connector != "google_search_console":
            continue
        query = fact.dimensions.get("query")
        value = numeric_metric_value(fact)
        if not query or value is None:
            continue
        impressions, clicks = query_scores.get(query, (0.0, 0.0))
        if fact.name == "impressions":
            impressions += value
        elif fact.name == "clicks":
            clicks += value
        query_scores[query] = (impressions, clicks)
    if query_scores:
        return max(query_scores.items(), key=lambda item: (item[1][0], item[1][1]))[0]
    return queries[0] if queries else None


def content_decision_status(
    decision_type: ContentDecisionType,
) -> Literal["ready", "blocked"]:
    if decision_type in {"inventory_check_before_create", "block_as_tracking_not_content"}:
        return "blocked"
    return "ready"


def content_decision_priority(
    decision_type: ContentDecisionType,
    metrics: ContentDecisionMetrics,
    query_count: int,
) -> int:
    base_priority = {
        "refresh_or_merge": 20,
        "merge_create_after_inventory_check": 24,
        "inventory_check_before_create": 28,
        "block_as_tracking_not_content": 12,
    }[decision_type]
    impression_score = metrics.total_impressions or 0
    if impression_score >= 1000:
        evidence_bonus = 0
    elif impression_score >= 500:
        evidence_bonus = 2
    elif impression_score >= 100:
        evidence_bonus = 4
    else:
        evidence_bonus = 7
    query_bonus = min(query_count, 5)
    return max(1, base_priority + evidence_bonus - query_bonus)


def content_decision_metric_tiles(
    decision_type: ContentDecisionType,
    metrics: ContentDecisionMetrics,
    query_count: int,
    wordpress_match: str,
) -> dict[str, int | float | str]:
    tiles: dict[str, int | float | str] = {
        "zapytania": query_count,
        "WP": wordpress_match_tile(wordpress_match),
    }
    if metrics.total_impressions is not None:
        tiles["wyświetlenia"] = metrics.total_impressions
    if metrics.total_clicks is not None:
        tiles["kliknięcia"] = metrics.total_clicks
    if metrics.aggregate_ctr is not None:
        tiles["CTR"] = format_percent(metrics.aggregate_ctr)
    if metrics.best_average_position is not None:
        tiles["pozycja"] = round(metrics.best_average_position, 2)
    if decision_type != "refresh_or_merge":
        tiles["tryb"] = content_decision_mode_tile(decision_type)
    return tiles


def wordpress_match_tile(wordpress_match: str) -> str:
    if wordpress_match == "found":
        return "znaleziono"
    if wordpress_match == "missing":
        return "niepotwierdzono w WordPress"
    return "niepewne"


def content_decision_mode_tile(decision_type: ContentDecisionType) -> str:
    if decision_type == "merge_create_after_inventory_check":
        return "sprawdź scalenie albo nową treść"
    if decision_type == "inventory_check_before_create":
        return "blokada nowej treści"
    if decision_type == "block_as_tracking_not_content":
        return "GA4 tracking"
    return "odświeżenie albo scalenie"


def numeric_metric_value(fact: MetricFact) -> float | None:
    if isinstance(fact.value, int | float):
        return float(fact.value)
    return None


def content_decision_title(
    decision_type: ContentDecisionType,
    page: str,
    query_count: int,
    metrics: ContentDecisionMetrics,
) -> str:
    topic = content_topic_label(page, metrics.primary_query)
    query_label = query_count_label(query_count)
    if decision_type == "refresh_or_merge":
        return f"SEO: odśwież lub scal {topic} ({query_label})"
    if decision_type == "merge_create_after_inventory_check":
        return f"SEO: sprawdź klaster {topic} przed tworzeniem ({query_label})"
    return f"SEO: sprawdź spis treści dla {topic} ({query_label})"


def content_topic_label(page: str, primary_query_value: str | None) -> str:
    if primary_query_value:
        return f'"{primary_query_value}"'
    if page.rstrip("/") == "https://www.ekologus.pl":
        return "stronę główną"
    return page.rstrip("/").rsplit("/", maxsplit=1)[-1].replace("-", " ")


def content_decision_summary(
    decision_type: ContentDecisionType,
    metrics: ContentDecisionMetrics,
    wordpress_match: str,
) -> str:
    metric_sentence = content_metric_sentence(metrics)
    if decision_type == "refresh_or_merge":
        return (
            f"{metric_sentence} WordPress potwierdza istniejącą stronę, więc "
            "to jest decyzja odświeżenia albo scalenia, nie nowy artykuł."
        )
    if decision_type == "merge_create_after_inventory_check":
        return (
            f"{metric_sentence} WordPress nie potwierdza strony dla tego klastra, "
            "więc najpierw trzeba sprawdzić publiczny URL, spis treści i ryzyko duplikatu."
        )
    match_label = "nie potwierdza" if wordpress_match == "missing" else "nie daje pewności"
    return (
        f"{metric_sentence} WordPress {match_label} URL, więc WILQ blokuje "
        "plan nowej treści do czasu kontroli spisu."
    )


def content_metric_sentence(metrics: ContentDecisionMetrics) -> str:
    parts: list[str] = []
    if metrics.total_impressions is not None:
        impression_word = polish_count_word(
            metrics.total_impressions,
            "wyświetlenie",
            "wyświetlenia",
            "wyświetleń",
        )
        parts.append(f"{metrics.total_impressions} {impression_word}")
    if metrics.total_clicks is not None:
        click_word = polish_count_word(
            metrics.total_clicks,
            "kliknięcie",
            "kliknięcia",
            "kliknięć",
        )
        parts.append(f"{metrics.total_clicks} {click_word}")
    if metrics.aggregate_ctr is not None:
        parts.append(f"CTR {format_percent(metrics.aggregate_ctr)}")
    if metrics.best_average_position is not None:
        parts.append(f"najlepsza średnia pozycja {format_decimal(metrics.best_average_position)}")
    prefix = "GSC: " + ", ".join(parts) if parts else "GSC ma evidence dla tej strony."
    if metrics.primary_query:
        return f'{prefix}; główne zapytanie: "{metrics.primary_query}".'
    return prefix


def content_decision_sort_key(decision: ContentDecisionItem) -> tuple[int, int, int, int, str]:
    status_rank = 1 if decision.status == "blocked" else 0
    return (
        status_rank,
        decision.priority,
        -(decision.total_impressions or 0),
        -decision.query_count,
        decision.id,
    )


def query_count_label(query_count: int) -> str:
    if query_count == 1:
        return "1 zapytanie"
    return f"{query_count} zapytań"


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def format_decimal(value: float) -> str:
    return f"{value:.2f}"


def polish_count_word(value: int, one: str, few: str, many: str) -> str:
    absolute = abs(value)
    if absolute == 1:
        return one
    if 2 <= absolute % 10 <= 4 and not 12 <= absolute % 100 <= 14:
        return few
    return many


def int_dimension(item: TacticalQueueItem, key: str, fallback: int) -> int:
    try:
        return int(item.dimensions.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower()).strip(
        "_"
    )[:80]
