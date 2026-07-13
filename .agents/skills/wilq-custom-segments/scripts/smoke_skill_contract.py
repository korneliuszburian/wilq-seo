#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from custom_segment_assertions import validate_candidate_contract, validate_context_contract
from custom_segments_report import build_report
from custom_segments_runtime import (
    collect_connector_results,
    compact_brief_items,
    validate_polish_instruction,
)

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json

SKILL_NAME = "wilq-custom-segments"
REQUIRED_CONNECTORS = ["google_ads", "google_search_console"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "ads_diagnostics",
}
CUSTOM_SEGMENT_ACTION_ID = "act_prepare_custom_segments_from_search_terms"


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

    ads_diagnostics = request_json(args.api_base, "GET", "/api/ads/diagnostics")
    (
        pack_ads_diagnostics,
        pack_custom_segments_read_contract,
        pack_ads_action_ids,
        active_action_ids,
        decision_ids,
    ) = validate_context_contract(pack, ads_diagnostics, CUSTOM_SEGMENT_ACTION_ID)

    custom_segments_read_contract = ads_diagnostics.get("custom_segments_read_contract") or {}
    pack_custom_segments_read_contract = (
        pack_ads_diagnostics.get("custom_segments_read_contract") or {}
    )
    if pack_custom_segments_read_contract.get("id") != custom_segments_read_contract.get("id"):
        raise SystemExit("Context pack custom_segments_read_contract differs from endpoint")
    if custom_segments_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Custom segments read contract must be ready or blocked")
    if not custom_segments_read_contract.get("blocked_claims"):
        raise SystemExit("Custom segments read contract must expose blocked claims")
    audience_forecast_contract = (
        custom_segments_read_contract.get("audience_forecast_read_contract") or {}
    )
    if audience_forecast_contract.get("id") != (
        "ads_custom_segment_audience_forecast_read_contract"
    ):
        raise SystemExit("Custom segments must expose audience forecast read contract")
    if audience_forecast_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Audience forecast read contract must be ready or blocked")
    if "rozmiar odbiorców" not in (audience_forecast_contract.get("blocked_claims") or []):
        raise SystemExit("Audience forecast contract must block rozmiar odbiorców claims")

    custom_segment_candidates = custom_segments_read_contract.get("candidates") or []
    custom_segment_action_validation, action_validations, safety_review = (
        validate_candidate_contract(
            args.api_base,
            custom_segments_read_contract,
            audience_forecast_contract,
            custom_segment_candidates,
            pack_ads_action_ids,
            active_action_ids,
            decision_ids,
            CUSTOM_SEGMENT_ACTION_ID,
            request_json,
        )
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
                ads_diagnostics,
                custom_segments_read_contract,
                audience_forecast_contract,
                custom_segment_candidates,
                safety_review,
                custom_segment_action_validation,
                action_validations,
                brief_items,
                pack,
                decision_ids,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
