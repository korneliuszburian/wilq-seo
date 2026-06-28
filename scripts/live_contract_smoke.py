from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_API_BASE = "http://127.0.0.1:8000"
ENDPOINTS = {
    "health": "/api/health",
    "command_center": "/api/dashboard/command-center",
    "marketing_brief": "/api/marketing/brief",
    "ads_diagnostics": "/api/ads/diagnostics?view=summary",
    "merchant_diagnostics": "/api/merchant/diagnostics",
    "content_diagnostics": "/api/content/diagnostics",
    "ga4_diagnostics": "/api/ga4/diagnostics",
    "localo_diagnostics": "/api/localo/diagnostics",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "WILQ live contract smoke: checks API contract shape/freshness signals "
            "without asserting exact live metric values."
        )
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    args = parser.parse_args()

    try:
        payloads = fetch_payloads(args.api_base)
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "errors": [str(error)]}, ensure_ascii=False))
        return 1

    errors = evaluate_contracts(payloads)
    result = {
        "status": "completed" if not errors else "failed",
        "api_base": args.api_base,
        "checked_endpoints": ENDPOINTS,
        "assertion_policy": (
            "shape/evidence/status only; no exact live clicks/costs/rankings/reviews"
        ),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def fetch_payloads(api_base: str) -> dict[str, Any]:
    return {name: _fetch_json(api_base, path) for name, path in ENDPOINTS.items()}


def evaluate_contracts(payloads: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    health = _mapping(payloads.get("health"))
    if health.get("status") != "ok":
        errors.append("health.status must be ok")

    command_center = _mapping(payloads.get("command_center"))
    _require_nonempty_list(
        command_center,
        "daily_decisions",
        "command_center.daily_decisions",
        errors,
    )
    _require_nonempty_list(command_center, "action_plan", "command_center.action_plan", errors)
    for index, decision in enumerate(_list(command_center.get("daily_decisions"))):
        _check_decision_shape(
            _mapping(decision),
            f"command_center.daily_decisions[{index}]",
            errors,
        )

    marketing_brief = _mapping(payloads.get("marketing_brief"))
    _require_nonempty_list(marketing_brief, "sections", "marketing_brief.sections", errors)
    _require_nonempty_list(
        marketing_brief,
        "evidence_ids",
        "marketing_brief.evidence_ids",
        errors,
    )

    for name in (
        "ads_diagnostics",
        "merchant_diagnostics",
        "content_diagnostics",
        "ga4_diagnostics",
        "localo_diagnostics",
    ):
        diagnostics = _mapping(payloads.get(name))
        _check_diagnostics_shape(diagnostics, name, errors)

    for name, payload in payloads.items():
        _check_metric_labels(payload, name, errors)

    return errors


def _check_decision_shape(
    decision: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    for key in (
        "id",
        "title",
        "domain",
        "freshness",
        "decision_state",
        "status",
        "why_it_matters",
        "operator_action",
        "metric_facts",
    ):
        if not decision.get(key):
            errors.append(f"{label}.{key} must be present")
    freshness = decision.get("freshness") or {}
    if freshness.get("state") not in {"fresh", "stale", "unknown", "missing"}:
        errors.append(f"{label}.freshness.state must be present")
    if decision.get("decision_state") not in {
        "ready",
        "stale",
        "blocked",
        "missing",
        "unknown",
    }:
        errors.append(f"{label}.decision_state must be present")
    if decision.get("status") not in {"ready", "blocked"}:
        errors.append(f"{label}.status must be ready or blocked")
    metric_facts = decision.get("metric_facts")
    if not isinstance(metric_facts, list):
        errors.append(f"{label}.metric_facts must be a list")
    _require_nonempty_list(decision, "evidence_ids", f"{label}.evidence_ids", errors)
    _require_nonempty_list(
        decision,
        "source_connectors",
        f"{label}.source_connectors",
        errors,
    )


def _check_diagnostics_shape(
    diagnostics: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    if diagnostics.get("language") != "pl-PL":
        errors.append(f"{label}.language must be pl-PL")
    _require_nonempty_list(diagnostics, "evidence_ids", f"{label}.evidence_ids", errors)
    if not (
        _list(diagnostics.get("decision_queue"))
        or _list(diagnostics.get("tactical_items"))
        or _list(diagnostics.get("action_ids"))
    ):
        errors.append(
            f"{label} must expose decision_queue, tactical_items or action_ids"
        )


def _require_nonempty_list(
    payload: dict[str, Any],
    key: str,
    label: str,
    errors: list[str],
) -> None:
    if not _list(payload.get(key)):
        errors.append(f"{label} must not be empty")


def _check_metric_labels(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        if _looks_like_metric_fact(value):
            metric_label = value.get("metric_label")
            if not isinstance(metric_label, str) or not metric_label.strip():
                errors.append(f"{path}.metric_label must be present")
            elif _looks_like_raw_operator_value(metric_label):
                errors.append(f"{path}.metric_label must be marketer-readable")
        for key, child in value.items():
            _check_metric_labels(child, f"{path}.{key}", errors)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _check_metric_labels(child, f"{path}[{index}]", errors)


def _looks_like_metric_fact(value: dict[str, Any]) -> bool:
    return {
        "name",
        "value",
        "period",
        "source_connector",
        "evidence_id",
    }.issubset(value)


def _looks_like_raw_operator_value(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return True
    return bool(re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)+", normalized))


def _fetch_json(api_base: str, path: str) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}{path}"
    try:
        with urlopen(url, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except URLError as error:
        raise RuntimeError(f"Could not fetch {url}: {error}") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Endpoint {url} did not return JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"Endpoint {url} returned non-object JSON")
    return payload


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    sys.exit(main())
