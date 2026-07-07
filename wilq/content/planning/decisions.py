from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse, unquote

from wilq.content.canonical.urls import content_decision_url_semantics
from wilq.content.inventory.gates import content_inventory_gate_status
from wilq.schemas import (
    ActionRisk,
    ContentDecisionItem,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)

ContentDecisionType = Literal[
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
    "review_ahrefs_gap_records",
]
CONTENT_REFRESH_ACTION_IDS = {
    "act_prepare_content_refresh_queue",
    "act_prepare_wordpress_draft_handoff",
}


@dataclass(frozen=True)
class ContentDecisionMetrics:
    primary_query: str | None
    total_clicks: int | None
    total_impressions: int | None
    aggregate_ctr: float | None
    best_average_position: float | None


def gsc_content_decisions(
    items: list[TacticalQueueItem],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
) -> list[ContentDecisionItem]:
    page_groups: dict[str, list[TacticalQueueItem]] = {}
    for item in _unique_tactical_items(items):
        if item.domain != OpportunityDomain.gsc_seo:
            continue
        page = item.dimensions.get("page")
        if page:
            page_groups.setdefault(page, []).append(item)

    decisions: list[ContentDecisionItem] = []
    for page, page_items in page_groups.items():
        first = page_items[0]
        wordpress_match = first.dimensions.get("wordpress_match", "missing")
        query_count = int_dimension(first, "gsc_page_query_count", len(page_items))
        wordpress_title_or_h1 = first.dimensions.get("wordpress_title_or_h1") or None
        wordpress_section_headings = wordpress_section_headings_from_dimensions(
            first.dimensions.get("wordpress_section_headings_json")
        )
        wordpress_section_count = optional_int_text(
            first.dimensions.get("wordpress_section_heading_count")
        )
        wordpress_content_summary = first.dimensions.get("wordpress_content_summary") or None
        wordpress_content_word_count = optional_int_text(
            first.dimensions.get("wordpress_content_word_count")
        )
        wordpress_content_inventory_status: Literal["available", "missing"] = (
            "available" if wordpress_content_summary else "missing"
        )
        wordpress_content_inventory_note = (
            None
            if wordpress_content_summary
            else (
                "WordPress REST nie wystawia bezpiecznego skrótu aktualnej treści "
                "dla tej strony. WILQ widzi publiczne H2/H3, ale pełny body/ACF "
                "wymaga osobnego read-only kontraktu albo exportu."
            )
        )
        wordpress_block_names = json_string_list_from_dimensions(
            first.dimensions.get("wordpress_block_names_json"),
            limit=16,
        )
        wordpress_block_count = optional_int_text(
            first.dimensions.get("wordpress_block_name_count")
        )
        wordpress_section_inventory_status: Literal["available", "missing"] = (
            "available" if wordpress_section_headings else "missing"
        )
        wordpress_acf_section_inventory_note = (
            "Brakuje read-only kontraktu aktualnych wierszy ACF/flexible content "
            "dla tej strony. WILQ widzi publiczne nagłówki HTML, ale nie udaje "
            "pełnego układu edytora WordPress."
        )
        queries = _unique(
            item.dimensions.get("query") for item in page_items if item.dimensions.get("query")
        )
        metric_facts = _unique_metric_facts(
            fact for item in page_items for fact in item.metric_facts
        )
        wordpress_content_url = first.dimensions.get("wordpress_content_url")
        metrics = content_decision_metrics(metric_facts, queries)
        decision_type: ContentDecisionType
        if wordpress_match == "found":
            decision_type = "refresh_or_merge"
            title = content_decision_title(decision_type, page, query_count, metrics)
            summary = content_decision_summary(
                decision_type,
                metrics,
                wordpress_match,
                wordpress_title_or_h1=wordpress_title_or_h1,
                wordpress_section_headings=wordpress_section_headings,
            )
            section_step = (
                "Porównaj widoczne sekcje WordPress z zapytaniami GSC, sprawdź CTA "
                "i dopiero potem zdecyduj: odświeżyć, scalić albo zostawić."
                if wordpress_section_headings
                else "Otwórz aktualny adres WordPress i sprawdź istniejące H1, sekcje "
                "ACF/flexible content oraz CTA."
            )
            next_step = (
                f"{section_step} Nie przygotowuj rewrite ani scalenia z samego "
                "zapytania GSC."
            )
            rationale = (
                "Spis treści WordPress potwierdza istniejący URL, więc WILQ kieruje "
                "to do przeglądu konkretnej strony zamiast tworzenia nowej treści "
                "albo abstrakcyjnego zadania z samego query."
            )
        elif query_count > 1:
            decision_type = "merge_create_after_inventory_check"
            title = content_decision_title(decision_type, page, query_count, metrics)
            summary = content_decision_summary(
                decision_type,
                metrics,
                wordpress_match,
                wordpress_title_or_h1=wordpress_title_or_h1,
                wordpress_section_headings=wordpress_section_headings,
            )
            next_step = (
                "Sprawdź publiczny URL, spis strony i duplikaty w WordPress. Dopiero potem "
                "wybierz scalenie, nową treść albo przywrócenie."
            )
            rationale = (
                "Wiele zapytań prowadzi do jednego URL, ale spis treści nie potwierdza "
                "strony, więc nowy plan treści bez kontroli grozi duplikacją."
            )
        else:
            decision_type = "inventory_check_before_create"
            title = content_decision_title(decision_type, page, query_count, metrics)
            summary = content_decision_summary(
                decision_type,
                metrics,
                wordpress_match,
                wordpress_title_or_h1=wordpress_title_or_h1,
                wordpress_section_headings=wordpress_section_headings,
            )
            next_step = (
                "Najpierw potwierdź, czy URL istnieje w WordPress lub sitemap. "
                "Jeśli nie istnieje, przygotuj plan treści dopiero po kontroli duplikatów."
            )
            rationale = (
                "GSC pokazuje popyt, ale spis treści WordPress nie potwierdza URL, "
                "więc WILQ blokuje automatyczne tworzenie nowej treści."
            )
        url_semantics = content_decision_url_semantics(
            source_url=page,
            wordpress_content_url=wordpress_content_url,
        )
        gate_status = content_inventory_gate_status(
            decision_type=decision_type,
            wordpress_match=wordpress_match,
        )
        decisions.append(
            ContentDecisionItem(
                id=f"content_decision_{slug(page)}",
                decision_type=decision_type,
                status=content_decision_status(decision_type),
                title=title,
                summary=summary,
                priority=content_decision_priority(
                    decision_type,
                    metrics,
                    query_count,
                ),
                metric_tiles=content_decision_metric_tiles(
                    decision_type,
                    metrics,
                    query_count,
                    wordpress_match,
                    wordpress_section_count=wordpress_section_count,
                    wordpress_section_inventory_status=wordpress_section_inventory_status,
                ),
                page=page,
                normalized_page_path=first.dimensions.get("wordpress_requested_path"),
                queries=queries,
                query_count=query_count,
                primary_query=metrics.primary_query,
                total_clicks=metrics.total_clicks,
                total_impressions=metrics.total_impressions,
                aggregate_ctr=metrics.aggregate_ctr,
                best_average_position=metrics.best_average_position,
                wordpress_match=wordpress_match,
                wordpress_match_confidence=first.dimensions.get("wordpress_match_confidence"),
                wordpress_title_or_h1=wordpress_title_or_h1,
                wordpress_inventory_source=first.dimensions.get("wordpress_inventory_source"),
                wordpress_modified_gmt=first.dimensions.get("wordpress_modified_gmt"),
                wordpress_section_headings=wordpress_section_headings,
                wordpress_section_count=wordpress_section_count,
                wordpress_section_inventory_status=wordpress_section_inventory_status,
                wordpress_content_summary=wordpress_content_summary,
                wordpress_content_word_count=wordpress_content_word_count,
                wordpress_content_inventory_status=wordpress_content_inventory_status,
                wordpress_content_inventory_note=wordpress_content_inventory_note,
                wordpress_block_names=wordpress_block_names,
                wordpress_block_count=wordpress_block_count,
                wordpress_acf_section_inventory_status="missing",
                wordpress_acf_section_inventory_note=wordpress_acf_section_inventory_note,
                source_public_url=url_semantics["source_public_url"],
                preview_url=url_semantics["preview_url"],
                intended_final_url=url_semantics["intended_final_url"],
                final_canonical_url=url_semantics["final_canonical_url"],
                inventory_gate_status=gate_status["inventory_gate_status"],
                canonical_gate_status=gate_status["canonical_gate_status"],
                duplicate_gate_status=gate_status["duplicate_gate_status"],
                content_gate_summary=gate_status["content_gate_summary"],
                source_connectors=_unique(
                    connector for item in page_items for connector in item.source_connectors
                ),
                evidence_ids=_unique(
                    evidence_id for item in page_items for evidence_id in item.evidence_ids
                ),
                metric_facts=metric_facts[:8],
                action_ids=_unique(
                    action_id
                    for item in page_items
                    for action_id in item.action_ids
                    if action_id in CONTENT_REFRESH_ACTION_IDS
                ),
                knowledge_card_ids=list(knowledge_card_ids),
                expert_rule_ids=list(expert_rule_ids),
                blocked_claims=_unique(
                    claim for item in page_items for claim in item.blocked_claims
                ),
                rationale=rationale,
                next_step=next_step,
                risk=ActionRisk.medium if wordpress_match == "missing" else ActionRisk.low,
            )
        )
    return decisions


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
    *,
    wordpress_section_count: int | None = None,
    wordpress_section_inventory_status: Literal["available", "missing"] = "missing",
) -> dict[str, int | float | str]:
    tiles: dict[str, int | float | str] = {
        "zapytania": query_count,
        "WP": wordpress_match_tile(wordpress_match),
    }
    if decision_type == "refresh_or_merge" and wordpress_match == "found":
        tiles["sekcje WP"] = (
            wordpress_section_count
            if wordpress_section_inventory_status == "available" and wordpress_section_count
            else "brak odczytu sekcji"
        )
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
    page_label = content_page_label(page)
    topic = content_topic_label(page, metrics.primary_query)
    query_label = query_count_label(query_count)
    if decision_type == "refresh_or_merge":
        return f"{page_label}: sprawdź istniejącą treść ({query_label})"
    if decision_type == "merge_create_after_inventory_check":
        return f"{page_label}: sprawdź klaster {topic} przed tworzeniem ({query_label})"
    return f"{page_label}: sprawdź spis treści przed nową treścią ({query_label})"


def content_page_label(page: str) -> str:
    parsed = urlparse(page)
    host = parsed.netloc or ""
    path = parsed.path.rstrip("/")
    if host == "www.ekologus.pl" and path in {"", "/"}:
        return "Strona główna ekologus.pl"
    if host:
        display_path = path or "/"
        return f"Istniejący URL {unquote(display_path)}"
    cleaned = page.rstrip("/") or page
    return f"URL {unquote(cleaned)}"


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
    *,
    wordpress_title_or_h1: str | None = None,
    wordpress_section_headings: list[str] | None = None,
) -> str:
    metric_sentence = content_metric_sentence(metrics)
    if decision_type == "refresh_or_merge":
        section_headings = wordpress_section_headings or []
        title_sentence = (
            f' Aktualny tytuł/H1 w WordPress: "{wordpress_title_or_h1}".'
            if wordpress_title_or_h1
            else " Aktualny tytuł/H1 nie jest jeszcze dostępny w tym widoku."
        )
        section_sentence = (
            f" Widoczne sekcje: {', '.join(section_headings[:3])}."
            if section_headings
            else " Brakuje odczytu aktualnych sekcji, więc trzeba je sprawdzić przed szkicem."
        )
        return (
            f"{metric_sentence} WordPress potwierdza istniejącą stronę, więc "
            "najpierw sprawdź aktualny URL, obecne sekcje i CTA."
            f"{title_sentence}{section_sentence} To nie jest nowy artykuł ani zadanie budowane "
            "z samego zapytania."
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


def wordpress_section_headings_from_dimensions(value: str | None) -> list[str]:
    return json_string_list_from_dimensions(value, limit=12)


def json_string_list_from_dimensions(value: str | None, *, limit: int) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    headings: list[str] = []
    for item in parsed:
        if isinstance(item, str):
            heading = item.strip()
            if heading:
                headings.append(heading)
    return headings[:limit]


def optional_int_text(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


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


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _unique_tactical_items(items: Iterable[TacticalQueueItem]) -> list[TacticalQueueItem]:
    unique_items: dict[str, TacticalQueueItem] = {}
    for item in items:
        unique_items.setdefault(item.id, item)
    return list(unique_items.values())


def _unique_metric_facts(values: Iterable[MetricFact]) -> list[MetricFact]:
    unique_facts: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in values:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted((str(key), str(value)) for key, value in fact.dimensions.items())),
        )
        unique_facts.setdefault(key, fact)
    return list(unique_facts.values())
