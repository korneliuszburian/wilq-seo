#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from demand_gen_assertions import validate_readiness

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json

SKILL_NAME = "wilq-demand-gen-operator"
REQUIRED_CONNECTORS = ["google_ads", "google_analytics_4"]
EXPECTED_ACTION_ID = "act_review_demand_gen_readiness"
EXPECTED_PREVIEW_CONTRACT = "demand_gen_readiness_review_preview_v1"
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "demand_gen_readiness",
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
        if any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ][:8]


def connector_statuses(api_base: str) -> list[dict[str, Any]]:
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
    readiness, metric_tiles, rows, active_action, counts = validate_readiness(
        pack, EXPECTED_ACTION_ID, EXPECTED_PREVIEW_CONTRACT
    )
    ads_diagnostics = pack.get("ads_diagnostics") or {}
    if ads_diagnostics.get("action_ids"):
        raise SystemExit("Demand Gen Ads diagnostics must not expose scoped action IDs")
    brief_items = compact_items(request_json(args.api_base, "GET", "/api/marketing/brief"))
    if not has_polish_metric_source_guardrails(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    quoted = urllib.parse.quote(EXPECTED_ACTION_ID, safe="")
    validation = request_json(args.api_base, "POST", f"/api/actions/{quoted}/validate")
    if validation.get("valid") is not True or validation.get("status") != "valid":
        raise SystemExit(f"Demand Gen action validation failed: {validation}")
    action_validations = [
        {
            "action_id": validation.get("action_id"),
            "valid": validation.get("valid"),
            "status": validation.get("status"),
            "errors": validation.get("errors", []),
        }
    ]
    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "demand_gen_readiness": {
                    "status": readiness.get("status"),
                    "title": readiness.get("title"),
                    "metric_tiles": metric_tiles,
                    "campaign_rows_evaluated": counts["campaigns"],
                    "campaign_channel_counts": counts["channels"],
                    "demand_gen_campaign_row_count": len(rows[0]),
                    "demand_gen_ad_group_ad_row_count": len(rows[1]),
                    "demand_gen_creative_asset_row_count": len(rows[2]),
                    "demand_gen_landing_quality_row_count": len(rows[3]),
                    "demand_gen_campaign_mode_review_row_count": len(rows[4]),
                    "available_read_contracts": counts["available"],
                    "missing_read_contracts": counts["missing"],
                    "blocked_claims": readiness.get("blocked_claims", []),
                    "next_step": readiness.get("next_step"),
                },
                "required_connectors": connector_statuses(args.api_base),
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "action_validations": action_validations,
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
