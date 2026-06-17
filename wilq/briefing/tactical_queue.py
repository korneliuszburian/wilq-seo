from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

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
        for fact in metric_store().list_metric_facts(limit=500)
        if fact.dimensions and not _is_probe_only_fact(fact)
    ]
    actions = list_actions()
    action_ids_by_connector = _action_ids_by_connector(actions)
    items = [
        *_gsc_content_items(facts, action_ids_by_connector),
        *_ga4_quality_items(facts, action_ids_by_connector),
        *_merchant_feed_items(facts, action_ids_by_connector),
    ]
    items = sorted(items, key=lambda item: item.priority)[:TACTICAL_QUEUE_LIMIT]
    return TacticalQueueResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        items=items,
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=_unique(action_id for item in items for action_id in item.action_ids),
    )


def _gsc_content_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
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
        intent = _content_intent(clicks, impressions, ctr, position)
        priority = _content_priority(intent, impressions, position, index)
        items.append(
            TacticalQueueItem(
                id=f"tq_gsc_{_stable_slug(page)}_{_stable_slug(query)}",
                title=f"GSC: {query} -> {page}",
                domain=OpportunityDomain.gsc_seo,
                intent=intent,
                priority=priority,
                risk=ActionRisk.low,
                source_connectors=["google_search_console"],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                metric_facts=group_facts[:6],
                dimensions={"query": query, "page": page},
                diagnosis=_gsc_diagnosis(query, page, clicks, impressions, ctr, position),
                next_step=_content_next_step(intent),
                blocked_claims=["lead quality", "conversion uplift", "revenue impact"],
                action_ids=action_ids_by_connector.get("wordpress_ekologus", []),
            )
        )
    return items


def _ga4_quality_items(
    facts: list[MetricFact],
    action_ids_by_connector: dict[str, list[str]],
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
        intent: TacticalIntent = (
            "landing_page_quality"
            if engagement_rate is not None and engagement_rate < 0.2
            else "traffic_quality_review"
        )
        priority = _ga4_priority(active_users, engagement_rate, index)
        items.append(
            TacticalQueueItem(
                id=f"tq_ga4_{_stable_slug(landing_page)}_{_stable_slug(source_medium)}",
                title=f"GA4: {landing_page} / {source_medium}",
                domain=OpportunityDomain.ga4,
                intent=intent,
                priority=priority,
                risk=ActionRisk.low,
                source_connectors=["google_analytics_4"],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                metric_facts=group_facts[:6],
                dimensions={
                    "landing_page": landing_page,
                    "source_medium": source_medium,
                    "campaign_name": campaign_name,
                },
                diagnosis=_ga4_diagnosis(
                    landing_page,
                    source_medium,
                    campaign_name,
                    active_users,
                    sessions,
                    engagement_rate,
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


def _content_intent(
    clicks: float | int | None,
    impressions: float | int | None,
    ctr: float | int | None,
    position: float | int | None,
) -> TacticalIntent:
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
) -> str:
    return (
        f"Query `{query}` prowadzi do `{page}`. GSC facts: clicks={clicks or 0}, "
        f"impressions={impressions or 0}, ctr={ctr or 0}, average_position={position or 0}."
    )


def _ga4_diagnosis(
    landing_page: str,
    source_medium: str,
    campaign_name: str,
    active_users: float | int | None,
    sessions: float | int | None,
    engagement_rate: float | int | None,
) -> str:
    return (
        f"Landing `{landing_page}` z `{source_medium}` i kampanii `{campaign_name}` ma "
        f"active_users={active_users or 0}, sessions={sessions or 0}, "
        f"engagement_rate={engagement_rate or 0}."
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


def _unique(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items
