from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from typing import Any


def compact_brief_items(brief: dict[str, Any], connectors: list[str]) -> list[dict[str, Any]]:
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
        if any(connector in connectors for connector in item.get("source_connectors", []))
    ][:8]


def collect_connector_results(
    api_base: str, connectors: list[str], request_json: Callable[..., dict[str, Any]]
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


def validate_polish_instruction(pack: dict[str, Any], guardrail: Callable[[str], bool]) -> None:
    if not guardrail(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
