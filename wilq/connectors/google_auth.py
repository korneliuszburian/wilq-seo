from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from wilq.credentials.runtime import access_pack_path, credential_file_names, variable_value


class GoogleCredentialError(RuntimeError):
    pass


GOOGLE_SERVICE_ACCOUNT_ENV_NAMES = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_CREDENTIALS",
)


def google_service_account_available() -> bool:
    try:
        _service_account_info()
    except GoogleCredentialError:
        return False
    return True


def google_service_account_access_token(scopes: Iterable[str]) -> str:
    info = _service_account_info()
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=list(scopes),
    )  # type: ignore[no-untyped-call]
    credentials.refresh(Request())
    token = credentials.token
    if not isinstance(token, str) or not token:
        raise GoogleCredentialError("Google service account token refresh returned no token.")
    return token


def _service_account_info() -> dict[str, Any]:
    attempted = False
    for raw_value in _service_account_candidates():
        attempted = True
        try:
            return _load_service_account_json(raw_value)
        except GoogleCredentialError:
            continue
    if attempted:
        raise GoogleCredentialError("No valid Google service account credentials found.")
    raise GoogleCredentialError("Missing Google service account credentials.")


def _service_account_candidates() -> Iterable[str]:
    for name in GOOGLE_SERVICE_ACCOUNT_ENV_NAMES:
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
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise GoogleCredentialError("Google service account JSON could not be parsed.") from exc
    if not isinstance(payload, dict):
        raise GoogleCredentialError("Google service account JSON must be an object.")
    if payload.get("type") != "service_account":
        raise GoogleCredentialError("Google credentials are not a service account.")
    return payload
