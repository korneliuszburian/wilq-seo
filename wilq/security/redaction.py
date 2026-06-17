from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SECRET_KEY_RE = re.compile(r"(token|secret|password|credential|api[_-]?key|client_secret)", re.I)
SECRET_VALUE_RE = re.compile(
    r"(gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|ya29\.[A-Za-z0-9._-]+|[A-Za-z0-9_-]{32,})"
)
SAFE_IDENTIFIER_KEYS = {
    "id",
    "action_id",
    "action_ids",
    "available_credential_sources",
    "connector",
    "connector_ids",
    "credential_runtime",
    "credential_sources",
    "evidence_id",
    "evidence_ids",
    "checked_credentials",
    "missing_credentials",
    "required_credentials",
    "source_connector",
    "source_connectors",
    "source_id",
    "workflow_id",
    "workflow_run_id",
}


def is_secret_key(key: str) -> bool:
    return bool(SECRET_KEY_RE.search(key))


def redact_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        if SECRET_VALUE_RE.search(value):
            return "[REDACTED]"
        return value
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, Mapping):
        return redact_mapping(value)
    return value


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if key in SAFE_IDENTIFIER_KEYS:
            redacted[key] = value
        elif is_secret_key(key):
            redacted[key] = "[REDACTED]" if value else value
        else:
            redacted[key] = redact_value(value)
    return redacted
