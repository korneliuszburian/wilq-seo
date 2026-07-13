#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from ga4_assertions import validate_ga4_contract

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    require_polish_language,
)

SKILL_NAME = "wilq-ga4-analyst"
GA4_CONNECTOR_ID = "google_analytics_4"
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "ga4_diagnostics",
}


def compact_items(brief: dict[str, Any]) -> list[dict[str, Any]]:
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
        if GA4_CONNECTOR_ID in item.get("source_connectors", [])
    ][:8]


def connector_status(api_base: str) -> list[dict[str, Any]]:
    quoted = urllib.parse.quote(GA4_CONNECTOR_ID, safe="")
    status = request_json(api_base, "GET", f"/api/connectors/{quoted}/status")
    return [
        {
            "id": status.get("id"),
            "status": status.get("status"),
            "configured": status.get("configured"),
            "missing_credentials": status.get("missing_credentials", []),
            "error": status.get("error"),
        }
    ]


def action_validations(api_base: str, action_ids: list[Any]) -> list[dict[str, Any]]:
    results = []
    for action_id in action_ids:
        quoted = urllib.parse.quote(str(action_id), safe="")
        validation = request_json(api_base, "POST", f"/api/actions/{quoted}/validate")
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"GA4 action validation failed: {validation}")
        results.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
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
    diagnostics = request_json(args.api_base, "GET", "/api/ga4/diagnostics")
    require_polish_language(diagnostics, "GA4 diagnostics")
    readiness, decisions, context, section_ids = validate_ga4_contract(pack, diagnostics)
    brief_items = compact_items(request_json(args.api_base, "GET", "/api/marketing/brief"))
    if not has_polish_metric_source_guardrails(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    validations = action_validations(args.api_base, diagnostics.get("action_ids", []))
    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_status(args.api_base),
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "action_validations": validations,
                "ga4_diagnostics": {
                    "live_data_available": diagnostics.get("live_data_available"),
                    "landing_group_count": diagnostics.get("landing_group_count"),
                    "low_engagement_count": diagnostics.get("low_engagement_count"),
                    "wordpress_match_count": diagnostics.get("wordpress_match_count"),
                    "blocker_count": diagnostics.get("blocker_count"),
                    "conversion_readiness_contract": {
                        "status": readiness.get("status"),
                        "missing_read_contracts": readiness.get("missing_read_contracts", []),
                        "conversion_like_metric_count": readiness.get(
                            "conversion_like_metric_count"
                        ),
                    },
                    "decision_count": len(decisions),
                    "decision_ids": [item.get("id") for item in decisions if item.get("id")][:20],
                    "decision_types": sorted(
                        {
                            item.get("decision_type")
                            for item in decisions
                            if item.get("decision_type")
                        }
                    ),
                    "section_ids": section_ids,
                    "evidence_ids": diagnostics.get("evidence_ids", [])[:20],
                    "action_ids": diagnostics.get("action_ids", []),
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
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
