"""Decomposed tactical_queue labels implementation."""

from __future__ import annotations

from urllib.parse import urlparse

from wilq.briefing.merchant_labels import MERCHANT_ATTRIBUTE_LABELS, MERCHANT_ISSUE_LABELS
from wilq.briefing.tactical_queue.shared import (
    TacticalIntent,
    WordPressMatch,
    WordPressMatchConfidence,
)
from wilq.schemas import OpportunityDomain, TacticalQueueItem


def _compact_tactical_title(item: TacticalQueueItem, group_size: int) -> str:
    if item.domain == OpportunityDomain.gsc_seo and item.dimensions.get("page"):
        action = "odśwież" if item.intent == "content_refresh" else "zweryfikuj treść"
        return (
            f"SEO: {action} {_short_path(item.dimensions['page'])} "
            f"({group_size} {_polish_query_label(group_size)})"
        )
    if item.domain == OpportunityDomain.ga4:
        landing_label = item.dimensions.get("landing_page", "strona wejścia")
        source_label = item.dimensions.get("source_medium", "źródło ruchu")
        return f"GA4: sprawdź {landing_label}; źródło ruchu: {source_label}"
    if item.domain == OpportunityDomain.merchant:
        issue_type = item.dimensions.get("issue_type", "problem pliku produktowego")
        return (
            "Merchant: sprawdź "
            f"{_merchant_dimension_label(issue_type)}; "
            f"{_merchant_dimension_label(item.dimensions.get('affected_attribute', 'atrybut'))}"
        )
    return item.title


def _compact_tactical_diagnosis(
    item: TacticalQueueItem,
    queries: list[str],
    clicks: float | int | None,
    impressions: float | int | None,
    group_size: int,
) -> str:
    if item.domain == OpportunityDomain.gsc_seo:
        query_text = f" Zapytania: {', '.join(queries[:4])}." if queries else ""
        metrics = ", ".join(
            metric
            for metric in (
                None if clicks is None else f"kliknięcia: {_format_compact_number(clicks)}",
                None
                if impressions is None
                else f"wyświetlenia: {_format_compact_number(impressions)}",
            )
            if metric is not None
        )
        metrics_text = f" Suma widocznych metryk: {metrics}." if metrics else ""
        return (
            f"{_polish_related_query_sentence(group_size)} do tej samej strony."
            f"{query_text}{metrics_text}"
        )
    return item.diagnosis


def _short_path(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc if parsed.path in {"", "/"} else parsed.path
    return value


def _format_compact_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return str(int(value)) if value.is_integer() else f"{value:.2f}"


def _polish_query_label(count: int) -> str:
    if count == 1:
        return "zapytanie"
    if 2 <= count <= 4:
        return "zapytania"
    return "zapytań"


def _polish_related_query_sentence(count: int) -> str:
    if count == 1:
        return "1 powiązane zapytanie prowadzi"
    if 2 <= count <= 4:
        return f"{count} powiązane zapytania prowadzą"
    return f"{count} powiązanych zapytań prowadzi"


def _priority_label(priority: int) -> str:
    if priority <= 15:
        return "najpierw"
    if priority <= 25:
        return "wysoki priorytet"
    return "do sprawdzenia"


def _tactical_domain_label(domain: OpportunityDomain) -> str:
    labels = {
        OpportunityDomain.gsc_seo: "Treści i GSC",
        OpportunityDomain.ga4: "GA4",
        OpportunityDomain.merchant: "Merchant",
        OpportunityDomain.content: "Treści",
    }
    return labels.get(domain, domain.value)


def _tactical_intent_label(intent: TacticalIntent) -> str:
    labels: dict[TacticalIntent, str] = {
        "content_refresh": "odświeżenie treści",
        "content_create": "nowa treść",
        "content_merge": "scalenie treści",
        "content_block": "blokada treści",
        "landing_page_quality": "jakość strony wejścia",
        "tracking_gap": "problem pomiaru",
        "merchant_feed_triage": "kolejność oceny pliku produktowego",
        "traffic_quality_review": "jakość ruchu",
    }
    return labels[intent]


def _merchant_dimension_label(value: str) -> str:
    return (
        MERCHANT_ISSUE_LABELS.get(value)
        or MERCHANT_ATTRIBUTE_LABELS.get(value)
        or "wymiar Merchant do sprawdzenia"
    )


def _gsc_diagnosis(
    query: str,
    page: str,
    clicks: float | int | None,
    impressions: float | int | None,
    ctr: float | int | None,
    position: float | int | None,
    *,
    wordpress_match: WordPressMatch,
) -> str:
    wordpress_note = _wordpress_match_note(wordpress_match)
    return (
        f"Zapytanie `{query}` prowadzi do `{page}`. Metryki GSC: "
        f"kliknięcia: {_metric_or_missing(clicks)}, "
        f"wyświetlenia: {_metric_or_missing(impressions)}, "
        f"CTR: {_metric_or_missing(ctr)}, "
        f"średnia pozycja: {_metric_or_missing(position)}. "
        f"{wordpress_note}"
    )


def _ga4_diagnosis(
    landing_page: str,
    source_medium: str,
    campaign_name: str,
    active_users: float | int | None,
    sessions: float | int | None,
    engagement_rate: float | int | None,
    *,
    wordpress_match: WordPressMatch,
) -> str:
    wordpress_note = _wordpress_match_note(wordpress_match)
    if _has_not_set_dimension(landing_page, source_medium, campaign_name):
        return (
            "GA4 ma brakujące wymiary raportu: "
            f"landing_page=`{landing_page}`, source_medium=`{source_medium}`, "
            f"campaign_name=`{campaign_name}`. To jest problem pomiaru/atrybucji, "
            "nie zwykła taktyka strony wejścia. "
            f"active_users={_metric_or_missing(active_users)}, "
            f"sessions={_metric_or_missing(sessions)}, "
            f"engagement_rate={_metric_or_missing(engagement_rate)}. "
            f"{wordpress_note}"
        )
    return (
        f"Strona wejścia `{landing_page}` z `{source_medium}` i kampanii `{campaign_name}` ma "
        f"active_users={_metric_or_missing(active_users)}, "
        f"sessions={_metric_or_missing(sessions)}, "
        f"engagement_rate={_metric_or_missing(engagement_rate)}. {wordpress_note}"
    )


def _has_not_set_dimension(*values: str) -> bool:
    return any(value.strip().lower() == "(not set)" for value in values)


def _wordpress_match_note(wordpress_match: WordPressMatch) -> str:
    wordpress_fact = wordpress_match.fact
    if wordpress_fact is None:
        return "Spis treści WordPress nie potwierdza istniejącej strony w ostatnim odczycie."
    dimensions = wordpress_fact.dimensions
    return (
        "Spis treści WordPress potwierdza istniejący obiekt "
        f"typu {dimensions.get('content_type', 'content')}, "
        f"stan wpisu: {_wordpress_status_label(dimensions.get('status'))}, "
        f"dopasowanie: {_wordpress_match_confidence_label(wordpress_match.confidence)}."
    )


def _metric_or_missing(value: float | int | None) -> str:
    if value is None:
        return "brak w evidence"
    return str(value)


def _wordpress_status_label(status: str | None) -> str:
    if status == "indexed":
        return "zaindeksowany"
    if status:
        return status
    return "brak statusu"


def _wordpress_match_confidence_label(confidence: WordPressMatchConfidence) -> str:
    if confidence == "exact_url":
        return "dokładny URL"
    if confidence == "host_alias_sitemap":
        return "alias hosta z sitemap"
    if confidence == "path_fallback":
        return "dopasowanie ścieżki"
    return "brak dopasowania"
