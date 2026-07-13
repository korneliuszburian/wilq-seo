from __future__ import annotations

import urllib.parse
from typing import Any

from content_action_preview import assert_current_content_url_keys, validate_content_action_preview
from content_strategy_assertions import (
    validate_content_decision_queue,
    validate_wordpress_draft_handoff_action_preview,
)

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json


def load_content_strategy_runtime(
    api_base: str,
    *,
    timeout_seconds: float,
    required_context_keys: set[str],
    required_connectors: list[str],
    content_action_id: str,
    content_action_decision_types: set[str],
) -> dict[str, Any]:
    health = request_json(api_base, "GET", "/api/health", timeout_seconds=timeout_seconds)
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")
    pack = request_json(
        api_base,
        "POST",
        "/api/codex/context-pack",
        {"skill": "wilq-content-strategist"},
        timeout_seconds=timeout_seconds,
    )
    missing = sorted(required_context_keys - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")
    content_diagnostics = request_json(
        api_base, "GET", "/api/content/diagnostics", timeout_seconds=timeout_seconds
    )
    content_brief_preview = _validate_content_diagnostics(
        pack,
        content_diagnostics,
        content_action_id=content_action_id,
        content_action_decision_types=content_action_decision_types,
    )
    action_validations = _validate_actions(
        api_base,
        content_diagnostics.get("action_ids", []),
        timeout_seconds=timeout_seconds,
    )
    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )
    return {
        "health": health,
        "pack": pack,
        "content_diagnostics": content_diagnostics,
        "action_validations": action_validations,
        "brief_items": _brief_items(api_base, required_connectors, timeout_seconds=timeout_seconds),
        "connector_results": _connector_results(
            api_base, required_connectors, timeout_seconds=timeout_seconds
        ),
        "content_brief_preview": content_brief_preview,
    }


def _validate_content_diagnostics(
    pack: dict[str, Any],
    content_diagnostics: dict[str, Any],
    *,
    content_action_id: str,
    content_action_decision_types: set[str],
) -> list[dict[str, Any]]:
    if content_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Content diagnostics language must be pl-PL")
    sections = content_diagnostics.get("sections")
    if not isinstance(sections, list) or not sections:
        raise SystemExit("Content diagnostics must expose sections")
    packed = pack.get("content_diagnostics", {})
    if packed.get("evidence_ids") != content_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack content_diagnostics evidence IDs differ from endpoint")
    if packed.get("action_ids") != content_diagnostics.get("action_ids"):
        raise SystemExit("Context pack content_diagnostics action IDs differ from endpoint")
    if _decision_trace(packed.get("decision_queue")) != _decision_trace(
        content_diagnostics.get("decision_queue")
    ):
        raise SystemExit("Context pack content_diagnostics decision_queue differs from endpoint")
    decision_queue = content_diagnostics.get("decision_queue", [])
    validate_content_decision_queue(
        content_diagnostics,
        content_action_id=content_action_id,
        decision_types=content_action_decision_types,
        assert_url_keys=assert_current_content_url_keys,
    )
    _validate_operator_summary(content_diagnostics)
    content_brief_preview = validate_content_action_preview(
        pack.get("active_action_objects"),
        content_action_id=content_action_id,
        require_preview=bool(content_diagnostics.get("live_data_available") and decision_queue),
    )
    validate_wordpress_draft_handoff_action_preview(
        pack.get("active_action_objects"), assert_url_keys=assert_current_content_url_keys
    )
    return content_brief_preview


def _validate_actions(
    api_base: str, action_ids: Any, *, timeout_seconds: float
) -> list[dict[str, Any]]:
    results = []
    for action_id in action_ids:
        quoted = urllib.parse.quote(str(action_id), safe="")
        validation = request_json(
            api_base,
            "POST",
            f"/api/actions/{quoted}/validate",
            timeout_seconds=timeout_seconds,
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Content action validation failed: {validation}")
        results.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
    return results


def _brief_items(
    api_base: str, required_connectors: list[str], *, timeout_seconds: float
) -> list[dict[str, Any]]:
    brief = request_json(api_base, "GET", "/api/marketing/brief", timeout_seconds=timeout_seconds)
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


def _connector_results(
    api_base: str, required_connectors: list[str], *, timeout_seconds: float
) -> list[dict[str, Any]]:
    results = []
    for connector in required_connectors:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(
            api_base,
            "GET",
            f"/api/connectors/{quoted}/status",
            timeout_seconds=timeout_seconds,
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


def _validate_operator_summary(content_diagnostics: dict[str, Any]) -> None:
    summary = content_diagnostics.get("operator_summary")
    if not isinstance(summary, dict):
        raise SystemExit("Content diagnostics lacks operator_summary")
    assert_current_content_url_keys(summary, "Content operator_summary")
    for field in ("title", "summary", "next_step"):
        if "action" in str(summary.get(field, "")):
            raise SystemExit(
                "Content operator_summary exposes internal jargon in marketer-facing fields: "
                + field
            )
    for decision in content_diagnostics.get("decision_queue", []):
        if isinstance(decision, dict):
            assert_current_content_url_keys(decision, "Content decision_queue")


def _decision_trace(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        {
            "id": item.get("id"),
            "decision_type": item.get("decision_type"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
        }
        for item in value
        if isinstance(item, dict)
    ]
