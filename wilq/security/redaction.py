from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SECRET_KEY_RE = re.compile(r"(token|secret|password|credential|api[_-]?key|client_secret)", re.I)
SECRET_VALUE_RE = re.compile(
    r"(gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|ya29\.[A-Za-z0-9._-]+|[A-Za-z0-9_-]{32,})"
)
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
SAFE_IDENTIFIER_KEYS = {
    "api",
    "affected_attribute",
    "id",
    "action_id",
    "action_ids",
    "available_credential_sources",
    "available_read_contracts",
    "blocked_claims",
    "connector",
    "connector_ids",
    "connector_refresh_run_ids",
    "cluster_id",
    "country",
    "credential_runtime",
    "credential_sources",
    "decision_id",
    "decision_ids",
    "decision_type",
    "decision_types",
    "evidence_id",
    "evidence_ids",
    "expert_rule_id",
    "expert_rule_ids",
    "issue_type",
    "content_url",
    "job_id",
    "job_run_id",
    "knowledge_card_id",
    "knowledge_card_ids",
    "landing_page",
    "metric_name",
    "metric_names",
    "name",
    "normalized_page_path",
    "omitted_contracts",
    "operator_review_gates",
    "operator_checklist",
    "operations",
    "page",
    "apply_blockers",
    "checked_credentials",
    "missing_credentials",
    "missing_read_contracts",
    "preview_contract",
    "recommended_actions",
    "required_credentials",
    "required_checks",
    "required_validation",
    "review_gate",
    "reporting_context",
    "resolution",
    "severity",
    "source_connector",
    "source_connectors",
    "source_id",
    "source_metric_names",
    "supported_actions",
    "wordpress_content_url",
    "wordpress_matched_path",
    "wordpress_matched_url_key",
    "wordpress_requested_path",
    "wordpress_requested_url_key",
    "workflow_id",
    "workflow_run_id",
}
SAFE_SECRET_TELEMETRY_KEYS = {
    "access_token_present",
    "access_token_received",
    "client_secret_configured",
    "client_secret_file_used",
    "oauth_client_env_written",
    "refresh_token_received",
    "secrets_redacted",
}


def is_secret_key(key: str) -> bool:
    return bool(SECRET_KEY_RE.search(key))


def redact_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        matches = SECRET_VALUE_RE.findall(value)
        if matches and not all(_looks_like_env_name(match) for match in matches):
            return "[REDACTED]"
        return value
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, Mapping):
        return redact_mapping(value)
    return value


def _looks_like_env_name(value: str) -> bool:
    return "_" in value and bool(ENV_NAME_RE.fullmatch(value))


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if key in SAFE_IDENTIFIER_KEYS or (
            key in SAFE_SECRET_TELEMETRY_KEYS and isinstance(value, bool | int)
        ):
            redacted[key] = value
        elif is_secret_key(key):
            redacted[key] = "[REDACTED]" if value else value
        else:
            redacted[key] = redact_value(value)
    return redacted
