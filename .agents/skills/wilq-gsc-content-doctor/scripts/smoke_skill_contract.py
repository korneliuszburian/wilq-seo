#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from gsc_decision_parity import validate_gsc_context_parity
from gsc_freshness_assertions import validate_freshness_and_gsc_contract
from gsc_marketer_card_assertions import validate_marketer_decision_card
from gsc_refresh_contract import read_latest_gsc_refresh_contract
from gsc_report_compaction import compact_gsc_brief_items, compact_gsc_connector_statuses
from gsc_runtime_assertions import validate_gsc_runtime

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    require_polish_language,
    validate_action_ids,
)

SKILL_NAME = "wilq-gsc-content-doctor"
REQUIRED_CONNECTORS = ["google_search_console", "wordpress_ekologus", "wordpress_sklep"]
CONTENT_ACTION_ID = "act_prepare_content_refresh_queue"
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "content_diagnostics",
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
    diagnostics = request_json(args.api_base, "GET", "/api/content/diagnostics")
    require_polish_language(diagnostics, "Content diagnostics")
    if not isinstance(diagnostics.get("sections"), list) or not diagnostics["sections"]:
        raise SystemExit("Content diagnostics must expose sections")
    if not isinstance(diagnostics.get("decision_queue"), list):
        raise SystemExit("Content diagnostics must expose decision_queue")
    freshness, gsc_contract = validate_freshness_and_gsc_contract(diagnostics)
    packed, packed_trace, endpoint_trace = validate_gsc_context_parity(pack, diagnostics)
    marketer_card = validate_marketer_decision_card(diagnostics, endpoint_trace, CONTENT_ACTION_ID)
    refresh_summary, refresh_evidence = read_latest_gsc_refresh_contract(args.api_base)
    evidence_ids = diagnostics.get("evidence_ids") or []
    refresh_ids = [
        str(item)
        for item in evidence_ids
        if str(item).startswith("ev_refresh_refresh_google_search_console_")
    ]
    if refresh_evidence and refresh_evidence not in refresh_ids:
        raise SystemExit("Content diagnostics must include latest completed GSC refresh evidence")
    facts = request_json(
        args.api_base, "GET", "/api/metrics?connector_id=google_search_console&limit=2000"
    )
    query_page_count, actions = validate_gsc_runtime(
        args.api_base, diagnostics, facts, CONTENT_ACTION_ID, validate_action_ids
    )
    action_ids = diagnostics.get("action_ids") or []
    if not has_polish_metric_source_guardrails(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": compact_gsc_connector_statuses(
                    args.api_base, REQUIRED_CONNECTORS
                ),
                "brief_items": compact_gsc_brief_items(args.api_base, REQUIRED_CONNECTORS),
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "action_validations": actions,
                "content_diagnostics": {
                    "live_data_available": diagnostics.get("live_data_available"),
                    "freshness_assessment": freshness,
                    "query_page_count": diagnostics.get("query_page_count"),
                    "matched_inventory_count": diagnostics.get("matched_inventory_count"),
                    "decision_count": len(diagnostics.get("decision_queue", [])),
                    "context_pack_decision_count": len(packed_trace),
                    "api_gsc_search_analytics_contract": gsc_contract,
                    "gsc_query_page_metric_fact_count": query_page_count,
                    "latest_gsc_refresh_evidence_id": refresh_evidence,
                    "gsc_refresh_evidence_ids": refresh_ids,
                    "marketer_review_card": marketer_card,
                    "blocker_count": diagnostics.get("blocker_count"),
                    "section_ids": [section.get("id") for section in diagnostics["sections"]],
                    "evidence_ids": evidence_ids[:20],
                    "action_ids": action_ids,
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
