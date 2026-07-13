from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from typing import Any


def validate_polish_instruction(pack: dict[str, Any], guardrail: Any) -> None:
    if not guardrail(str(pack.get("strict_instruction", ""))):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )


def compact_brief_items(brief: dict[str, Any], connector: str) -> list[dict[str, Any]]:
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
        if connector in item.get("source_connectors", [])
    ][:8]


def validate_localo_brief_blockers(brief_items: list[dict[str, Any]], connector: str) -> None:
    blockers = [
        item
        for item in brief_items
        if item.get("kind") == "blocker" and connector in item.get("source_connectors", [])
    ]
    if any(item.get("metric_facts") for item in blockers):
        raise SystemExit("Localo blocker must not expose Localo ranking metric facts")


def collect_connector_results(
    api_base: str, connector: str, request_json: Callable[..., dict[str, Any]]
) -> list[dict[str, Any]]:
    quoted = urllib.parse.quote(connector, safe="")
    status = request_json(api_base, "GET", f"/api/connectors/{quoted}/status")
    return [
        {
            "id": status.get("id"),
            "status": status.get("status"),
            "configured": status.get("configured"),
            "missing_credentials": status.get("missing_credentials", []),
            "error": status.get("error"),
        }
    ]


def validate_review_action(
    api_base: str,
    action_id: str,
    active_action_ids: list[Any],
    request_json: Callable[..., dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    if action_id not in active_action_ids:
        return [], None
    quoted = urllib.parse.quote(action_id, safe="")
    validation = request_json(api_base, "POST", f"/api/actions/{quoted}/validate")
    full_action = request_json(api_base, "GET", f"/api/actions/{quoted}")
    payload = full_action.get("payload") if isinstance(full_action, dict) else {}
    contract = payload.get("preview_contract") if isinstance(payload, dict) else None
    result = {
        "action_id": validation.get("action_id"),
        "valid": validation.get("valid"),
        "status": validation.get("status"),
        "errors": validation.get("errors", []),
    }
    if result["valid"] is not True or result["status"] != "valid":
        raise SystemExit(f"Localo action validation failed: {validation}")
    return [result], str(contract) if contract else None


def validate_review_action_linkage(
    operator_summary: dict[str, Any], active_action_ids: list[Any], action_id: str
) -> list[Any]:
    review_action_ids = operator_summary.get("review_action_ids") or []
    if action_id in active_action_ids:
        if review_action_ids != [action_id]:
            raise SystemExit("Localo review card must point only to the review action")
    elif review_action_ids:
        raise SystemExit("Localo review card must not invent review action IDs")
    return review_action_ids
