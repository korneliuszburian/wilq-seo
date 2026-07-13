#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from localo_refresh_assertions import (
    validate_localo_diagnostics_contract,
    validate_localo_refresh_contract,
)
from localo_report_compaction import build_localo_smoke_report
from localo_runtime_assertions import (
    collect_connector_results,
    compact_brief_items,
    validate_localo_brief_blockers,
    validate_polish_instruction,
    validate_review_action,
    validate_review_action_linkage,
)

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json

SKILL_NAME = "wilq-localo-operator"
REQUIRED_CONNECTORS = ["localo"]
LOCALO_VISIBILITY_REVIEW_ACTION_ID = "act_review_localo_visibility_facts"
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "localo_diagnostics",
}


def latest_localo_run_from_pack(
    pack: dict[str, Any],
    localo_diagnostics: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    diagnostics_run = localo_diagnostics.get("latest_refresh")
    if isinstance(diagnostics_run, dict) and diagnostics_run.get("connector_id") == "localo":
        return diagnostics_run, "localo_diagnostics.latest_refresh"

    localo_refresh_runs = [
        run for run in pack.get("connector_refresh_runs", []) if run.get("connector_id") == "localo"
    ]
    if localo_refresh_runs:
        return localo_refresh_runs[0], "context_pack.connector_refresh_runs"
    return None, "missing"


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=("Run an explicit Localo data read before validating the skill contract."),
    )
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    refresh_attempt = None
    if args.refresh:
        refresh_attempt = request_json(
            args.api_base,
            "POST",
            "/api/connectors/localo/refresh",
            {"mode": "vendor_read", "reason": "Localo skill smoke MCP contract proof"},
        )
        if refresh_attempt.get("status") == "failed":
            raise SystemExit(
                "Explicit Localo refresh failed before skill contract validation: "
                f"{refresh_attempt.get('summary')}"
            )
        pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    (
        localo_diagnostics,
        access_probe,
        decision_queue,
        decision_ids,
        operator_summary,
        localo_actions,
    ) = validate_localo_diagnostics_contract(pack, LOCALO_VISIBILITY_REVIEW_ACTION_ID)

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    localo_action_preview_contract: str | None = None
    localo_preview_metric_names: list[str] = []
    brief_items = compact_brief_items(brief, REQUIRED_CONNECTORS[0])
    validate_localo_brief_blockers(brief_items, REQUIRED_CONNECTORS[0])

    (
        _,
        latest_localo_run_source,
        latest_localo_run_status,
        metric_summary,
        localo_action_preview_contract,
        localo_preview_metric_names,
    ) = validate_localo_refresh_contract(
        pack, localo_diagnostics, access_probe, decision_ids, localo_actions
    )

    connector_results = collect_connector_results(
        args.api_base, REQUIRED_CONNECTORS[0], request_json
    )

    validate_polish_instruction(pack, has_polish_metric_source_guardrails)
    active_action_ids = [action.get("id") for action in pack.get("active_action_objects", [])]
    action_validations, action_contract = validate_review_action(
        args.api_base, LOCALO_VISIBILITY_REVIEW_ACTION_ID, active_action_ids, request_json
    )
    localo_action_preview_contract = action_contract or localo_action_preview_contract
    review_action_ids = validate_review_action_linkage(
        operator_summary, active_action_ids, LOCALO_VISIBILITY_REVIEW_ACTION_ID
    )

    print(
        json.dumps(
            build_localo_smoke_report(
                api_base=args.api_base,
                health=health,
                connector_results=connector_results,
                brief_items=brief_items,
                latest_status=latest_localo_run_status,
                latest_source=latest_localo_run_source,
                refresh_attempt=refresh_attempt,
                metric_summary=metric_summary,
                access_status=access_probe.get("status"),
                operator_summary={**operator_summary, "review_action_ids": review_action_ids},
                decision_ids=decision_ids,
                preview_contract=localo_action_preview_contract,
                preview_metric_names=localo_preview_metric_names,
                pack=pack,
                action_validations=action_validations,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
