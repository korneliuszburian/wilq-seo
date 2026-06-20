#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-ahrefs-gap-finder"
REQUIRED_CONNECTORS = ["ahrefs", "google_search_console", "wordpress_ekologus"]
REQUIRED_CONTEXT_KEYS = {
    "ahrefs_diagnostics",
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
    ahrefs_diagnostics = pack.get("ahrefs_diagnostics")
    if not isinstance(ahrefs_diagnostics, dict):
        raise SystemExit("Context pack ahrefs_diagnostics must be an object")
    if ahrefs_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Ahrefs diagnostics must use pl-PL language contract")
    decision_ids = {
        decision.get("id")
        for decision in ahrefs_diagnostics.get("decision_queue", [])
        if isinstance(decision, dict)
    }
    if not decision_ids:
        raise SystemExit("Ahrefs diagnostics must expose a decision_queue")
    if "ahrefs_block_gap_claims_without_records" not in decision_ids:
        raise SystemExit("Ahrefs diagnostics must explicitly block gap claims without records")
    serialized_ahrefs = json.dumps(ahrefs_diagnostics, ensure_ascii=False)
    for required_term in ("evidence_ids", "missing_read_contracts", "blocked_claims"):
        if required_term not in serialized_ahrefs:
            raise SystemExit(f"Ahrefs diagnostics missing {required_term}")
    diagnostics_action_ids = ahrefs_diagnostics.get("action_ids") or []
    context_action_ids = [
        item.get("id")
        for item in (pack.get("active_action_objects") or [])
        if isinstance(item, dict) and item.get("id")
    ]
    if not diagnostics_action_ids and context_action_ids:
        raise SystemExit(
            "Ahrefs context pack must not expose adjacent ActionObjects when "
            f"diagnostics action_ids is empty: {context_action_ids}"
        )

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
                "ahrefs_authority_fact_count": ahrefs_diagnostics.get(
                    "authority_fact_count"
                ),
                "ahrefs_gap_fact_count": ahrefs_diagnostics.get("gap_fact_count"),
                "ahrefs_blocker_count": ahrefs_diagnostics.get("blocker_count"),
                "ahrefs_decision_ids": sorted(decision_ids),
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
