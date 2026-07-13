#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

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

    readiness = pack.get("demand_gen_readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("Context pack demand_gen_readiness must be an object")
    if readiness.get("status") != "blocked":
        raise SystemExit("Demand Gen must stay blocked until specific evidence exists")
    title = readiness.get("title")
    if not isinstance(title, str) or not title.startswith("Demand Gen:"):
        raise SystemExit("Demand Gen readiness must expose a marketer-facing title")
    missing_read_contracts = readiness.get("missing_read_contracts")
    if not isinstance(missing_read_contracts, list):
        raise SystemExit("Demand Gen readiness must expose missing read contracts list")
    available_read_contracts = readiness.get("available_read_contracts")
    if not isinstance(available_read_contracts, list):
        raise SystemExit("Demand Gen readiness must expose available read contracts")
    if "demand_gen_asset_group_rows" in missing_read_contracts:
        raise SystemExit("Demand Gen readiness must not use obsolete asset group rows contract")
    for contract in ("demand_gen_ad_group_ad_rows", "demand_gen_creative_asset_rows"):
        in_available = contract in available_read_contracts
        in_missing = contract in missing_read_contracts
        if in_available and in_missing:
            raise SystemExit(f"Demand Gen contract {contract} cannot be both available and missing")
        if not in_available and not in_missing:
            raise SystemExit(f"Demand Gen contract {contract} must be either available or missing")
    for contract in (
        "demand_gen_landing_quality_by_campaign",
        "demand_gen_campaign_mode_review",
    ):
        in_available = contract in available_read_contracts
        in_missing = contract in missing_read_contracts
        if in_available and in_missing:
            raise SystemExit(f"Demand Gen contract {contract} cannot be both available and missing")
        if not in_available and not in_missing:
            raise SystemExit(f"Demand Gen contract {contract} must be either available or missing")
    campaign_rows_evaluated = readiness.get("campaign_rows_evaluated")
    if not isinstance(campaign_rows_evaluated, int):
        raise SystemExit("Demand Gen readiness must expose campaign_rows_evaluated")
    campaign_channel_counts = readiness.get("campaign_channel_counts")
    if not isinstance(campaign_channel_counts, dict):
        raise SystemExit("Demand Gen readiness must expose campaign_channel_counts")
    metric_tiles = readiness.get("metric_tiles")
    if not isinstance(metric_tiles, dict):
        raise SystemExit("Demand Gen readiness must expose metric_tiles")
    if metric_tiles.get("kampanie Ads") != campaign_rows_evaluated:
        raise SystemExit("Demand Gen metric tiles must include evaluated campaign count")
    if metric_tiles.get("braki") != len(missing_read_contracts):
        raise SystemExit("Demand Gen metric tiles must include missing contract count")
    if campaign_rows_evaluated > 0 and not campaign_channel_counts:
        raise SystemExit("Demand Gen readiness must count campaign channels when rows exist")
    if campaign_rows_evaluated > 0 and "demand_gen_campaign_rows" in missing_read_contracts:
        raise SystemExit(
            "Demand Gen campaign rows must not be missing when Ads campaign channels exist"
        )
    demand_gen_campaign_rows = readiness.get("demand_gen_campaign_rows")
    if not isinstance(demand_gen_campaign_rows, list):
        raise SystemExit("Demand Gen readiness must expose demand_gen_campaign_rows list")
    demand_gen_ad_group_ad_rows = readiness.get("demand_gen_ad_group_ad_rows")
    if not isinstance(demand_gen_ad_group_ad_rows, list):
        raise SystemExit("Demand Gen readiness must expose demand_gen_ad_group_ad_rows list")
    demand_gen_creative_asset_rows = readiness.get("demand_gen_creative_asset_rows")
    if not isinstance(demand_gen_creative_asset_rows, list):
        raise SystemExit("Demand Gen readiness must expose demand_gen_creative_asset_rows list")
    demand_gen_landing_quality_rows = readiness.get("demand_gen_landing_quality_rows")
    if not isinstance(demand_gen_landing_quality_rows, list):
        raise SystemExit("Demand Gen readiness must expose demand_gen_landing_quality_rows list")
    demand_gen_campaign_mode_review_rows = readiness.get("demand_gen_campaign_mode_review_rows")
    if not isinstance(demand_gen_campaign_mode_review_rows, list):
        raise SystemExit(
            "Demand Gen readiness must expose demand_gen_campaign_mode_review_rows list"
        )
    action_ids = readiness.get("action_ids")
    if action_ids != [EXPECTED_ACTION_ID]:
        raise SystemExit("Demand Gen readiness must expose the action to validate")
    payload_preview = readiness.get("payload_preview")
    if not isinstance(payload_preview, list) or not payload_preview:
        raise SystemExit("Demand Gen readiness must expose review payload_preview")
    if payload_preview[0].get("preview_contract") != EXPECTED_PREVIEW_CONTRACT:
        raise SystemExit("Demand Gen readiness change preview uses wrong contract")
    if payload_preview[0].get("api_mutation_ready") is not False:
        raise SystemExit("Demand Gen readiness change preview must be validation-only")
    if "[REDACTED]" in json.dumps(readiness):
        raise SystemExit("Demand Gen readiness contract IDs must not be redacted")
    active_actions = pack.get("active_action_objects") or []
    active_action_ids = [action.get("id") for action in active_actions]
    if active_action_ids != [EXPECTED_ACTION_ID]:
        raise SystemExit("Demand Gen context must expose only its review action")
    active_payload = active_actions[0].get("action_plan") or {}
    preview_items = active_payload.get("preview_items") or []
    if not isinstance(preview_items, list) or not preview_items:
        raise SystemExit("Demand Gen action plan must expose preview_items")
    preview = preview_items[0]
    if preview.get("apply_status_label") != "zablokowane do sprawdzenia":
        raise SystemExit("Demand Gen action plan must keep apply blocked")
    if preview.get("write_status_label") != "bez zapisu automatycznego":
        raise SystemExit("Demand Gen action plan must keep write disabled")
    ads_diagnostics = pack.get("ads_diagnostics") or {}
    if ads_diagnostics.get("action_ids"):
        raise SystemExit("Demand Gen Ads diagnostics must not expose scoped action IDs")
    quoted_action = urllib.parse.quote(EXPECTED_ACTION_ID, safe="")
    validation = request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")
    action_validations = [
        {
            "action_id": validation.get("action_id"),
            "valid": validation.get("valid"),
            "status": validation.get("status"),
            "errors": validation.get("errors", []),
        }
    ]
    if validation.get("valid") is not True or validation.get("status") != "valid":
        raise SystemExit(f"Demand Gen action validation failed: {validation}")

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "demand_gen_readiness": {
                    "status": readiness.get("status"),
                    "title": title,
                    "metric_tiles": metric_tiles,
                    "campaign_rows_evaluated": campaign_rows_evaluated,
                    "campaign_channel_counts": campaign_channel_counts,
                    "demand_gen_campaign_row_count": len(demand_gen_campaign_rows),
                    "demand_gen_ad_group_ad_row_count": len(demand_gen_ad_group_ad_rows),
                    "demand_gen_creative_asset_row_count": len(demand_gen_creative_asset_rows),
                    "demand_gen_landing_quality_row_count": len(demand_gen_landing_quality_rows),
                    "demand_gen_campaign_mode_review_row_count": len(
                        demand_gen_campaign_mode_review_rows
                    ),
                    "available_read_contracts": available_read_contracts,
                    "missing_read_contracts": missing_read_contracts,
                    "blocked_claims": readiness.get("blocked_claims", []),
                    "next_step": readiness.get("next_step"),
                },
                "required_connectors": connector_results,
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
