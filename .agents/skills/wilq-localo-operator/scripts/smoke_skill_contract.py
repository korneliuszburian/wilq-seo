#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-localo-operator"
REQUIRED_CONNECTORS = ["localo"]
LOCALO_VISIBILITY_REVIEW_ACTION_ID = "act_review_localo_visibility_facts"
LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT = "local_visibility_review_preview_v1"
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "localo_diagnostics",
}


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


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

    request_json(
        args.api_base,
        "POST",
        "/api/connectors/localo/refresh",
        {"mode": "vendor_read", "reason": "Localo skill smoke MCP OAuth blocker proof"},
    )
    pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    localo_diagnostics = pack.get("localo_diagnostics") or {}
    access_probe = localo_diagnostics.get("access_probe") or {}
    decision_queue = localo_diagnostics.get("decision_queue") or []
    decision_ids = {decision.get("id") for decision in decision_queue}
    if access_probe.get("status") not in {"access_ready", "access_blocked", "unknown"}:
        raise SystemExit(f"Unexpected Localo access status: {access_probe.get('status')}")
    if not localo_diagnostics.get("evidence_ids"):
        raise SystemExit("Localo diagnostics must expose evidence IDs")
    if not decision_queue:
        raise SystemExit("Localo diagnostics must expose a decision queue")

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    action_objects = pack.get("active_action_objects") or []
    localo_actions = [
        action
        for action in action_objects
        if action.get("id") == LOCALO_VISIBILITY_REVIEW_ACTION_ID
    ]
    localo_action_preview_contract: str | None = None
    localo_preview_metric_names: list[str] = []
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
        if any(
            connector in REQUIRED_CONNECTORS
            for connector in item.get("source_connectors", [])
        )
    ][:8]
    localo_blockers = [
        item
        for item in brief_items
        if item.get("kind") == "blocker"
        and any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ]
    if any(item.get("metric_facts") for item in localo_blockers):
        raise SystemExit("Localo blocker must not expose Localo ranking metric facts")

    localo_refresh_runs = [
        run
        for run in pack.get("connector_refresh_runs", [])
        if run.get("connector_id") == "localo"
    ]
    latest_localo_run = localo_refresh_runs[0] if localo_refresh_runs else None
    if latest_localo_run is None:
        raise SystemExit("Context pack does not expose any Localo refresh run")
    if latest_localo_run.get("status") not in {"blocked", "completed"}:
        raise SystemExit(f"Unexpected Localo refresh status: {latest_localo_run.get('status')}")
    metric_summary = latest_localo_run.get("metric_summary") or {}
    if metric_summary.get("api") != "localo_mcp_oauth_probe":
        raise SystemExit("Latest Localo run is not the MCP OAuth probe")
    if latest_localo_run.get("status") == "blocked":
        if metric_summary.get("access_token_present") != 0:
            raise SystemExit("Blocked Localo OAuth probe must report access_token_present=0")
        if metric_summary.get("mcp_initialize_status") != 401:
            raise SystemExit("Blocked Localo OAuth probe must report MCP initialize 401")
        if "localo_fix_access_before_visibility_review" not in decision_ids:
            raise SystemExit("Blocked Localo diagnostics must expose the access repair decision")
    if latest_localo_run.get("status") == "completed":
        if metric_summary.get("mcp_initialize_status") != 200:
            raise SystemExit("Completed Localo OAuth probe must report MCP initialize 200")
        if access_probe.get("status") != "access_ready":
            raise SystemExit("Completed Localo OAuth probe must produce access_ready diagnostics")
        localo_metric_facts = [
            fact
            for decision in decision_queue
            for fact in decision.get("metric_facts", [])
        ]
        if metric_summary.get("localo_read_contract_count"):
            if "localo_review_visibility_facts" not in decision_ids:
                raise SystemExit("Localo value facts must expose a visibility review decision")
            if "localo_block_visibility_claims_without_read_contract" not in decision_ids:
                raise SystemExit("Partial Localo value facts must keep blocked-claim decision")
            review_decision: dict[str, Any] = next(
                (
                    decision
                    for decision in decision_queue
                    if decision.get("id") == "localo_review_visibility_facts"
                ),
                {},
            )
            allowed_evidence = set(review_decision.get("allowed_evidence") or [])
            if not {"place_inventory", "local_rankings", "reviews"}.issubset(
                allowed_evidence
            ):
                raise SystemExit("Localo value review is missing aggregate evidence contracts")
            missing_contracts = set(review_decision.get("missing_read_contracts") or [])
            unsupported_contracts = {"local_tasks"}
            if "gbp_visibility" not in allowed_evidence:
                unsupported_contracts.add("gbp_visibility")
            if "competitor_visibility" not in allowed_evidence:
                unsupported_contracts.add("competitor_visibility")
            if not unsupported_contracts.issubset(missing_contracts):
                raise SystemExit("Localo value review must keep unsupported contracts missing")
            blocked_claims = set(review_decision.get("blocked_claims") or [])
            unsupported_claims = {"local visibility uplift"}
            if "gbp_visibility" not in allowed_evidence:
                unsupported_claims.add("GBP performance")
            if "competitor_visibility" not in allowed_evidence:
                unsupported_claims.add("competitor visibility")
            if not unsupported_claims.issubset(blocked_claims):
                raise SystemExit("Localo value review must block unsupported marketing claims")
            if not localo_metric_facts:
                raise SystemExit("Localo value review must expose aggregate metric facts")
            if not localo_actions:
                raise SystemExit("Localo value review must expose review ActionObject")
            localo_action = localo_actions[0]
            payload = localo_action.get("payload") or {}
            payload_preview = payload.get("payload_preview") or []
            if not isinstance(payload_preview, list) or not payload_preview:
                raise SystemExit("Localo review ActionObject must expose payload_preview")
            preview = payload_preview[0]
            if preview.get("preview_contract") != LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT:
                raise SystemExit(
                    "Localo review ActionObject must expose "
                    f"{LOCALO_VISIBILITY_REVIEW_PREVIEW_CONTRACT}"
                )
            if preview.get("apply_allowed") is not False:
                raise SystemExit("Localo review payload preview must keep apply_allowed=false")
            if preview.get("api_mutation_ready") is not False:
                raise SystemExit(
                    "Localo review payload preview must keep api_mutation_ready=false"
                )
            metric_snapshot = preview.get("metric_snapshot") or {}
            if not isinstance(metric_snapshot, dict) or not metric_snapshot:
                raise SystemExit("Localo review payload preview must include metric_snapshot")
            localo_action_preview_contract = str(preview.get("preview_contract"))
            localo_preview_metric_names = sorted(str(name) for name in metric_snapshot)
            redacted_metric_names = [
                fact.get("name") for fact in localo_metric_facts if fact.get("name") == "[REDACTED]"
            ]
            if redacted_metric_names:
                raise SystemExit("Localo metric fact names must not be redacted")
        else:
            if "localo_access_ready_wait_for_visibility_facts" not in decision_ids:
                raise SystemExit("Access-ready Localo diagnostics must wait for visibility facts")
            if "localo_block_visibility_claims_without_read_contract" not in decision_ids:
                raise SystemExit("Access-ready Localo diagnostics must block visibility claims")
            if localo_metric_facts:
                raise SystemExit(
                    "Localo OAuth probe is not ranking/GBP evidence "
                    "and must not create metric facts"
                )

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

    instruction = str(pack.get("strict_instruction", "")).lower()
    if "must not invent metrics" not in instruction or "evidence" not in instruction:
        raise SystemExit("Context pack strict instruction does not include evidence guardrails")
    action_validations = []
    active_action_ids = [
        action.get("id") for action in pack.get("active_action_objects", [])
    ]
    if LOCALO_VISIBILITY_REVIEW_ACTION_ID in active_action_ids:
        quoted_action = urllib.parse.quote(LOCALO_VISIBILITY_REVIEW_ACTION_ID, safe="")
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
            raise SystemExit(f"Localo ActionObject validation failed: {validation}")

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "brief_items": brief_items,
                "localo_refresh_status": latest_localo_run.get("status"),
                "localo_metric_summary": metric_summary,
                "localo_access_status": access_probe.get("status"),
                "localo_decision_ids": sorted(
                    decision_id for decision_id in decision_ids if decision_id
                ),
                "localo_action_preview_contract": localo_action_preview_contract,
                "localo_preview_metric_names": localo_preview_metric_names[:20],
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
