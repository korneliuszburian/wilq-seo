#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from content_strategy_runtime import load_content_strategy_runtime

SKILL_NAME = "wilq-content-strategist"
REQUIRED_CONNECTORS = [
    "google_search_console",
    "google_analytics_4",
    "ahrefs",
    "wordpress_ekologus",
    "wordpress_sklep",
]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "content_diagnostics",
}
CONTENT_ACTION_ID = "act_prepare_content_refresh_queue"
WORDPRESS_DRAFT_HANDOFF_ACTION_ID = "act_prepare_wordpress_draft_handoff"
CONTENT_ACTION_DECISION_TYPES = {
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "review_ahrefs_gap_records",
}
CURRENT_CONTENT_URL_KEYS = frozenset(
    {
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "preview_url",
    }
)


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    args = parser.parse_args()

    runtime = load_content_strategy_runtime(
        args.api_base,
        timeout_seconds=args.timeout_seconds,
        required_context_keys=REQUIRED_CONTEXT_KEYS,
        required_connectors=REQUIRED_CONNECTORS,
        content_action_id=CONTENT_ACTION_ID,
        content_action_decision_types=CONTENT_ACTION_DECISION_TYPES,
    )
    health = runtime["health"]
    pack = runtime["pack"]
    content_diagnostics = runtime["content_diagnostics"]
    action_validations = runtime["action_validations"]
    brief_items = runtime["brief_items"]
    connector_results = runtime["connector_results"]
    content_brief_preview = runtime["content_brief_preview"]
    validate_context_pack_condensation(pack)
    decision_queue = content_diagnostics.get("decision_queue", [])

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
                "content_diagnostics": {
                    "live_data_available": content_diagnostics.get("live_data_available"),
                    "content_domain_marker": "ekologus.pl",
                    "measurement_blocker_label": "problem pomiaru, nie temat treści",
                    "required_gate_markers": [
                        "inventory_check_before_create",
                        "merge_create_after_inventory_check",
                    ],
                    "query_page_count": content_diagnostics.get("query_page_count"),
                    "matched_inventory_count": content_diagnostics.get("matched_inventory_count"),
                    "blocker_count": content_diagnostics.get("blocker_count"),
                    "operator_summary": content_diagnostics.get("operator_summary", {}),
                    "decision_queue": decision_queue,
                    "decision_types": [
                        item.get("decision_type")
                        for item in decision_queue
                        if isinstance(item, dict)
                    ],
                    "section_ids": [
                        section.get("id") for section in content_diagnostics.get("sections", [])
                    ],
                    "evidence_ids": content_diagnostics.get("evidence_ids", [])[:20],
                    "action_ids": content_diagnostics.get("action_ids", []),
                    "content_brief_preview_type": "content_brief_preview_v1",
                    "content_brief_preview": content_brief_preview,
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
                "action_validations": action_validations,
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


def validate_context_pack_condensation(pack: dict[str, Any]) -> None:
    compaction = pack.get("context_pack_compaction")
    if not isinstance(compaction, dict):
        raise SystemExit("Context pack must expose compaction metadata")
    required_flags = {
        "connector_refresh_runs_compacted",
        "evidence_summaries_compacted",
        "knowledge_card_summaries_compacted",
        "raw_history_omitted",
    }
    missing_flags = sorted(flag for flag in required_flags if compaction.get(flag) is not True)
    if missing_flags:
        raise SystemExit(
            "Context pack compaction is missing required flags: " + ", ".join(missing_flags)
        )
    operator_context = {
        "connector_status": pack.get("connector_status"),
        "connector_refresh_runs": pack.get("connector_refresh_runs"),
        "evidence_summaries": pack.get("evidence_summaries"),
        "knowledge_card_summaries": pack.get("knowledge_card_summaries"),
        "expert_rule_summaries": pack.get("expert_rule_summaries"),
        "active_action_objects": pack.get("active_action_objects"),
        "content_diagnostics_connectors": (pack.get("content_diagnostics") or {}).get("connectors"),
        "content_diagnostics_latest_refreshes": (pack.get("content_diagnostics") or {}).get(
            "latest_refreshes"
        ),
    }
    serialized = json.dumps(operator_context, ensure_ascii=False)
    forbidden_terms = (
        "vendor_read",
        "Read-only",
        "read-only",
        "review-only",
        "ActionObject",
    )
    leaked_terms = [term for term in forbidden_terms if term in serialized]
    if leaked_terms:
        raise SystemExit(
            "Context pack leaked raw history or technical wording: " + ", ".join(leaked_terms)
        )


if __name__ == "__main__":
    raise SystemExit(main())
