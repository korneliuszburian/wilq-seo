#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    validate_action_ids,
)

SKILL_NAME = "wilq-campaign-builder"
REQUIRED_CONNECTORS = ["google_ads", "google_analytics_4", "google_search_console"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
}
CORE_CAMPAIGN_ACTION_IDS = {
    "act_prepare_ads_campaign_review_queue",
    "act_prepare_google_ads_recommendation_review_queue",
}
UNSUPPORTED_GENERATOR_FIELDS = {
    "keywords",
    "keyword_ideas",
    "ad_groups",
    "assets",
    "sitelinks",
    "ad_copy",
    "targeting",
    "targeting_plan",
    "target_budget",
    "budget_recommendation",
    "forecast",
}


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

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief_items = [
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

    connector_results = []
    for connector in REQUIRED_CONNECTORS:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(args.api_base, "GET", f"/api/connectors/{quoted}/status")
        connector_results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )

    content_landing_context = pack.get("content_landing_context")
    if not isinstance(content_landing_context, dict):
        raise SystemExit("Context pack must expose content_landing_context")
    landing_candidates = content_landing_context.get("query_page_candidates")
    if not isinstance(landing_candidates, list):
        raise SystemExit("content_landing_context must expose query_page_candidates")
    if content_landing_context.get("live_data_available") is True and not landing_candidates:
        raise SystemExit("Live content_landing_context must expose landing candidates")

    action_validations = validate_core_campaign_actions(args.api_base, pack)
    assert_review_contract_does_not_invent_campaign_build_inputs(pack)

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "content_landing_context": {
                    "live_data_available": content_landing_context.get("live_data_available"),
                    "query_page_candidate_count": content_landing_context.get(
                        "query_page_candidate_count"
                    ),
                    "query_page_candidates": landing_candidates[:4],
                    "blocked_claims": content_landing_context.get("blocked_claims", []),
                    "context_pack_compaction": content_landing_context.get(
                        "context_pack_compaction"
                    ),
                },
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
                "action_validations": action_validations,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def validate_core_campaign_actions(api_base: str, pack: dict[str, Any]) -> list[dict[str, Any]]:
    pack_action_ids = {str(item.get("id")) for item in (pack.get("active_action_objects") or [])}
    available_action_ids = sorted(CORE_CAMPAIGN_ACTION_IDS & pack_action_ids)
    return validate_action_ids(api_base, available_action_ids, label="Campaign")


def assert_review_contract_does_not_invent_campaign_build_inputs(pack: dict[str, Any]) -> None:
    """Keep the review-only surface honest until a typed builder contract exists."""
    context = pack.get("content_landing_context") or {}
    for candidate in context.get("query_page_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        invented = sorted(UNSUPPORTED_GENERATOR_FIELDS.intersection(candidate))
        if invented:
            raise SystemExit(
                "content_landing_context exposes unsupported campaign-builder fields: "
                + ", ".join(invented)
            )
    for action in pack.get("active_action_objects") or []:
        payload = action.get("action_plan") if isinstance(action, dict) else None
        if not isinstance(payload, dict):
            continue
        invented = sorted(UNSUPPORTED_GENERATOR_FIELDS.intersection(payload))
        if invented:
            raise SystemExit(
                "campaign action exposes unsupported generator fields: " + ", ".join(invented)
            )


if __name__ == "__main__":
    raise SystemExit(main())
