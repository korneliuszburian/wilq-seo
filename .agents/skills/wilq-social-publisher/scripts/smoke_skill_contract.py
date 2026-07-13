#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from social_assertions import validate_social_context

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    validate_action_ids,
)

SKILL_NAME = "wilq-social-publisher"
REQUIRED_CONNECTORS = ["linkedin", "facebook"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
}
CORE_ACTIONS = {"act_prepare_facebook_social_drafts", "act_prepare_linkedin_social_drafts"}


def brief_items(brief: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "kind": item.get("kind"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
            "metric_facts": item.get("metric_facts", []),
        }
        for section in brief.get("sections", [])
        for item in section.get("items", [])
        if any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ][:8]


def connectors(api_base: str) -> list[dict[str, Any]]:
    results = []
    for connector in REQUIRED_CONNECTORS:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(api_base, "GET", f"/api/connectors/{quoted}/status")
        results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")
    pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")
    context, inventory = validate_social_context(pack)
    direct = request_json(args.api_base, "GET", "/api/social/history-inventory")
    if direct.get("contract") != "social_history_inventory_v1":
        raise SystemExit("Direct social history endpoint must expose versioned contract")
    brief = brief_items(request_json(args.api_base, "GET", "/api/marketing/brief"))
    if not has_polish_metric_source_guardrails(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    action_ids = sorted(
        CORE_ACTIONS & {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
    )
    actions = validate_action_ids(args.api_base, action_ids, label="Social")
    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connectors(args.api_base),
                "brief_items": brief,
                "brief_item_count": len(brief),
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "social_draft_context": {
                    "mode": context.get("mode"),
                    "publish_allowed": context.get("publish_allowed"),
                    "missing_publish_access": context.get("missing_publish_access"),
                    "historical_social_inventory_status": context.get(
                        "historical_social_inventory_status"
                    ),
                    "duplicate_risk_status": context.get("duplicate_risk_status"),
                    "history_audit_endpoint": context.get("history_audit_endpoint"),
                    "history_audit_contract": context.get("history_audit_contract"),
                    "social_history_inventory": inventory,
                    "direct_inventory_seed_count": len(direct.get("discovery_seeds") or []),
                    "source_input_count": len(context.get("source_inputs", [])),
                    "draft_action_ids": context.get("draft_action_ids", []),
                    "blocked_claims": context.get("blocked_claims", []),
                    "operator_next_step": context.get("operator_next_step"),
                },
                "action_validations": actions,
                "evidence_ids": [
                    item.get("id")
                    for item in (pack.get("evidence_summaries") or [])
                    if item.get("id")
                ][:20],
                "opportunity_ids": [
                    item.get("id")
                    for item in (pack.get("top_opportunities") or [])
                    if item.get("id")
                ][:20],
                "action_ids": [
                    item.get("id")
                    for item in (pack.get("active_action_objects") or [])
                    if item.get("id")
                ][:20],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
