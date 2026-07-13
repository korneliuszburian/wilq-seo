from __future__ import annotations

import urllib.parse
from typing import Any

from scripts.skill_smoke_harness import request_json


def compact_ads_brief_items(api_base: str, required_connectors: list[str]) -> list[dict[str, Any]]:
    brief = request_json(api_base, "GET", "/api/marketing/brief")
    return [
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
        if any(connector in required_connectors for connector in item.get("source_connectors", []))
    ][:8]


def compact_connector_statuses(
    api_base: str, required_connectors: list[str]
) -> list[dict[str, Any]]:
    results = []
    for connector in required_connectors:
        status = request_json(
            api_base,
            "GET",
            f"/api/connectors/{urllib.parse.quote(connector, safe='')}/status",
        )
        results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )
    return results
