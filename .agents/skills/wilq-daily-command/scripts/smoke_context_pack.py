#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

REQUIRED_KEYS = {
    "strict_instruction",
    "available_connectors",
    "connector_status",
    "connector_refresh_runs",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "command_center",
    "marketing_brief",
    "knowledge_card_summaries",
    "expert_rule_summaries",
    "expert_capabilities",
}
REQUIRED_BRIEF_SECTIONS = {
    "what_we_know",
    "what_blocks_us",
    "safe_next_actions",
    "recommended_focus",
}
FORBIDDEN_MARKERS = ("fake_metric", "mock_metric", "seed_metric")
MAX_CONTEXT_PACK_BYTES = 180_000
CORE_DAILY_ACTION_IDS = {
    "act_prepare_content_refresh_queue",
    "act_review_ga4_tracking_quality",
    "act_review_merchant_feed_issues",
}
CONDITIONAL_DAILY_ACTION_IDS = {
    "act_prepare_ads_campaign_review_queue",
}
FORBIDDEN_DAILY_ACTION_IDS = {
    "act_prepare_facebook_social_drafts",
    "act_prepare_linkedin_social_drafts",
}
CORE_OPERATOR_ITEM_IDS = {
    "daily_ads_status",
    "daily_content_queue",
    "daily_ga4_landing_quality",
    "daily_merchant_feed",
}
FORBIDDEN_READY_OPERATOR_ITEM_IDS = {
    "daily_localo_readiness",
}


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def scan_strings(value: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(value, str):
        lowered = value.lower()
        hits.extend(marker for marker in FORBIDDEN_MARKERS if marker in lowered)
    elif isinstance(value, dict):
        for nested in value.values():
            hits.extend(scan_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            hits.extend(scan_strings(nested))
    return hits


def normalize_for_marker_check(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")


def has_metric_evidence_guardrails(value: str) -> bool:
    normalized = normalize_for_marker_check(value)
    return "metryk" in normalized and "dowod" in normalized and "zrodl" in normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test wilq-daily-command against WILQ API")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    command_center = request_json(args.api_base, "GET", "/api/dashboard/command-center")
    validate_command_center(command_center)

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    validate_marketing_brief(brief)

    pack = request_json(
        args.api_base, "POST", "/api/codex/context-pack", {"skill": "wilq-daily-command"}
    )
    pack_bytes = len(json.dumps(pack, ensure_ascii=False).encode())
    if pack_bytes >= MAX_CONTEXT_PACK_BYTES:
        raise SystemExit(f"Daily context-pack exceeds budget: {pack_bytes} bytes")
    missing = sorted(REQUIRED_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    instruction = str(pack.get("strict_instruction", "")).lower()
    if not has_metric_evidence_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera zasad metryk i dowodów z WILQ API"
        )

    marker_hits = sorted(set(scan_strings(pack)))
    if marker_hits:
        raise SystemExit(f"Context pack contains forbidden marker(s): {', '.join(marker_hits)}")

    pack_brief = pack.get("marketing_brief")
    validate_marketing_brief(pack_brief)
    compare_briefs(brief, pack_brief)
    pack_command_center = pack.get("command_center")
    validate_command_center(pack_command_center, compact=True)
    compare_command_centers(command_center, pack_command_center)
    validate_daily_action_scope(command_center, brief, pack)
    action_validations = validate_core_daily_actions(args.api_base, pack)

    connector_status = pack.get("connector_status") or []
    configured = [item.get("id") for item in connector_status if item.get("configured")]
    blocked = [
        item.get("id")
        for item in connector_status
        if item.get("status") in {"missing_credentials", "disabled"}
    ]
    summary = {
        "api_base": args.api_base,
        "health": health.get("status"),
        "configured_connectors": configured,
        "blocked_or_disabled_connectors": blocked,
        "marketing_brief_language": brief.get("language"),
        "marketing_brief_sections": [section.get("id") for section in brief.get("sections", [])],
        "marketing_brief_blocker_count": brief.get("blocker_count"),
        "marketing_brief_recommendation_count": brief.get("recommendation_count"),
        "command_center_primary_next_step": command_center.get("primary_next_step"),
        "command_center_blocker_count": command_center.get("blocker_count"),
        "command_center_tactical_item_count": command_center.get("tactical_item_count"),
        "daily_decisions": compact_daily_decisions(command_center),
        "operator_brief": compact_operator_brief(command_center),
        "demo_script": compact_demo_script(command_center),
        "action_plan": compact_action_plan(command_center),
        "evidence_count": len(pack.get("evidence_summaries") or []),
        "brief_evidence_ids": (brief.get("evidence_ids") or [])[:10],
        "brief_evidence_count": len(brief.get("evidence_ids") or []),
        "brief_items": compact_brief_items(brief),
        "opportunity_ids": [item.get("id") for item in (pack.get("top_opportunities") or [])[:5]],
        "active_action_object_ids": [
            item.get("id") for item in (pack.get("active_action_objects") or [])
        ],
        "action_validations": action_validations,
        "brief_action_ids": brief.get("action_ids") or [],
        "core_daily_action_ids": sorted(
            CORE_DAILY_ACTION_IDS | (CONDITIONAL_DAILY_ACTION_IDS & collect_pack_action_ids(pack))
        ),
        "forbidden_daily_action_ids_present": sorted(
            (
                set(collect_action_ids(command_center))
                | set(brief.get("action_ids") or [])
                | {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
            )
            & FORBIDDEN_DAILY_ACTION_IDS
        ),
        "refresh_run_count": len(pack.get("connector_refresh_runs") or []),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def validate_command_center(command_center: Any, *, compact: bool = False) -> None:
    if not isinstance(command_center, dict):
        raise SystemExit("Command center is not an object")
    instruction = str(command_center.get("strict_instruction", ""))
    if not has_metric_evidence_guardrails(instruction):
        raise SystemExit(
            "Instrukcja Centrum pracy nie zawiera zasad metryk i dowodów źródłowych"
        )
    operator_brief = command_center.get("operator_brief") or []
    if not compact:
        if not isinstance(operator_brief, list) or not operator_brief:
            raise SystemExit("Command center has no operator_brief")
        item_ids = {str(item.get("id")) for item in operator_brief if isinstance(item, dict)}
        missing_ids = sorted(CORE_OPERATOR_ITEM_IDS - item_ids)
        if missing_ids:
            raise SystemExit(f"Command center missing operator items: {', '.join(missing_ids)}")
        ready_forbidden_ids = sorted(
            str(item.get("id"))
            for item in operator_brief
            if isinstance(item, dict)
            and item.get("id") in FORBIDDEN_READY_OPERATOR_ITEM_IDS
            and item.get("status") == "ready"
        )
        if ready_forbidden_ids:
            raise SystemExit(
                "Command center promotes readiness-only Localo item as primary: "
                + ", ".join(ready_forbidden_ids)
            )
    if not isinstance(command_center.get("blocker_count"), int):
        raise SystemExit("Command center blocker_count is missing or not numeric")
    if not isinstance(command_center.get("tactical_item_count"), int):
        raise SystemExit("Command center tactical_item_count is missing or not numeric")
    if not command_center.get("primary_next_step"):
        raise SystemExit("Command center primary_next_step is missing")
    demo_script = command_center.get("demo_script") or []
    if not isinstance(demo_script, list):
        raise SystemExit("Command center demo_script must be a list")
    action_plan = command_center.get("action_plan") or []
    if not compact and (not isinstance(action_plan, list) or len(action_plan) < 4):
        raise SystemExit("Command center action_plan is missing or too small")
    daily_decisions = command_center.get("daily_decisions") or []
    if not isinstance(daily_decisions, list) or len(daily_decisions) < 4:
        raise SystemExit("Command center daily_decisions is missing or too small")
    if len(daily_decisions) > 4:
        raise SystemExit("Command center daily_decisions must stay focused on core daily work")
    required_plan_ids = {
        "plan_review_merchant_feed_issues",
        "plan_prepare_content_refresh_queue",
        "plan_review_ga4_landing_quality",
    }
    if compact:
        ads_live_ready = any(
            item.get("id") == "decision_review_ads_campaign_metrics"
            and item.get("status") == "ready"
            for item in daily_decisions
            if isinstance(item, dict)
        )
    else:
        ads_live_ready = any(
            item.get("id") == "daily_ads_status" and item.get("status") == "ready"
            for item in operator_brief
            if isinstance(item, dict)
        )
    if ads_live_ready:
        required_plan_ids.add("plan_review_ads_campaign_metrics")
    else:
        required_plan_ids.add("plan_fix_ads_oauth_before_spend_analysis")
    if not compact:
        plan_ids = {item.get("id") for item in action_plan if isinstance(item, dict)}
        missing_plan_ids = sorted(required_plan_ids - plan_ids)
        if missing_plan_ids:
            raise SystemExit(
                f"Command center missing action_plan items: {', '.join(missing_plan_ids)}"
            )
    decision_ids = {item.get("id") for item in daily_decisions if isinstance(item, dict)}
    forbidden_decision_ids = {
        "decision_review_localo_visibility_facts",
        "decision_finish_localo_access_before_local_visibility",
    }
    leaked_decision_ids = sorted(forbidden_decision_ids & decision_ids)
    if leaked_decision_ids:
        raise SystemExit(
            "Command center promoted non-core daily decisions: " + ", ".join(leaked_decision_ids)
        )
    expected_decision_ids = {
        plan_id.replace("plan_", "decision_", 1) for plan_id in required_plan_ids
    }
    missing_decision_ids = sorted(expected_decision_ids - decision_ids)
    if missing_decision_ids:
        raise SystemExit(
            f"Command center missing daily_decisions: {', '.join(missing_decision_ids)}"
        )
    if not compact:
        for item in operator_brief:
            if not isinstance(item, dict):
                continue
            if not item.get("source_connectors"):
                raise SystemExit(f"Command center item lacks source connectors: {item.get('id')}")
            if not item.get("evidence_ids"):
                raise SystemExit(f"Command center item lacks evidence IDs: {item.get('id')}")
        for item in action_plan:
            if not isinstance(item, dict):
                continue
            if not item.get("source_connectors"):
                raise SystemExit(
                    f"Command center action_plan item lacks source connectors: {item.get('id')}"
                )
            if not item.get("evidence_ids"):
                raise SystemExit(
                    f"Command center action_plan item lacks evidence IDs: {item.get('id')}"
                )
            if (
                item.get("status") == "ready"
                and not item.get("action_ids")
                and not item.get("blocked_claims")
            ):
                raise SystemExit(
                    f"Ready action_plan item lacks action IDs or blocked claims: {item.get('id')}"
                )
    for item in daily_decisions:
        if not isinstance(item, dict):
            continue
        for key in (
            "co_widzimy",
            "dlaczego_to_ma_znaczenie",
            "bezpieczny_next_step",
            "source_connectors",
            "evidence_ids",
            "blocked_claims",
            "route",
            "skill_id",
            "codex_prompt",
        ):
            if not item.get(key):
                raise SystemExit(f"DailyDecision lacks {key}: {item.get('id')}")


def validate_marketing_brief(brief: Any) -> None:
    if not isinstance(brief, dict):
        raise SystemExit("Marketing brief is not an object")
    if brief.get("language") != "pl-PL":
        raise SystemExit(f"Marketing brief language is not pl-PL: {brief.get('language')}")
    instruction = str(brief.get("strict_instruction", ""))
    if not has_metric_evidence_guardrails(instruction):
        raise SystemExit("Instrukcja briefu nie zawiera zasad metryk i dowodów źródłowych")
    section_ids = {section.get("id") for section in brief.get("sections", [])}
    missing_sections = sorted(REQUIRED_BRIEF_SECTIONS - section_ids)
    if missing_sections:
        raise SystemExit(f"Marketing brief missing sections: {', '.join(missing_sections)}")
    if not isinstance(brief.get("blocker_count"), int):
        raise SystemExit("Marketing brief blocker_count is missing or not numeric")
    if not isinstance(brief.get("recommendation_count"), int):
        raise SystemExit("Marketing brief recommendation_count is missing or not numeric")
    evidence_ids = brief.get("evidence_ids") or []
    if not evidence_ids:
        raise SystemExit("Marketing brief has no evidence IDs")
    action_ids = brief.get("action_ids") or []
    if not action_ids:
        raise SystemExit("Marketing brief has no action IDs")
    missing_core_actions = sorted(CORE_DAILY_ACTION_IDS - set(action_ids))
    if missing_core_actions:
        raise SystemExit(
            "Marketing brief missing core daily action IDs: " + ", ".join(missing_core_actions)
        )
    forbidden_actions = sorted(FORBIDDEN_DAILY_ACTION_IDS & set(action_ids))
    if forbidden_actions:
        raise SystemExit(
            "Marketing brief promotes non-core daily action IDs: " + ", ".join(forbidden_actions)
        )


def validate_daily_action_scope(
    command_center: dict[str, Any],
    brief: dict[str, Any],
    pack: dict[str, Any],
) -> None:
    command_center_action_ids = set(collect_action_ids(command_center))
    brief_action_ids = set(brief.get("action_ids") or [])
    pack_action_ids = {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
    all_daily_action_ids = command_center_action_ids | brief_action_ids | pack_action_ids

    missing_core_actions = sorted(CORE_DAILY_ACTION_IDS - all_daily_action_ids)
    if missing_core_actions:
        raise SystemExit(
            "Daily command context missing core action IDs: " + ", ".join(missing_core_actions)
        )

    forbidden_actions = sorted(FORBIDDEN_DAILY_ACTION_IDS & all_daily_action_ids)
    if forbidden_actions:
        raise SystemExit(
            "Daily command context includes social action IDs: " + ", ".join(forbidden_actions)
        )

    active_action_objects = pack.get("active_action_objects") or []
    if not isinstance(active_action_objects, list):
        raise SystemExit("Context pack active_action_objects must be a list")
    missing_active_core = sorted(CORE_DAILY_ACTION_IDS - pack_action_ids)
    if missing_active_core:
        raise SystemExit(
            "Context pack active_action_objects missing core daily actions: "
            + ", ".join(missing_active_core)
        )


def validate_core_daily_actions(api_base: str, pack: dict[str, Any]) -> list[dict[str, Any]]:
    pack_action_ids = {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
    action_validations = []
    action_ids_to_validate = CORE_DAILY_ACTION_IDS | (
        CONDITIONAL_DAILY_ACTION_IDS & pack_action_ids
    )
    for action_id in sorted(action_ids_to_validate):
        if action_id not in pack_action_ids:
            raise SystemExit(f"Daily context missing core action: {action_id}")
        quoted_action = urllib.parse.quote(action_id, safe="")
        validation = request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Daily action validation failed: {validation}")
    return action_validations


def compare_briefs(brief: dict[str, Any], pack_brief: dict[str, Any]) -> None:
    checks = {
        "language": brief.get("language") == pack_brief.get("language"),
        "blocker_count": brief.get("blocker_count") == pack_brief.get("blocker_count"),
        "recommendation_count": brief.get("recommendation_count")
        == pack_brief.get("recommendation_count"),
        "evidence_ids": brief.get("evidence_ids") == pack_brief.get("evidence_ids"),
        "action_ids": brief.get("action_ids") == pack_brief.get("action_ids"),
        "section_ids": [section.get("id") for section in brief.get("sections", [])]
        == [section.get("id") for section in pack_brief.get("sections", [])],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit(
            "Marketing brief in context pack does not match /api/marketing/brief: "
            + ", ".join(failed)
        )


def compare_command_centers(
    command_center: dict[str, Any],
    pack_command_center: dict[str, Any],
) -> None:
    checks = {
        "primary_next_step": command_center.get("primary_next_step")
        == pack_command_center.get("primary_next_step"),
        "blocker_count": command_center.get("blocker_count")
        == pack_command_center.get("blocker_count"),
        "tactical_item_count": command_center.get("tactical_item_count")
        == pack_command_center.get("tactical_item_count"),
        "daily_decisions": _trace_fields(command_center.get("daily_decisions"))
        == _trace_fields(pack_command_center.get("daily_decisions")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit(
            "Command center in context pack does not match /api/dashboard/command-center: "
            + ", ".join(failed)
        )


def compact_operator_brief(command_center: dict[str, Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    for item in command_center.get("operator_brief", []):
        if not isinstance(item, dict):
            continue
        compact_items.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "route": item.get("route"),
                "status": item.get("status"),
                "source_connectors": item.get("source_connectors") or [],
                "evidence_ids": item.get("evidence_ids") or [],
                "action_ids": item.get("action_ids") or [],
                "metric_tiles": item.get("metric_tiles") or {},
                "next_step": item.get("next_step"),
            }
        )
    return compact_items


def compact_daily_decisions(command_center: dict[str, Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    for item in command_center.get("daily_decisions", []):
        if not isinstance(item, dict):
            continue
        compact_items.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "route": item.get("route"),
                "status": item.get("status"),
                "source_connectors": item.get("source_connectors") or [],
                "evidence_ids": item.get("evidence_ids") or [],
                "action_ids": item.get("action_ids") or [],
                "skill_id": item.get("skill_id"),
            }
        )
    return compact_items


def compact_demo_script(command_center: dict[str, Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    for item in command_center.get("demo_script", []):
        if not isinstance(item, dict):
            continue
        compact_items.append(
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "route": item.get("route"),
                "status": item.get("status"),
                "evidence_ids": item.get("evidence_ids") or [],
                "action_ids": item.get("action_ids") or [],
            }
        )
    return compact_items


def compact_action_plan(command_center: dict[str, Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    for item in command_center.get("action_plan", []):
        if not isinstance(item, dict):
            continue
        compact_items.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "route": item.get("route"),
                "status": item.get("status"),
                "source_connectors": item.get("source_connectors") or [],
                "evidence_ids": item.get("evidence_ids") or [],
                "action_ids": item.get("action_ids") or [],
                "blocked_claims": item.get("blocked_claims") or [],
            }
        )
    return compact_items


def _trace_fields(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        {
            "id": item.get("id"),
            "route": item.get("route"),
            "status": item.get("status"),
            "source_connectors": item.get("source_connectors") or [],
            "evidence_ids": item.get("evidence_ids") or [],
            "action_ids": item.get("action_ids") or [],
            "blocked_claims": item.get("blocked_claims") or [],
            "skill_id": item.get("skill_id"),
        }
        for item in value
        if isinstance(item, dict)
    ]


def collect_action_ids(command_center: dict[str, Any]) -> list[str]:
    action_ids: list[str] = []
    for section_name in ("operator_brief", "daily_decisions", "action_plan", "demo_script"):
        for item in command_center.get(section_name, []) or []:
            if not isinstance(item, dict):
                continue
            action_ids.extend(str(action_id) for action_id in item.get("action_ids") or [])
    return action_ids


def collect_pack_action_ids(pack: dict[str, Any]) -> set[str]:
    return {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}


def compact_brief_items(brief: dict[str, Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    for section in brief.get("sections", []):
        if not isinstance(section, dict):
            continue
        for item in section.get("items", [])[:2]:
            if not isinstance(item, dict):
                continue
            compact_items.append(
                {
                    "section_id": section.get("id"),
                    "id": item.get("id"),
                    "kind": item.get("kind"),
                    "title": item.get("title"),
                    "source_connectors": item.get("source_connectors") or [],
                    "evidence_ids": item.get("evidence_ids") or [],
                    "action_ids": item.get("action_ids") or [],
                    "blocker_reason": item.get("blocker_reason"),
                    "next_step": item.get("next_step"),
                }
            )
    return compact_items[:8]


if __name__ == "__main__":
    raise SystemExit(main())
