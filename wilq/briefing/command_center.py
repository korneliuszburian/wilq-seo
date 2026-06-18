from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionRisk,
    AdsDiagnosticsResponse,
    CommandCenterBriefItem,
    ConnectorStatus,
    ConnectorStatusValue,
    ContentDiagnosticsResponse,
    Ga4DiagnosticsResponse,
    MerchantDiagnosticsResponse,
)


def build_command_center_brief() -> tuple[list[CommandCenterBriefItem], str, int]:
    ads = build_ads_diagnostics()
    merchant = build_merchant_diagnostics()
    content = build_content_diagnostics()
    ga4 = build_ga4_diagnostics()
    localo = get_connector_status("localo")
    items = [
        _ads_item(ads),
        _merchant_item(merchant),
        _content_item(content),
        _ga4_item(ga4),
    ]
    if localo is not None:
        items.append(_localo_item(localo))
    sorted_items = sorted(items, key=lambda item: item.priority)
    blocker_count = sum(1 for item in sorted_items if item.status == "blocked")
    return sorted_items, _primary_next_step(sorted_items), blocker_count


def tactical_item_count() -> int:
    return len(build_tactical_queue().items)


def _ads_item(data: AdsDiagnosticsResponse) -> CommandCenterBriefItem:
    blocked_section = _first_blocked_section(data.sections)
    summary = (
        "Google Ads ma live metric facts."
        if data.live_data_available
        else (blocked_section.summary if blocked_section else "Google Ads nie ma live danych.")
    )
    next_step = (
        "Otwórz /ads-doctor i przejdź do read-only performance review."
        if data.live_data_available
        else "Otwórz /ads-doctor i napraw OAuth przez `act_configure_google_ads_env`."
    )
    return CommandCenterBriefItem(
        id="daily_ads_status",
        title="Ads: blocker OAuth przed analizą spendu",
        route="/ads-doctor",
        status="ready" if data.live_data_available else "blocked",
        priority=30 if data.live_data_available else 5,
        summary=summary,
        next_step=next_step,
        source_connectors=["google_ads"],
        evidence_ids=_limited_ids(data.evidence_ids),
        action_ids=data.action_ids,
        metric_tiles={"blockery": data.blocker_count},
        blocked_claims=["spend", "CPA", "ROAS", "search terms", "wasted budget"],
        risk=ActionRisk.medium,
    )


def _merchant_item(data: MerchantDiagnosticsResponse) -> CommandCenterBriefItem:
    issue_count = data.issue_count if data.issue_count is not None else _metric_total(
        data,
        "issue_product_count",
    )
    return CommandCenterBriefItem(
        id="daily_merchant_feed",
        title="Merchant: feed/product issues do przeglądu",
        route="/merchant",
        status="ready" if data.live_data_available else "blocked",
        priority=10 if data.live_data_available and issue_count > 0 else 35,
        summary=(
            f"Produkty={data.product_count or 0}, issues={issue_count}. "
            "To jest read-only queue, nie automatyczna naprawa feedu."
        ),
        next_step="Otwórz /merchant i waliduj `act_review_merchant_feed_issues`.",
        source_connectors=["google_merchant_center"],
        evidence_ids=_limited_ids(data.evidence_ids),
        action_ids=data.action_ids,
        metric_tiles={
            "produkty": data.product_count or 0,
            "issues": issue_count,
            "blockery": data.blocker_count,
        },
        blocked_claims=["approval restored", "revenue recovered", "automatic feed edit"],
        risk=ActionRisk.medium,
    )


def _content_item(data: ContentDiagnosticsResponse) -> CommandCenterBriefItem:
    return CommandCenterBriefItem(
        id="daily_content_queue",
        title="Content: GSC query/page + WordPress inventory",
        route="/content-planner",
        status="ready" if data.live_data_available else "blocked",
        priority=12 if data.live_data_available else 40,
        summary=(
            f"Query/page={data.query_page_count}, WordPress match="
            f"{data.matched_inventory_count}. WILQ może przygotować refresh queue."
        ),
        next_step="Otwórz /content-planner i przygotuj queue refresh/create/merge/block.",
        source_connectors=[
            "google_search_console",
            "wordpress_ekologus",
            "wordpress_sklep",
        ],
        evidence_ids=_limited_ids(data.evidence_ids),
        action_ids=data.action_ids,
        metric_tiles={
            "query/page": data.query_page_count,
            "WP match": data.matched_inventory_count,
            "blockery": data.blocker_count,
        },
        blocked_claims=["lead uplift", "revenue impact", "ranking guarantee"],
        risk=ActionRisk.low if data.live_data_available else ActionRisk.medium,
    )


def _ga4_item(data: Ga4DiagnosticsResponse) -> CommandCenterBriefItem:
    return CommandCenterBriefItem(
        id="daily_ga4_landing_quality",
        title="GA4: landing/source/campaign quality review",
        route="/ga4",
        status="ready" if data.live_data_available else "blocked",
        priority=14 if data.live_data_available else 42,
        summary=(
            f"Landing groups={data.landing_group_count}, low engagement="
            f"{data.low_engagement_count}, WP match={data.wordpress_match_count}."
        ),
        next_step="Otwórz /ga4 i waliduj `act_review_ga4_tracking_quality`.",
        source_connectors=["google_analytics_4"],
        evidence_ids=_limited_ids(data.evidence_ids),
        action_ids=data.action_ids,
        metric_tiles={
            "landing groups": data.landing_group_count,
            "low engagement": data.low_engagement_count,
            "WP match": data.wordpress_match_count,
        },
        blocked_claims=["ROAS", "revenue", "conversion drop", "tracking fixed"],
        risk=ActionRisk.low if data.live_data_available else ActionRisk.medium,
    )


def _localo_item(connector: ConnectorStatus) -> CommandCenterBriefItem:
    is_ready = (
        connector.configured
        and connector.status == ConnectorStatusValue.configured
        and connector.freshness.state == "fresh"
    )
    missing = ", ".join(connector.missing_credentials) or "brak świeżego Localo evidence"
    return CommandCenterBriefItem(
        id="daily_localo_readiness",
        title="Localo: lokalna widoczność jako blocker",
        route="/localo",
        status="ready" if is_ready else "blocked",
        priority=45 if is_ready else 20,
        summary=(
            "Localo jest gotowe do local visibility review."
            if is_ready
            else f"Localo nie ma pełnego dostępu: {missing}."
        ),
        next_step="Otwórz /localo i dokończ dostęp zanim WILQ pokaże lokalne metryki.",
        source_connectors=["localo"],
        evidence_ids=[connector_evidence_id("localo")],
        action_ids=[],
        metric_tiles={"missing credentials": len(connector.missing_credentials)},
        blocked_claims=["local ranking", "GBP performance", "local visibility uplift"],
        risk=ActionRisk.medium,
    )


def _first_blocked_section(sections: Iterable[Any]) -> Any | None:
    for section in sections:
        if getattr(section, "status", None) == "blocked":
            return section
    return None


def _limited_ids(values: list[str], limit: int = 12) -> list[str]:
    return values[:limit]


def _metric_total(data: MerchantDiagnosticsResponse, metric_name: str) -> int:
    total = 0
    for section in data.sections:
        for fact in section.metric_facts:
            if fact.name != metric_name:
                continue
            if isinstance(fact.value, int | float):
                total += int(fact.value)
    return total


def _primary_next_step(items: list[CommandCenterBriefItem]) -> str:
    for item in items:
        if item.id == "daily_merchant_feed" and item.status == "ready":
            return "Najpierw otwórz /merchant i przejrzyj feed/product issues z ActionObject."
    for item in items:
        if item.status == "ready":
            return item.next_step
    return "Najpierw usuń blocker dostępu z najwyższym priorytetem."


__all__ = ["STRICT_BRIEF_INSTRUCTION", "build_command_center_brief", "tactical_item_count"]
