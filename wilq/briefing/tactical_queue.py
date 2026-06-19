from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.schemas import (
    ActionRisk,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    TacticalQueueResponse,
)
from wilq.storage.metric_store import metric_store

TACTICAL_QUEUE_LIMIT = 24
TACTICAL_QUEUE_DOMAIN_FLOOR = 4
TACTICAL_QUEUE_SOURCE_CONNECTORS = (
    "google_search_console",
    "google_analytics_4",
    "google_merchant_center",
    "wordpress_ekologus",
    "wordpress_sklep",
)
TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT = 300
WORDPRESS_INVENTORY_FACT_LIMIT = 1200
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
    "www.ekologus.pl": {"ekologus.dev.proudsite.pl", "ekologus.pl"},
    "ekologus.pl": {"ekologus.dev.proudsite.pl", "www.ekologus.pl"},
}


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


def build_tactical_queue() -> TacticalQueueResponse:
    facts = [
        fact
        for fact in _tactical_metric_facts()
        if fact.dimensions and not _is_probe_only_fact(fact)
    ]
    actions = list_actions()
    action_ids_by_connector = _action_ids_by_connector(actions)
    wordpress_index = _wordpress_content_index(facts)
    gsc_page_counts = _gsc_page_counts(facts)
    items = [
        *_gsc_content_items(facts, action_ids_by_connector, wordpress_index, gsc_page_counts),
        *_ga4_quality_items(facts, action_ids_by_connector, wordpress_index),
        *_merchant_feed_items(facts, action_ids_by_connector),
    ]
    items = _balanced_tactical_items(items, limit=TACTICAL_QUEUE_LIMIT)
    return TacticalQueueResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        items=items,
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=_unique(action_id for item in items for action_id in item.action_ids),
    )


def _tactical_metric_facts() -> list[MetricFact]:
    facts_by_connector = metric_store().list_metric_facts_by_connector(
        list(TACTICAL_QUEUE_SOURCE_CONNECTORS),
        limit_per_connector=WORDPRESS_INVENTORY_FACT_LIMIT,
    )
    facts: list[MetricFact] = []
    for connector_id in TACTICAL_QUEUE_SOURCE_CONNECTORS:
        connector_limit = (
            WORDPRESS_INVENTORY_FACT_LIMIT
            if connector_id.startswith("wordpress")
            else TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT
        )
        facts.extend(facts_by_connector.get(connector_id, [])[:connector_limit])
    return facts


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
                blocked_claims=["lead quality", "conversion uplift", "revenue impact"],
                action_ids=action_ids_by_connector.get("wordpress_ekologus", []),
            )
        )
    return items


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
                    f"Problem pomiaru GA4: {landing_page} / {source_medium}"
                    if has_not_set_dimension
                    else f"GA4: {landing_page} / {source_medium}"
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
                blocked_claims=["conversion rate", "ROAS", "revenue", "profitability"],
                action_ids=action_ids_by_connector.get("google_analytics_4", []),
            )
        )
    return items


def _merchant_feed_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
) -> list[TacticalQueueItem]:
    merchant_facts = [
        fact for fact in facts if fact.source_connector == "google_merchant_center"
    ]
    merchant_issue_facts = [
        fact
        for fact in merchant_facts
        if fact.name == "issue_product_count"
        and {"severity", "issue_type", "country"}.issubset(fact.dimensions)
    ]
    if any(fact.dimensions.get("issue_type") for fact in merchant_issue_facts):
        merchant_issue_facts = [
            fact for fact in merchant_issue_facts if fact.dimensions.get("issue_type")
        ]
    issue_groups = _group_facts(
        merchant_issue_facts
    )
    product_groups = _group_facts(
        fact
        for fact in merchant_facts
        if fact.name
        in {"active_products", "pending_products", "disapproved_products", "expiring_products"}
        and "country" in fact.dimensions
    )
    items: list[TacticalQueueItem] = []
    for index, ((severity, resolution, issue_type, country), group_facts) in enumerate(
        issue_groups.items(),
        start=1,
    ):
        product_count = _numeric_fact(group_facts, "issue_product_count")
        issue_title = _dimension_value(group_facts, "issue_title")
        affected_attribute = _dimension_value(group_facts, "affected_attribute")
        items.append(
            TacticalQueueItem(
                id=(
                    f"tq_merchant_issue_{_stable_slug(country)}_"
                    f"{_stable_slug(severity)}_{_stable_slug(issue_type)}"
                ),
                title=f"Merchant: {severity} / {issue_type} / {country}",
                domain=OpportunityDomain.merchant,
                intent="merchant_feed_triage",
                priority=_merchant_issue_priority(severity, product_count, index),
                risk=ActionRisk.medium if resolution == "MERCHANT_ACTION" else ActionRisk.low,
                source_connectors=["google_merchant_center"],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                metric_facts=group_facts[:6],
                dimensions={
                    "country": country,
                    "severity": severity,
                    "resolution": resolution,
                    "issue_type": issue_type,
                    **({"issue_title": issue_title} if issue_title else {}),
                    **({"affected_attribute": affected_attribute} if affected_attribute else {}),
                },
                diagnosis=(
                    f"Merchant Center pokazuje {product_count or 0} produktów w issue "
                    f"{severity}/{issue_type}/{resolution} dla kraju {country}."
                ),
                next_step=(
                    "Przygotuj review feed issue queue i payload preview. Nie zmieniaj "
                    "danych produktu bez walidacji ActionObject i zgody operatora."
                ),
                blocked_claims=["product fix applied", "approval restored", "revenue recovered"],
                action_ids=action_ids_by_connector.get("google_merchant_center", []),
            )
        )
    for index, ((country, reporting_context), group_facts) in enumerate(
        product_groups.items(),
        start=1,
    ):
        expiring = _numeric_fact(group_facts, "expiring_products")
        disapproved = _numeric_fact(group_facts, "disapproved_products")
        if not expiring and not disapproved:
            continue
        items.append(
            TacticalQueueItem(
                id=f"tq_merchant_status_{_stable_slug(country)}_{_stable_slug(reporting_context)}",
                title=f"Merchant: status produktów {country} / {reporting_context}",
                domain=OpportunityDomain.merchant,
                intent="merchant_feed_triage",
                priority=45 + index,
                risk=ActionRisk.medium if disapproved else ActionRisk.low,
                source_connectors=["google_merchant_center"],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                metric_facts=group_facts[:6],
                dimensions={"country": country, "reporting_context": reporting_context},
                diagnosis=(
                    f"Status feedu: disapproved_products={disapproved or 0}, "
                    f"expiring_products={expiring or 0} dla {country}/{reporting_context}."
                ),
                next_step="Sprawdź statusy produktów i przygotuj kolejkę manualnego review.",
                blocked_claims=["approval restored", "feed issue resolved"],
                action_ids=action_ids_by_connector.get("google_merchant_center", []),
            )
        )
    return items


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
        if path_key != "/":
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
    if path_key == "/":
        return WordPressMatch(
            fact=None,
            confidence="missing",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    path_candidates = index.paths.get(path_key, [])
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
    if current is None or fact.source_connector == "wordpress_ekologus":
        index[key] = fact


def _preferred_wordpress_path_match(candidates: list[MetricFact]) -> MetricFact | None:
    preferred: MetricFact | None = None
    for fact in candidates:
        if preferred is None:
            preferred = fact
            continue
        if fact.source_connector == "wordpress_ekologus":
            preferred = fact
    return preferred


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
        f"clicks={_metric_or_missing(clicks)}, "
        f"impressions={_metric_or_missing(impressions)}, "
        f"ctr={_metric_or_missing(ctr)}, "
        f"average_position={_metric_or_missing(position)}. "
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
            "nie zwykła taktyka landing page. "
            f"active_users={_metric_or_missing(active_users)}, "
            f"sessions={_metric_or_missing(sessions)}, "
            f"engagement_rate={_metric_or_missing(engagement_rate)}. "
            f"{wordpress_note}"
        )
    return (
        f"Landing `{landing_page}` z `{source_medium}` i kampanii `{campaign_name}` ma "
        f"active_users={_metric_or_missing(active_users)}, "
        f"sessions={_metric_or_missing(sessions)}, "
        f"engagement_rate={_metric_or_missing(engagement_rate)}. {wordpress_note}"
    )


def _has_not_set_dimension(*values: str) -> bool:
    return any(value.strip().lower() == "(not set)" for value in values)


def _ga4_next_step(has_not_set_dimension: bool) -> str:
    if has_not_set_dimension:
        return (
            "Napraw pomiar GA4: sprawdź landing page attribution, source/medium, "
            "UTM-y i konfigurację raportu. Nie traktuj tego jako rekomendacji "
            "marketingowej dla strony."
        )
    return (
        "Sprawdź landing page, message match i tracking. Nie oceniaj kampanii "
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
        return "Sprawdź overlap intencji i przygotuj merge plan z redirect/audit checklist."
    return "Przygotuj refresh istniejącej strony: tytuł, H1/H2, sekcje brakujące i CTA."


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
        return "WordPress inventory nie potwierdza istniejącej strony w ostatnim odczycie."
    dimensions = wordpress_fact.dimensions
    return (
        "WordPress inventory potwierdza istniejący obiekt "
        f"typu {dimensions.get('content_type', 'content')}, "
        f"status: {_wordpress_status_label(dimensions.get('status'))}, "
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


def _action_ids_by_connector(actions: Iterable[object]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for action in actions:
        connector = getattr(action, "connector", None)
        action_id = getattr(action, "id", None)
        if isinstance(connector, str) and isinstance(action_id, str):
            grouped.setdefault(connector, []).append(action_id)
    return grouped


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
