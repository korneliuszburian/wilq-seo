from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import credentials as user_credentials
from google.oauth2 import service_account

from wilq.credentials.runtime import access_pack_path, credential_file_names, variable_value


class GoogleCredentialError(RuntimeError):
    pass


GOOGLE_CREDENTIAL_ENV_NAMES = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_CREDENTIALS",
)
GOOGLE_SERVICE_ACCOUNT_ENV_NAMES = GOOGLE_CREDENTIAL_ENV_NAMES


def google_service_account_available() -> bool:
    return google_credentials_available()


def google_credentials_available() -> bool:
    try:
        _google_credential_info()
    except GoogleCredentialError:
        return False
    return True


def google_service_account_diagnostic() -> str:
    return google_credentials_diagnostic()


def google_credentials_diagnostic() -> str:
    attempted = False
    reasons: list[str] = []
    for raw_value in _google_credential_candidates():
        attempted = True
        try:
            payload = _load_google_credential_json(raw_value)
            credential_type = payload.get("type")
            if credential_type == "service_account":
                return "valid_service_account"
            if credential_type == "authorized_user":
                return "valid_authorized_user"
            return "invalid_google_credentials_type"
        except GoogleCredentialError as exc:
            reason = str(exc)
            if reason not in reasons:
                reasons.append(reason)
    if not attempted:
        return "missing_google_credentials"
    if reasons:
        return _safe_diagnostic_label(reasons[0])
    return "invalid_google_credentials"


def google_service_account_access_token(scopes: Iterable[str]) -> str:
    return google_access_token(scopes)


def google_access_token(scopes: Iterable[str]) -> str:
    scope_list = list(scopes)
    info = _google_credential_info()
    credential_type = info.get("type")
    if credential_type == "service_account":
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=scope_list,
        )  # type: ignore[no-untyped-call]
    elif credential_type == "authorized_user":
        credentials = user_credentials.Credentials.from_authorized_user_info(
            info,
            scopes=scope_list,
        )  # type: ignore[no-untyped-call]
    else:
        raise GoogleCredentialError("Unsupported Google credential type.")
    credentials.refresh(Request())
    token = credentials.token
    if not isinstance(token, str) or not token:
        raise GoogleCredentialError("Google credential token refresh returned no token.")
    return token


def _service_account_info() -> dict[str, Any]:
    info = _google_credential_info()
    if info.get("type") != "service_account":
        raise GoogleCredentialError("Google credentials are not a service account.")
    return info


def _google_credential_info() -> dict[str, Any]:
    attempted = False
    for raw_value in _google_credential_candidates():
        attempted = True
        try:
            return _load_google_credential_json(raw_value)
        except GoogleCredentialError:
            continue
    if attempted:
        raise GoogleCredentialError("No valid Google credentials found.")
    raise GoogleCredentialError("Missing Google credentials.")


def _service_account_candidates() -> Iterable[str]:
    return _google_credential_candidates()


def _google_credential_candidates() -> Iterable[str]:
    for name in GOOGLE_CREDENTIAL_ENV_NAMES:
        raw_value = variable_value(name)
        if not raw_value:
            continue
        path = _existing_file(raw_value)
        if path is not None:
            yield path.read_text(encoding="utf-8")
        else:
            yield raw_value

    credential_dir = access_pack_path() / "credentials"
    for filename in credential_file_names():
        path = credential_dir / filename
        if path.exists() and path.is_file():
            yield path.read_text(encoding="utf-8", errors="ignore")


def _existing_file(raw_value: str) -> Path | None:
    try:
        path = Path(raw_value).expanduser()
        if path.exists() and path.is_file():
            return path
    except OSError:
        return None
    return None


def _load_service_account_json(raw_value: str) -> dict[str, Any]:
    payload = _load_google_credential_json(raw_value)
    if payload.get("type") != "service_account":
        raise GoogleCredentialError("Google credentials are not a service account.")
    return payload


def _load_google_credential_json(raw_value: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise GoogleCredentialError("google_credentials_json_parse_error") from exc
    if not isinstance(payload, dict):
        raise GoogleCredentialError("google_credentials_json_not_object")
    if payload.get("type") not in {"service_account", "authorized_user"}:
        credential_type = payload.get("type")
        if isinstance(credential_type, str) and credential_type:
            raise GoogleCredentialError(f"google_credentials_type_{credential_type}")
        raise GoogleCredentialError("google_credentials_type_missing")
    return payload


def _safe_diagnostic_label(reason: str) -> str:
    normalized = reason.strip().lower().replace(" ", "_").replace(".", "")
    allowed = {
        "google_credentials_json_parse_error",
        "google_credentials_json_not_object",
        "google_credentials_type_authorized_user",
        "google_credentials_type_missing",
        "google_credentials_type_external_account",
    }
    return normalized if normalized in allowed else "invalid_google_credentials"
