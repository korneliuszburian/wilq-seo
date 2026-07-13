from __future__ import annotations

from collections.abc import Callable
from typing import Any


def validate_command_center(
    command_center: Any,
    *,
    compact: bool = False,
    guardrail: Callable[[str], bool],
    core_operator_ids: set[str],
    forbidden_ready_ids: set[str],
) -> None:
    if not isinstance(command_center, dict):
        raise SystemExit("Command center is not an object")
    if not guardrail(str(command_center.get("strict_instruction", ""))):
        raise SystemExit("Instrukcja Centrum pracy nie zawiera zasad metryk i dowodów źródłowych")
    operator_brief = command_center.get("operator_brief") or []
    action_plan = command_center.get("action_plan") or []
    decisions = command_center.get("daily_decisions") or []
    _validate_counts(command_center, operator_brief, action_plan, decisions, compact)
    if not compact:
        _validate_operator_items(operator_brief, core_operator_ids, forbidden_ready_ids)
        _validate_plan_evidence(operator_brief, action_plan)
        _validate_plan_ids(action_plan, operator_brief)
    _validate_decisions(decisions)


def _validate_counts(
    center: dict[str, Any], operator_brief: Any, plan: Any, decisions: Any, compact: bool
) -> None:
    if not isinstance(center.get("blocker_count"), int) or not isinstance(
        center.get("tactical_item_count"), int
    ):
        raise SystemExit("Command center counts are missing or not numeric")
    if not center.get("primary_next_step") or not isinstance(center.get("demo_script") or [], list):
        raise SystemExit("Command center primary_next_step/demo_script is invalid")
    if not isinstance(decisions, list) or len(decisions) < 4 or len(decisions) > 4:
        raise SystemExit("Command center daily_decisions must contain exactly four focused items")
    if not compact and (not isinstance(plan, list) or len(plan) < 4):
        raise SystemExit("Command center action_plan is missing or too small")


def _validate_operator_items(
    items: list[Any], required: set[str], forbidden_ready: set[str]
) -> None:
    if not items:
        raise SystemExit("Command center has no operator_brief")
    ids = {str(item.get("id")) for item in items if isinstance(item, dict)}
    if missing := sorted(required - ids):
        raise SystemExit(f"Command center missing operator items: {', '.join(missing)}")
    leaked = [
        str(item.get("id"))
        for item in items
        if isinstance(item, dict)
        and item.get("id") in forbidden_ready
        and item.get("status") == "ready"
    ]
    if leaked:
        raise SystemExit("Command center promotes readiness-only item: " + ", ".join(leaked))


def _validate_plan_evidence(operator_brief: list[Any], plan: list[Any]) -> None:
    for item in [*operator_brief, *plan]:
        if not isinstance(item, dict):
            continue
        if not item.get("source_connectors") or not item.get("evidence_ids"):
            raise SystemExit(f"Command center item lacks evidence/source: {item.get('id')}")


def _validate_plan_ids(plan: list[Any], operator_brief: list[Any]) -> None:
    required = {
        "plan_review_merchant_feed_issues",
        "plan_prepare_content_refresh_queue",
        "plan_review_ga4_landing_quality",
    }
    ads_ready = any(
        isinstance(item, dict)
        and item.get("id") == "daily_ads_status"
        and item.get("status") == "ready"
        for item in operator_brief
    )
    required.add(
        "plan_review_ads_campaign_metrics"
        if ads_ready
        else "plan_fix_ads_oauth_before_spend_analysis"
    )
    ids = {item.get("id") for item in plan if isinstance(item, dict)}
    if missing := sorted(required - ids):
        raise SystemExit(f"Command center missing action_plan items: {', '.join(missing)}")


def _validate_decisions(decisions: list[Any]) -> None:
    required = {
        "plan_review_merchant_feed_issues",
        "plan_prepare_content_refresh_queue",
        "plan_review_ga4_landing_quality",
    }
    ids = {item.get("id") for item in decisions if isinstance(item, dict)}
    leaked = ids & {
        "decision_review_localo_visibility_facts",
        "decision_finish_localo_access_before_local_visibility",
    }
    if leaked:
        raise SystemExit(
            "Command center promoted non-core daily decisions: " + ", ".join(sorted(leaked))
        )
    expected = {item.replace("plan_", "decision_", 1) for item in required}
    if missing := sorted(expected - ids):
        raise SystemExit(f"Command center missing daily_decisions: {', '.join(missing)}")
    for item in decisions:
        if not isinstance(item, dict):
            continue
        fields = (
            "co_widzimy",
            "dlaczego_to_ma_znaczenie",
            "bezpieczny_next_step",
            "source_connectors",
            "evidence_ids",
            "blocked_claims",
            "route",
            "skill_id",
            "codex_prompt",
        )
        if any(not item.get(field) for field in fields):
            raise SystemExit(f"DailyDecision lacks required field: {item.get('id')}")
