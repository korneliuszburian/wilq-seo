#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-demand-gen-operator"
REQUIRED_CONNECTORS = ["google_ads", "google_analytics_4"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "demand_gen_readiness",
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

    readiness = pack.get("demand_gen_readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("Context pack demand_gen_readiness must be an object")
    if readiness.get("status") != "blocked":
        raise SystemExit("Demand Gen must stay blocked until specific evidence exists")
    title = readiness.get("title")
    if not isinstance(title, str) or not title.startswith("Demand Gen:"):
        raise SystemExit("Demand Gen readiness must expose a marketer-facing title")
    missing_read_contracts = readiness.get("missing_read_contracts")
    if not isinstance(missing_read_contracts, list) or not missing_read_contracts:
        raise SystemExit("Demand Gen readiness must expose missing read contracts")
    campaign_rows_evaluated = readiness.get("campaign_rows_evaluated")
    if not isinstance(campaign_rows_evaluated, int):
        raise SystemExit("Demand Gen readiness must expose campaign_rows_evaluated")
    campaign_channel_counts = readiness.get("campaign_channel_counts")
    if not isinstance(campaign_channel_counts, dict):
        raise SystemExit("Demand Gen readiness must expose campaign_channel_counts")
    metric_tiles = readiness.get("metric_tiles")
    if not isinstance(metric_tiles, dict):
        raise SystemExit("Demand Gen readiness must expose metric_tiles")
    if metric_tiles.get("kampanie Ads") != campaign_rows_evaluated:
        raise SystemExit("Demand Gen metric tiles must include evaluated campaign count")
    if metric_tiles.get("braki") != len(missing_read_contracts):
        raise SystemExit("Demand Gen metric tiles must include missing contract count")
    if campaign_rows_evaluated > 0 and not campaign_channel_counts:
        raise SystemExit("Demand Gen readiness must count campaign channels when rows exist")
    if campaign_rows_evaluated > 0 and "demand_gen_campaign_rows" in missing_read_contracts:
        raise SystemExit(
            "Demand Gen campaign rows must not be missing when Ads campaign channels exist"
        )
    demand_gen_campaign_rows = readiness.get("demand_gen_campaign_rows")
    if not isinstance(demand_gen_campaign_rows, list):
        raise SystemExit("Demand Gen readiness must expose demand_gen_campaign_rows list")
    if "[REDACTED]" in json.dumps(readiness):
        raise SystemExit("Demand Gen readiness contract IDs must not be redacted")
    active_actions = pack.get("active_action_objects") or []
    if active_actions:
        raise SystemExit("Demand Gen context must not expose adjacent ActionObjects as active")
    ads_diagnostics = pack.get("ads_diagnostics") or {}
    if ads_diagnostics.get("action_ids"):
        raise SystemExit("Demand Gen Ads diagnostics must not expose adjacent Ads action IDs")

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "demand_gen_readiness": {
                    "status": readiness.get("status"),
                    "title": title,
                    "metric_tiles": metric_tiles,
                    "campaign_rows_evaluated": campaign_rows_evaluated,
                    "campaign_channel_counts": campaign_channel_counts,
                    "demand_gen_campaign_row_count": len(demand_gen_campaign_rows),
                    "missing_read_contracts": missing_read_contracts,
                    "blocked_claims": readiness.get("blocked_claims", []),
                },
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
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
