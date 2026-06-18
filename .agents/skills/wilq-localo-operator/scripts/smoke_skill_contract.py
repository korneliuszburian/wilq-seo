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
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
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
        if not localo_blockers:
            raise SystemExit("MarketingBrief does not expose a Localo blocker item")
        if not any("LOCALO_ACCESS_TOKEN" in json.dumps(item) for item in localo_blockers):
            raise SystemExit("Localo blocker does not name missing LOCALO_ACCESS_TOKEN")
    if latest_localo_run.get("status") == "completed":
        if metric_summary.get("mcp_initialize_status") != 200:
            raise SystemExit("Completed Localo OAuth probe must report MCP initialize 200")
        localo_metric_facts = [
            item
            for item in brief_items
            if item.get("kind") != "blocker" and item.get("metric_facts")
        ]
        if localo_metric_facts:
            raise SystemExit(
                "Localo OAuth probe is not ranking/GBP evidence and must not create metric facts"
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
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
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
