from __future__ import annotations

from wilq.actions.service import list_actions
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.schemas import (
    ActionObject,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorRefreshRun,
    ConnectorStatus,
    ConnectorSummary,
    MetricFact,
    TacticalQueueResponse,
)
from wilq.storage.metric_store import metric_store

from .actions import (
    _command_center_action_stubs,
    build_command_center_action_plan,
)
from .daily_check import (
    build_daily_decisions,
)
from .metrics import (
    command_center_metric_fact_limits,
)
from .shared import (
    AHREFS_CONNECTOR_ID,
    GA4_CONNECTOR_ID,
    GOOGLE_ADS_CONNECTOR_ID,
    GOOGLE_MERCHANT_CONNECTOR_ID,
    STRICT_DAILY_INSTRUCTION,
    _latest_refresh_runs_by_connector,
    _refresh_runs_for_connector,
)
from .tactical_queue import (
    _ads_business_context_item_from_facts,
    _ads_item_from_facts,
    _content_item_from_tactical,
    _ga4_item_from_tactical,
    _localo_item,
    _merchant_item_from_tactical,
)


def build_command_center_response(
    connectors: list[ConnectorStatus] | None = None,
    tactical_queue: TacticalQueueResponse | None = None,
    actions: list[ActionObject] | None = None,
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
    refresh_runs: list[ConnectorRefreshRun] | None = None,
) -> CommandCenterResponse:
    connectors = connectors if connectors is not None else list_connector_statuses()
    if facts_by_connector is None:
        facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
            command_center_metric_fact_limits()
        )
    tactical_queue = (
        tactical_queue
        if tactical_queue is not None
        else build_tactical_queue(facts_by_connector=facts_by_connector)
    )
    actions = actions if actions is not None else _command_center_action_stubs()
    operator_brief, primary_next_step, blocker_count = build_command_center_brief(
        tactical_queue=tactical_queue,
        actions=actions,
        facts_by_connector=facts_by_connector,
        refresh_runs=refresh_runs,
    )
    operator_brief = _operator_brief_for_marketer(operator_brief)
    action_plan = build_command_center_action_plan(operator_brief, tactical_queue.items)
    return CommandCenterResponse(
        strict_instruction=STRICT_DAILY_INSTRUCTION,
        primary_next_step=primary_next_step,
        blocker_count=blocker_count,
        tactical_item_count=len(tactical_queue.items),
        daily_decisions=build_daily_decisions(
            action_plan,
            operator_brief,
            connectors=connectors,
            refresh_runs=refresh_runs,
            facts_by_connector=facts_by_connector,
        ),
        operator_brief=operator_brief,
        demo_script=[],
        action_plan=action_plan,
        connector_summary=_connector_summary(connectors),
        sections={},
        active_actions=[],
        connector_health=connectors,
        codex_operator_status=codex_runtime_status(),
    )


def _operator_brief_for_marketer(
    items: list[CommandCenterBriefItem],
) -> list[CommandCenterBriefItem]:
    return [
        item.model_copy(update={"blocked_claims": operator_blocked_claims(item.blocked_claims)})
        for item in items
    ]


def _connector_summary(connectors: list[ConnectorStatus]) -> ConnectorSummary:
    return ConnectorSummary(
        total=len(connectors),
        configured=sum(1 for connector in connectors if connector.configured),
        missing_credentials=sum(1 for connector in connectors if connector.missing_credentials),
    )


def build_command_center_brief(
    tactical_queue: TacticalQueueResponse | None = None,
    actions: list[ActionObject] | None = None,
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
    refresh_runs: list[ConnectorRefreshRun] | None = None,
) -> tuple[list[CommandCenterBriefItem], str, int]:
    tactical_queue = tactical_queue if tactical_queue is not None else build_tactical_queue()
    actions = actions if actions is not None else list_actions()
    if facts_by_connector is None:
        facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
            command_center_metric_fact_limits()
        )
    ads_facts = facts_by_connector.get(GOOGLE_ADS_CONNECTOR_ID, [])
    merchant_facts = facts_by_connector.get(GOOGLE_MERCHANT_CONNECTOR_ID, [])
    ga4_facts = facts_by_connector.get(GA4_CONNECTOR_ID, [])
    ahrefs_facts = facts_by_connector.get(AHREFS_CONNECTOR_ID, [])
    localo_facts = facts_by_connector.get("localo", [])
    refresh_runs_by_connector = _latest_refresh_runs_by_connector(refresh_runs)
    localo = get_connector_status("localo")
    localo_runs = _refresh_runs_for_connector("localo", refresh_runs)
    items = [
        _ads_item_from_facts(
            ads_facts,
            actions,
            latest_refresh=refresh_runs_by_connector.get(GOOGLE_ADS_CONNECTOR_ID),
            allow_refresh_lookup=refresh_runs is None,
        ),
        _merchant_item_from_tactical(
            tactical_queue.items,
            actions,
            merchant_facts,
            latest_refresh=refresh_runs_by_connector.get(GOOGLE_MERCHANT_CONNECTOR_ID),
            allow_refresh_lookup=refresh_runs is None,
        ),
        _content_item_from_tactical(
            tactical_queue,
            ahrefs_facts,
            actions,
            latest_ahrefs_refresh=refresh_runs_by_connector.get(AHREFS_CONNECTOR_ID),
            allow_refresh_lookup=refresh_runs is None,
        ),
        _ga4_item_from_tactical(tactical_queue.items, actions, ga4_facts),
    ]
    ads_business_item = _ads_business_context_item_from_facts(
        ads_facts,
        actions,
        latest_refresh=refresh_runs_by_connector.get(GOOGLE_ADS_CONNECTOR_ID),
        allow_refresh_lookup=refresh_runs is None,
    )
    if ads_business_item is not None:
        items.append(ads_business_item)
    if localo is not None:
        localo_item = _localo_item(localo, localo_runs, localo_facts)
        if localo_item.status == "blocked" or localo_item.id == "daily_localo_visibility_facts":
            items.append(localo_item)
    sorted_items = sorted(items, key=lambda item: item.priority)
    blocker_count = sum(1 for item in sorted_items if item.status == "blocked")
    return sorted_items, _primary_next_step(sorted_items), blocker_count


def _primary_next_step(items: list[CommandCenterBriefItem]) -> str:
    for item in items:
        if item.id == "daily_merchant_feed" and item.status == "ready":
            return (
                "Najpierw otwórz widok Merchant i przejrzyj kolejkę problemów pliku produktowego."
            )
    for item in items:
        if item.status == "ready":
            return item.next_step
    return "Najpierw usuń blokadę dostępu z najwyższym priorytetem."
