from __future__ import annotations

from collections.abc import Iterable
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
TacticalIntent = Literal[
    "content_refresh",
    "content_create",
    "content_merge",
    "content_block",
    "landing_page_quality",
    "merchant_feed_triage",
    "traffic_quality_review",
]


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
    facts: list[MetricFact] = []
    for connector_id in TACTICAL_QUEUE_SOURCE_CONNECTORS:
        facts.extend(
            metric_store().list_metric_facts(
                connector_id=connector_id,
                limit=TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT,
            )
        )
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
    wordpress_index: dict[str, MetricFact],
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
        wordpress_fact = _find_wordpress_fact(wordpress_index, page)
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
                    **_wordpress_match_dimensions(wordpress_fact),
                    "gsc_page_query_count": str(gsc_page_counts.get(_normalize_url_key(page), 1)),
                },
                diagnosis=_gsc_diagnosis(
                    query,
                    page,
                    clicks,
                    impressions,
                    ctr,
                    position,
                    wordpress_fact=wordpress_fact,
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
    wordpress_index: dict[str, MetricFact],
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
        wordpress_fact = _find_wordpress_fact(wordpress_index, landing_page)
        intent: TacticalIntent = (
            "landing_page_quality"
            if engagement_rate is not None and engagement_rate < 0.2
            else "traffic_quality_review"
        )
        priority = _ga4_priority(active_users, engagement_rate, index)
        item_facts = [*group_facts[:6], *([wordpress_fact] if wordpress_fact else [])]
        source_connectors = ["google_analytics_4"]
        if wordpress_fact:
            source_connectors.append(wordpress_fact.source_connector)
        items.append(
            TacticalQueueItem(
                id=f"tq_ga4_{_stable_slug(landing_page)}_{_stable_slug(source_medium)}",
                title=f"GA4: {landing_page} / {source_medium}",
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
                    **_wordpress_match_dimensions(wordpress_fact),
                },
                diagnosis=_ga4_diagnosis(
                    landing_page,
                    source_medium,
                    campaign_name,
                    active_users,
                    sessions,
                    engagement_rate,
                    wordpress_fact=wordpress_fact,
                ),
                next_step=(
                    "Sprawdź landing page, message match i tracking. Nie oceniaj kampanii "
                    "po samych użytkownikach bez konwersji."
                ),
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
    issue_groups = _group_facts(
        fact
        for fact in merchant_facts
        if fact.name == "issue_product_count"
        and {"severity", "resolution"}.issubset(fact.dimensions)
    )
    product_groups = _group_facts(
        fact
        for fact in merchant_facts
        if fact.name
        in {"active_products", "pending_products", "disapproved_products", "expiring_products"}
        and "country" in fact.dimensions
    )
    items: list[TacticalQueueItem] = []
    for index, ((severity, resolution, country), group_facts) in enumerate(
        issue_groups.items(),
        start=1,
    ):
        product_count = _numeric_fact(group_facts, "issue_product_count")
        items.append(
            TacticalQueueItem(
                id=f"tq_merchant_issue_{_stable_slug(country)}_{_stable_slug(severity)}",
                title=f"Merchant: {severity} / {resolution} / {country}",
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
                },
                diagnosis=(
                    f"Merchant Center pokazuje {product_count or 0} produktów w issue "
                    f"{severity}/{resolution} dla kraju {country}."
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
            fact.dimensions.get("resolution", ""),
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


def _wordpress_content_index(facts: list[MetricFact]) -> dict[str, MetricFact]:
    index: dict[str, MetricFact] = {}
    for fact in facts:
        if not fact.source_connector.startswith("wordpress"):
            continue
        if fact.name != "content_object_seen":
            continue
        content_url = fact.dimensions.get("content_url")
        if not content_url:
            continue
        _set_wordpress_index(index, _normalize_url_key(content_url), fact)
        path_key = _normalize_path_key(content_url)
        if path_key != "/":
            _set_wordpress_index(index, path_key, fact)
    return index


def _find_wordpress_fact(index: dict[str, MetricFact], page_or_path: str) -> MetricFact | None:
    full_match = index.get(_normalize_url_key(page_or_path))
    if full_match:
        return full_match
    path_key = _normalize_path_key(page_or_path)
    if path_key == "/":
        return None
    return index.get(path_key)


def _set_wordpress_index(
    index: dict[str, MetricFact],
    key: str,
    fact: MetricFact,
) -> None:
    current = index.get(key)
    if current is None or fact.source_connector == "wordpress_ekologus":
        index[key] = fact


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
    wordpress_fact: MetricFact | None,
) -> str:
    wordpress_note = _wordpress_match_note(wordpress_fact)
    return (
        f"Query `{query}` prowadzi do `{page}`. GSC facts: clicks={clicks or 0}, "
        f"impressions={impressions or 0}, ctr={ctr or 0}, average_position={position or 0}. "
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
    wordpress_fact: MetricFact | None,
) -> str:
    wordpress_note = _wordpress_match_note(wordpress_fact)
    return (
        f"Landing `{landing_page}` z `{source_medium}` i kampanii `{campaign_name}` ma "
        f"active_users={active_users or 0}, sessions={sessions or 0}, "
        f"engagement_rate={engagement_rate or 0}. {wordpress_note}"
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


def _wordpress_match_dimensions(wordpress_fact: MetricFact | None) -> dict[str, str]:
    if wordpress_fact is None:
        return {"wordpress_match": "missing"}
    dimensions = wordpress_fact.dimensions
    return {
        "wordpress_match": "found",
        "wordpress_connector": wordpress_fact.source_connector,
        "wordpress_content_type": dimensions.get("content_type", ""),
        "wordpress_status": dimensions.get("status", ""),
        "wordpress_content_url": dimensions.get("content_url", ""),
        "wordpress_modified_gmt": dimensions.get("modified_gmt", ""),
    }


def _wordpress_match_note(wordpress_fact: MetricFact | None) -> str:
    if wordpress_fact is None:
        return "WordPress inventory nie potwierdza istniejącej strony w ostatnim odczycie."
    dimensions = wordpress_fact.dimensions
    return (
        "WordPress inventory potwierdza istniejący obiekt "
        f"{dimensions.get('content_type', 'content')} "
        f"status={dimensions.get('status', 'unknown')}."
    )


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


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items
