#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from gsc_refresh_contract import read_latest_gsc_refresh_contract

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    require_polish_language,
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
    freshness_assessment = content_diagnostics.get("freshness_assessment")
    if not isinstance(freshness_assessment, dict):
        raise SystemExit("Content diagnostics must expose freshness_assessment")
    if freshness_assessment.get("state") not in {"fresh", "stale", "missing", "blocked"}:
        raise SystemExit("Content diagnostics freshness_assessment has invalid state")
    if not str(freshness_assessment.get("state_label") or "").strip():
        raise SystemExit("Content diagnostics freshness_assessment state_label is missing")
    if not str(freshness_assessment.get("summary") or "").strip():
        raise SystemExit("Content diagnostics freshness_assessment summary is missing")
    if not str(freshness_assessment.get("next_step") or "").strip():
        raise SystemExit("Content diagnostics freshness_assessment next_step is missing")
    if freshness_assessment.get("requires_refresh") is True and not (
        freshness_assessment.get("connector_labels_requiring_refresh") or []
    ):
        raise SystemExit(
            "Content diagnostics freshness_assessment requires refresh but lists no connectors"
        )
    packed_content = pack.get("content_diagnostics", {})
    packed_evidence_ids = packed_content.get("evidence_ids") or []
    endpoint_evidence_ids = content_diagnostics.get("evidence_ids") or []
    latest_gsc_refresh_summary, latest_gsc_refresh_evidence_id = read_latest_gsc_refresh_contract(
        args.api_base
    )
    if content_diagnostics.get("live_data_available") is True:
        if not isinstance(api_gsc_contract, dict):
            raise SystemExit("Content diagnostics must expose GSC Search Analytics contract")
        if api_gsc_contract.get("data_availability_checked") is not True:
            raise SystemExit("Content diagnostics GSC contract must check date availability")
        if api_gsc_contract.get("date_availability_status") != "available":
            raise SystemExit("Content diagnostics GSC contract must record available status")
        if api_gsc_contract.get("search_type") != "web":
            raise SystemExit("Content diagnostics GSC contract must pin search_type=web")
        if api_gsc_contract.get("detail_dimensions") != "query,page":
            raise SystemExit("Content diagnostics GSC contract must expose query,page dimensions")
        if api_gsc_contract.get("detail_data_completeness") != "partial_possible":
            raise SystemExit(
                "Content diagnostics GSC contract must expose partial_possible completeness"
            )
        if api_gsc_contract.get("aggregate_dimensions") != "country,device":
            raise SystemExit("Content diagnostics GSC contract must expose aggregate dimensions")
        if api_gsc_contract.get("aggregate_aggregation_type") != "byProperty":
            raise SystemExit("Content diagnostics GSC contract must expose byProperty aggregate")
        if (
            api_gsc_contract.get("aggregate_data_completeness")
            != "aggregate_without_query_page_dimensions"
        ):
            raise SystemExit(
                "Content diagnostics GSC contract must distinguish aggregate completeness"
            )
        if not str(api_gsc_contract.get("aggregate_summary_label") or "").strip():
            raise SystemExit("Content diagnostics GSC contract aggregate_summary_label is missing")
        if api_gsc_contract.get("expected_data_delay_days_min") != 2:
            raise SystemExit("Content diagnostics GSC contract must expose 2-day delay minimum")
        if api_gsc_contract.get("expected_data_delay_days_max") != 3:
            raise SystemExit("Content diagnostics GSC contract must expose 3-day delay maximum")
        if api_gsc_contract.get("read_granularity") != "single_day_latest_available":
            raise SystemExit("Content diagnostics GSC contract must expose single-day reads")
        if api_gsc_contract.get("api_recommended_page_size") != 25000:
            raise SystemExit("Content diagnostics GSC contract must expose official 25k page size")
        if api_gsc_contract.get("api_daily_row_cap_per_search_type") != 50000:
            raise SystemExit("Content diagnostics GSC contract must expose official 50k row cap")
        if not str(api_gsc_contract.get("summary_label") or "").strip():
            raise SystemExit("Content diagnostics GSC contract summary_label is missing")
        if "nie pełną sumą całego ruchu" not in str(
            api_gsc_contract.get("partial_detail_warning_label") or ""
        ):
            raise SystemExit("Content diagnostics GSC contract must warn about partial totals")
        if "25 000 wierszy" not in str(api_gsc_contract.get("official_limits_label") or ""):
            raise SystemExit("Content diagnostics GSC contract must explain official paging")
        if "rowLimit=" not in str(api_gsc_contract.get("wilq_internal_cap_label") or ""):
            raise SystemExit("Content diagnostics GSC contract must explain WILQ internal cap")
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
    if not set(packed_evidence_ids).issubset(set(endpoint_evidence_ids)):
        raise SystemExit("Context pack content_diagnostics evidence IDs are not endpoint subset")
    if any("_ahrefs" in str(evidence_id) for evidence_id in packed_evidence_ids):
        raise SystemExit("GSC context pack must not include Ahrefs evidence IDs")
    if packed_content.get("action_ids") != content_diagnostics.get("action_ids"):
        raise SystemExit("Context pack content_diagnostics action IDs differ from endpoint")
    packed_decision_trace = _decision_trace(packed_content.get("decision_queue"))
    endpoint_decision_trace = _decision_trace(content_diagnostics.get("decision_queue"))
    if not packed_decision_trace:
        raise SystemExit("GSC context pack must expose scoped content decisions")
    endpoint_decision_ids = {str(item.get("id")) for item in endpoint_decision_trace}
    if any(str(item.get("id")) not in endpoint_decision_ids for item in packed_decision_trace):
        raise SystemExit("GSC context pack decision_queue must be endpoint subset")
    if any(
        item.get("decision_type") == "review_ahrefs_gap_records"
        or "ahrefs" in item.get("source_connectors", [])
        for item in packed_decision_trace
    ):
        raise SystemExit("GSC context pack must not include Ahrefs decisions")
    compaction = packed_content.get("context_pack_compaction") or {}
    if compaction.get("purpose") != "gsc_content_doctor_context":
        raise SystemExit("GSC context pack compaction purpose is missing")
    if compaction.get("ahrefs_decisions_removed") is not True:
        raise SystemExit("GSC context pack must mark removed Ahrefs decisions")

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
    action_validations = []
    if CONTENT_ACTION_ID in action_ids:
        quoted_action = urllib.parse.quote(CONTENT_ACTION_ID, safe="")
        validation = request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"GSC content action validation failed: {validation}")

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


def _decision_trace(decisions: Any) -> list[dict[str, Any]]:
    if not isinstance(decisions, list):
        return []
    return [
        {
            "id": item.get("id"),
            "decision_type": item.get("decision_type"),
            "page": item.get("page"),
            "normalized_page_path": item.get("normalized_page_path"),
            "queries": item.get("queries", []),
            "wordpress_match": item.get("wordpress_match"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
        }
        for item in decisions
        if isinstance(item, dict)
    ]


if __name__ == "__main__":
    raise SystemExit(main())
