from __future__ import annotations

from typing import Any

from wilq.connectors.registry import get_connector_status

INTERNAL_ACTION_TYPES = {"configure_connector"}


def validate_action_payload(connector_id: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    action_type = payload.get("action_type")
    payload_connector = payload.get("connector")
    connector = get_connector_status(connector_id)

    if not isinstance(action_type, str) or not action_type.strip():
        errors.append("Action payload requires a non-empty action_type.")
        return errors

    if payload_connector is not None and payload_connector != connector_id:
        errors.append("Action payload connector must match ActionObject connector.")

    if action_type in INTERNAL_ACTION_TYPES:
        required_env = payload.get("required_env")
        if action_type == "configure_connector" and not isinstance(required_env, list):
            errors.append("configure_connector payload requires required_env list.")
        return errors

    if connector is None:
        errors.append(f"Unknown connector for payload validation: {connector_id}")
        return errors

    if action_type not in connector.supported_actions:
        errors.append(
            f"Action type {action_type} is not supported by connector {connector_id}."
        )

    return errors
