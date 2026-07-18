from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from time import monotonic
from typing import Literal
from urllib.parse import urlparse

from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.merchant_labels import (
    MERCHANT_ATTRIBUTE_LABELS,
    MERCHANT_ISSUE_LABELS,
)
from wilq.briefing.metric_fact_identity import latest_metric_facts_by_identity
from wilq.briefing.tactical_ahrefs import build_ahrefs_gap_items
from wilq.briefing.tactical_merchant import build_merchant_feed_items
from wilq.content.planning.ahrefs_overlap import AhrefsCrossSourceOverlap
from wilq.schemas import (
    ActionRisk,
    MetricFact,
    OpportunityDomain,
    TacticalQueueGroup,
    TacticalQueueItem,
    TacticalQueueResponse,
)
from wilq.storage.metric_store import metric_store

TACTICAL_QUEUE_LIMIT = 24
TACTICAL_QUEUE_DOMAIN_FLOOR = 4
TACTICAL_QUEUE_SOURCE_CONNECTORS = (
    "ahrefs",
    "google_search_console",
    "google_analytics_4",
    "google_merchant_center",
    "wordpress_ekologus",
    "wordpress_sklep",
)
TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT = 300
GSC_QUERY_PAGE_FACT_LIMIT = 1200
GA4_LANDING_FACT_LIMIT = 2000
WORDPRESS_INVENTORY_FACT_LIMIT = 5000
TacticalIntent = Literal[
    "content_refresh",
    "content_create",
    "content_merge",
    "content_block",
    "landing_page_quality",
    "tracking_gap",
    "merchant_feed_triage",
    "traffic_quality_review",
]
WordPressMatchConfidence = Literal[
    "exact_url",
    "host_alias_sitemap",
    "path_fallback",
    "missing",
]
WORDPRESS_CANONICAL_HOST_ALIASES = {
    "www.ekologus.pl": {"ekologus.pl"},
    "ekologus.pl": {"www.ekologus.pl"},
}
WORDPRESS_PUBLIC_CONTENT_HOSTS = {
    "ekologus.pl",
    "www.ekologus.pl",
    "sklep.ekologus.pl",
}
AHREFS_GAP_FACT_NAMES = {
    "ahrefs_competitor_page_count",
    "ahrefs_content_gap_count",
    "ahrefs_backlink_gap_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
}
AHREFS_GAP_TYPE_LABELS = {
    "competitor_page": "strona konkurencji",
    "content_gap": "luka treści",
    "backlink_gap": "luka linków",
    "organic_keyword_gap": "luka słów organicznych",
    "top_page_gap": "luka najlepszych stron konkurencji",
}
AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS = {
    "cuk.pl",
    "ltesty.pl",
}
AHREFS_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie samochodu",
    "samochod",
    "samochodu",
    "ubezpieczenie",
)
AHREFS_RELEVANT_COMPETITOR_DOMAINS = {
    "denios.pl",
    "dla-przemyslu.pl",
    "manutan.pl",
}
AHREFS_RELEVANT_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "zielony lad",
    "ppwr",
    "audyt",
    "beczka",
    "sorbent",
)
DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS = 30.0
_cached_tactical_queue: TacticalQueueCacheEntry | None = None


@dataclass(frozen=True)
class WordPressContentIndex:
    exact_urls: dict[str, MetricFact]
    paths: dict[str, list[MetricFact]]


@dataclass(frozen=True)
class WordPressMatch:
    fact: MetricFact | None
    confidence: WordPressMatchConfidence
    requested_url_key: str
    requested_path_key: str


@dataclass(frozen=True)
class TacticalQueueCacheEntry:
    created_at: float
    queue: TacticalQueueResponse


def build_tactical_queue(
    use_cache: bool = True,
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> TacticalQueueResponse:
    if use_cache and facts_by_connector is None:
        cached_queue = _read_tactical_queue_cache()
        if cached_queue is not None:
            return cached_queue
    queue = _build_tactical_queue(facts_by_connector=facts_by_connector)
    if use_cache and facts_by_connector is None:
        _write_tactical_queue_cache(queue)
    return queue


def clear_tactical_queue_cache() -> None:
    global _cached_tactical_queue
    _cached_tactical_queue = None


def _read_tactical_queue_cache() -> TacticalQueueResponse | None:
    cache_seconds = _cache_seconds()
    if cache_seconds <= 0:
        return None
    if _cached_tactical_queue is None:
        return None
    if monotonic() - _cached_tactical_queue.created_at > cache_seconds:
        return None
    return _cached_tactical_queue.queue


def _write_tactical_queue_cache(queue: TacticalQueueResponse) -> None:
    global _cached_tactical_queue
    if _cache_seconds() <= 0:
        return
    _cached_tactical_queue = TacticalQueueCacheEntry(created_at=monotonic(), queue=queue)


def _cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_TACTICAL_QUEUE_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS


def _build_tactical_queue(
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> TacticalQueueResponse:
    facts = [
        fact
        for fact in _tactical_metric_facts(facts_by_connector=facts_by_connector)
        if fact.dimensions and not _is_probe_only_fact(fact)
    ]
    action_ids_by_connector = _tactical_action_ids_by_connector()
    wordpress_index = _wordpress_content_index(facts)
    gsc_cross_check_facts = [
        fact for fact in facts if fact.source_connector == "google_search_console"
    ]
    wordpress_cross_check_facts = [
        fact for fact in facts if fact.source_connector.startswith("wordpress")
    ]
    items = [
        *build_gsc_content_tactical_items(
            facts,
            wordpress_action_ids=action_ids_by_connector.get("wordpress_ekologus", []),
        ),
        *_ga4_quality_items(facts, action_ids_by_connector, wordpress_index),
        *build_merchant_feed_items(facts=facts, action_ids=action_ids_by_connector),
        *_ahrefs_gap_items(
            facts,
            action_ids_by_connector,
            gsc_cross_check_facts,
            wordpress_cross_check_facts,
        ),
    ]
    items = _balanced_tactical_items(items, limit=TACTICAL_QUEUE_LIMIT)
    return TacticalQueueResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        items=items,
        compact_groups=_compact_tactical_groups(items),
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=_unique(action_id for item in items for action_id in item.action_ids),
    )


def _compact_tactical_groups(items: list[TacticalQueueItem]) -> list[TacticalQueueGroup]:
    groups: dict[str, list[TacticalQueueItem]] = {}
    for item in items:
        key = _compact_tactical_group_key(item)
        groups.setdefault(key, []).append(item)
    return sorted(
        (_compact_tactical_group(group_items) for group_items in groups.values()),
        key=lambda group: (group.priority, group.id),
    )


def _compact_tactical_group_key(item: TacticalQueueItem) -> str:
    if item.domain == OpportunityDomain.gsc_seo and item.dimensions.get("page"):
        return f"{item.domain.value}:{item.intent}:{item.dimensions['page']}"
    if item.domain == OpportunityDomain.ga4:
        return (
            f"{item.domain.value}:{item.intent}:"
            f"{item.dimensions.get('landing_page', '')}:"
            f"{item.dimensions.get('source_medium', '')}"
        )
    if item.domain == OpportunityDomain.merchant:
        return (
            f"{item.domain.value}:{item.intent}:"
            f"{item.dimensions.get('issue_type', '')}:"
            f"{item.dimensions.get('affected_attribute', '')}:"
            f"{item.dimensions.get('country', '')}"
        )
    return item.id


def _compact_tactical_group(items: list[TacticalQueueItem]) -> TacticalQueueGroup:
    first = items[0]
    facts = [fact for item in items for fact in item.metric_facts]
    queries = _unique(
        query for item in items if (query := item.dimensions.get("query")) is not None
    )
    clicks = _sum_metric_facts(facts, "clicks")
    impressions = _sum_metric_facts(facts, "impressions")
    return TacticalQueueGroup(
        id=_compact_tactical_group_key(first),
        title=_compact_tactical_title(first, len(items)),
        meta=(
            f"Obszar: {_tactical_domain_label(first.domain)}. "
            f"Zadanie: {_tactical_intent_label(first.intent)}. "
            f"Priorytet: {_priority_label(first.priority)}."
        ),
        diagnosis=_compact_tactical_diagnosis(
            first,
            queries,
            clicks,
            impressions,
            len(items),
        ),
        next_step=first.next_step,
        priority=first.priority,
        risk=first.risk,
        source_connectors=_unique(
            connector for item in items for connector in item.source_connectors
        ),
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=_unique(action_id for item in items for action_id in item.action_ids),
        blocked_claims=_unique(claim for item in items for claim in item.blocked_claims),
    )


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


def _sum_metric_facts(facts: list[MetricFact], name: str) -> float | int | None:
    values = [
        float(fact.value)
        for fact in facts
        if fact.name == name and isinstance(fact.value, int | float)
    ]
    if not values:
        return None
    total = sum(values)
    return int(total) if total.is_integer() else total


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


def _tactical_metric_facts(
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> list[MetricFact]:
    if facts_by_connector is None:
        facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
            {
                connector_id: _tactical_connector_fact_limit(connector_id)
                for connector_id in TACTICAL_QUEUE_SOURCE_CONNECTORS
            }
        )
    facts: list[MetricFact] = []
    for connector_id in TACTICAL_QUEUE_SOURCE_CONNECTORS:
        facts.extend(facts_by_connector.get(connector_id, []))
    return latest_metric_facts_by_identity(facts)


def _tactical_connector_fact_limit(connector_id: str) -> int:
    if connector_id == "google_search_console":
        return GSC_QUERY_PAGE_FACT_LIMIT
    if connector_id == "google_analytics_4":
        return GA4_LANDING_FACT_LIMIT
    if connector_id.startswith("wordpress"):
        return WORDPRESS_INVENTORY_FACT_LIMIT
    return TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT


def _balanced_tactical_items(
    items: list[TacticalQueueItem],
    *,
    limit: int,
) -> list[TacticalQueueItem]:
    sorted_items = sorted(items, key=_tactical_sort_key)
    selected: list[TacticalQueueItem] = []
    for domain in _unique(item.domain.value for item in sorted_items):
        domain_items = [item for item in sorted_items if item.domain.value == domain]
        for item in domain_items[:TACTICAL_QUEUE_DOMAIN_FLOOR]:
            if item not in selected:
                selected.append(item)
    for item in sorted_items:
        if len(selected) >= limit:
            break
        if item not in selected:
            selected.append(item)
    return sorted(selected, key=_tactical_sort_key)[:limit]


def _tactical_sort_key(item: TacticalQueueItem) -> tuple[int, str]:
    return (item.priority, item.id)


def _gsc_content_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
    wordpress_index: WordPressContentIndex,
    gsc_page_counts: dict[str, int],
) -> list[TacticalQueueItem]:
    grouped = _group_facts(
        fact
        for fact in facts
        if fact.source_connector == "google_search_console"
        and {"query", "page"}.issubset(fact.dimensions)
    )
    items: list[TacticalQueueItem] = []
    for index, ((query, page), group_facts) in enumerate(grouped.items(), start=1):
        clicks = _numeric_fact(group_facts, "clicks")
        impressions = _numeric_fact(group_facts, "impressions")
        ctr = _numeric_fact(group_facts, "ctr")
        position = _numeric_fact(group_facts, "average_position")
        wordpress_match = _find_wordpress_match(wordpress_index, page)
        wordpress_fact = wordpress_match.fact
        intent = _content_intent(
            clicks,
            impressions,
            ctr,
            position,
            wordpress_fact=wordpress_fact,
            page_query_count=gsc_page_counts.get(_normalize_url_key(page), 1),
        )
        priority = _content_priority(intent, impressions, position, index)
        item_facts = [*group_facts[:6], *([wordpress_fact] if wordpress_fact else [])]
        source_connectors = ["google_search_console"]
        if wordpress_fact:
            source_connectors.append(wordpress_fact.source_connector)
        items.append(
            TacticalQueueItem(
                id=f"tq_gsc_{_stable_slug(page)}_{_stable_slug(query)}",
                title=f"GSC: {query} -> {page}",
                domain=OpportunityDomain.gsc_seo,
                intent=intent,
                priority=priority,
                risk=ActionRisk.low,
                source_connectors=source_connectors,
                evidence_ids=_unique(fact.evidence_id for fact in item_facts),
                metric_facts=item_facts,
                dimensions={
                    "query": query,
                    "page": page,
                    **_wordpress_match_dimensions(wordpress_match),
                    "gsc_page_query_count": str(gsc_page_counts.get(_normalize_url_key(page), 1)),
                },
                diagnosis=_gsc_diagnosis(
                    query,
                    page,
                    clicks,
                    impressions,
                    ctr,
                    position,
                    wordpress_match=wordpress_match,
                ),
                next_step=_content_next_step(intent),
                blocked_claims=["jakość leadów", "wzrost konwersji", "wpływ na przychód"],
                action_ids=action_ids_by_connector.get("wordpress_ekologus", []),
            )
        )
    return items


def build_gsc_content_tactical_items(
    facts: list[MetricFact],
    *,
    wordpress_action_ids: Iterable[str] = (),
) -> list[TacticalQueueItem]:
    """Build the complete GSC/page inventory before any daily-queue limit.

    Content diagnostics needs every evidenced page so its own ranking can pick
    work items. The cross-domain tactical queue applies its balancing limit
    only after this complete page set exists.
    """
    current_facts = latest_metric_facts_by_identity(facts)
    return _gsc_content_items(
        current_facts,
        {"wordpress_ekologus": list(wordpress_action_ids)},
        _wordpress_content_index(current_facts),
        _gsc_page_counts(current_facts),
    )


def _ga4_quality_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
    wordpress_index: WordPressContentIndex,
) -> list[TacticalQueueItem]:
    grouped = _group_facts(
        fact
        for fact in facts
        if fact.source_connector == "google_analytics_4"
        and {"landing_page", "source_medium", "campaign_name"}.issubset(fact.dimensions)
    )
    items: list[TacticalQueueItem] = []
    for index, ((landing_page, source_medium, campaign_name), group_facts) in enumerate(
        grouped.items(),
        start=1,
    ):
        active_users = _numeric_fact(group_facts, "active_users")
        sessions = _numeric_fact(group_facts, "sessions")
        engagement_rate = _numeric_fact(group_facts, "engagement_rate")
        has_not_set_dimension = _has_not_set_dimension(
            landing_page,
            source_medium,
            campaign_name,
        )
        wordpress_match = _find_wordpress_match(wordpress_index, landing_page)
        wordpress_fact = wordpress_match.fact
        intent: TacticalIntent
        if has_not_set_dimension:
            intent = "tracking_gap"
        elif engagement_rate is not None and engagement_rate < 0.2:
            intent = "landing_page_quality"
        else:
            intent = "traffic_quality_review"
        priority = _ga4_priority(active_users, engagement_rate, index)
        item_facts = [*group_facts[:6], *([wordpress_fact] if wordpress_fact else [])]
        source_connectors = ["google_analytics_4"]
        if wordpress_fact:
            source_connectors.append(wordpress_fact.source_connector)
        items.append(
            TacticalQueueItem(
                id=f"tq_ga4_{_stable_slug(landing_page)}_{_stable_slug(source_medium)}",
                title=(
                    f"Problem pomiaru GA4: {landing_page}; źródło ruchu: {source_medium}"
                    if has_not_set_dimension
                    else f"GA4: {landing_page}; źródło ruchu: {source_medium}"
                ),
                domain=OpportunityDomain.ga4,
                intent=intent,
                priority=priority,
                risk=ActionRisk.low,
                source_connectors=source_connectors,
                evidence_ids=_unique(fact.evidence_id for fact in item_facts),
                metric_facts=item_facts,
                dimensions={
                    "landing_page": landing_page,
                    "source_medium": source_medium,
                    "campaign_name": campaign_name,
                    **_wordpress_match_dimensions(wordpress_match),
                },
                diagnosis=_ga4_diagnosis(
                    landing_page,
                    source_medium,
                    campaign_name,
                    active_users,
                    sessions,
                    engagement_rate,
                    wordpress_match=wordpress_match,
                ),
                next_step=_ga4_next_step(has_not_set_dimension),
                blocked_claims=[
                    "współczynnik konwersji",
                    "zwrot z reklam",
                    "przychód",
                    "opłacalność",
                ],
                action_ids=action_ids_by_connector.get("google_analytics_4", []),
            )
        )
    return items


def _ahrefs_gap_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
    gsc_cross_check_facts: list[MetricFact],
    wordpress_cross_check_facts: list[MetricFact],
) -> list[TacticalQueueItem]:
    return build_ahrefs_gap_items(
        facts=facts,
        action_ids=action_ids_by_connector,
        gsc_facts=gsc_cross_check_facts,
        wordpress_facts=wordpress_cross_check_facts,
    )


def _group_ahrefs_gap_facts(facts: list[MetricFact]) -> dict[tuple[str, ...], list[MetricFact]]:
    grouped: dict[tuple[str, ...], list[MetricFact]] = {}
    for fact in facts:
        if not is_reviewable_ahrefs_gap_fact(fact):
            continue
        dimensions = fact.dimensions
        gap_type = dimensions.get("gap_type") or _ahrefs_gap_type_for_fact(fact.name)
        key = (
            gap_type,
            dimensions.get("keyword", ""),
            dimensions.get("source_url", ""),
            dimensions.get("referenced_public_url", ""),
            _normalized_domain(dimensions.get("competitor_domain", "")),
        )
        if not any(key):
            continue
        grouped.setdefault(key, []).append(fact)
    return dict(sorted(grouped.items(), key=lambda item: _ahrefs_group_sort_key(item)))


def is_ahrefs_gap_fact(fact: MetricFact) -> bool:
    return fact.source_connector == "ahrefs" and fact.name in AHREFS_GAP_FACT_NAMES


def is_reviewable_ahrefs_gap_fact(fact: MetricFact) -> bool:
    if not is_ahrefs_gap_fact(fact):
        return False
    dimensions = fact.dimensions
    if not any(
        dimensions.get(key)
        for key in (
            "gap_type",
            "keyword",
            "source_url",
            "referenced_public_url",
            "competitor_domain",
        )
    ):
        return False
    return not _is_ahrefs_off_topic(
        dimensions.get("keyword", ""),
        dimensions.get("source_url", ""),
        dimensions.get("referenced_public_url", ""),
        _normalized_domain(dimensions.get("competitor_domain", "")),
    )


def _ahrefs_group_sort_key(item: tuple[tuple[str, ...], list[MetricFact]]) -> tuple[int, str]:
    gap_type, keyword, source_url, referenced_public_url, competitor_domain = item[0]
    topic = _ahrefs_topic(keyword, source_url, referenced_public_url, competitor_domain)
    return (_ahrefs_gap_priority(gap_type, topic, competitor_domain, 0), topic)


def _ahrefs_gap_type_for_fact(name: str) -> str:
    if name == "ahrefs_competitor_page_count":
        return "competitor_page"
    if name == "ahrefs_content_gap_count":
        return "content_gap"
    if name in {"ahrefs_backlink_gap_count", "ahrefs_referring_domain_gap_count"}:
        return "backlink_gap"
    if name == "ahrefs_organic_keyword_gap_count":
        return "organic_keyword_gap"
    if name == "ahrefs_top_page_gap_count":
        return "top_page_gap"
    return "content_gap"


def _ahrefs_gap_type_label(gap_type: str) -> str:
    return AHREFS_GAP_TYPE_LABELS.get(gap_type, "rekord Ahrefs do sprawdzenia")


def _ahrefs_content_intent(gap_type: str) -> TacticalIntent:
    if gap_type == "backlink_gap":
        return "content_block"
    return "content_create"


def _ahrefs_gap_priority(
    gap_type: str,
    topic: str,
    competitor_domain: str,
    index: int,
) -> int:
    base_by_type = {
        "content_gap": 26,
        "organic_keyword_gap": 28,
        "top_page_gap": 30,
        "competitor_page": 34,
        "backlink_gap": 48,
    }
    base = base_by_type.get(gap_type, 40)
    normalized_topic = _normalize_ahrefs_text(topic)
    if any(term in normalized_topic for term in AHREFS_RELEVANT_TERMS):
        base -= 4
    if competitor_domain in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        base -= 3
    return max(1, min(base + index, 69))


def _ahrefs_topic(
    keyword: str,
    source_url: str,
    referenced_public_url: str,
    competitor_domain: str,
) -> str:
    if keyword:
        return keyword
    if referenced_public_url:
        return _short_path(referenced_public_url)
    if source_url:
        return _short_path(source_url)
    if competitor_domain:
        return competitor_domain
    return "rekord Ahrefs"


def _ahrefs_gap_diagnosis(
    gap_type: str,
    topic: str,
    source_url: str,
    referenced_public_url: str,
    competitor_domain: str,
    facts: list[MetricFact],
    confirmation: AhrefsCrossSourceOverlap,
) -> str:
    context = ", ".join(
        part
        for part in (
            f"konkurent: {competitor_domain}" if competitor_domain else None,
            f"adres źródłowy: {_short_path(source_url)}" if source_url else None,
            f"publiczny adres: {_short_path(referenced_public_url)}"
            if referenced_public_url
            else None,
        )
        if part is not None
    )
    context_text = f" Kontekst: {context}." if context else ""
    confirmation_text = _ahrefs_confirmation_text(confirmation)
    return (
        f"Ahrefs wskazuje: {_ahrefs_gap_type_label(gap_type)} dla tematu {topic}. "
        f"Fakty: {_ahrefs_fact_summary(facts)}.{context_text} "
        f"{confirmation_text} To jest sygnał do sprawdzenia contentu, "
        "nie samodzielna rekomendacja SEO."
    )


def _ahrefs_cross_check_label(
    source: str,
    confirmation: AhrefsCrossSourceOverlap,
) -> str:
    check = confirmation.gsc if source == "GSC" else confirmation.wordpress
    labels = {
        "exact": f"potwierdzone dopasowanie w {source}",
        "weak": f"słabe podobieństwo w {source} — sprawdź ręcznie",
        "missing": f"brak potwierdzonego dopasowania w {source}",
    }
    return labels[check.strength]


def _ahrefs_confirmation_text(confirmation: AhrefsCrossSourceOverlap) -> str:
    if confirmation.gsc.strength == "exact" and confirmation.wordpress.strength == "exact":
        return "GSC i WordPress potwierdzają dokładne dopasowanie tematu."
    if confirmation.gsc.strength == "exact":
        wordpress_note = (
            " WordPress ma tylko słabe podobieństwo i wymaga ręcznej oceny."
            if confirmation.wordpress.strength == "weak"
            else " WordPress wymaga sprawdzenia."
        )
        return f"GSC potwierdza dokładne dopasowanie tematu.{wordpress_note}"
    if confirmation.wordpress.strength == "exact":
        gsc_note = (
            " GSC ma tylko słabe podobieństwo i wymaga ręcznej oceny."
            if confirmation.gsc.strength == "weak"
            else " GSC wymaga sprawdzenia popytu."
        )
        return f"WordPress potwierdza dokładne dopasowanie tematu.{gsc_note}"
    if confirmation.gsc.strength == "weak" or confirmation.wordpress.strength == "weak":
        return (
            "WILQ widzi wyłącznie słabe podobieństwo w GSC lub WordPress; "
            "nie jest to potwierdzenie popytu ani istniejącej treści."
        )
    return "Brak potwierdzonego dopasowania z GSC i WordPress w bieżących dowodach."


def _ahrefs_gap_next_step(
    topic: str,
    confirmation: AhrefsCrossSourceOverlap,
) -> str:
    if confirmation.gsc.strength == "exact" and confirmation.wordpress.strength == "exact":
        return (
            f"Zweryfikuj `{topic}` na podstawie dokładnych dopasowań GSC i WordPress, potem "
            "wybierz odświeżenie, scalenie, nową treść albo blokadę. Nie traktuj Ahrefs jako "
            "samodzielnej obietnicy ruchu."
        )
    if confirmation.has_exact_match:
        return (
            f"Jedno źródło dokładnie potwierdza `{topic}`. Ręcznie sprawdź drugie źródło, "
            "potem wybierz odświeżenie, scalenie, nową treść albo blokadę."
        )
    if confirmation.gsc.strength == "weak" or confirmation.wordpress.strength == "weak":
        return (
            f"WILQ widzi tylko słabe podobieństwo dla `{topic}`. Sprawdź ręcznie GSC "
            "i spis WordPress; nie przygotowuj briefu ani decyzji o duplikacie na tej podstawie."
        )
    return (
        f"Sprawdź ręcznie `{topic}` w GSC i spisie treści WordPress, potem wybierz "
        "odświeżenie, scalenie, nową treść albo blokadę. Bez dopasowania nie twórz briefu tylko "
        "z Ahrefs."
    )


def _ahrefs_fact_summary(facts: list[MetricFact]) -> str:
    sorted_facts = sorted(facts, key=lambda item: item.name)
    return ", ".join(f"{fact.name}={fact.value}" for fact in sorted_facts)


def _is_ahrefs_off_topic(
    keyword: str,
    source_url: str,
    referenced_public_url: str,
    competitor_domain: str,
) -> bool:
    if competitor_domain in AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS:
        return True
    text = _normalize_ahrefs_text(
        " ".join((keyword, source_url, referenced_public_url, competitor_domain))
    )
    return any(term in text for term in AHREFS_OFF_TOPIC_TERMS)


def _normalize_ahrefs_text(value: str) -> str:
    replacements = str.maketrans(
        {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"}
    )
    return value.lower().translate(replacements)


def _normalized_domain(value: str) -> str:
    host = urlparse(value).netloc or value
    return host.removeprefix("www.").lower()


def _group_facts(facts: Iterable[MetricFact]) -> dict[tuple[str, ...], list[MetricFact]]:
    grouped: dict[tuple[str, ...], list[MetricFact]] = {}
    for fact in facts:
        key = _fact_group_key(fact)
        if not key:
            continue
        grouped.setdefault(key, []).append(fact)
    return grouped


def _fact_group_key(fact: MetricFact) -> tuple[str, ...] | None:
    if fact.source_connector == "google_search_console":
        return (fact.dimensions.get("query", ""), fact.dimensions.get("page", ""))
    if fact.source_connector == "google_analytics_4":
        return (
            fact.dimensions.get("landing_page", ""),
            fact.dimensions.get("source_medium", ""),
            fact.dimensions.get("campaign_name", ""),
        )
    if fact.source_connector == "google_merchant_center" and fact.name == "issue_product_count":
        return (
            fact.dimensions.get("severity", ""),
            fact.dimensions.get("resolution", "unknown_resolution"),
            fact.dimensions.get("issue_type", "unknown_issue"),
            fact.dimensions.get("country", ""),
        )
    if fact.source_connector == "google_merchant_center":
        return (
            fact.dimensions.get("country", ""),
            fact.dimensions.get("reporting_context", ""),
        )
    return None


def _numeric_fact(facts: list[MetricFact], name: str) -> float | int | None:
    fact = next((item for item in facts if item.name == name), None)
    if fact is None or not isinstance(fact.value, int | float):
        return None
    return fact.value


def _dimension_value(facts: list[MetricFact], name: str) -> str | None:
    for fact in facts:
        value = fact.dimensions.get(name)
        if value:
            return value
    return None


def _wordpress_content_index(facts: list[MetricFact]) -> WordPressContentIndex:
    exact_urls: dict[str, MetricFact] = {}
    paths: dict[str, list[MetricFact]] = {}
    for fact in facts:
        if not fact.source_connector.startswith("wordpress"):
            continue
        if fact.name != "content_object_seen":
            continue
        content_url = fact.dimensions.get("content_url")
        if not content_url:
            continue
        _set_wordpress_index(exact_urls, _normalize_url_key(content_url), fact)
        path_key = _normalize_path_key(content_url)
        paths.setdefault(path_key, []).append(fact)
    return WordPressContentIndex(exact_urls=exact_urls, paths=paths)


def _find_wordpress_match(index: WordPressContentIndex, page_or_path: str) -> WordPressMatch:
    requested_url_key = _normalize_url_key(page_or_path)
    path_key = _normalize_path_key(page_or_path)
    full_match = index.exact_urls.get(requested_url_key)
    if full_match:
        return WordPressMatch(
            fact=full_match,
            confidence="exact_url",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    requested_host = _url_host(page_or_path)
    path_candidates = [
        candidate
        for candidate in index.paths.get(path_key, [])
        if _wordpress_path_candidate_allowed_for_request(requested_host, candidate)
    ]
    if path_key == "/" and not _url_host(page_or_path):
        path_match = _preferred_wordpress_path_match(path_candidates)
        if path_match:
            return WordPressMatch(
                fact=path_match,
                confidence="path_fallback",
                requested_url_key=requested_url_key,
                requested_path_key=path_key,
            )
        return WordPressMatch(
            fact=None,
            confidence="missing",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    alias_match = _host_alias_sitemap_match(page_or_path, path_candidates)
    if alias_match:
        return WordPressMatch(
            fact=alias_match,
            confidence="host_alias_sitemap",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    path_match = _preferred_wordpress_path_match(path_candidates)
    if path_match:
        return WordPressMatch(
            fact=path_match,
            confidence="path_fallback",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    return WordPressMatch(
        fact=None,
        confidence="missing",
        requested_url_key=requested_url_key,
        requested_path_key=path_key,
    )


def _set_wordpress_index(
    index: dict[str, MetricFact],
    key: str,
    fact: MetricFact,
) -> None:
    current = index.get(key)
    if current is None or _wordpress_index_fact_score(fact) > _wordpress_index_fact_score(current):
        index[key] = fact


def _preferred_wordpress_path_match(candidates: list[MetricFact]) -> MetricFact | None:
    return max(candidates, key=_wordpress_path_match_score, default=None)


def _wordpress_path_candidate_allowed_for_request(
    requested_host: str | None,
    fact: MetricFact,
) -> bool:
    if not requested_host:
        return True
    content_host = _url_host(fact.dimensions.get("content_url", ""))
    return not (content_host and content_host not in WORDPRESS_PUBLIC_CONTENT_HOSTS)


def _wordpress_path_match_score(fact: MetricFact) -> tuple[int, int, int, int, int, str, str]:
    return _wordpress_index_fact_score(fact)


def _wordpress_index_fact_score(fact: MetricFact) -> tuple[int, int, int, int, int, str, str]:
    dimensions = fact.dimensions
    inventory_source = dimensions.get("inventory_source")
    host = _url_host(dimensions.get("content_url", ""))
    collected_at = fact.collected_at.isoformat() if fact.collected_at is not None else ""
    return (
        1 if fact.source_connector == "wordpress_ekologus" else 0,
        1 if inventory_source in {"public_sitemap", "sitemap"} else 0,
        1 if host in {"www.ekologus.pl", "ekologus.pl"} else 0,
        1 if dimensions.get("title_or_h1") else 0,
        1 if dimensions.get("canonical_url") else 0,
        collected_at,
        fact.evidence_id,
    )


def _host_alias_sitemap_match(
    requested_url_or_path: str,
    candidates: list[MetricFact],
) -> MetricFact | None:
    requested_host = _url_host(requested_url_or_path)
    if not requested_host:
        return None
    for fact in candidates:
        dimensions = fact.dimensions
        if dimensions.get("inventory_source") not in {"sitemap", "public_sitemap"}:
            continue
        content_url = dimensions.get("content_url", "")
        content_host = _url_host(content_url)
        if _is_allowed_wordpress_host_alias(requested_host, content_host):
            return fact
    return None


def _is_allowed_wordpress_host_alias(requested_host: str, content_host: str) -> bool:
    if not requested_host or not content_host:
        return False
    normalized_requested = requested_host.lower()
    normalized_content = content_host.lower()
    return normalized_content in WORDPRESS_CANONICAL_HOST_ALIASES.get(
        normalized_requested,
        set(),
    )


def _gsc_page_counts(facts: list[MetricFact]) -> dict[str, int]:
    queries_by_page: dict[str, set[str]] = {}
    for fact in facts:
        if fact.source_connector != "google_search_console":
            continue
        page = fact.dimensions.get("page")
        query = fact.dimensions.get("query")
        if not page or not query:
            continue
        queries_by_page.setdefault(_normalize_url_key(page), set()).add(query)
    return {page: len(queries) for page, queries in queries_by_page.items()}


def _content_intent(
    clicks: float | int | None,
    impressions: float | int | None,
    ctr: float | int | None,
    position: float | int | None,
    *,
    wordpress_fact: MetricFact | None,
    page_query_count: int,
) -> TacticalIntent:
    if wordpress_fact is None:
        return "content_create"
    if page_query_count >= 3:
        return "content_merge"
    if (
        impressions
        and impressions >= 100
        and (not ctr or ctr < 0.03)
        and position
        and position <= 10
    ):
        return "content_refresh"
    if impressions and impressions >= 50 and position and position > 8:
        return "content_create"
    if clicks == 0 and impressions and impressions < 20:
        return "content_block"
    return "content_refresh"


def _content_priority(
    intent: str,
    impressions: float | int | None,
    position: float | int | None,
    index: int,
) -> int:
    base = 20 if intent == "content_refresh" else 28
    if impressions and impressions >= 100:
        base -= 5
    if position and position <= 3:
        base -= 3
    return max(1, min(base + index, 59))


def _ga4_priority(
    active_users: float | int | None,
    engagement_rate: float | int | None,
    index: int,
) -> int:
    base = 35
    if active_users and active_users >= 50:
        base -= 5
    if engagement_rate is not None and engagement_rate < 0.2:
        base -= 8
    return max(1, min(base + index, 69))


def _merchant_issue_priority(
    severity: str,
    product_count: float | int | None,
    index: int,
) -> int:
    base = 18 if severity == "DISAPPROVED" else 34
    if product_count and product_count >= 10:
        base -= 4
    return max(1, min(base + index, 59))


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


def _ga4_next_step(has_not_set_dimension: bool) -> str:
    if has_not_set_dimension:
        return (
            "Napraw pomiar GA4: sprawdź stronę wejścia, źródło i medium ruchu, "
            "UTM-y i konfigurację raportu. Nie traktuj tego jako rekomendacji "
            "marketingowej dla strony."
        )
    return (
        "Sprawdź stronę wejścia, dopasowanie komunikatu i pomiar. Nie oceniaj kampanii "
        "po samych użytkownikach bez konwersji."
    )


def _content_next_step(intent: TacticalIntent) -> str:
    if intent == "content_create":
        return (
            "Przygotuj brief nowej lub rozbudowanej sekcji, ale najpierw sprawdź "
            "duplikaty w WordPress."
        )
    if intent == "content_block":
        return "Oznacz jako niski priorytet; nie twórz zadania bez mocniejszego demand evidence."
    if intent == "content_merge":
        return (
            "Sprawdź overlap intencji i przygotuj plan scalenia z listą kontroli "
            "przekierowania i audytu."
        )
    return "Przygotuj odświeżenie istniejącej strony: tytuł, H1/H2, sekcje brakujące i CTA."


def _wordpress_match_dimensions(wordpress_match: WordPressMatch) -> dict[str, str]:
    wordpress_fact = wordpress_match.fact
    base_dimensions = {
        "wordpress_match_confidence": wordpress_match.confidence,
        "wordpress_requested_url_key": wordpress_match.requested_url_key,
        "wordpress_requested_path": wordpress_match.requested_path_key,
    }
    if wordpress_fact is None:
        return {
            **base_dimensions,
            "wordpress_match": "missing",
        }
    dimensions = wordpress_fact.dimensions
    return {
        **base_dimensions,
        "wordpress_match": "found",
        "wordpress_connector": wordpress_fact.source_connector,
        "wordpress_content_type": dimensions.get("content_type", ""),
        "wordpress_status": dimensions.get("status", ""),
        "wordpress_content_url": dimensions.get("content_url", ""),
        "wordpress_title_or_h1": dimensions.get("title_or_h1", ""),
        "wordpress_section_headings_json": dimensions.get("section_headings_json", ""),
        "wordpress_section_heading_count": dimensions.get("section_heading_count", ""),
        "wordpress_content_summary": dimensions.get("content_summary", ""),
        "wordpress_content_word_count": dimensions.get("content_word_count", ""),
        "wordpress_block_names_json": dimensions.get("block_names_json", ""),
        "wordpress_block_name_count": dimensions.get("block_name_count", ""),
        "wordpress_acf_field_count": dimensions.get("acf_field_count", ""),
        "wordpress_acf_section_headings_json": dimensions.get(
            "acf_section_headings_json", ""
        ),
        "wordpress_acf_section_count": dimensions.get("acf_section_count", ""),
        "wordpress_content_host": _url_host(dimensions.get("content_url", "")),
        "wordpress_matched_url_key": _normalize_url_key(dimensions.get("content_url", "")),
        "wordpress_matched_path": _normalize_path_key(dimensions.get("content_url", "")),
        "wordpress_host_alias_applied": str(
            wordpress_match.confidence == "host_alias_sitemap"
        ).lower(),
        "wordpress_modified_gmt": dimensions.get("modified_gmt", ""),
        "wordpress_inventory_source": dimensions.get("inventory_source", ""),
    }


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


def _tactical_action_ids_by_connector() -> dict[str, list[str]]:
    return {
        "ahrefs": ["act_prepare_content_refresh_queue"],
        "google_analytics_4": ["act_review_ga4_tracking_quality"],
        "google_merchant_center": ["act_review_merchant_feed_issues"],
        "wordpress_ekologus": ["act_prepare_content_refresh_queue"],
    }


def _is_probe_only_fact(fact: MetricFact) -> bool:
    return fact.source_connector == "localo" and fact.name in {
        "api",
        "access_token_present",
        "authorization_code_supported",
        "pkce_s256_supported",
        "mcp_initialize_status",
    }


def _stable_slug(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.lower())
    compact = "_".join(part for part in normalized.split("_") if part)
    return (compact or "unknown")[:48]


def _normalize_url_key(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc:
        path = parsed.path or "/"
        return f"{parsed.netloc.lower()}{_normalize_path_only(path)}"
    return _normalize_path_key(value)


def _normalize_path_key(value: str) -> str:
    parsed = urlparse(value)
    return _normalize_path_only(parsed.path or value)


def _normalize_path_only(value: str) -> str:
    path = value.strip() or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path.lower()


def _url_host(value: str) -> str:
    return urlparse(value).netloc.lower()


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items
