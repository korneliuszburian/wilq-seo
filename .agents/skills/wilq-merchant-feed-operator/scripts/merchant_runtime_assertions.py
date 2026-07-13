from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from typing import Any


def validate_action_ids(
    api_base: str, action_ids: list[Any], request_json: Callable[..., dict[str, Any]]
) -> list[dict[str, Any]]:
    results = []
    for action_id in action_ids:
        quoted_action = urllib.parse.quote(str(action_id), safe="")
        validation = request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")
        result = {
            "action_id": validation.get("action_id"),
            "valid": validation.get("valid"),
            "status": validation.get("status"),
            "errors": validation.get("errors", []),
        }
        if result["valid"] is not True or result["status"] != "valid":
            raise SystemExit(f"Merchant action validation failed: {validation}")
        results.append(result)
    return results


def compact_brief_items(
    brief: dict[str, Any], required_connectors: list[str]
) -> list[dict[str, Any]]:
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


def collect_connector_results(
    api_base: str,
    connectors: list[str],
    request_json: Callable[..., dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for connector in connectors:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(api_base, "GET", f"/api/connectors/{quoted}/status")
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
