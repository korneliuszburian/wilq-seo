#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
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


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
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
    missing = sorted(REQUIRED_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    instruction = str(pack.get("strict_instruction", "")).lower()
    if "must not invent metrics" not in instruction or "evidence" not in instruction:
        raise SystemExit(
            "Context pack strict instruction does not include WILQ evidence/API guardrails"
        )

    marker_hits = sorted(set(scan_strings(pack)))
    if marker_hits:
        raise SystemExit(f"Context pack contains forbidden marker(s): {', '.join(marker_hits)}")

    pack_brief = pack.get("marketing_brief")
    validate_marketing_brief(pack_brief)
    compare_briefs(brief, pack_brief)
    pack_command_center = pack.get("command_center")
    validate_command_center(pack_command_center)
    compare_command_centers(command_center, pack_command_center)

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
        "operator_brief": compact_operator_brief(command_center),
        "demo_script": compact_demo_script(command_center),
        "action_plan": compact_action_plan(command_center),
        "evidence_count": len(pack.get("evidence_summaries") or []),
        "brief_evidence_ids": (brief.get("evidence_ids") or [])[:10],
        "brief_evidence_count": len(brief.get("evidence_ids") or []),
        "brief_items": compact_brief_items(brief),
        "opportunity_ids": [item.get("id") for item in (pack.get("top_opportunities") or [])[:5]],
        "action_ids": [item.get("id") for item in (pack.get("active_action_objects") or [])[:5]],
        "brief_action_ids": brief.get("action_ids") or [],
        "refresh_run_count": len(pack.get("connector_refresh_runs") or []),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def validate_command_center(command_center: Any) -> None:
    if not isinstance(command_center, dict):
        raise SystemExit("Command center is not an object")
    instruction = str(command_center.get("strict_instruction", "")).lower()
    if "metryki" not in instruction or "evidence" not in instruction:
        raise SystemExit("Command center strict instruction lacks metric/evidence guardrails")
    operator_brief = command_center.get("operator_brief") or []
    if not isinstance(operator_brief, list) or not operator_brief:
        raise SystemExit("Command center has no operator_brief")
    required_ids = {
        "daily_ads_status",
        "daily_merchant_feed",
        "daily_content_queue",
        "daily_ga4_landing_quality",
    }
    item_ids = {item.get("id") for item in operator_brief if isinstance(item, dict)}
    missing_ids = sorted(required_ids - item_ids)
    if missing_ids:
        raise SystemExit(f"Command center missing operator items: {', '.join(missing_ids)}")
    if not isinstance(command_center.get("blocker_count"), int):
        raise SystemExit("Command center blocker_count is missing or not numeric")
    if not isinstance(command_center.get("tactical_item_count"), int):
        raise SystemExit("Command center tactical_item_count is missing or not numeric")
    if not command_center.get("primary_next_step"):
        raise SystemExit("Command center primary_next_step is missing")
    demo_script = command_center.get("demo_script") or []
    if not isinstance(demo_script, list) or len(demo_script) < 4:
        raise SystemExit("Command center demo_script is missing or too small")
    action_plan = command_center.get("action_plan") or []
    if not isinstance(action_plan, list) or len(action_plan) < 4:
        raise SystemExit("Command center action_plan is missing or too small")
    required_plan_ids = {
        "plan_review_merchant_feed_issues",
        "plan_prepare_content_refresh_queue",
        "plan_review_ga4_landing_quality",
        "plan_fix_ads_oauth_before_spend_analysis",
    }
    plan_ids = {item.get("id") for item in action_plan if isinstance(item, dict)}
    missing_plan_ids = sorted(required_plan_ids - plan_ids)
    if missing_plan_ids:
        raise SystemExit(f"Command center missing action_plan items: {', '.join(missing_plan_ids)}")
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
        if item.get("status") == "ready" and not item.get("action_ids"):
            raise SystemExit(f"Ready action_plan item lacks action IDs: {item.get('id')}")


def validate_marketing_brief(brief: Any) -> None:
    if not isinstance(brief, dict):
        raise SystemExit("Marketing brief is not an object")
    if brief.get("language") != "pl-PL":
        raise SystemExit(f"Marketing brief language is not pl-PL: {brief.get('language')}")
    instruction = str(brief.get("strict_instruction", "")).lower()
    if "metryki" not in instruction or "evidence" not in instruction:
        raise SystemExit("Marketing brief strict instruction lacks metric/evidence guardrails")
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
    if "act_configure_google_ads_env" not in action_ids:
        raise SystemExit("Marketing brief does not expose Google Ads OAuth ActionObject")


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
        "operator_brief": command_center.get("operator_brief")
        == pack_command_center.get("operator_brief"),
        "demo_script": command_center.get("demo_script") == pack_command_center.get("demo_script"),
        "action_plan": _trace_fields(command_center.get("action_plan"))
        == _trace_fields(pack_command_center.get("action_plan")),
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
        }
        for item in value
        if isinstance(item, dict)
    ]


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
