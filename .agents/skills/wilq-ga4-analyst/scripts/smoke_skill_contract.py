#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-ga4-analyst"
REQUIRED_CONNECTORS = ["google_analytics_4"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "ga4_diagnostics",
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

    ga4_diagnostics = request_json(args.api_base, "GET", "/api/ga4/diagnostics")
    if ga4_diagnostics.get("language") != "pl-PL":
        raise SystemExit("GA4 diagnostics must declare language=pl-PL")
    section_ids = [section.get("id") for section in ga4_diagnostics.get("sections", [])]
    required_sections = {
        "ga4_landing_behavior",
        "ga4_tracking_readiness",
        "ga4_action_safety",
    }
    missing_sections = sorted(required_sections - set(section_ids))
    if missing_sections:
        raise SystemExit(f"GA4 diagnostics missing sections: {', '.join(missing_sections)}")
    context_ga4 = pack.get("ga4_diagnostics") or {}
    if context_ga4.get("evidence_ids") != ga4_diagnostics.get("evidence_ids"):
        raise SystemExit("Context-pack ga4_diagnostics evidence IDs differ from route")
    if context_ga4.get("action_ids") != ga4_diagnostics.get("action_ids"):
        raise SystemExit("Context-pack ga4_diagnostics action IDs differ from route")

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
                "ga4_diagnostics": {
                    "live_data_available": ga4_diagnostics.get("live_data_available"),
                    "landing_group_count": ga4_diagnostics.get("landing_group_count"),
                    "low_engagement_count": ga4_diagnostics.get("low_engagement_count"),
                    "wordpress_match_count": ga4_diagnostics.get("wordpress_match_count"),
                    "blocker_count": ga4_diagnostics.get("blocker_count"),
                    "section_ids": section_ids,
                    "evidence_ids": ga4_diagnostics.get("evidence_ids", [])[:20],
                    "action_ids": ga4_diagnostics.get("action_ids", []),
                    "blocked_claims": sorted(
                        {
                            claim
                            for section in ga4_diagnostics.get("sections", [])
                            for claim in section.get("blocked_claims", [])
                        }
                    ),
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
