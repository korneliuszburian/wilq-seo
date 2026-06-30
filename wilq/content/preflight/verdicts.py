from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.content.canonical.urls import content_decision_final_canonical_url
from wilq.schemas import ContentDecisionItem

ContentPreflightMode = Literal["preserve", "refresh", "merge", "create", "block"]
ContentPreflightStatus = Literal["allowed", "review_required", "blocked"]


def content_preflight_mode(decision: ContentDecisionItem) -> ContentPreflightMode:
    if decision.decision_type == "refresh_or_merge":
        return "refresh"
    if decision.decision_type == "merge_create_after_inventory_check":
        return "merge"
    if decision.decision_type == "inventory_check_before_create":
        return "block"
    return "block"


def content_preflight_status(
    decision: ContentDecisionItem,
    recommended_mode: ContentPreflightMode,
) -> ContentPreflightStatus:
    if decision.status == "blocked" or recommended_mode == "block":
        return "blocked"
    return "review_required"


def content_preflight_similar_urls(decision: ContentDecisionItem) -> list[str]:
    urls: list[str | None] = []
    if decision.wordpress_match == "found":
        urls.append(content_decision_final_canonical_url(decision) or decision.source_public_url)
    urls.extend(url for row in decision.ahrefs_candidate_rows for url in row.wordpress_overlap_urls)
    return _unique(url for url in urls if url)


def content_preflight_query_overlap(decision: ContentDecisionItem) -> str:
    if decision.query_count <= 0:
        return "Brak potwierdzonych wspólnych zapytań."
    primary = f"; główne zapytanie: {decision.primary_query}" if decision.primary_query else ""
    return f"{decision.query_count} zapytań z GSC{primary}."


def content_preflight_next_step(
    decision: ContentDecisionItem,
    recommended_mode: ContentPreflightMode,
    status: ContentPreflightStatus,
) -> str:
    if status == "blocked":
        return decision.next_step
    if recommended_mode == "refresh":
        return "Przygotuj plan odświeżenia dopiero po sprawdzeniu ryzykownych obietnic."
    if recommended_mode == "merge":
        return "Najpierw sprawdź duplikaty i zdecyduj, które sekcje scalić."
    return decision.next_step


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
