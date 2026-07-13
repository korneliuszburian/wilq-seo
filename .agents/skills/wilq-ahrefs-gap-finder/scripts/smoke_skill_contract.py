#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from ahrefs_contract_assertions import validate_ahrefs_contract
from ahrefs_report import build_report
from ahrefs_runtime import (
    collect_action_validations,
    collect_connector_results,
    compact_brief_items,
    validate_polish_instruction,
)

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json

SKILL_NAME = "wilq-ahrefs-gap-finder"
CONTENT_REFRESH_ACTION_ID = "act_prepare_content_refresh_queue"
REQUIRED_CONNECTORS = ["ahrefs", "google_search_console", "wordpress_ekologus"]
REQUIRED_CONTEXT_KEYS = {
    "ahrefs_diagnostics",
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health", timeout_seconds=args.timeout_seconds)
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(
        args.api_base,
        "POST",
        "/api/codex/context-pack",
        {"skill": SKILL_NAME},
        timeout_seconds=args.timeout_seconds,
    )
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")
    (
        ahrefs_diagnostics,
        gap_contract,
        decision_ids,
        gap_records,
        gap_record_count,
        freshness_states,
        freshness_labels,
    ) = validate_ahrefs_contract(pack)
    operator_summary = ahrefs_diagnostics.get("operator_summary") or {}
    missing_read_contracts = gap_contract.get("missing_read_contracts") or []
    cross_check_status = gap_contract.get("cross_check_status")
    diagnostics_action_ids = ahrefs_diagnostics.get("action_ids") or []
    action_validations = collect_action_validations(
        args.api_base, diagnostics_action_ids, request_json, args.timeout_seconds
    )
    context_action_ids = [
        item.get("id")
        for item in (pack.get("active_action_objects") or [])
        if isinstance(item, dict) and item.get("id")
    ]
    if cross_check_status == "api_backed":
        if CONTENT_REFRESH_ACTION_ID not in diagnostics_action_ids:
            raise SystemExit(
                "Ahrefs diagnostics must expose content refresh handoff when "
                "cross-check is API-backed"
            )
        if CONTENT_REFRESH_ACTION_ID not in operator_summary.get("review_action_ids", []):
            raise SystemExit(
                "Ahrefs operator summary must expose content refresh review action "
                "when cross-check is API-backed"
            )
        if CONTENT_REFRESH_ACTION_ID not in str(operator_summary.get("review_next_safe_click", "")):
            raise SystemExit("Ahrefs operator summary must name the safe content refresh click")
        if not action_validations.get(CONTENT_REFRESH_ACTION_ID, {}).get("valid"):
            raise SystemExit("Ahrefs content refresh action must validate as valid")
        if CONTENT_REFRESH_ACTION_ID not in context_action_ids:
            raise SystemExit(
                "Ahrefs context pack must expose content refresh ActionObject when "
                "cross-check is API-backed"
            )
    if not diagnostics_action_ids and context_action_ids:
        raise SystemExit(
            "Ahrefs context pack must not expose adjacent actions when "
            f"diagnostics action_ids is empty: {context_action_ids}"
        )

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief_items = compact_brief_items(brief, REQUIRED_CONNECTORS)
    connector_results = collect_connector_results(args.api_base, REQUIRED_CONNECTORS, request_json)

    validate_polish_instruction(pack, has_polish_metric_source_guardrails)

    print(
        json.dumps(
            build_report(
                health,
                args.api_base,
                connector_results,
                brief_items,
                pack,
                ahrefs_diagnostics,
                gap_contract,
                gap_record_count,
                missing_read_contracts,
                cross_check_status,
                freshness_states,
                freshness_labels,
                operator_summary,
                diagnostics_action_ids,
                action_validations,
                decision_ids,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
