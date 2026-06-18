from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

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
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    CommandCenterDemoStep,
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


def build_command_center_demo_script(
    items: list[CommandCenterBriefItem],
) -> list[CommandCenterDemoStep]:
    items_by_id = {item.id: item for item in items}
    ordered_item_ids = [
        "daily_merchant_feed",
        "daily_content_queue",
        "daily_ga4_landing_quality",
        "daily_ads_status",
        "daily_localo_readiness",
    ]
    steps = [
        CommandCenterDemoStep(
            id="demo_start_command_center",
            label="Start: plan dnia WILQ",
            route="/command-center",
            status="ready",
            what_it_proves=(
                "WILQ zbiera gotowe źródła, blockery, evidence IDs i ActionObjecty "
                "w jeden polski plan pracy."
            ),
            operator_prompt=(
                "Pokaż dzisiejszy priorytet, gotowe źródła, blockery i akcje, "
                "których nie wolno wykonać bez walidacji."
            ),
            source_item_ids=[item.id for item in items],
            evidence_ids=_limited_ids(
                [evidence for item in items for evidence in item.evidence_ids],
                10,
            ),
            action_ids=_limited_ids([action for item in items for action in item.action_ids], 10),
        )
    ]
    for item_id in ordered_item_ids:
        item = items_by_id.get(item_id)
        if item is None:
            continue
        steps.append(_demo_step_from_item(item))
    return steps


def build_command_center_action_plan(
    items: list[CommandCenterBriefItem],
) -> list[CommandCenterActionPlanItem]:
    items_by_id = {item.id: item for item in items}
    tactical_items = build_tactical_queue().items
    plan: list[CommandCenterActionPlanItem] = []
    for item_id in (
        "daily_merchant_feed",
        "daily_content_queue",
        "daily_ga4_landing_quality",
        "daily_ads_status",
        "daily_localo_readiness",
    ):
        item = items_by_id.get(item_id)
        if item is None:
            continue
        plan.append(_action_plan_item(item, tactical_items))
    return plan


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


def _demo_step_from_item(item: CommandCenterBriefItem) -> CommandCenterDemoStep:
    return CommandCenterDemoStep(
        id=f"demo_{item.id}",
        label=_demo_label(item),
        route=item.route,
        status="ready" if item.status == "ready" else "blocked",
        what_it_proves=_demo_proof(item),
        operator_prompt=item.next_step,
        source_item_ids=[item.id],
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
    )


def _demo_label(item: CommandCenterBriefItem) -> str:
    if item.id == "daily_merchant_feed":
        return "Merchant Center: dowód feedu produktów"
    if item.id == "daily_content_queue":
        return "Content Planner: kolejka treści"
    if item.id == "daily_ga4_landing_quality":
        return "GA4: jakość ruchu"
    if item.id == "daily_ads_status":
        return "Ads Doctor: blocker OAuth"
    if item.id == "daily_localo_readiness":
        return "Localo: blocker lokalnej widoczności"
    return item.title


def _demo_proof(item: CommandCenterBriefItem) -> str:
    if item.id == "daily_merchant_feed":
        return (
            "Merchant Center daje realne product/feed metryki, issue count i review-safe "
            "ActionObject bez automatycznej edycji feedu."
        )
    if item.id == "daily_content_queue":
        return (
            "GSC i WordPress inventory tworzą kolejkę content refresh/create/merge/block "
            "bez obietnic wzrostu pozycji."
        )
    if item.id == "daily_ga4_landing_quality":
        return (
            "GA4 wskazuje jakość landing/source/campaign i blokuje ROAS/revenue claimy, "
            "jeśli nie ma takich danych w evidence."
        )
    if item.id == "daily_ads_status":
        return (
            "Ads Doctor nie zmyśla spendu ani search terms: pokazuje OAuth blocker i "
            "bezpieczny ActionObject naprawy dostępu."
        )
    if item.id == "daily_localo_readiness":
        return (
            "Localo jest jawnie oznaczone jako dostęp/readiness blocker, dopóki WILQ "
            "nie ma świeżego evidence lokalnej widoczności."
        )
    return item.summary


def _action_plan_item(
    item: CommandCenterBriefItem,
    tactical_items: list[Any],
) -> CommandCenterActionPlanItem:
    related_tactics = _related_tactical_items(item, tactical_items)
    if item.id == "daily_merchant_feed":
        return CommandCenterActionPlanItem(
            id="plan_review_merchant_feed_issues",
            title="Przejrzyj produkty z problemami w Merchant Center",
            route=item.route,
            status=_action_plan_status(item),
            priority=10,
            category="Merchant Center",
            why_it_matters=(
                f"WILQ widzi {item.metric_tiles.get('produkty', 0)} produktów i "
                f"{item.metric_tiles.get('issues', 0)} feed/product issues. To może blokować "
                "widoczność produktów, ale wymaga ręcznego review przed zmianami."
            ),
            operator_action="Otwórz /merchant, sprawdź issue queue i waliduj ActionObject.",
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_content_queue":
        top_titles = ", ".join(tactic.title for tactic in related_tactics[:3])
        return CommandCenterActionPlanItem(
            id="plan_prepare_content_refresh_queue",
            title="Ułóż kolejkę refresh/merge/create dla treści SEO",
            route=item.route,
            status=_action_plan_status(item),
            priority=12,
            category="Content + SEO",
            why_it_matters=(
                f"WILQ ma {item.metric_tiles.get('query/page', 0)} query/page kandydatów i "
                f"{item.metric_tiles.get('WP match', 0)} dopasowań WordPress. "
                f"Pierwsze taktyki: {top_titles or 'brak taktyk w kolejce'}."
            ),
            operator_action="Otwórz /content-planner i wybierz refresh, merge, create albo block.",
            source_connectors=item.source_connectors,
            evidence_ids=_merge_ids(item.evidence_ids, related_tactics),
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_ga4_landing_quality":
        top_titles = ", ".join(tactic.title for tactic in related_tactics[:2])
        return CommandCenterActionPlanItem(
            id="plan_review_ga4_landing_quality",
            title="Sprawdź jakość ruchu i landing page w GA4",
            route=item.route,
            status=_action_plan_status(item),
            priority=14,
            category="GA4",
            why_it_matters=(
                f"WILQ widzi {item.metric_tiles.get('landing groups', 0)} grup landing/source "
                f"i {item.metric_tiles.get('low engagement', 0)} niskiej jakości grupy. "
                f"Pierwsze taktyki: {top_titles or 'brak taktyk w kolejce'}."
            ),
            operator_action="Otwórz /ga4 i waliduj jakość ruchu bez ROAS/revenue claimów.",
            source_connectors=item.source_connectors,
            evidence_ids=_merge_ids(item.evidence_ids, related_tactics),
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_ads_status":
        return CommandCenterActionPlanItem(
            id="plan_fix_ads_oauth_before_spend_analysis",
            title="Napraw Google Ads OAuth zanim padną wnioski o spendzie",
            route=item.route,
            status="blocked",
            priority=5,
            category="Google Ads",
            why_it_matters=(
                "Ads Doctor ma blocker OAuth. WILQ nie pokaże spendu, CPA, ROAS ani search "
                "terms bez świeżego Ads evidence."
            ),
            operator_action="Otwórz /ads-doctor i wykonaj repair path z ActionObject.",
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=ActionRisk.medium,
        )
    if item.id == "daily_localo_readiness":
        return CommandCenterActionPlanItem(
            id="plan_finish_localo_access_before_local_visibility",
            title="Dokończ Localo access przed lokalnymi rekomendacjami",
            route=item.route,
            status="blocked",
            priority=20,
            category="Localo",
            why_it_matters=(
                "Localo nie ma świeżego evidence lokalnej widoczności, więc WILQ blokuje "
                "claimy o rankingach i GBP performance."
            ),
            operator_action="Otwórz /localo i pokaż blocker dostępu zamiast metryk lokalnych.",
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=ActionRisk.medium,
        )
    return CommandCenterActionPlanItem(
        id=f"plan_{item.id}",
        title=item.title,
        route=item.route,
        status="ready" if item.status == "ready" else "blocked",
        priority=item.priority,
        category="WILQ",
        why_it_matters=item.summary,
        operator_action=item.next_step,
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=item.risk,
    )


def _related_tactical_items(item: CommandCenterBriefItem, tactical_items: list[Any]) -> list[Any]:
    source_connectors = set(item.source_connectors)
    return [
        tactic
        for tactic in tactical_items
        if source_connectors.intersection(set(tactic.source_connectors))
    ]


def _action_plan_status(item: CommandCenterBriefItem) -> Literal["ready", "blocked"]:
    return "ready" if item.status == "ready" else "blocked"


def _merge_ids(base_ids: list[str], tactical_items: list[Any], limit: int = 12) -> list[str]:
    merged = list(base_ids)
    for tactic in tactical_items:
        for evidence_id in tactic.evidence_ids:
            if evidence_id not in merged:
                merged.append(evidence_id)
    return merged[:limit]


__all__ = ["STRICT_BRIEF_INSTRUCTION", "build_command_center_brief", "tactical_item_count"]
