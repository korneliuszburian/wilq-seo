from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionRisk,
    AdsDiagnosticsResponse,
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorSummary,
    ContentDiagnosticsResponse,
    DailyDecision,
    Ga4DiagnosticsResponse,
    MerchantDiagnosticsResponse,
    TacticalQueueResponse,
)
from wilq.storage.local_state import local_state_store

STRICT_DAILY_INSTRUCTION = (
    "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza blocker, "
    "nie domysł marketingowy."
)


def build_command_center_response(
    connectors: list[ConnectorStatus] | None = None,
    tactical_queue: TacticalQueueResponse | None = None,
) -> CommandCenterResponse:
    connectors = connectors if connectors is not None else list_connector_statuses()
    operator_brief, primary_next_step, blocker_count = build_command_center_brief()
    tactical_queue = tactical_queue if tactical_queue is not None else build_tactical_queue()
    action_plan = build_command_center_action_plan(operator_brief, tactical_queue.items)
    return CommandCenterResponse(
        strict_instruction=STRICT_DAILY_INSTRUCTION,
        primary_next_step=primary_next_step,
        blocker_count=blocker_count,
        tactical_item_count=len(tactical_queue.items),
        daily_decisions=build_daily_decisions(action_plan, operator_brief),
        operator_brief=operator_brief,
        demo_script=[],
        action_plan=action_plan,
        connector_summary=_connector_summary(connectors),
        sections={},
        active_actions=[],
        connector_health=connectors,
        codex_operator_status=codex_runtime_status(),
    )


def _connector_summary(connectors: list[ConnectorStatus]) -> ConnectorSummary:
    return ConnectorSummary(
        total=len(connectors),
        configured=sum(1 for connector in connectors if connector.configured),
        missing_credentials=sum(1 for connector in connectors if connector.missing_credentials),
    )


def build_command_center_brief() -> tuple[list[CommandCenterBriefItem], str, int]:
    with ThreadPoolExecutor(max_workers=4) as executor:
        ads_future = executor.submit(build_ads_diagnostics)
        merchant_future = executor.submit(build_merchant_diagnostics)
        content_future = executor.submit(build_content_diagnostics)
        ga4_future = executor.submit(build_ga4_diagnostics)
        ads = ads_future.result()
        merchant = merchant_future.result()
        content = content_future.result()
        ga4 = ga4_future.result()
    localo = get_connector_status("localo")
    localo_runs = local_state_store().list_connector_refresh_runs("localo")
    items = [
        _ads_item(ads),
        _merchant_item(merchant),
        _content_item(content),
        _ga4_item(ga4),
    ]
    if localo is not None:
        localo_item = _localo_item(localo, localo_runs)
        if localo_item.status == "blocked":
            items.append(localo_item)
    sorted_items = sorted(items, key=lambda item: item.priority)
    blocker_count = sum(1 for item in sorted_items if item.status == "blocked")
    return sorted_items, _primary_next_step(sorted_items), blocker_count


def build_command_center_action_plan(
    items: list[CommandCenterBriefItem],
    tactical_items: list[Any] | None = None,
) -> list[CommandCenterActionPlanItem]:
    items_by_id = {item.id: item for item in items}
    if tactical_items is None:
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
        if item.id == "daily_localo_readiness" and item.status == "ready":
            continue
        plan.append(_action_plan_item(item, tactical_items))
    return plan


def build_daily_decisions(
    action_plan: list[CommandCenterActionPlanItem],
    operator_brief: list[CommandCenterBriefItem],
) -> list[DailyDecision]:
    brief_by_plan_id = _brief_items_by_plan_id(operator_brief)
    return [
        DailyDecision(
            id=plan_item.id.replace("plan_", "decision_", 1),
            title=plan_item.title,
            route=plan_item.route,
            status=plan_item.status,
            priority=plan_item.priority,
            metric_tiles=_decision_metric_tiles(plan_item, brief_by_plan_id),
            co_widzimy=_decision_observation(
                plan_item,
                brief_by_plan_id.get(plan_item.id),
            ),
            dlaczego_to_ma_znaczenie=plan_item.why_it_matters,
            bezpieczny_next_step=plan_item.operator_action,
            source_connectors=plan_item.source_connectors,
            evidence_ids=plan_item.evidence_ids,
            action_ids=plan_item.action_ids,
            blocked_claims=plan_item.blocked_claims,
            skill_id=plan_item.skill_id,
            codex_prompt=plan_item.codex_prompt,
            codex_context_endpoint=plan_item.codex_context_endpoint,
            expected_codex_output=plan_item.expected_codex_output,
            risk=plan_item.risk,
        )
        for plan_item in action_plan
    ]


def _brief_items_by_plan_id(
    operator_brief: list[CommandCenterBriefItem],
) -> dict[str, CommandCenterBriefItem]:
    items_by_id = {item.id: item for item in operator_brief}
    mapping = {
        "plan_review_merchant_feed_issues": "daily_merchant_feed",
        "plan_prepare_content_refresh_queue": "daily_content_queue",
        "plan_review_ga4_landing_quality": "daily_ga4_landing_quality",
        "plan_review_ads_campaign_metrics": "daily_ads_status",
        "plan_fix_ads_oauth_before_spend_analysis": "daily_ads_status",
        "plan_localo_access_ready_wait_for_visibility_facts": "daily_localo_readiness",
        "plan_finish_localo_access_before_local_visibility": "daily_localo_readiness",
    }
    return {
        plan_id: items_by_id[item_id]
        for plan_id, item_id in mapping.items()
        if item_id in items_by_id
    }


def _decision_metric_tiles(
    plan_item: CommandCenterActionPlanItem,
    brief_by_plan_id: dict[str, CommandCenterBriefItem],
) -> dict[str, float | int | str]:
    brief_item = brief_by_plan_id.get(plan_item.id)
    if brief_item is None:
        return {}
    return brief_item.metric_tiles


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
        title=(
            "Ads: live campaign metrics dostępne"
            if data.live_data_available
            else "Ads: blocker OAuth przed analizą spendu"
        ),
        route="/ads-doctor",
        status="ready" if data.live_data_available else "blocked",
        priority=30 if data.live_data_available else 5,
        summary=summary,
        next_step=next_step,
        source_connectors=["google_ads"],
        evidence_ids=_limited_ids(data.evidence_ids),
        action_ids=data.action_ids,
        metric_tiles=(
            {
                "kampanie": len(data.campaign_read_contract.campaign_rows),
                "search terms": len(data.search_terms_read_contract.search_term_rows),
                "blockery": data.blocker_count,
            }
            if data.live_data_available
            else {"blockery": data.blocker_count}
        ),
        blocked_claims=(
            ["CPA", "ROAS", "search-term waste", "negative keyword candidates"]
            if data.live_data_available
            else ["spend", "CPA", "ROAS", "search terms", "wasted budget"]
        ),
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


def _localo_item(
    connector: ConnectorStatus,
    runs: list[ConnectorRefreshRun],
) -> CommandCenterBriefItem:
    successful_mcp_run = _latest_successful_localo_mcp_run(runs)
    latest_run = runs[0] if runs else None
    oauth_access_ready = successful_mcp_run is not None
    missing = (
        ", ".join(connector.missing_credentials)
        if connector.missing_credentials
        else "brak świeżego vendor_read proof z Localo MCP"
    )
    evidence_ids = [connector_evidence_id("localo")]
    if successful_mcp_run is not None:
        evidence_ids = successful_mcp_run.evidence_ids
    elif latest_run is not None:
        evidence_ids = latest_run.evidence_ids
    return CommandCenterBriefItem(
        id="daily_localo_readiness",
        title=(
            "Localo: MCP access działa, brak jeszcze ranking/GBP facts"
            if oauth_access_ready
            else "Localo: brak dostępu przed lokalnymi rekomendacjami"
        ),
        route="/localo",
        status="ready" if oauth_access_ready else "blocked",
        priority=60 if oauth_access_ready else 20,
        summary=(
            "Localo MCP initialize zwrócił 200. To potwierdza access, ale WILQ "
            "nie ma jeszcze konkretnych rankingów, GBP visibility ani konkurencji."
            if oauth_access_ready
            else f"Localo nie ma pełnego dostępu: {missing}."
        ),
        next_step=(
            "Otwórz /localo tylko jako status źródła; lokalne rekomendacje wymagają "
            "kolejnego read contractu z konkretnymi ranking/GBP facts."
            if oauth_access_ready
            else "Otwórz /localo i dokończ OAuth access token przez Localo MCP."
        ),
        source_connectors=["localo"],
        evidence_ids=_limited_ids(evidence_ids),
        action_ids=[],
        metric_tiles={
            "MCP access": 1 if oauth_access_ready else 0,
            "ranking facts": 0,
            "GBP facts": 0,
        },
        blocked_claims=["local ranking", "GBP performance", "local visibility uplift"],
        risk=ActionRisk.low if oauth_access_ready else ActionRisk.medium,
    )


def _latest_successful_localo_mcp_run(
    runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    for run in runs:
        if (
            run.status == ConnectorRefreshStatus.completed
            and run.metric_summary.get("api") == "localo_mcp_oauth_probe"
            and run.metric_summary.get("mcp_initialize_status") == 200
        ):
            return run
    return None


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
            skill_id="wilq-merchant-feed-operator",
            codex_prompt=(
                "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center "
                "dla Ekologus, pogrupuj feed/product issues, wskaż najbezpieczniejszą "
                "kolejkę review i nie twierdź, że approval albo revenue zostały odzyskane."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski brief feed issue review z evidence IDs, ActionObject "
                "i blockerami claimów."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_content_queue":
        tactic_summary = _content_tactic_summary(related_tactics)
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
                f"{tactic_summary}"
            ),
            operator_action="Otwórz /content-planner i wybierz refresh, merge, create albo block.",
            skill_id="wilq-content-strategist",
            codex_prompt=(
                "Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh, "
                "merge, create albo block dla Ekologus na podstawie GSC, WordPress, "
                "GA4 i Ahrefs evidence. Nie obiecuj leadów, revenue ani wzrostów pozycji."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polska kolejka content decyzji z evidence IDs, source connectors "
                "i następnym krokiem."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=_merge_ids(item.evidence_ids, related_tactics),
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_ga4_landing_quality":
        review_tactics = [
            tactic
            for tactic in related_tactics
            if getattr(tactic, "intent", None) != "tracking_gap"
        ]
        tactic_summary = _ga4_tactic_summary(review_tactics)
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
                f"{tactic_summary}"
            ),
            operator_action="Otwórz /ga4 i waliduj jakość ruchu bez ROAS/revenue claimów.",
            skill_id="wilq-ga4-analyst",
            codex_prompt=(
                "Użyj skilla wilq-ga4-analyst. Sprawdź jakość ruchu Ekologus po "
                "landing/source/campaign, rozdziel problem marketingowy od problemu "
                "pomiaru i nie wyciągaj wniosków o ROAS, revenue ani konwersjach bez evidence."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polska diagnoza GA4 z landing/source/campaign facts, tracking "
                "blockerami i ActionObject."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=_merge_ids(item.evidence_ids, review_tactics),
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_ads_status":
        if item.status == "ready":
            return CommandCenterActionPlanItem(
                id="plan_review_ads_campaign_metrics",
                title="Przejrzyj kampanie Google Ads z live metryk",
                route=item.route,
                status="ready",
                priority=16,
                category="Google Ads",
                why_it_matters=(
                    "Google Ads OAuth, MCC login i child customer działają. WILQ ma "
                    "świeże campaign i search-term metric facts z konwersjami, ale "
                    "CPA, ROAS, waste i negative keywords nadal wymagają osobnych "
                    "read/safety/ActionObject contractów."
                ),
                operator_action="Otwórz /ads-doctor i analizuj tylko metryki widoczne w evidence.",
                skill_id="wilq-ads-doctor",
                codex_prompt=(
                    "Użyj skilla wilq-ads-doctor. Pokaż przestrzeń do poprawy adsów "
                    "w Ekologus na podstawie dostępnych campaign i search-term metric facts. "
                    "Wyraźnie zablokuj CPA, ROAS, wasted budget i negative keywords, jeśli "
                    "brakuje derived KPI, safety checku albo ActionObject validation."
                ),
                codex_context_endpoint="/api/codex/context-pack",
                expected_codex_output=(
                    "Polska diagnoza Ads z tym, co już wiadomo, czego nie wolno "
                    "twierdzić i co odczytać dalej."
                ),
                source_connectors=item.source_connectors,
                evidence_ids=item.evidence_ids,
                action_ids=item.action_ids,
                blocked_claims=item.blocked_claims,
                risk=ActionRisk.medium,
            )
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
            skill_id="wilq-ads-doctor",
            codex_prompt=(
                "Użyj skilla wilq-ads-doctor. Zweryfikuj Ads blocker dla Ekologus "
                "i przygotuj repair path bez diagnozowania spendu, CPA, ROAS ani search terms."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski blocker handoff z evidence IDs i bez zmyślonych metryk Ads."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=ActionRisk.medium,
        )
    if item.id == "daily_localo_readiness":
        if item.status == "ready":
            return CommandCenterActionPlanItem(
                id="plan_localo_access_ready_wait_for_visibility_facts",
                title="Localo access działa; nie ma jeszcze ranking/GBP facts",
                route=item.route,
                status="ready",
                priority=60,
                category="Localo",
                why_it_matters=(
                    "WILQ potwierdził Localo MCP initialize=200, więc to nie jest już "
                    "blokada OAuth. Nadal brakuje konkretnych local ranking, GBP visibility "
                    "i competitor facts, więc lokalnych rekomendacji nie wolno dopowiadać."
                ),
                operator_action=(
                    "Nie pokazuj tego jako pilnego zadania marketera. Traktuj /localo "
                    "jako status źródła do czasu dodania read contractu dla ranking/GBP facts."
                ),
                skill_id="wilq-localo-operator",
                codex_prompt=(
                    "Użyj skilla wilq-localo-operator. Potwierdź Localo MCP access dla "
                    "Ekologus i wskaż, jakich konkretnych ranking/GBP facts brakuje do "
                    "lokalnych rekomendacji. Nie twierdź nic o lokalnej widoczności bez evidence."
                ),
                codex_context_endpoint="/api/codex/context-pack",
                expected_codex_output=(
                    "Polski status Localo: access działa, ranking/GBP evidence jeszcze brak."
                ),
                source_connectors=item.source_connectors,
                evidence_ids=item.evidence_ids,
                action_ids=item.action_ids,
                blocked_claims=item.blocked_claims,
                risk=ActionRisk.low,
            )
        return CommandCenterActionPlanItem(
            id="plan_finish_localo_access_before_local_visibility",
            title="Dokończ dostęp Localo przed lokalnymi rekomendacjami",
            route=item.route,
            status="blocked",
            priority=20,
            category="Localo",
            why_it_matters=(
                "Localo nie ma świeżego evidence lokalnej widoczności, więc WILQ blokuje "
                "claimy o rankingach i GBP performance."
            ),
            operator_action="Otwórz /localo i pokaż blocker dostępu zamiast metryk lokalnych.",
            skill_id="wilq-localo-operator",
            codex_prompt=(
                "Użyj skilla wilq-localo-operator. Sprawdź stan Localo dla Ekologus "
                "i pokaż tylko readiness/blockery, dopóki WILQ nie ma świeżego evidence "
                "lokalnej widoczności, rankingów albo GBP."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski Localo readiness report z blockerami i bez claimów o rankingach."
            ),
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
        skill_id="wilq-daily-command",
        codex_prompt=(
            "Użyj skilla wilq-daily-command. Skondensuj ten element Command Center "
            "do decyzji marketera po polsku, używając tylko WILQ API evidence."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output="Polska decyzja operatora z evidence IDs i następnym krokiem.",
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


def _content_tactic_summary(tactical_items: list[Any]) -> str:
    pages: dict[str, int] = {}
    for tactic in tactical_items:
        page = getattr(tactic, "dimensions", {}).get("page")
        if not page:
            continue
        pages[page] = pages.get(page, 0) + 1
    if not pages:
        return "Brak skondensowanej kolejki contentowej."
    summary_parts = [
        f"{_short_page_label(page)} ({query_count} {_polish_query_label(query_count)})"
        for page, query_count in list(pages.items())[:3]
    ]
    return "Skondensowane tematy: " + ", ".join(summary_parts) + "."


def _ga4_tactic_summary(tactical_items: list[Any]) -> str:
    landings: dict[str, int] = {}
    for tactic in tactical_items:
        landing = getattr(tactic, "dimensions", {}).get("landing_page")
        if not landing:
            continue
        landings[landing] = landings.get(landing, 0) + 1
    if not landings:
        return "Brak gotowych taktyk jakości ruchu; tracking gaps sprawdź w /ga4."
    summary_parts = [
        f"{_short_landing_label(landing)} ({count} {_polish_group_label(count)})"
        for landing, count in list(landings.items())[:3]
    ]
    return "Skondensowane obszary jakości ruchu: " + ", ".join(summary_parts) + "."


def _short_page_label(page: str) -> str:
    if "://" not in page:
        return page
    return page.split("://", maxsplit=1)[1].removeprefix("www.").rstrip("/") or page


def _short_landing_label(landing: str) -> str:
    if landing == "/":
        return "strona główna"
    return landing[:64]


def _polish_group_label(count: int) -> str:
    if count == 1:
        return "grupa"
    if 2 <= count <= 4:
        return "grupy"
    return "grup"


def _polish_query_label(query_count: int) -> str:
    if query_count == 1:
        return "zapytanie"
    if 2 <= query_count <= 4:
        return "zapytania"
    return "zapytań"


def _action_plan_status(item: CommandCenterBriefItem) -> Literal["ready", "blocked"]:
    return "ready" if item.status == "ready" else "blocked"


def _decision_observation(
    item: CommandCenterActionPlanItem,
    brief_item: CommandCenterBriefItem | None,
) -> str:
    connector_labels = ", ".join(item.source_connectors) if item.source_connectors else "brak"
    evidence_label = f"{len(item.evidence_ids)} evidence ID"
    if len(item.evidence_ids) != 1:
        evidence_label += "s"
    action_label = ", ".join(item.action_ids) if item.action_ids else "brak ActionObject"
    metric_sentence = ""
    if brief_item and brief_item.metric_tiles:
        metric_sentence = _metric_tiles_sentence(brief_item.metric_tiles) + ". "
    return (
        f"{item.category}: {metric_sentence}Źródła={connector_labels}, "
        f"dowody={evidence_label}, akcje={action_label}."
    )


def _metric_tiles_sentence(metric_tiles: dict[str, float | int | str]) -> str:
    return ", ".join(f"{label}={value}" for label, value in metric_tiles.items())


def _merge_ids(base_ids: list[str], tactical_items: list[Any], limit: int = 12) -> list[str]:
    merged = list(base_ids)
    for tactic in tactical_items:
        for evidence_id in tactic.evidence_ids:
            if evidence_id not in merged:
                merged.append(evidence_id)
    return merged[:limit]


__all__ = ["STRICT_BRIEF_INSTRUCTION", "build_command_center_brief", "tactical_item_count"]
