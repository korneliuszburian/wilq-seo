from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from wilq.actions.google_ads.business_context import ADS_BUSINESS_CONTEXT_ACTION_ID
from wilq.actions.service import list_actions
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
    ActionObject,
    ActionRisk,
    AdsDiagnosticsResponse,
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorSummary,
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    DailyDecision,
    Ga4DecisionItem,
    Ga4DiagnosticsResponse,
    MerchantDecisionItem,
    MerchantDiagnosticsResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    TacticalQueueResponse,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

STRICT_DAILY_INSTRUCTION = (
    "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza blocker, "
    "nie domysł marketingowy."
)
GA4_CONNECTOR_ID = "google_analytics_4"
GA4_COMMAND_CENTER_METRIC_FACT_LIMIT = 2000
LOCALO_PROBE_METRIC_NAMES = {
    "access_token_present",
    "api",
    "authorization_code_supported",
    "mcp_initialize_status",
    "pkce_s256_supported",
}


def build_command_center_response(
    connectors: list[ConnectorStatus] | None = None,
    tactical_queue: TacticalQueueResponse | None = None,
    actions: list[ActionObject] | None = None,
) -> CommandCenterResponse:
    connectors = connectors if connectors is not None else list_connector_statuses()
    tactical_queue = tactical_queue if tactical_queue is not None else build_tactical_queue()
    actions = actions if actions is not None else list_actions()
    operator_brief, primary_next_step, blocker_count = build_command_center_brief(
        tactical_queue=tactical_queue,
        actions=actions,
    )
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


def build_command_center_brief(
    tactical_queue: TacticalQueueResponse | None = None,
    actions: list[ActionObject] | None = None,
) -> tuple[list[CommandCenterBriefItem], str, int]:
    tactical_queue = tactical_queue if tactical_queue is not None else build_tactical_queue()
    actions = actions if actions is not None else list_actions()
    with ThreadPoolExecutor(max_workers=4) as executor:
        ads_future = executor.submit(build_ads_diagnostics, actions=actions)
        content_future = executor.submit(
            build_content_diagnostics,
            tactical_items=tactical_queue.items,
            actions=actions,
        )
        merchant_facts_future = executor.submit(
            metric_store().list_metric_facts,
            "google_merchant_center",
            2000,
        )
        ga4_facts_future = executor.submit(
            metric_store().list_metric_facts,
            GA4_CONNECTOR_ID,
            GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
        )
        localo_facts_future = executor.submit(
            metric_store().list_metric_facts,
            "localo",
            120,
        )
        ads = ads_future.result()
        content = content_future.result()
        merchant_facts = merchant_facts_future.result()
        ga4_facts = ga4_facts_future.result()
        localo_facts = localo_facts_future.result()
    merchant = build_merchant_diagnostics(
        tactical_items=tactical_queue.items,
        actions=actions,
        metric_facts=merchant_facts,
    )
    ga4_diagnostics = build_ga4_diagnostics(
        tactical_items=tactical_queue.items,
        actions=actions,
        metric_facts=ga4_facts,
    )
    localo = get_connector_status("localo")
    localo_runs = local_state_store().list_connector_refresh_runs("localo")
    items = [
        _ads_item(ads),
        _merchant_item_from_diagnostics(merchant),
        _content_item_from_diagnostics(content),
        _ga4_item_from_diagnostics(ga4_diagnostics),
    ]
    ads_business_item = _ads_business_context_item(ads)
    if ads_business_item is not None:
        items.append(ads_business_item)
    if localo is not None:
        localo_item = _localo_item(localo, localo_runs, localo_facts)
        if localo_item.status == "blocked" or localo_item.id == "daily_localo_visibility_facts":
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
        "daily_ads_business_context",
        "daily_localo_visibility_facts",
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
        "plan_ads_business_context_before_budget_decisions": "daily_ads_business_context",
        "plan_review_localo_visibility_facts": "daily_localo_visibility_facts",
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
    metric_tiles = _ads_metric_tiles(data) if data.live_data_available else {}
    summary = (
        _ads_ready_summary(metric_tiles)
        if data.live_data_available
        else (blocked_section.summary if blocked_section else "Google Ads nie ma live danych.")
    )
    next_step = (
        _ads_ready_next_step(metric_tiles)
        if data.live_data_available
        else "Otwórz /ads-doctor i napraw OAuth przez `act_configure_google_ads_env`."
    )
    return CommandCenterBriefItem(
        id="daily_ads_status",
        title=(
            "Ads: kolejki budżetu, rekomendacji i zapytań"
            if data.live_data_available
            else "Ads: blocker OAuth przed analizą spendu"
        ),
        route="/ads-doctor",
        status="ready" if data.live_data_available else "blocked",
        priority=16 if data.live_data_available else 5,
        summary=summary,
        next_step=next_step,
        source_connectors=["google_ads"],
        evidence_ids=_limited_ids(data.evidence_ids),
        action_ids=[
            action_id
            for action_id in data.action_ids
            if action_id != ADS_BUSINESS_CONTEXT_ACTION_ID
        ],
        metric_tiles=metric_tiles if data.live_data_available else {"blockery": data.blocker_count},
        blocked_claims=(
            _ads_ready_blocked_claims(data)
            if data.live_data_available
            else ["spend", "CPA", "ROAS", "search terms", "wasted budget"]
        ),
        risk=ActionRisk.medium,
    )


def _ads_metric_tiles(data: AdsDiagnosticsResponse) -> dict[str, float | int | str]:
    return {
        "kampanie": len(data.campaign_read_contract.campaign_rows),
        "zapytania": len(data.search_terms_read_contract.search_term_rows),
        "podgląd budżetu": len(data.budget_pacing_read_contract.payload_preview),
        "rekomendacje": len(data.recommendations_read_contract.payload_preview),
        "wykluczenia": len(data.negative_keywords_read_contract.payload_preview),
        "segmenty": len(data.custom_segments_read_contract.payload_preview),
    }


def _ads_business_context_item(
    data: AdsDiagnosticsResponse,
) -> CommandCenterBriefItem | None:
    if not hasattr(data, "business_context_read_contract"):
        return None
    contract = data.business_context_read_contract
    if not data.live_data_available or contract.status != "blocked":
        return None
    return CommandCenterBriefItem(
        id="daily_ads_business_context",
        title="Ads: brakuje kontekstu biznesowego do decyzji budżetowych",
        route="/ads-doctor",
        status="blocked",
        priority=18,
        summary=contract.summary,
        next_step=contract.next_step,
        source_connectors=contract.source_connectors,
        evidence_ids=_limited_ids(contract.evidence_ids),
        action_ids=[
            action_id
            for action_id in data.action_ids
            if action_id == ADS_BUSINESS_CONTEXT_ACTION_ID
        ],
        metric_tiles={
            "braki": len(contract.missing_read_contracts),
            **contract.metric_tiles,
        },
        blocked_claims=contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _ads_ready_summary(metric_tiles: dict[str, float | int | str]) -> str:
    return (
        "Google Ads ma liczniki do oceny: "
        f"kampanie={metric_tiles.get('kampanie', 0)}, "
        f"zapytania={metric_tiles.get('zapytania', 0)}, "
        f"podgląd budżetu={metric_tiles.get('podgląd budżetu', 0)}, "
        f"rekomendacje={metric_tiles.get('rekomendacje', 0)}, "
        f"wykluczenia={metric_tiles.get('wykluczenia', 0)}, "
        f"segmenty={metric_tiles.get('segmenty', 0)}. "
        "To są kolejki tylko do oceny z evidence i ActionObjectami, nie ścieżka apply."
    )


def _ads_ready_next_step(metric_tiles: dict[str, float | int | str]) -> str:
    review_parts: list[str] = []
    if _numeric_tile(metric_tiles, "podgląd budżetu") > 0:
        review_parts.append("budżety")
    if _numeric_tile(metric_tiles, "rekomendacje") > 0:
        review_parts.append("rekomendacje")
    if _numeric_tile(metric_tiles, "wykluczenia") > 0:
        review_parts.append("wykluczenia")
    if _numeric_tile(metric_tiles, "segmenty") > 0:
        review_parts.append("segmenty")
    if not review_parts:
        review_parts.append("kampanie i zapytania")
    return (
        "Otwórz /ads-doctor i przejdź przez ocenę: "
        f"{', '.join(review_parts)}. Nie wdrażaj apply bez walidacji, "
        "potwierdzenia i audytu."
    )


def _ads_ready_blocked_claims(data: AdsDiagnosticsResponse) -> list[str]:
    blocked_claims = _unique(
        [
            *data.budget_pacing_read_contract.blocked_claims,
            *data.recommendations_read_contract.blocked_claims,
            *data.negative_keywords_read_contract.blocked_claims,
            *data.custom_segments_read_contract.blocked_claims,
            *data.business_context_read_contract.blocked_claims,
            "profitability",
            "wasted budget",
        ]
    )
    return blocked_claims[:8]


def _numeric_tile(metric_tiles: dict[str, float | int | str], name: str) -> float:
    value = metric_tiles.get(name, 0)
    return float(value) if isinstance(value, int | float) else 0.0


def _risk_rank(risk: ActionRisk) -> int:
    return {
        ActionRisk.critical: 0,
        ActionRisk.high: 1,
        ActionRisk.medium: 2,
        ActionRisk.low: 3,
    }.get(risk, 4)


def _merchant_item_from_diagnostics(data: MerchantDiagnosticsResponse) -> CommandCenterBriefItem:
    top_decision = _top_merchant_decision(data.decision_queue)
    decision_count = len(data.decision_queue)
    problem_type_count = data.issue_count or len(data.issue_clusters)
    issue_occurrence_count = sum(cluster.product_count for cluster in data.issue_clusters)
    if not issue_occurrence_count:
        issue_occurrence_count = sum(
            decision.issue_count
            if decision.issue_count is not None
            else decision.product_count or 0
            for decision in data.decision_queue
        )
    product_count = data.product_count or 0
    live_data_available = data.live_data_available and bool(data.decision_queue)
    action_ids = data.action_ids or _unique(
        action_id for decision in data.decision_queue for action_id in decision.action_ids
    )
    evidence_ids = (
        data.evidence_ids
        or _unique(
            evidence_id
            for decision in data.decision_queue
            for evidence_id in decision.evidence_ids
        )
        or [connector_evidence_id("google_merchant_center")]
    )
    if live_data_available:
        top_reason = (
            f"Najważniejsza decyzja: {top_decision.title}."
            if top_decision is not None
            else "Najpierw przejrzyj kolejkę Merchant."
        )
        summary = (
            f"Produkty={product_count}, typy problemów={problem_type_count}, "
            f"zgłoszenia={issue_occurrence_count}, decyzje={decision_count}. {top_reason} "
            "To jest read-only queue, nie automatyczna naprawa feedu."
        )
        next_step = "Otwórz /merchant i przejrzyj decyzje feedu przed walidacją ActionObject."
    else:
        summary = "Merchant nie ma gotowej kolejki decyzji z aktualnych metric facts."
        next_step = "Uruchom read-only Merchant vendor_read, potem wróć do /merchant."
    return CommandCenterBriefItem(
        id="daily_merchant_feed",
        title="Merchant: kolejka problemów feedu",
        route="/merchant",
        status="ready" if live_data_available else "blocked",
        priority=10 if live_data_available and issue_occurrence_count > 0 else 35,
        summary=summary,
        next_step=next_step,
        source_connectors=["google_merchant_center"],
        evidence_ids=_limited_ids(evidence_ids),
        action_ids=action_ids,
        metric_tiles={
            "produkty": product_count,
            "typy problemów": problem_type_count,
            "zgłoszenia": issue_occurrence_count,
            "decyzje": decision_count,
            "blockery": data.blocker_count,
        },
        blocked_claims=_unique(
            [
                *(claim for section in data.sections for claim in section.blocked_claims),
                *(claim for decision in data.decision_queue for claim in decision.blocked_claims),
            ]
        )
        or ["approval restored", "revenue recovered", "automatic feed edit"],
        risk=ActionRisk.medium,
    )


def _top_merchant_decision(
    decisions: list[MerchantDecisionItem],
) -> MerchantDecisionItem | None:
    if not decisions:
        return None
    return sorted(
        decisions,
        key=lambda decision: (
            _risk_rank(decision.risk),
            -(decision.product_count or 0),
            decision.title,
        ),
    )[0]


def _content_item_from_diagnostics(data: ContentDiagnosticsResponse) -> CommandCenterBriefItem:
    top_decision = _top_content_decision(data.decision_queue)
    live_data_available = data.live_data_available and bool(data.decision_queue)
    action_ids = data.action_ids or _unique(
        action_id for decision in data.decision_queue for action_id in decision.action_ids
    )
    evidence_ids = (
        data.evidence_ids
        or _unique(
            evidence_id
            for decision in data.decision_queue
            for evidence_id in decision.evidence_ids
        )
        or [connector_evidence_id("google_search_console")]
    )
    total_clicks = sum(decision.total_clicks or 0 for decision in data.decision_queue)
    total_impressions = sum(decision.total_impressions or 0 for decision in data.decision_queue)
    summary = (
        _content_command_summary(top_decision)
        if top_decision is not None
        else (
            "Brak gotowej kolejki contentowej. WILQ potrzebuje GSC query/page "
            "i WordPress inventory."
        )
    )
    next_step = (
        _content_command_next_step(top_decision)
        if top_decision is not None
        else "Otwórz /content-planner i odśwież GSC oraz WordPress inventory."
    )
    return CommandCenterBriefItem(
        id="daily_content_queue",
        title=(
            "Content: kolejka SEO z GSC i WordPress"
            if live_data_available
            else "Content: brak kolejki SEO"
        ),
        route="/content-planner",
        status="ready" if live_data_available else "blocked",
        priority=12 if live_data_available else 40,
        summary=summary,
        next_step=next_step,
        source_connectors=[
            "google_search_console",
            "wordpress_ekologus",
            "wordpress_sklep",
        ],
        evidence_ids=_limited_ids(evidence_ids),
        action_ids=action_ids,
        metric_tiles={
            "query/page": data.query_page_count,
            "WP match": data.matched_inventory_count,
            "decyzje": len(data.decision_queue),
            "wyświetlenia": total_impressions,
            "kliknięcia": total_clicks,
            "blockery": 0 if live_data_available else 1,
        },
        blocked_claims=_unique(
            claim for decision in data.decision_queue for claim in decision.blocked_claims
        )
        or ["lead uplift", "revenue impact", "ranking guarantee"],
        risk=ActionRisk.low if live_data_available else ActionRisk.medium,
    )


def _top_content_decision(
    decisions: list[ContentDecisionItem],
) -> ContentDecisionItem | None:
    return next(
        (
            decision
            for decision in decisions
            if decision.decision_type != "block_as_tracking_not_content"
        ),
        decisions[0] if decisions else None,
    )


def _content_command_summary(decision: ContentDecisionItem) -> str:
    if decision.summary:
        return decision.summary
    if decision.primary_query:
        return f'Najważniejsze zapytanie contentowe: "{decision.primary_query}".'
    return decision.rationale


def _content_command_next_step(decision: ContentDecisionItem) -> str:
    if decision.page:
        return f"Otwórz /content-planner i zacznij od: {decision.title}."
    return decision.next_step


def _ga4_item_from_diagnostics(data: Ga4DiagnosticsResponse) -> CommandCenterBriefItem:
    decision_count = len(data.decision_queue)
    measurement_issue_count = _ga4_decision_type_count(
        data.decision_queue,
        "fix_measurement",
    )
    traffic_review_count = _ga4_decision_type_count(
        data.decision_queue,
        "review_traffic_quality",
    )
    landing_mapping_count = _ga4_decision_type_count(
        data.decision_queue,
        "review_landing_mapping",
    )
    missing_contract_count = sum(1 for section in data.sections if section.status != "ready")
    action_ids = data.action_ids or _unique(
        action_id for decision in data.decision_queue for action_id in decision.action_ids
    )
    evidence_ids = (
        data.evidence_ids
        or _unique(
            evidence_id
            for decision in data.decision_queue
            for evidence_id in decision.evidence_ids
        )
        or [connector_evidence_id(GA4_CONNECTOR_ID)]
    )
    live_data_available = data.live_data_available and data.landing_group_count > 0
    return CommandCenterBriefItem(
        id="daily_ga4_landing_quality",
        title=(
            "GA4: pomiar i jakość ruchu do kontroli"
            if live_data_available
            else "GA4: brak danych do oceny ruchu"
        ),
        route="/ga4",
        status="blocked",
        priority=14 if live_data_available else 42,
        summary=(
            f"GA4 ma {data.landing_group_count} grup landing/source/campaign i "
            f"{decision_count} decyzji review: pomiar={measurement_issue_count}, "
            f"jakość ruchu={traffic_review_count}, mapowanie={landing_mapping_count}. "
            "Status blocked oznacza brak kontraktu na ROAS/revenue/conversion "
            "drop/tracking fixed, nie awarię connectora."
        ),
        next_step=(
            "Otwórz /ga4 i przejdź przez kolejkę decyzji: problemy pomiaru, "
            "mapowanie landingów i jakość ruchu. Waliduj "
            "`act_review_ga4_tracking_quality`; nie traktuj tego jako werdyktu "
            "performance."
        ),
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_limited_ids(evidence_ids),
        action_ids=action_ids,
        metric_tiles={
            "grupy ruchu": data.landing_group_count,
            "decyzje": decision_count,
            "pomiar": measurement_issue_count,
            "jakość ruchu": traffic_review_count,
            "braki kontraktu": max(missing_contract_count, 1),
        },
        blocked_claims=_unique(
            [
                *(claim for section in data.sections for claim in section.blocked_claims),
                *(claim for decision in data.decision_queue for claim in decision.blocked_claims),
                "tracking fixed",
            ]
        )[:8],
        risk=ActionRisk.medium,
    )


def _ga4_decision_type_count(
    decisions: list[Ga4DecisionItem],
    decision_type: str,
) -> int:
    return sum(1 for decision in decisions if decision.decision_type == decision_type)


def _ga4_item_from_tactical(
    tactical_items: list[TacticalQueueItem],
    actions: list[ActionObject],
    ga4_facts: list[MetricFact],
) -> CommandCenterBriefItem:
    ga4_items = [item for item in tactical_items if item.domain == OpportunityDomain.ga4]
    dimensioned_facts = _dimensioned_ga4_facts(ga4_facts)
    landing_group_count = max(len(ga4_items), _ga4_landing_group_count(dimensioned_facts))
    low_engagement_items = [
        item for item in ga4_items if item.intent == "landing_page_quality"
    ]
    matched_items = [
        item for item in ga4_items if item.dimensions.get("wordpress_match") == "found"
    ]
    action_ids = _action_ids_for(
        actions,
        connector=GA4_CONNECTOR_ID,
    )
    live_data_available = landing_group_count > 0
    return CommandCenterBriefItem(
        id="daily_ga4_landing_quality",
        title=(
            "GA4: pomiar i jakość ruchu do kontroli"
            if live_data_available
            else "GA4: brak danych do oceny ruchu"
        ),
        route="/ga4",
        status="blocked",
        priority=14 if live_data_available else 42,
        summary=(
            f"GA4 ma {landing_group_count} grup landing/source/campaign, "
            f"{len(low_engagement_items)} grup niskiego zaangażowania i "
            f"{len(matched_items)} dopasowań WordPress. "
            "Status blocked oznacza brak kontraktu na ROAS/revenue/conversion "
            "drop/tracking fixed, nie awarię connectora."
        ),
        next_step=(
            "Otwórz /ga4, sprawdź kolejkę jakości ruchu i waliduj "
            "`act_review_ga4_tracking_quality`."
        ),
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            _unique(evidence_id for item in ga4_items for evidence_id in item.evidence_ids)
            or _unique(fact.evidence_id for fact in dimensioned_facts)
            or [connector_evidence_id(GA4_CONNECTOR_ID)]
        ),
        action_ids=action_ids,
        metric_tiles={
            "grupy ruchu": landing_group_count,
            "decyzje": len(ga4_items),
            "pomiar": sum(1 for item in ga4_items if item.intent == "tracking_gap"),
            "jakość ruchu": len(low_engagement_items),
            "braki kontraktu": 1,
        },
        blocked_claims=["ROAS", "revenue", "conversion drop", "tracking fixed"],
        risk=ActionRisk.medium,
    )


def _dimensioned_ga4_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.source_connector == GA4_CONNECTOR_ID
        and {"landing_page", "source_medium", "campaign_name"}.issubset(fact.dimensions)
    ]


def _ga4_landing_group_count(facts: Iterable[MetricFact]) -> int:
    return len(
        {
            (
                fact.dimensions.get("landing_page", ""),
                fact.dimensions.get("source_medium", ""),
                fact.dimensions.get("campaign_name", ""),
            )
            for fact in facts
        }
    )


def _localo_item(
    connector: ConnectorStatus,
    runs: list[ConnectorRefreshRun],
    metric_facts: list[MetricFact],
) -> CommandCenterBriefItem:
    successful_mcp_run = _latest_successful_localo_mcp_run(runs)
    latest_run = runs[0] if runs else None
    oauth_access_ready = successful_mcp_run is not None
    metric_facts = _localo_metric_facts_for_run(successful_mcp_run, metric_facts)
    value_facts = _localo_value_facts(metric_facts)
    has_value_facts = bool(value_facts)
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
    if has_value_facts:
        item_id = "daily_localo_visibility_facts"
        title = "Localo: agregaty widoczności i recenzji są gotowe"
        summary = (
            "Localo dostarczył read-only agregaty miejsc, monitorowanych fraz "
            "i recenzji. WILQ nadal blokuje GBP, konkurencję i claim o wzroście "
            "widoczności bez osobnych kontraktów."
        )
        next_step = (
            "Otwórz /localo i przejrzyj agregaty fraz, grid positions oraz recenzji. "
            "Nie twierdź nic o GBP/konkurencji bez dodatkowego evidence."
        )
        priority = 18
        blocked_claims = ["GBP performance", "competitor visibility", "local visibility uplift"]
    elif oauth_access_ready:
        item_id = "daily_localo_readiness"
        title = "Localo: MCP access działa, brak jeszcze ranking/GBP facts"
        summary = (
            "Localo MCP initialize zwrócił 200. To potwierdza access, ale WILQ "
            "nie ma jeszcze konkretnych rankingów, GBP visibility ani konkurencji."
        )
        next_step = (
            "Otwórz /localo tylko jako status źródła; lokalne rekomendacje wymagają "
            "kolejnego read contractu z konkretnymi ranking/GBP facts."
        )
        priority = 60
        blocked_claims = ["local ranking", "GBP performance", "local visibility uplift"]
    else:
        item_id = "daily_localo_readiness"
        title = "Localo: brak dostępu przed lokalnymi rekomendacjami"
        summary = f"Localo nie ma pełnego dostępu: {missing}."
        next_step = "Otwórz /localo i dokończ OAuth access token przez Localo MCP."
        priority = 20
        blocked_claims = ["local ranking", "GBP performance", "local visibility uplift"]
    return CommandCenterBriefItem(
        id=item_id,
        title=title,
        route="/localo",
        status="ready" if oauth_access_ready or has_value_facts else "blocked",
        priority=priority,
        summary=summary,
        next_step=next_step,
        source_connectors=["localo"],
        evidence_ids=_limited_ids(evidence_ids),
        action_ids=[],
        metric_tiles=_localo_metric_tiles(value_facts, oauth_access_ready),
        blocked_claims=blocked_claims,
        risk=ActionRisk.low if oauth_access_ready or has_value_facts else ActionRisk.medium,
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


def _localo_value_facts(metric_facts: list[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in metric_facts
        if not (fact.source_connector == "localo" and fact.name in LOCALO_PROBE_METRIC_NAMES)
        and not (
            fact.source_connector == "localo"
            and fact.name == "api"
            and fact.value == "localo_mcp_oauth_probe"
        )
    ]


def _localo_metric_facts_for_run(
    run: ConnectorRefreshRun | None,
    fallback_facts: list[MetricFact],
) -> list[MetricFact]:
    if run and run.evidence_ids:
        facts = metric_store().list_metric_facts_by_evidence_ids(run.evidence_ids)
        if facts:
            return facts
    return fallback_facts


def _localo_metric_tiles(
    value_facts: list[MetricFact],
    oauth_access_ready: bool,
) -> dict[str, int | float | str]:
    if not value_facts:
        return {
            "MCP access": 1 if oauth_access_ready else 0,
            "ranking facts": 0,
            "GBP facts": 0,
        }
    return {
        "miejsca": _numeric_fact(value_facts, "localo_active_place_count"),
        "frazy": _numeric_fact(value_facts, "localo_tracked_keyword_count"),
        "widoczność": _numeric_fact(value_facts, "localo_avg_visibility_current"),
        "recenzje": _numeric_fact(value_facts, "localo_reviews_count"),
    }


def _numeric_fact(value_facts: list[MetricFact], name: str) -> int | float:
    for fact in value_facts:
        if fact.name != name or not isinstance(fact.value, int | float):
            continue
        if isinstance(fact.value, float) and fact.value.is_integer():
            return int(fact.value)
        return round(float(fact.value), 4) if isinstance(fact.value, float) else fact.value
    return 0


def _first_blocked_section(sections: Iterable[Any]) -> Any | None:
    for section in sections:
        if getattr(section, "status", None) == "blocked":
            return section
    return None


def _limited_ids(values: list[str], limit: int = 12) -> list[str]:
    return values[:limit]


def _action_ids_for(
    actions: list[ActionObject],
    *,
    connector: str,
    domain: OpportunityDomain | None = None,
) -> list[str]:
    return _unique(
        action.id
        for action in actions
        if action.connector == connector or (domain is not None and action.domain == domain)
    )


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _primary_next_step(items: list[CommandCenterBriefItem]) -> str:
    for item in items:
        if item.id == "daily_merchant_feed" and item.status == "ready":
            return "Najpierw otwórz /merchant i przejrzyj kolejkę problemów feedu."
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
        issue_count = item.metric_tiles.get("zgłoszenia", item.metric_tiles.get("issues", 0))
        return CommandCenterActionPlanItem(
            id="plan_review_merchant_feed_issues",
            title="Przejrzyj kolejkę problemów Merchant Center",
            route=item.route,
            status=_action_plan_status(item),
            priority=10,
            category="Merchant Center",
            why_it_matters=(
                f"WILQ widzi {item.metric_tiles.get('produkty', 0)} produktów i "
                f"{issue_count} zgłoszeń problemów feedu. To może blokować "
                "widoczność produktów, ale wymaga ręcznego review przed zmianami."
            ),
            operator_action=(
                "Otwórz /merchant, sprawdź kolejkę problemów i waliduj ActionObject."
            ),
            skill_id="wilq-merchant-feed-operator",
            codex_prompt=(
                "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center "
                "dla Ekologus, pogrupuj problemy feedu, wskaż najbezpieczniejszą "
                "kolejkę review i nie twierdź, że approval albo revenue zostały odzyskane."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski brief przeglądu problemów feedu z evidence IDs, ActionObject "
                "i blockerami claimów."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_content_queue":
        return CommandCenterActionPlanItem(
            id="plan_prepare_content_refresh_queue",
            title="Przejrzyj kolejkę SEO z GSC i WordPress",
            route=item.route,
            status=_action_plan_status(item),
            priority=12,
            category="Content + SEO",
            why_it_matters=(
                f"{item.summary} Pełny drilldown query/page i URL jest w /content-planner."
            ),
            operator_action=item.next_step,
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
        landing_groups = item.metric_tiles.get("grupy ruchu", 0)
        decision_count = item.metric_tiles.get("decyzje", 0)
        measurement_count = item.metric_tiles.get("pomiar", 0)
        traffic_review_count = item.metric_tiles.get("jakość ruchu", 0)
        return CommandCenterActionPlanItem(
            id="plan_review_ga4_landing_quality",
            title=item.title,
            route=item.route,
            status=_action_plan_status(item),
            priority=14,
            category="GA4",
            why_it_matters=(
                f"WILQ ma {landing_groups} grup landing/source/campaign i "
                f"{decision_count} decyzji GA4 do review: pomiar={measurement_count}, "
                f"jakość ruchu={traffic_review_count}. To jest kolejka analityczna, "
                "nie werdykt performance, bo ROAS/revenue/conversion drop/tracking "
                "fixed pozostają zablokowane bez osobnych kontraktów."
            ),
            operator_action=(
                "Otwórz /ga4, przejdź przez kolejkę decyzji pomiaru i jakości "
                "ruchu, a potem waliduj `act_review_ga4_tracking_quality` jako "
                "review-only. Nie wdrażaj zmian ani nie oceniaj opłacalności."
            ),
            skill_id="wilq-ga4-analyst",
            codex_prompt=(
                "Użyj skilla wilq-ga4-analyst. Sprawdź jakość ruchu Ekologus po "
                "landing/source/campaign z /api/ga4/diagnostics decision_queue, "
                "rozdziel problem marketingowy od problemu pomiaru i nie wyciągaj "
                "wniosków o ROAS, revenue ani konwersjach bez dowodów."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polska diagnoza GA4 z landing/source/campaign facts, tracking "
                "blockerami i ActionObject."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_ads_business_context":
        return CommandCenterActionPlanItem(
            id="plan_ads_business_context_before_budget_decisions",
            title="Uzupełnij kontekst biznesowy Ads przed decyzjami budżetowymi",
            route=item.route,
            status="blocked",
            priority=18,
            category="Google Ads",
            why_it_matters=(
                "Ads ma live metryki i kolejki review, ale bez marży, celu biznesowego, "
                "celu budżetu oraz targetu ROAS albo CPA WILQ nie może uczciwie mówić "
                "o rentowności, zmarnowanym budżecie ani skalowaniu."
            ),
            operator_action=item.next_step,
            skill_id="wilq-ads-doctor",
            codex_prompt=(
                "Użyj skilla wilq-ads-doctor. Wyjaśnij blocker kontekstu biznesowego "
                "Ads dla Ekologus, wskaż brakujące pola .env i nie twierdź "
                "rentowności, zmarnowanego budżetu ani skalowania budżetu bez tych danych."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski blocker handoff Ads z brakującymi polami kontekstu biznesowego, "
                "evidence IDs i listą claimów, których nie wolno dopowiadać."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=item.risk,
        )
    if item.id == "daily_ads_status":
        if item.status == "ready":
            return CommandCenterActionPlanItem(
                id="plan_review_ads_campaign_metrics",
                title="Przejrzyj kolejki Ads do oceny bez apply",
                route=item.route,
                status="ready",
                priority=16,
                category="Google Ads",
                why_it_matters=(
                    f"{item.summary} Marketer ma tu decyzje do oceny, a nie listę "
                    "connectorów: budżet, rekomendacje, wykluczenia i segmenty mają "
                    "evidence oraz ActionObjecty, ale apply pozostaje zablokowany."
                ),
                operator_action=(
                    "Otwórz /ads-doctor i przejrzyj kolejno: podgląd budżetów, "
                    "podgląd rekomendacji, przegląd wykluczeń i podgląd segmentów. "
                    "Waliduj ActionObjecty, ale nie wdrażaj zmian."
                ),
                skill_id="wilq-ads-doctor",
                codex_prompt=(
                    "Użyj skilla wilq-ads-doctor. Przejrzyj Google Ads dla Ekologus "
                    "jako kolejkę oceny: budżety, rekomendacje, zapytania wyszukiwane, "
                    "wykluczenia i segmenty niestandardowe. Cytuj evidence IDs i "
                    "ActionObject IDs. Nie twierdź opłacalności, zmarnowanego budżetu "
                    "ani wdrożenia zmian; wskaż tylko bezpieczne decyzje tylko do "
                    "oceny i brakujące kontrakty."
                ),
                codex_context_endpoint="/api/codex/context-pack",
                expected_codex_output=(
                    "Polska kolejka oceny Ads z evidence IDs, ActionObjectami, "
                    "zablokowanymi claimami i następnymi krokami bez apply."
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
    if item.id == "daily_localo_visibility_facts":
        return CommandCenterActionPlanItem(
            id="plan_review_localo_visibility_facts",
            title="Przejrzyj agregaty widoczności lokalnej z Localo",
            route=item.route,
            status="ready",
            priority=20,
            category="Localo",
            why_it_matters=(
                "Localo ma read-only agregaty miejsc, fraz i recenzji. To pozwala "
                "zrobić review lokalnej widoczności, ale WILQ nadal blokuje claimy "
                "o GBP, konkurencji i wzroście widoczności bez osobnych kontraktów."
            ),
            operator_action=(
                "Otwórz /localo i przejrzyj tylko agregaty widoczne w evidence. "
                "Nie twierdź nic o GBP performance, konkurencji ani wzroście widoczności."
            ),
            skill_id="wilq-localo-operator",
            codex_prompt=(
                "Użyj skilla wilq-localo-operator. Przejrzyj agregaty Localo dla "
                "Ekologus na podstawie WILQ API evidence i wskaż bezpieczne następne "
                "kroki. Nie twierdź nic o GBP, konkurencji ani wzroście widoczności "
                "bez osobnych kontraktów."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski Localo review z evidence IDs, agregatami i zablokowanymi claimami."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=ActionRisk.low,
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
    action_label = _action_count_label(item.action_ids)
    if item.id == "plan_review_ga4_landing_quality" and brief_item is not None:
        return (
            f"{brief_item.summary} Źródła={connector_labels}, "
            f"dowody={evidence_label}, akcje={action_label}."
        )
    if item.id == "plan_ads_business_context_before_budget_decisions" and brief_item is not None:
        return (
            f"{brief_item.summary} Źródła={connector_labels}, "
            f"dowody={evidence_label}, akcje={action_label}."
        )
    metric_sentence = ""
    if brief_item and brief_item.metric_tiles:
        metric_sentence = _metric_tiles_sentence(brief_item.metric_tiles) + ". "
    return (
        f"{item.category}: {metric_sentence}Źródła={connector_labels}, "
        f"dowody={evidence_label}, akcje={action_label}."
    )


def _metric_tiles_sentence(metric_tiles: dict[str, float | int | str]) -> str:
    return ", ".join(f"{label}={value}" for label, value in metric_tiles.items())


def _action_count_label(action_ids: list[str]) -> str:
    if not action_ids:
        return "brak ActionObject"
    if len(action_ids) == 1:
        return "1 ActionObject"
    return f"{len(action_ids)} ActionObjects"


def _merge_ids(base_ids: list[str], tactical_items: list[Any], limit: int = 12) -> list[str]:
    merged = list(base_ids)
    for tactic in tactical_items:
        for evidence_id in tactic.evidence_ids:
            if evidence_id not in merged:
                merged.append(evidence_id)
    return merged[:limit]


__all__ = ["STRICT_BRIEF_INSTRUCTION", "build_command_center_brief", "tactical_item_count"]
