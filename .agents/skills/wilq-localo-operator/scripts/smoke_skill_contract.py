#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

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


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


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



def has_polish_metric_source_guardrails(value: str) -> bool:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")
    return "metryk" in normalized and "dowod" in normalized and "zrodl" in normalized

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
        if any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ][:8]
    localo_blockers = [
        item
        for item in brief_items
        if item.get("kind") == "blocker"
        and any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ]
    if any(item.get("metric_facts") for item in localo_blockers):
        raise SystemExit("Localo blocker must not expose Localo ranking metric facts")

    latest_localo_run, latest_localo_run_source = latest_localo_run_from_pack(
        pack,
        localo_diagnostics,
    )
    if latest_localo_run is None:
        if access_probe.get("status") != "unknown":
            raise SystemExit("Missing Localo refresh run is allowed only for unknown access status")
        if "localo_fix_access_before_visibility_review" not in decision_ids:
            raise SystemExit("Missing Localo refresh run must expose the access review decision")
        if "localo_block_visibility_claims_without_read_contract" not in decision_ids:
            raise SystemExit("Missing Localo refresh run must keep visibility claims blocked")
        latest_localo_run_source = "clean_runtime_without_refresh"
        latest_localo_run_status = "missing"
    else:
        latest_localo_run_status = str(latest_localo_run.get("status") or "")
    if latest_localo_run_status not in {"blocked", "completed", "missing"}:
        raise SystemExit(f"Unexpected Localo refresh status: {latest_localo_run_status}")
    raw_metric_summary = latest_localo_run.get("metric_summary") if latest_localo_run else {}
    metric_summary = raw_metric_summary if isinstance(raw_metric_summary, dict) else {}
    if (
        metric_summary.get("api") != "localo_mcp_oauth_probe"
        and latest_localo_run_status != "missing"
    ):
        raise SystemExit("Latest Localo run is not the MCP OAuth probe")
    if latest_localo_run_status == "blocked":
        if metric_summary.get("access_token_present") != 0:
            raise SystemExit("Blocked Localo OAuth probe must report access_token_present=0")
        if metric_summary.get("mcp_initialize_status") != 401:
            raise SystemExit("Blocked Localo OAuth probe must report MCP initialize 401")
        if "localo_fix_access_before_visibility_review" not in decision_ids:
            raise SystemExit("Blocked Localo diagnostics must expose the access repair decision")
    if latest_localo_run_status == "completed":
        if metric_summary.get("mcp_initialize_status") != 200:
            raise SystemExit("Completed Localo OAuth probe must report MCP initialize 200")
        if access_probe.get("status") != "access_ready":
            raise SystemExit("Completed Localo OAuth probe must produce access_ready diagnostics")
        localo_metric_facts = [
            fact for decision in decision_queue for fact in decision.get("metric_facts", [])
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
            if not {"place_inventory", "local_rankings", "reviews"}.issubset(allowed_evidence):
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
            unsupported_claims = {"poprawa widoczności lokalnej"}
            if "gbp_visibility" not in allowed_evidence:
                unsupported_claims.add("wyniki profilu firmy w Google")
            if "competitor_visibility" not in allowed_evidence:
                unsupported_claims.add("widoczność konkurencji")
            if not unsupported_claims.issubset(blocked_claims):
                raise SystemExit("Localo value review must block unsupported marketing claims")
            if not localo_metric_facts:
                raise SystemExit("Localo value review must expose aggregate metric facts")
            if not localo_actions:
                raise SystemExit("Localo value review must expose review action")
            localo_action = localo_actions[0]
            payload = localo_action.get("action_plan") or {}
            payload_preview = payload.get("preview_items") or []
            if not isinstance(payload_preview, list) or not payload_preview:
                raise SystemExit("Localo review action must expose preview_items")
            preview = payload_preview[0]
            if preview.get("apply_status_label") != "zablokowane do sprawdzenia":
                raise SystemExit("Localo review change preview must keep apply_allowed=false")
            if preview.get("write_status_label") != "bez zapisu automatycznego":
                raise SystemExit("Localo review change preview must keep api_mutation_ready=false")
            metric_snapshot = preview.get("metric_tiles") or {}
            if not isinstance(metric_snapshot, dict) or not metric_snapshot:
                raise SystemExit("Localo review change preview must include metric_snapshot")
            localo_action_preview_contract = "action_plan.preview_items"
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

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    action_validations = []
    active_action_ids = [action.get("id") for action in pack.get("active_action_objects", [])]
    if LOCALO_VISIBILITY_REVIEW_ACTION_ID in active_action_ids:
        quoted_action = urllib.parse.quote(LOCALO_VISIBILITY_REVIEW_ACTION_ID, safe="")
        validation = request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")
        full_action = request_json(args.api_base, "GET", f"/api/actions/{quoted_action}")
        full_payload = full_action.get("payload") if isinstance(full_action, dict) else {}
        if isinstance(full_payload, dict) and full_payload.get("preview_contract"):
            localo_action_preview_contract = str(full_payload["preview_contract"])
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Localo action validation failed: {validation}")

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "brief_items": brief_items,
                "localo_refresh_status": latest_localo_run_status,
                "localo_refresh_source": latest_localo_run_source,
                "localo_refresh_attempt_status": (
                    refresh_attempt.get("status") if refresh_attempt else None
                ),
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
