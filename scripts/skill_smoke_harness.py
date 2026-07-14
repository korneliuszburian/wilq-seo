"""Shared transport and language guards for WILQ skill contract smokes."""

from __future__ import annotations

import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_TOP_LEVEL_ACTION_ID_KEYS = (
    "action_ids",
    "diagnostics_action_ids",
    "selected_action_ids",
)
_TOP_LEVEL_VALIDATED_ACTION_ID_KEYS = ("selected_validated_action_ids",)


def request_json(
    api_base: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    timeout_seconds: float = 60.0,
    timeout: float | None = None,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        request_timeout = timeout if timeout is not None else timeout_seconds
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def has_polish_metric_source_guardrails(value: str) -> bool:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")
    return "metryk" in normalized and "dowod" in normalized and "zrodl" in normalized


def require_polish_language(payload: dict[str, Any], label: str) -> None:
    if payload.get("language") != "pl-PL":
        raise SystemExit(f"{label} must declare language=pl-PL")


def require_evidence_sources(
    payload: dict[str, Any], label: str, required_connector: str | None = None
) -> None:
    if not payload.get("evidence_ids"):
        raise SystemExit(f"{label} lacks evidence IDs")
    connectors = payload.get("source_connectors") or []
    if not connectors:
        raise SystemExit(f"{label} lacks source connectors")
    if required_connector is not None and required_connector not in connectors:
        raise SystemExit(f"{label} lacks source connector {required_connector}")


def validate_action_ids(
    api_base: str, action_ids: list[str], *, label: str
) -> list[dict[str, Any]]:
    validations: list[dict[str, Any]] = []
    for action_id in action_ids:
        quoted_action = urllib.parse.quote(action_id, safe="")
        validation = request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")
        validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"{label} action validation failed: {validation}")
    return validations


def smoke_action_contract(payload: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return ActionObjects exposed and validated by the deterministic smoke."""
    exposed: set[str] = set()
    validated: set[str] = set()

    for key in _TOP_LEVEL_ACTION_ID_KEYS:
        exposed.update(_action_ids(payload.get(key)))
    for key in _TOP_LEVEL_VALIDATED_ACTION_ID_KEYS:
        action_ids = _action_ids(payload.get(key))
        exposed.update(action_ids)
        validated.update(action_ids)

    active_actions = payload.get("active_action_objects") or []
    if isinstance(active_actions, list):
        exposed.update(
            action_id
            for action in active_actions
            if isinstance(action, dict)
            for action_id in _action_ids([action.get("id"), action.get("action_id")])
        )

    action_validations = payload.get("action_validations") or []
    if isinstance(action_validations, dict):
        validation_rows = [
            {"action_id": action_id, **validation}
            for action_id, validation in action_validations.items()
            if isinstance(validation, dict)
        ]
    elif isinstance(action_validations, list):
        validation_rows = [
            validation for validation in action_validations if isinstance(validation, dict)
        ]
    else:
        validation_rows = []
    for validation in validation_rows:
        action_ids = _action_ids([validation.get("action_id"), validation.get("id")])
        exposed.update(action_ids)
        if validation.get("valid") is True and validation.get("status") == "valid":
            validated.update(action_ids)

    return exposed, validated


def skill_eval_action_state_errors(
    action_candidates: Any,
    smoke_action_ids: set[str],
    smoke_validated_action_ids: set[str],
) -> list[str]:
    """Reject optimistic ActionObject states not proven by the deterministic smoke."""
    if not isinstance(action_candidates, list):
        return []

    errors: list[str] = []
    for index, action in enumerate(action_candidates, start=1):
        if not isinstance(action, dict):
            continue
        action_id = action.get("action_id")
        state = action.get("validation_state")
        has_action_id = isinstance(action_id, str) and bool(action_id.strip())
        if (
            has_action_id
            and action_id not in smoke_action_ids
            and state
            not in {
                "missing",
                "blocked",
            }
        ):
            errors.append(
                f"action candidate {index} uses unproved action_id outside "
                f"blocked/missing state: {action_id}"
            )
        if state == "validated" and has_action_id and action_id not in smoke_validated_action_ids:
            errors.append(
                f"action_id claims validation without deterministic smoke proof: {action_id}"
            )
    return errors


def _action_ids(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {value for value in values if isinstance(value, str) and value.startswith("act_")}
