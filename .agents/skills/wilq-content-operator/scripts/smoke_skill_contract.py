#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.skill_smoke_harness import request_json

SKILL_NAME = "wilq-content-operator"
DEV_HOST = "ekologus.dev.proudsite.pl"


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    return value


def assert_false_everywhere(value: Any, key: str) -> None:
    if isinstance(value, dict):
        if value.get(key) is True:
            raise SystemExit(f"Content workflow must not expose {key}=true")
        for child in value.values():
            assert_false_everywhere(child, key)
    elif isinstance(value, list):
        for child in value:
            assert_false_everywhere(child, key)


def select_candidate(queue: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in require_list(queue.get("candidates"), "content queue candidates")
        if isinstance(candidate, dict)
    ]
    if queue.get("candidate_count") != len(candidates) or not candidates:
        raise SystemExit("Content queue must expose at least one counted candidate")
    selected = next(
        (candidate for candidate in candidates if candidate.get("recommended_mode") != "block"),
        candidates[0],
    )
    if not selected.get("work_item_id"):
        raise SystemExit("Selected candidate must expose work_item_id")
    if selected.get("recommended_mode") != "block" and (
        not selected.get("evidence_ids") or not selected.get("source_connectors")
    ):
        raise SystemExit("Actionable candidate needs evidence IDs and source connectors")
    final_url = selected.get("final_canonical_url") or selected.get("intended_final_url")
    if final_url and DEV_HOST in str(final_url):
        raise SystemExit("Dev URL cannot be final canonical")
    return selected


def validate_queue_actions(api_base: str, selected: dict[str, Any]) -> list[str]:
    if selected.get("recommended_mode") == "block":
        return []
    validated: list[str] = []
    for raw_action_id in selected.get("action_ids") or []:
        action_id = str(raw_action_id)
        encoded = urllib.parse.quote(action_id, safe="")
        result = require_dict(
            request_json(api_base, "POST", f"/api/actions/{encoded}/validate"),
            f"action validation {action_id}",
        )
        if result.get("valid") is not True:
            raise SystemExit(f"Selected action {action_id} did not validate")
        validated.append(action_id)
    if not validated:
        raise SystemExit("Actionable candidate needs a validated ActionObject")
    return validated


def validate_snapshot(snapshot: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    if snapshot.get("response_type") != "workflow_snapshot":
        raise SystemExit("Selected work item must expose a workflow snapshot")
    item = require_dict(snapshot.get("preflight", {}).get("item"), "preflight item")
    if item.get("id") != work_item_id:
        raise SystemExit("Selected snapshot work_item_id mismatch")

    steps = require_list(snapshot.get("operator_steps"), "operator steps")
    expected_steps = ["scope", "section_map", "draft", "review", "dev_draft"]
    if [step.get("id") for step in steps if isinstance(step, dict)] != expected_steps:
        raise SystemExit("Snapshot must expose the canonical five-step journey")
    if snapshot.get("current_step_id") not in expected_steps:
        raise SystemExit("Snapshot current_step_id is outside the canonical journey")

    planning = require_dict(snapshot.get("planning_workspace"), "planning workspace")
    proposal = require_dict(planning.get("proposal"), "planning proposal")
    demand = require_dict(proposal.get("search_demand"), "search demand")
    for row in demand.get("gsc_query_rows") or []:
        validate_gsc_query_row(require_dict(row, "GSC query row"))
    if (demand.get("ads_term_rows") or demand.get("keyword_planner_rows")) and demand.get(
        "optional_ads_status"
    ) != "exact_rows_available":
        raise SystemExit("Ads/Planner rows require exact mapping status")

    revision = require_dict(snapshot.get("revision_workspace"), "revision workspace")
    latest_revision = revision.get("latest_revision")
    handoff = snapshot.get("wordpress_handoff", {}).get("handoff_result", {}).get("handoff")
    if handoff is not None:
        binding = require_dict(handoff.get("revision_binding"), "revision binding")
        if not latest_revision or binding.get("revision_id") != latest_revision.get("revision_id"):
            raise SystemExit("WordPress handoff must bind the latest exact revision")

    for key in ("publish_ready", "publish_allowed", "destructive_update_allowed"):
        assert_false_everywhere(snapshot, key)
    return {
        "current_step_id": snapshot.get("current_step_id"),
        "planning_digest": proposal.get("planning_digest"),
        "scope_current": planning.get("scope_current"),
        "section_map_current": planning.get("section_map_current"),
        "gsc_query_row_count": len(demand.get("gsc_query_rows") or []),
        "ads_term_row_count": len(demand.get("ads_term_rows") or []),
        "keyword_planner_row_count": len(demand.get("keyword_planner_rows") or []),
        "revision_status": revision.get("status"),
        "latest_revision_id": (
            None if latest_revision is None else latest_revision.get("revision_id")
        ),
        "handoff_revision_bound": handoff is not None,
        "evidence_ids": item.get("evidence_ids") or [],
        "source_connectors": item.get("source_connectors") or [],
    }


def validate_gsc_query_row(row: dict[str, Any]) -> None:
    if (
        row.get("source_connector") != "google_search_console"
        or not row.get("evidence_ids")
        or not row.get("period")
        or not row.get("freshness")
    ):
        raise SystemExit("GSC row needs source, evidence, period and freshness")
    mapping_status = row.get("section_mapping_status")
    section_headings = row.get("section_headings")
    if mapping_status == "lexical_relevance" and not section_headings:
        raise SystemExit("Lexically mapped GSC row needs at least one section")
    if mapping_status == "page_only" and section_headings:
        raise SystemExit("Page-only GSC row cannot claim a section mapping")
    if not section_headings and mapping_status != "page_only":
        raise SystemExit("Unmapped GSC row must be explicitly page-only")


def read_wordpress_boundary(api_base: str, work_item_id: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"work_item_id": work_item_id})
    activation = require_dict(
        request_json(
            api_base,
            "GET",
            f"/api/content/wordpress/draft-activation-packet?{query}",
        ),
        "WordPress activation packet",
    )
    readiness = require_dict(
        request_json(api_base, "GET", "/api/content/wordpress/draft-write-readiness"),
        "WordPress write readiness",
    )
    for value in (activation, readiness):
        for key in ("publish_allowed", "destructive_update_allowed"):
            assert_false_everywhere(value, key)
    return {
        "action_id": activation.get("action_id"),
        "activation_missing_step": activation.get("activation_missing_step"),
        "activation_next_step": activation.get("operator_next_step"),
        "handoff_ready": activation.get("handoff_ready"),
        "write_ready": readiness.get("ready"),
        "write_authorization_status": readiness.get("write_authorization_status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    health = require_dict(request_json(args.api_base, "GET", "/api/health"), "health")
    if health.get("status") != "ok":
        raise SystemExit("WILQ API health is not ok")
    queue = require_dict(
        request_json(args.api_base, "GET", "/api/content/work-items/queue"),
        "content queue",
    )
    selected = select_candidate(queue)
    work_item_id = str(selected["work_item_id"])
    validated_action_ids = validate_queue_actions(args.api_base, selected)

    summary: dict[str, Any] = {
        "skill": SKILL_NAME,
        "queue_status": queue.get("queue_status"),
        "candidate_count": queue.get("candidate_count"),
        "selected_work_item_id": work_item_id,
        "selected_mode": selected.get("recommended_mode"),
        "selected_action_ids": selected.get("action_ids") or [],
        "selected_validated_action_ids": validated_action_ids,
    }
    if selected.get("recommended_mode") == "block":
        summary.update(
            workflow_blocked=True,
            safe_next_step=selected.get("safe_next_step"),
            evidence_ids=selected.get("evidence_ids") or [],
            source_connectors=selected.get("source_connectors") or [],
        )
    else:
        snapshot = require_dict(
            request_json(
                args.api_base,
                "GET",
                f"/api/content/work-items/{urllib.parse.quote(work_item_id, safe='')}/snapshot",
            ),
            "content workflow snapshot",
        )
        summary.update(validate_snapshot(snapshot, work_item_id))
        summary["wordpress_boundary"] = read_wordpress_boundary(args.api_base, work_item_id)
        summary["workflow_blocked"] = snapshot.get("current_step_id") != "dev_draft"

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
