from __future__ import annotations

from datetime import date
from typing import Literal

from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.briefing.false_positive_guards import evaluate_source_trace_guard
from wilq.schemas import (
    ActionRisk,
    ConnectorStatus,
    DailyCheckConnectorRef,
    DailyCheckItem,
    DailyCheckResult,
    DailyDecision,
    FreshnessState,
)

WORKSPACE_ID = "ekologus"

_RULE_IDS_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "google_ads": ("ads_diagnostics_v1", "ads_platform_traps_v1"),
    "ga4": ("ga4_diagnostics_v1", "ga4_platform_traps_v1"),
    "merchant": ("merchant_feed_rules_v1", "merchant_platform_traps_v1"),
    "content": ("gsc_platform_traps_v1", "wordpress_platform_traps_v1"),
    "localo": ("local_visibility_v1",),
}


def build_daily_check(*, use_cache: bool = True) -> DailyCheckResult:
    """Compile the existing daily decision queue into a traceable operator result."""
    runtime = build_daily_runtime(use_cache=use_cache)
    connector_refs = _connector_refs(runtime.connectors)
    items = [_daily_item(decision) for decision in runtime.command_center.daily_decisions]
    safe_next_actions = [
        item for item in items if item.category == "safe_next_action" and item.status != "blocked"
    ]
    blocked = [
        item
        for item in items
        if item.category == "blocked_recommendation" or item.status == "blocked"
    ]
    do_not_touch = [_do_not_touch_item(items)] if any(item.blocked_claims for item in items) else []
    return DailyCheckResult(
        workspace_id=WORKSPACE_ID,
        date=date.today(),
        status=_result_status(safe_next_actions, blocked),
        checked_connectors=[ref for ref in connector_refs if ref.status == "checked"],
        skipped_connectors=[ref for ref in connector_refs if ref.status == "skipped"],
        opportunities=safe_next_actions,
        blocked_recommendations=blocked,
        safe_next_actions=safe_next_actions,
        do_not_touch=do_not_touch,
        freshness=_aggregate_freshness(connector_refs),
    )


def _connector_refs(connectors: list[ConnectorStatus]) -> list[DailyCheckConnectorRef]:
    return [
        DailyCheckConnectorRef(
            connector_id=connector.id,
            status=(
                "checked"
                if connector.configured and connector.status != "disabled"
                else "skipped"
            ),
            freshness=connector.freshness,
            reason=(
                "źródło sprawdzone w bieżącym przebiegu"
                if connector.configured and connector.status != "disabled"
                else "brak dostępu albo źródło wyłączone"
            ),
        )
        for connector in connectors
    ]


def _daily_item(decision: DailyDecision) -> DailyCheckItem:
    rule_ids = list(_RULE_IDS_BY_DOMAIN.get(decision.domain, ()))
    guard = evaluate_source_trace_guard(
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        expert_rule_ids=rule_ids,
        freshness=decision.freshness,
    )
    is_blocked = decision.status == "blocked" or guard.status == "blocked"
    category: Literal["blocked_recommendation", "safe_next_action"] = (
        "blocked_recommendation" if is_blocked else "safe_next_action"
    )
    status: Literal["blocked", "review_required"] = "blocked" if is_blocked else "review_required"
    summary = decision.co_widzimy
    next_step = decision.bezpieczny_next_step
    if guard.status == "blocked":
        summary = guard.reason
        next_step = guard.next_step
    return DailyCheckItem(
        id=f"daily_check_{decision.id}",
        category=category,
        title=decision.title,
        status=status,
        priority=decision.priority,
        summary=summary,
        next_step=next_step,
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        expert_rule_ids=rule_ids,
        freshness=decision.freshness,
        action_ids=decision.action_ids,
        blocked_claims=decision.blocked_claims,
        false_positive_guards=[guard.guard_id],
        risk=decision.risk,
    )


def _do_not_touch_item(items: list[DailyCheckItem]) -> DailyCheckItem:
    claims = sorted({claim for item in items for claim in item.blocked_claims})
    return DailyCheckItem(
        id="daily_check_do_not_touch_writes",
        category="do_not_touch",
        title="Nie zapisuj zmian bez potwierdzenia w WILQ",
        status="blocked",
        priority=1,
        summary="Brak dowodu i audytu nie jest zgodą na zapis ani publikację.",
        next_step=(
            "Pozostaw write/publish zablokowane i przejdź przez preview, review, "
            "confirm oraz audit."
        ),
        blocked_claims=claims,
        risk=ActionRisk.high,
    )


def _result_status(
    safe_next_actions: list[DailyCheckItem],
    blocked: list[DailyCheckItem],
) -> Literal["ready", "review_ready", "blocked", "degraded"]:
    if blocked:
        return "blocked"
    if safe_next_actions:
        return "review_ready"
    return "degraded"


def _aggregate_freshness(refs: list[DailyCheckConnectorRef]) -> FreshnessState:
    states = {ref.freshness.state for ref in refs if ref.status == "checked"}
    if "stale" in states:
        return FreshnessState(
            state="stale",
            notes="co najmniej jedno sprawdzone źródło wymaga odświeżenia",
        )
    if "fresh" in states:
        return FreshnessState(state="fresh")
    if "missing" in states:
        return FreshnessState(state="missing")
    return FreshnessState(state="unknown", notes="brak potwierdzonego odczytu")
