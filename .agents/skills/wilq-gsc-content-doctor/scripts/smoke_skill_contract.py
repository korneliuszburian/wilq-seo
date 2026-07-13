#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from gsc_decision_parity import validate_gsc_context_parity
from gsc_freshness_assertions import validate_freshness_and_gsc_contract
from gsc_refresh_contract import read_latest_gsc_refresh_contract
from gsc_report_compaction import compact_gsc_brief_items, compact_gsc_connector_statuses

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

    content_diagnostics = request_json(args.api_base, "GET", "/api/content/diagnostics")
    require_polish_language(content_diagnostics, "Content diagnostics")
    sections = content_diagnostics.get("sections")
    if not isinstance(sections, list) or not sections:
        raise SystemExit("Content diagnostics must expose sections")
    decision_queue = content_diagnostics.get("decision_queue")
    if not isinstance(decision_queue, list):
        raise SystemExit("Content diagnostics must expose decision_queue")
    api_gsc_contract = content_diagnostics.get("gsc_search_analytics_contract")
    freshness_assessment, api_gsc_contract = validate_freshness_and_gsc_contract(
        content_diagnostics
    )
    packed_content = pack.get("content_diagnostics", {})
    packed_evidence_ids = packed_content.get("evidence_ids") or []
    endpoint_evidence_ids = content_diagnostics.get("evidence_ids") or []
    latest_gsc_refresh_summary, latest_gsc_refresh_evidence_id = read_latest_gsc_refresh_contract(
        args.api_base
    )
    gsc_refresh_evidence_ids = [
        str(evidence_id)
        for evidence_id in endpoint_evidence_ids
        if str(evidence_id).startswith("ev_refresh_refresh_google_search_console_")
    ]
    if latest_gsc_refresh_evidence_id is not None:
        if latest_gsc_refresh_evidence_id not in gsc_refresh_evidence_ids:
            raise SystemExit(
                "Content diagnostics must include latest completed GSC refresh evidence"
            )
        if len(gsc_refresh_evidence_ids) > 1:
            raise SystemExit(
                "Content diagnostics must not include stale duplicate GSC refresh evidence IDs"
            )
    packed_content, packed_decision_trace, endpoint_decision_trace = validate_gsc_context_parity(
        pack, content_diagnostics
    )

    marketer_decision = content_diagnostics.get("marketer_decision")
    if content_diagnostics.get("live_data_available") is True:
        if not isinstance(marketer_decision, dict):
            raise SystemExit("Content diagnostics must expose marketer_decision")
        if marketer_decision.get("review_card_label") != "Karta decyzji dla Wilka":
            raise SystemExit("Content marketer decision must expose Wilku review card label")
        required_review_fields = {
            "review_decision_after_review",
            "review_question_for_wilku",
            "review_next_safe_click",
        }
        missing_review_fields = [
            field
            for field in sorted(required_review_fields)
            if not str(marketer_decision.get(field) or "").strip()
        ]
        if missing_review_fields:
            raise SystemExit(
                "Content marketer decision missing Wilku review fields: "
                + ", ".join(missing_review_fields)
            )
        if "publik" not in str(marketer_decision.get("review_next_safe_click") or "").lower():
            raise SystemExit("Wilku review next click must explicitly block publication")
        review_action_ids = marketer_decision.get("review_action_ids")
        selected_decision = next(
            (
                item
                for item in endpoint_decision_trace
                if item.get("id") == marketer_decision.get("technical_decision_id")
            ),
            None,
        )
        selected_action_ids = (selected_decision or {}).get("action_ids") or []
        expected_review_action_ids = (
            [CONTENT_ACTION_ID] if CONTENT_ACTION_ID in selected_action_ids else []
        )
        if review_action_ids != expected_review_action_ids:
            raise SystemExit(
                "Wilku review card action IDs must match the selected content decision"
            )

    gsc_metric_facts = request_json(
        args.api_base,
        "GET",
        "/api/metrics?connector_id=google_search_console&limit=2000",
    )
    gsc_query_page_fact_count = sum(
        1
        for fact in gsc_metric_facts
        if {"query", "page"}.issubset(set((fact.get("dimensions") or {}).keys()))
    )
    if gsc_query_page_fact_count:
        if not content_diagnostics.get("query_page_count"):
            raise SystemExit(
                "GSC query/page metric facts exist but content diagnostics has query_page_count=0"
            )
        if not decision_queue:
            raise SystemExit(
                "GSC query/page metric facts exist but content diagnostics has no decision_queue"
            )
        decision_types = {
            item.get("decision_type") for item in decision_queue if item.get("decision_type")
        }
        content_decision_types = {
            "refresh_or_merge",
            "merge_create_after_inventory_check",
            "inventory_check_before_create",
        }
        if not decision_types.intersection(content_decision_types):
            raise SystemExit(
                "Content diagnostics decision_queue must contain concrete "
                "refresh/merge/create inventory decisions"
            )
        if not any(item.get("page") and item.get("queries") for item in decision_queue):
            raise SystemExit("Content decisions must include concrete page and query values")

    action_ids = content_diagnostics.get("action_ids") or []
    if (
        content_diagnostics.get("live_data_available") is True
        and CONTENT_ACTION_ID not in action_ids
    ):
        raise SystemExit("Live GSC content diagnostics must expose content refresh action")
    action_validations = validate_action_ids(
        args.api_base,
        [CONTENT_ACTION_ID] if CONTENT_ACTION_ID in action_ids else [],
        label="GSC content",
    )

    brief_items = compact_gsc_brief_items(args.api_base, REQUIRED_CONNECTORS)
    connector_results = compact_gsc_connector_statuses(args.api_base, REQUIRED_CONNECTORS)

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )

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
                "action_validations": action_validations,
                "content_diagnostics": {
                    "live_data_available": content_diagnostics.get("live_data_available"),
                    "freshness_assessment": freshness_assessment,
                    "query_page_count": content_diagnostics.get("query_page_count"),
                    "matched_inventory_count": content_diagnostics.get("matched_inventory_count"),
                    "decision_count": len(decision_queue),
                    "decision_types": sorted(
                        str(item.get("decision_type"))
                        for item in decision_queue
                        if item.get("decision_type")
                    ),
                    "top_decisions": [
                        {
                            "id": item.get("id"),
                            "decision_type": item.get("decision_type"),
                            "page": item.get("page"),
                            "queries": item.get("queries", [])[:4],
                            "wordpress_match": item.get("wordpress_match"),
                        }
                        for item in decision_queue[:5]
                    ],
                    "context_pack_decision_count": len(packed_decision_trace),
                    "context_pack_decision_types": sorted(
                        str(item.get("decision_type"))
                        for item in packed_decision_trace
                        if item.get("decision_type")
                    ),
                    "context_pack_top_decisions": [
                        {
                            "id": item.get("id"),
                            "decision_type": item.get("decision_type"),
                            "page": item.get("page"),
                            "queries": item.get("queries", [])[:4],
                            "source_connectors": item.get("source_connectors", []),
                        }
                        for item in packed_decision_trace[:5]
                    ],
                    "context_pack_has_ahrefs_evidence": any(
                        "_ahrefs" in str(evidence_id) for evidence_id in packed_evidence_ids
                    ),
                    "api_gsc_search_analytics_contract": api_gsc_contract,
                    "gsc_search_analytics_contract": {
                        "data_availability_checked": latest_gsc_refresh_summary.get(
                            "data_availability_checked"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                        "date_availability_status": latest_gsc_refresh_summary.get(
                            "date_availability_status"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                        "availability_date_start": latest_gsc_refresh_summary.get(
                            "availability_date_start"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                        "availability_date_end": latest_gsc_refresh_summary.get(
                            "availability_date_end"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                        "detail_date_start": latest_gsc_refresh_summary.get("date_start")
                        if latest_gsc_refresh_summary
                        else None,
                        "detail_date_end": latest_gsc_refresh_summary.get("date_end")
                        if latest_gsc_refresh_summary
                        else None,
                        "query_page_row_limit": latest_gsc_refresh_summary.get(
                            "query_page_row_limit"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                        "query_page_max_rows": latest_gsc_refresh_summary.get("query_page_max_rows")
                        if latest_gsc_refresh_summary
                        else None,
                        "query_page_rows_truncated": latest_gsc_refresh_summary.get(
                            "query_page_rows_truncated"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                        "search_type": latest_gsc_refresh_summary.get("search_type")
                        if latest_gsc_refresh_summary
                        else None,
                        "detail_dimensions": latest_gsc_refresh_summary.get("detail_dimensions")
                        if latest_gsc_refresh_summary
                        else None,
                        "detail_data_completeness": latest_gsc_refresh_summary.get(
                            "detail_data_completeness"
                        )
                        if latest_gsc_refresh_summary
                        else None,
                    },
                    "gsc_query_page_metric_fact_count": gsc_query_page_fact_count,
                    "marketer_review_card": {
                        "label": (marketer_decision or {}).get("review_card_label")
                        if isinstance(marketer_decision, dict)
                        else None,
                        "decision_after_review": (marketer_decision or {}).get(
                            "review_decision_after_review"
                        )
                        if isinstance(marketer_decision, dict)
                        else None,
                        "question_for_wilku": (marketer_decision or {}).get(
                            "review_question_for_wilku"
                        )
                        if isinstance(marketer_decision, dict)
                        else None,
                        "next_safe_click": (marketer_decision or {}).get("review_next_safe_click")
                        if isinstance(marketer_decision, dict)
                        else None,
                        "action_ids": (marketer_decision or {}).get("review_action_ids")
                        if isinstance(marketer_decision, dict)
                        else [],
                    },
                    "latest_gsc_refresh_evidence_id": latest_gsc_refresh_evidence_id,
                    "gsc_refresh_evidence_ids": gsc_refresh_evidence_ids,
                    "blocker_count": content_diagnostics.get("blocker_count"),
                    "section_ids": [
                        section.get("id") for section in content_diagnostics.get("sections", [])
                    ],
                    "evidence_ids": content_diagnostics.get("evidence_ids", [])[:20],
                    "action_ids": content_diagnostics.get("action_ids", []),
                    "tactical_item_ids": [
                        item.get("id")
                        for section in content_diagnostics.get("sections", [])
                        for item in section.get("tactical_items", [])
                        if item.get("id")
                    ][:20],
                    "blocked_claims": [
                        claim
                        for section in content_diagnostics.get("sections", [])
                        for claim in section.get("blocked_claims", [])
                    ][:20],
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
