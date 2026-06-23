from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from wilq.actions.google_ads.business_context import ADS_BUSINESS_CONTEXT_ACTION_ID
from wilq.actions.google_ads.campaign_review import CAMPAIGN_REVIEW_ACTION_ID
from wilq.actions.google_ads.custom_segments import CUSTOM_SEGMENT_ACTION_ID
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.negative_keywords import NEGATIVE_KEYWORD_ACTION_ID
from wilq.actions.google_ads.recommendations import RECOMMENDATION_REVIEW_ACTION_ID
from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorSummary,
    DailyDecision,
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
GOOGLE_ADS_CONNECTOR_ID = "google_ads"
GOOGLE_MERCHANT_CONNECTOR_ID = "google_merchant_center"
AHREFS_CONNECTOR_ID = "ahrefs"
GA4_COMMAND_CENTER_DECISION_LIMIT = 6
GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT = 1200
MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT = 2000
GA4_COMMAND_CENTER_METRIC_FACT_LIMIT = 2000
AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT = 400
LOCALO_PROBE_METRIC_NAMES = {
    "access_token_present",
    "api",
    "authorization_code_supported",
    "mcp_initialize_status",
    "pkce_s256_supported",
}
PRIMARY_DAILY_PLAN_IDS = {
    "plan_review_merchant_feed_issues",
    "plan_prepare_content_refresh_queue",
    "plan_review_ga4_landing_quality",
    "plan_review_ads_campaign_metrics",
    "plan_fix_ads_oauth_before_spend_analysis",
}
CONFIGURE_GOOGLE_ADS_ACTION_ID = "act_configure_google_ads_env"


def build_command_center_response(
    connectors: list[ConnectorStatus] | None = None,
    tactical_queue: TacticalQueueResponse | None = None,
    actions: list[ActionObject] | None = None,
) -> CommandCenterResponse:
    connectors = connectors if connectors is not None else list_connector_statuses()
    tactical_queue = tactical_queue if tactical_queue is not None else build_tactical_queue()
    actions = actions if actions is not None else _command_center_action_stubs()
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


def _command_center_action_stubs() -> list[ActionObject]:
    return [
        _command_center_action_stub(
            CONFIGURE_GOOGLE_ADS_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            CAMPAIGN_REVIEW_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            RECOMMENDATION_REVIEW_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            CUSTOM_SEGMENT_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            NEGATIVE_KEYWORD_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            ADS_BUSINESS_CONTEXT_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            "act_review_merchant_feed_issues",
            connector=GOOGLE_MERCHANT_CONNECTOR_ID,
            domain=OpportunityDomain.merchant,
        ),
        _command_center_action_stub(
            "act_review_ga4_tracking_quality",
            connector=GA4_CONNECTOR_ID,
            domain=OpportunityDomain.ga4,
        ),
        _command_center_action_stub(
            "act_prepare_content_refresh_queue",
            connector="wordpress_ekologus",
            domain=OpportunityDomain.content,
        ),
        _command_center_action_stub(
            LOCALO_VISIBILITY_REVIEW_ACTION_ID,
            connector="localo",
            domain=OpportunityDomain.localo,
        ),
    ]


def _command_center_action_stub(
    action_id: str,
    *,
    connector: str,
    domain: OpportunityDomain,
) -> ActionObject:
    return ActionObject(
        id=action_id,
        title=action_id,
        domain=domain,
        connector=connector,
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=[connector_evidence_id(connector)],
        human_diagnosis="Command Center lightweight action reference.",
        recommended_reason="Use dedicated route for full ActionObject payload.",
        payload={},
        validation_status="not_validated",
        created_by="command_center_stub",
    )


def build_command_center_brief(
    tactical_queue: TacticalQueueResponse | None = None,
    actions: list[ActionObject] | None = None,
) -> tuple[list[CommandCenterBriefItem], str, int]:
    tactical_queue = tactical_queue if tactical_queue is not None else build_tactical_queue()
    actions = actions if actions is not None else list_actions()
    facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
        {
            GOOGLE_ADS_CONNECTOR_ID: GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT,
            GOOGLE_MERCHANT_CONNECTOR_ID: MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT,
            GA4_CONNECTOR_ID: GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
            AHREFS_CONNECTOR_ID: AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT,
            "localo": 120,
        }
    )
    ads_facts = facts_by_connector.get(GOOGLE_ADS_CONNECTOR_ID, [])
    merchant_facts = facts_by_connector.get(GOOGLE_MERCHANT_CONNECTOR_ID, [])
    ga4_facts = facts_by_connector.get(GA4_CONNECTOR_ID, [])
    ahrefs_facts = facts_by_connector.get(AHREFS_CONNECTOR_ID, [])
    localo_facts = facts_by_connector.get("localo", [])
    localo = get_connector_status("localo")
    localo_runs = local_state_store().list_connector_refresh_runs("localo")
    items = [
        _ads_item_from_facts(ads_facts, actions),
        _merchant_item_from_tactical(tactical_queue.items, actions, merchant_facts),
        _content_item_from_tactical(tactical_queue, ahrefs_facts),
        _ga4_item_from_tactical(tactical_queue.items, actions, ga4_facts),
    ]
    ads_business_item = _ads_business_context_item_from_facts(ads_facts, actions)
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
        if plan_item.id in PRIMARY_DAILY_PLAN_IDS
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


def _ads_item_from_facts(
    facts: list[MetricFact],
    actions: list[ActionObject],
) -> CommandCenterBriefItem:
    latest_refresh = _latest_connector_refresh(GOOGLE_ADS_CONNECTOR_ID)
    latest_summary = latest_refresh.metric_summary if latest_refresh is not None else {}
    live_data_available = _refresh_has_live_data(latest_refresh) and (
        bool(facts) or bool(latest_summary)
    )
    campaign_count = _ads_campaign_count(facts)
    search_term_count = _ads_search_term_count(facts)
    budget_preview_count = _ads_distinct_dimension_count(facts, "budget_id")
    recommendation_count = _ads_recommendation_count(facts)
    review_term_count = _ads_review_search_term_count(facts)
    ads_action_ids = _action_ids_for(actions, connector=GOOGLE_ADS_CONNECTOR_ID)
    if live_data_available:
        action_ids = [
            action_id
            for action_id in ads_action_ids
            if action_id
            not in {
                ADS_BUSINESS_CONTEXT_ACTION_ID,
                KEYWORD_PLANNER_ACCESS_ACTION_ID,
                CONFIGURE_GOOGLE_ADS_ACTION_ID,
            }
        ]
    else:
        action_ids = [
            action_id
            for action_id in ads_action_ids
            if action_id == CONFIGURE_GOOGLE_ADS_ACTION_ID
        ]
    metric_tiles: dict[str, float | int | str] = {
        "kampanie": _summary_int_tile(latest_summary, ("row_count",), campaign_count),
        "zapytania": _summary_int_tile(
            latest_summary,
            ("search_term_row_count",),
            search_term_count,
        ),
        "kliknięcia": _summary_number_tile(
            latest_summary,
            "clicks",
            _sum_numeric_facts(facts, "clicks"),
        ),
        "wyświetlenia": _summary_number_tile(
            latest_summary,
            "impressions",
            _sum_numeric_facts(facts, "impressions"),
        ),
        "koszt": _ads_currency_tile_from_summary(
            latest_summary,
            facts,
            "cost_micros",
            divide_by_million=True,
        ),
        "konwersje": _summary_number_tile(
            latest_summary,
            "conversions",
            _sum_numeric_facts(facts, "conversions"),
        ),
        "wartość konw.": _ads_currency_tile_from_summary(
            latest_summary,
            facts,
            "conversion_value",
        ),
        "podgląd budżetu": _summary_int_tile(
            latest_summary,
            ("budgeted_campaign_count", "recommended_budget_count"),
            budget_preview_count,
        ),
        "rekomendacje": _summary_int_tile(
            latest_summary,
            ("recommendation_row_count", "recommendation_campaign_count"),
            recommendation_count,
        ),
        "wykluczenia": review_term_count,
        "segmenty": review_term_count,
    }
    return CommandCenterBriefItem(
        id="daily_ads_status",
        title=(
            "Ads: kolejki budżetu, rekomendacji i zapytań"
            if live_data_available
            else "Ads: blocker OAuth przed analizą spendu"
        ),
        route="/ads-doctor",
        status="ready" if live_data_available else "blocked",
        priority=16 if live_data_available else 5,
        summary=(
            _ads_ready_summary(metric_tiles)
            if live_data_available
            else "Google Ads nie ma live danych do Command Center."
        ),
        next_step=(
            _ads_ready_next_step(metric_tiles)
            if live_data_available
            else "Otwórz /ads-doctor i wykonaj bezpieczny repair path OAuth przez ActionObject."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            _unique(
                [
                    *(latest_refresh.evidence_ids if latest_refresh is not None else []),
                    *(fact.evidence_id for fact in facts),
                    connector_evidence_id(GOOGLE_ADS_CONNECTOR_ID),
                ]
            )
        ),
        action_ids=action_ids,
        metric_tiles=metric_tiles if live_data_available else {"blockery": 1},
        blocked_claims=(
            [
                "CPA",
                "ROAS",
                "search-term waste",
                "negative keyword apply",
                "budget apply",
                "recommendation apply",
                "profitability",
                "wasted budget",
            ]
            if live_data_available
            else ["spend", "CPA", "ROAS", "search terms", "wasted budget"]
        ),
        risk=ActionRisk.medium,
    )


def _ads_campaign_count(facts: list[MetricFact]) -> int:
    return len(
        {
            fact.dimensions.get("campaign_id")
            for fact in facts
            if fact.dimensions.get("campaign_id")
            and fact.name
            in {
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
                "budget_amount_micros",
            }
        }
    )


def _ads_search_term_count(facts: list[MetricFact]) -> int:
    return len(
        {
            fact.dimensions.get("search_term")
            for fact in facts
            if fact.dimensions.get("search_term") and fact.name.startswith("search_term_")
        }
    )


def _ads_distinct_dimension_count(facts: list[MetricFact], dimension: str) -> int:
    return len({fact.dimensions.get(dimension) for fact in facts if fact.dimensions.get(dimension)})


def _ads_recommendation_count(facts: list[MetricFact]) -> int:
    return _ads_distinct_dimension_count(facts, "recommendation_type")


def _ads_review_search_term_count(facts: list[MetricFact]) -> int:
    return len(
        {
            fact.dimensions.get("search_term")
            for fact in facts
            if fact.name in {"search_term_cost_micros", "search_term_90d_cost_micros"}
            and fact.dimensions.get("search_term")
            and isinstance(fact.value, int | float)
            and fact.value > 0
        }
    )


def _ads_currency_tile(
    facts: list[MetricFact],
    metric_name: str,
    *,
    divide_by_million: bool = False,
) -> str:
    value = _sum_numeric_facts(facts, metric_name)
    amount = value / 1_000_000 if divide_by_million else value
    currency = _ads_currency_code(facts)
    amount_label = str(int(amount)) if amount.is_integer() else f"{amount:.2f}"
    return f"{amount_label} {currency}" if currency else amount_label


def _ads_currency_tile_from_summary(
    summary: dict[str, Any],
    facts: list[MetricFact],
    metric_name: str,
    *,
    divide_by_million: bool = False,
) -> str:
    value = _summary_numeric(summary, metric_name)
    if value is None:
        return _ads_currency_tile(facts, metric_name, divide_by_million=divide_by_million)
    amount = value / 1_000_000 if divide_by_million else value
    currency = _ads_summary_currency_code(summary) or _ads_currency_code(facts)
    amount_label = str(int(amount)) if amount.is_integer() else f"{amount:.2f}"
    return f"{amount_label} {currency}" if currency else amount_label


def _summary_int_tile(
    summary: dict[str, Any],
    keys: tuple[str, ...],
    fallback: int,
) -> int:
    for key in keys:
        value = _summary_numeric(summary, key)
        if value is not None:
            return int(value)
    return fallback


def _summary_number_tile(
    summary: dict[str, Any],
    key: str,
    fallback: float,
) -> int | float:
    value = _summary_numeric(summary, key)
    if value is None:
        value = fallback
    return int(value) if value.is_integer() else value


def _summary_numeric(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return None


def _ads_summary_currency_code(summary: dict[str, Any]) -> str | None:
    value = summary.get("customer_currency_code") or summary.get("account_currency_code")
    return value if isinstance(value, str) and value else None


def _ads_currency_code(facts: list[MetricFact]) -> str | None:
    for fact in facts:
        if fact.name in {"customer_currency_code", "account_currency_code"} and isinstance(
            fact.value, str
        ):
            return fact.value
    return None


def _ads_business_context_item_from_facts(
    facts: list[MetricFact],
    actions: list[ActionObject],
) -> CommandCenterBriefItem | None:
    latest_refresh = _latest_connector_refresh(GOOGLE_ADS_CONNECTOR_ID)
    if not (_refresh_has_live_data(latest_refresh) and facts):
        return None
    action_ids = [
        action_id
        for action_id in _action_ids_for(actions, connector=GOOGLE_ADS_CONNECTOR_ID)
        if action_id == ADS_BUSINESS_CONTEXT_ACTION_ID
    ]
    if not action_ids:
        return None
    return CommandCenterBriefItem(
        id="daily_ads_business_context",
        title="Ads: brakuje kontekstu biznesowego do decyzji budżetowych",
        route="/ads-doctor",
        status="blocked",
        priority=18,
        summary=(
            "Ads ma live evidence, ale WILQ nie ma kompletnego kontekstu "
            "biznesowego do decyzji budżetowych: marży, celu, target CPA/ROAS "
            "i potwierdzonego review strategii. Bez tego KPI są tylko triage, "
            "nie werdyktem opłacalności."
        ),
        next_step=(
            "Otwórz /ads-doctor i uzupełnij marżę, cel biznesowy, cel budżetu "
            "oraz target CPA/ROAS. Potem zwaliduj target guardrails i review "
            "strategii zanim ocenisz profitability albo skalowanie budżetu."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            _unique(
                [
                    *(latest_refresh.evidence_ids if latest_refresh is not None else []),
                    *(fact.evidence_id for fact in facts),
                    connector_evidence_id(GOOGLE_ADS_CONNECTOR_ID),
                ]
            )
        ),
        action_ids=action_ids,
        metric_tiles={
            "braki": 5,
            "marża": "brak",
            "cel biznesowy": "brak",
        },
        blocked_claims=[
            "profitability",
            "wasted budget",
            "budget scaling",
            "target CPA verdict",
            "target ROAS verdict",
        ],
        risk=ActionRisk.medium,
    )


def _merchant_item_from_tactical(
    tactical_items: list[TacticalQueueItem],
    actions: list[ActionObject],
    facts: list[MetricFact],
) -> CommandCenterBriefItem:
    latest_refresh = _latest_connector_refresh(GOOGLE_MERCHANT_CONNECTOR_ID)
    facts = _facts_for_latest_refresh(latest_refresh, facts)
    merchant_items = [
        item for item in tactical_items if item.domain == OpportunityDomain.merchant
    ]
    has_current_issue_facts = any(
        fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
        for fact in facts
    )
    merchant_items = (
        []
        if has_current_issue_facts
        else _tactical_items_for_latest_refresh(latest_refresh, merchant_items)
    )
    product_count = int(_first_numeric_fact(facts, "total_products"))
    issue_type_count = _merchant_issue_type_count(facts)
    issue_occurrence_count = int(_sum_numeric_facts(facts, "issue_product_count"))
    issue_cluster_count = _merchant_issue_cluster_count(facts)
    decision_count = max(len(merchant_items), min(issue_cluster_count, 8))
    live_data_available = bool(merchant_items or issue_occurrence_count)
    action_ids = _unique(
        [
            *(
                action_id
                for item in merchant_items
                for action_id in item.action_ids
            ),
            *_action_ids_for(actions, connector=GOOGLE_MERCHANT_CONNECTOR_ID),
        ]
    )
    top_item = sorted(
        merchant_items,
        key=lambda item: (_risk_rank(item.risk), -_merchant_item_product_count(item), item.id),
    )[0] if merchant_items else None
    summary = (
        f"Produkty={product_count}, typy problemów={issue_type_count}, "
        f"zgłoszenia={issue_occurrence_count}, decyzje={decision_count}. "
        f"Najważniejsza decyzja: {top_item.title}."
        if top_item is not None
        else (
            f"Produkty={product_count}, typy problemów={issue_type_count}, "
            f"zgłoszenia={issue_occurrence_count}, decyzje={decision_count}."
            if live_data_available
            else "Merchant nie ma gotowej kolejki decyzji z aktualnych metric facts."
        )
    )
    return CommandCenterBriefItem(
        id="daily_merchant_feed",
        title="Merchant: kolejka problemów feedu",
        route="/merchant",
        status="ready" if live_data_available else "blocked",
        priority=10 if live_data_available and issue_occurrence_count > 0 else 35,
        summary=(
            f"{summary} To jest read-only queue, nie automatyczna naprawa feedu."
            if live_data_available
            else summary
        ),
        next_step=(
            "Otwórz /merchant i przejrzyj decyzje feedu przed walidacją ActionObject."
            if live_data_available
            else "Uruchom read-only Merchant vendor_read, potem wróć do /merchant."
        ),
        source_connectors=[GOOGLE_MERCHANT_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            _unique(
                [
                    *(evidence_id for item in merchant_items for evidence_id in item.evidence_ids),
                    *(fact.evidence_id for fact in facts),
                    connector_evidence_id(GOOGLE_MERCHANT_CONNECTOR_ID),
                ]
            )
        ),
        action_ids=action_ids,
        metric_tiles={
            "produkty": product_count,
            "typy problemów": issue_type_count,
            "zgłoszenia": issue_occurrence_count,
            "decyzje": decision_count,
            "blockery": 0 if live_data_available else 1,
        },
        blocked_claims=_unique(
            claim for item in merchant_items for claim in item.blocked_claims
        )
        or ["approval restored", "revenue recovered", "automatic feed edit"],
        risk=ActionRisk.medium,
    )


def _latest_connector_refresh(connector_id: str) -> ConnectorRefreshRun | None:
    runs = local_state_store().list_connector_refresh_runs(connector_id)
    return runs[0] if runs else None


def _facts_for_latest_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> list[MetricFact]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return facts
    evidence_ids = set(latest_refresh.evidence_ids)
    current_facts = [fact for fact in facts if fact.evidence_id in evidence_ids]
    return current_facts or facts


def _tactical_items_for_latest_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    items: list[TacticalQueueItem],
) -> list[TacticalQueueItem]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return items
    evidence_ids = set(latest_refresh.evidence_ids)
    current_items = [
        item
        for item in items
        if any(evidence_id in evidence_ids for evidence_id in item.evidence_ids)
    ]
    return current_items


def _refresh_has_live_data(run: ConnectorRefreshRun | None) -> bool:
    return (
        run is not None
        and run.status == ConnectorRefreshStatus.completed
        and run.vendor_data_collected
    )


def _first_numeric_fact(facts: list[MetricFact], name: str) -> float:
    for fact in facts:
        if fact.name == name and isinstance(fact.value, int | float):
            return float(fact.value)
    return 0.0


def _sum_numeric_facts(facts: list[MetricFact], name: str) -> float:
    return sum(
        float(fact.value)
        for fact in facts
        if fact.name == name and isinstance(fact.value, int | float)
    )


def _merchant_issue_type_count(facts: list[MetricFact]) -> int:
    issue_keys = {
        (
            fact.dimensions.get("issue_type", ""),
            fact.dimensions.get("affected_attribute", ""),
            fact.dimensions.get("country", ""),
        )
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions
    }
    return len(issue_keys)


def _merchant_issue_cluster_count(facts: list[MetricFact]) -> int:
    issue_keys = {
        (
            fact.dimensions.get("issue_type", ""),
            fact.dimensions.get("affected_attribute", ""),
            fact.dimensions.get("country", ""),
            fact.dimensions.get("severity", "UNKNOWN"),
            fact.dimensions.get("resolution", ""),
        )
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
    }
    return len(issue_keys)


def _merchant_item_product_count(item: TacticalQueueItem) -> float:
    for fact in item.metric_facts:
        if fact.name == "issue_product_count" and isinstance(fact.value, int | float):
            return float(fact.value)
    return 0.0


def _content_item_from_tactical(
    queue: TacticalQueueResponse,
    ahrefs_facts: list[MetricFact],
) -> CommandCenterBriefItem:
    content_groups = [
        group
        for group in queue.compact_groups
        if group.source_connectors and "google_search_console" in group.source_connectors
    ]
    content_items = [
        item for item in queue.items if item.domain == OpportunityDomain.gsc_seo
    ]
    latest_ahrefs_refresh = _latest_connector_refresh(AHREFS_CONNECTOR_ID)
    ahrefs_facts = _facts_for_latest_refresh(latest_ahrefs_refresh, ahrefs_facts)
    ahrefs_gap_facts = _ahrefs_gap_facts(ahrefs_facts)
    ahrefs_metric_tiles = _ahrefs_content_metric_tiles(ahrefs_gap_facts)
    ahrefs_available = bool(ahrefs_gap_facts)
    live_data_available = bool(content_items)
    content_decision_count = len(content_groups) or len(content_items)
    decision_count = content_decision_count + (1 if ahrefs_available else 0)
    top_group = content_groups[0] if content_groups else None
    top_item = content_items[0] if content_items else None
    total_clicks = _sum_tactical_metric(content_items, "clicks")
    total_impressions = _sum_tactical_metric(content_items, "impressions")
    tactical_summary = (
        _content_tactical_summary(top_item, top_group.diagnosis)
        if top_group is not None
        else (
            _content_tactical_summary(top_item, "")
            if top_item is not None
            else (
                "Brak gotowej kolejki contentowej. WILQ potrzebuje GSC query/page "
                "i WordPress inventory."
            )
        )
    )
    summary = _content_summary_with_ahrefs(tactical_summary, ahrefs_metric_tiles)
    next_step = (
        top_group.next_step
        if top_group is not None
        else "Otwórz /content-planner i odśwież GSC oraz WordPress inventory."
    )
    source_connectors = [
        *(
            [AHREFS_CONNECTOR_ID]
            if ahrefs_available
            else []
        ),
        "google_search_console",
        "wordpress_ekologus",
        "wordpress_sklep",
    ]
    evidence_ids = _limited_ids(
        _unique(
            [
                *(fact.evidence_id for fact in ahrefs_gap_facts),
                *(evidence_id for item in content_items for evidence_id in item.evidence_ids),
            ]
        )
        or [connector_evidence_id("google_search_console")]
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
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        action_ids=_unique(action_id for item in content_items for action_id in item.action_ids),
        metric_tiles={
            "query/page": len(content_items),
            "WP match": sum(
                1 for item in content_items if item.dimensions.get("wordpress_match") == "found"
            ),
            "decyzje": decision_count,
            "wyświetlenia": total_impressions,
            "kliknięcia": total_clicks,
            **ahrefs_metric_tiles,
            "blockery": 0 if live_data_available else 1,
        },
        blocked_claims=_unique(
            claim for item in content_items for claim in item.blocked_claims
        )
        or ["lead uplift", "revenue impact", "ranking guarantee"],
        risk=ActionRisk.low if live_data_available else ActionRisk.medium,
    )


def _ahrefs_gap_facts(facts: list[MetricFact]) -> list[MetricFact]:
    gap_fact_names = {
        "ahrefs_content_gap_count",
        "ahrefs_organic_keyword_gap_count",
        "ahrefs_top_page_gap_count",
        "ahrefs_competitor_page_count",
        "ahrefs_referring_domain_gap_count",
        "ahrefs_backlink_gap_count",
    }
    record_facts = [
        fact
        for fact in facts
        if fact.source_connector == AHREFS_CONNECTOR_ID
        and fact.name in gap_fact_names
        and any(
            fact.dimensions.get(key)
            for key in (
                "gap_type",
                "keyword",
                "source_url",
                "target_url",
                "competitor_domain",
            )
        )
    ]
    if record_facts:
        return record_facts
    return [
        fact
        for fact in facts
        if fact.source_connector == AHREFS_CONNECTOR_ID and fact.name in gap_fact_names
    ]


def _ahrefs_content_metric_tiles(facts: list[MetricFact]) -> dict[str, int]:
    if not facts:
        return {}
    content_gap_count = sum(
        1
        for fact in facts
        if fact.name == "ahrefs_content_gap_count"
        or fact.dimensions.get("gap_type") == "content_gap"
    )
    backlink_gap_count = sum(
        1
        for fact in facts
        if fact.name in {"ahrefs_backlink_gap_count", "ahrefs_referring_domain_gap_count"}
        or fact.dimensions.get("gap_type") == "backlink_gap"
    )
    tiles = {
        "Ahrefs review": 1,
        "rekordy Ahrefs": len(facts),
    }
    if content_gap_count:
        tiles["luki Ahrefs"] = content_gap_count
    if backlink_gap_count:
        tiles["link gaps"] = backlink_gap_count
    return tiles


def _content_summary_with_ahrefs(
    tactical_summary: str,
    ahrefs_metric_tiles: dict[str, int],
) -> str:
    if not ahrefs_metric_tiles:
        return tactical_summary
    ahrefs_summary = (
        "Ahrefs ma kolejkę review luk SEO: "
        f"rekordy={ahrefs_metric_tiles.get('rekordy Ahrefs', 0)}, "
        f"content gaps={ahrefs_metric_tiles.get('luki Ahrefs', 0)}, "
        f"backlink gaps={ahrefs_metric_tiles.get('link gaps', 0)}. "
        "To jest materiał do połączenia z GSC/WordPress, nie obietnica wzrostu."
    )
    return f"{ahrefs_summary} {tactical_summary}".strip()


def _content_tactical_summary(
    item: TacticalQueueItem | None,
    fallback_summary: str,
) -> str:
    if item is None:
        return fallback_summary
    if item.dimensions.get("wordpress_match") == "found":
        return (
            f"{fallback_summary} WordPress potwierdza istniejącą stronę; "
            "to jest kandydat do refresh/merge, nie tworzenia duplikatu."
        ).strip()
    if item.diagnosis:
        return item.diagnosis
    return fallback_summary


def _sum_tactical_metric(items: list[TacticalQueueItem], name: str) -> int | float:
    total = sum(
        float(fact.value)
        for item in items
        for fact in item.metric_facts
        if fact.name == name and isinstance(fact.value, int | float)
    )
    return int(total) if total.is_integer() else total


def _ads_ready_summary(metric_tiles: dict[str, float | int | str]) -> str:
    return (
        "Google Ads ma aktualny odczyt do oceny: "
        f"kampanie={metric_tiles.get('kampanie', 0)}, "
        f"zapytania={metric_tiles.get('zapytania', 0)}, "
        f"kliknięcia={metric_tiles.get('kliknięcia', 0)}, "
        f"koszt={metric_tiles.get('koszt', 'brak')}, "
        f"konwersje={metric_tiles.get('konwersje', 0)}, "
        f"wartość konw.={metric_tiles.get('wartość konw.', 'brak')}, "
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


def _ga4_item_from_tactical(
    tactical_items: list[TacticalQueueItem],
    actions: list[ActionObject],
    ga4_facts: list[MetricFact],
) -> CommandCenterBriefItem:
    ga4_items = [item for item in tactical_items if item.domain == OpportunityDomain.ga4]
    dimensioned_facts = _dimensioned_ga4_facts(ga4_facts)
    landing_group_count = max(len(ga4_items), _ga4_landing_group_count(dimensioned_facts))
    measurement_issue_count = max(
        sum(1 for item in ga4_items if item.intent == "tracking_gap"),
        _ga4_measurement_issue_count(dimensioned_facts),
    )
    decision_count = min(
        max(len(ga4_items), landing_group_count),
        GA4_COMMAND_CENTER_DECISION_LIMIT,
    )
    traffic_quality_count = max(
        sum(1 for item in ga4_items if item.intent == "landing_page_quality"),
        _ga4_traffic_quality_count(dimensioned_facts),
    )
    measurement_issue_count = min(measurement_issue_count, decision_count)
    traffic_quality_count = min(
        traffic_quality_count,
        max(decision_count - measurement_issue_count, 0),
    )
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
            f"{measurement_issue_count} problemów pomiaru, "
            f"{traffic_quality_count} decyzji jakości ruchu i "
            f"{len(matched_items)} dopasowań WordPress. "
            "Status blocked oznacza brak kontraktu na ROAS/revenue/conversion "
            "drop/tracking fixed, nie awarię connectora."
        ),
        next_step=(
            "Otwórz /ga4, sprawdź kolejkę jakości ruchu i waliduj review GA4 "
            "jako ActionObject."
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
            "decyzje": decision_count,
            "pomiar": measurement_issue_count,
            "jakość ruchu": traffic_quality_count,
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
    return len(_ga4_landing_group_keys(facts))


def _ga4_measurement_issue_count(facts: Iterable[MetricFact]) -> int:
    return sum(
        1
        for landing_page, source_medium, campaign_name in _ga4_landing_group_keys(facts)
        if "(not set)" in {landing_page, source_medium, campaign_name}
    )


def _ga4_traffic_quality_count(facts: Iterable[MetricFact]) -> int:
    return sum(
        1
        for landing_page, source_medium, campaign_name in _ga4_landing_group_keys(facts)
        if "(not set)" not in {landing_page, source_medium, campaign_name}
    )


def _ga4_landing_group_keys(facts: Iterable[MetricFact]) -> set[tuple[str, str, str]]:
    return {
        (
            fact.dimensions.get("landing_page", ""),
            fact.dimensions.get("source_medium", ""),
            fact.dimensions.get("campaign_name", ""),
        )
        for fact in facts
    }


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
        action_ids=[LOCALO_VISIBILITY_REVIEW_ACTION_ID] if has_value_facts else [],
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
        evidence_ids = set(run.evidence_ids)
        batched_facts = [fact for fact in fallback_facts if fact.evidence_id in evidence_ids]
        if batched_facts:
            return batched_facts
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
                "ruchu, a potem waliduj review GA4 jako ActionObject review-only. "
                "Nie wdrażaj zmian ani nie oceniaj opłacalności."
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
                title="Przejrzyj aktualny odczyt Ads bez apply",
                route=item.route,
                status="ready",
                priority=16,
                category="Google Ads",
                why_it_matters=(
                    f"{item.summary} To jest aktualny odczyt Ads i zestaw decyzji do "
                    "review, a nie lista connectorów ani ścieżka apply: budżet, "
                    "rekomendacje, wykluczenia i segmenty mają evidence oraz "
                    "ActionObjecty, ale wdrożenie pozostaje zablokowane."
                ),
                operator_action=(
                    "Otwórz /ads-doctor: aktualny odczyt wartości Ads jest na górze, "
                    "a potem przejrzyj: podgląd budżetów, podgląd rekomendacji, "
                    "przegląd wykluczeń i podgląd segmentów. "
                    "Waliduj ActionObjecty, ale nie wdrażaj zmian."
                ),
                skill_id="wilq-ads-doctor",
                codex_prompt=(
                    "Użyj skilla wilq-ads-doctor. Przejrzyj aktualny odczyt Google "
                    "Ads dla Ekologus oraz kolejkę oceny: budżety, rekomendacje, "
                    "zapytania wyszukiwane, wykluczenia i segmenty niestandardowe. "
                    "Cytuj evidence IDs i "
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
    if item.id == "plan_review_merchant_feed_issues" and brief_item is not None:
        return _decision_metric_observation(
            prefix="Merchant Center ma",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To jest kolejka ręcznego review feedu; WILQ nie twierdzi, że "
                "approval, przychód albo dane produktu zostały już naprawione."
            ),
        )
    if item.id == "plan_prepare_content_refresh_queue" and brief_item is not None:
        return _decision_metric_observation(
            prefix="GSC i WordPress tworzą kolejkę SEO:",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To jest decyzja refresh/merge/create/block oparta o query/page "
                "i inventory, nie obietnica leadów ani wzrostów pozycji."
            ),
        )
    if item.id == "plan_review_ga4_landing_quality" and brief_item is not None:
        if "Status blocked oznacza" in brief_item.summary:
            return brief_item.summary
        return (
            f"{brief_item.summary} Status blocked oznacza brak kontraktu na "
            "ROAS/revenue/conversion drop/tracking fixed, nie awarię connectora."
        )
    if item.id == "plan_ads_business_context_before_budget_decisions" and brief_item is not None:
        return (
            f"{brief_item.summary} To blocker target-aware decyzji, nie awaria "
            "Google Ads ani brak live campaign facts."
        )
    if item.id == "plan_review_ads_campaign_metrics" and brief_item is not None:
        return _decision_metric_observation(
            prefix="Google Ads ma kolejki do oceny:",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To są read-only kolejki budżetu, rekomendacji, wykluczeń i "
                "segmentów. Wdrożenie zmian, ocena rentowności i werdykty o "
                "przepalonym budżecie pozostają zablokowane."
            ),
        )
    if item.id == "plan_review_localo_visibility_facts" and brief_item is not None:
        return _decision_metric_observation(
            prefix="Localo ma read-only agregaty:",
            metric_tiles=brief_item.metric_tiles,
            suffix=(
                "To pozwala zrobić ostrożny przegląd lokalnej widoczności, ale "
                "GBP, konkurencja i uplift nadal wymagają osobnych kontraktów."
            ),
        )
    metric_sentence = ""
    if brief_item and brief_item.metric_tiles:
        metric_sentence = _metric_tiles_sentence(brief_item.metric_tiles) + ". "
    return f"{item.category}: {metric_sentence}{item.why_it_matters}"


def _decision_metric_observation(
    *,
    prefix: str,
    metric_tiles: dict[str, float | int | str],
    suffix: str,
) -> str:
    metric_sentence = _metric_tiles_sentence(metric_tiles)
    if metric_sentence:
        return f"{prefix} {metric_sentence}. {suffix}"
    return suffix


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
