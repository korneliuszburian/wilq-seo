from __future__ import annotations

import base64
import hashlib
import os
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from wilq.connectors.localo.client import (
    LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT,
    LOCALO_RESOURCE_METADATA_ENDPOINT,
)
from wilq.credentials.runtime import load_local_env, local_env_path, variable_value

DEFAULT_LOCALO_REDIRECT_URI = "http://127.0.0.1:8095/oauth2callback"
LOCALO_ACCESS_TOKEN_ENV = "LOCALO_ACCESS_TOKEN"  # nosec B105
LOCALO_REFRESH_TOKEN_ENV = "LOCALO_REFRESH_TOKEN"  # nosec B105
LOCALO_CLIENT_ID_ENV = "LOCALO_ORGANIZATION_ID"
LOCALO_CLIENT_SECRET_ENV = "LOCALO_API_TOKEN"  # nosec B105  # pragma: allowlist secret


def localo_oauth_authorization_url(
    *,
    redirect_uri: str = DEFAULT_LOCALO_REDIRECT_URI,
    state: str | None = None,
    code_verifier: str | None = None,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    load_local_env()
    client_id = variable_value(LOCALO_CLIENT_ID_ENV)
    client_secret = variable_value(LOCALO_CLIENT_SECRET_ENV)
    missing = [
        name
        for name, value in (
            (LOCALO_CLIENT_ID_ENV, client_id),
            (LOCALO_CLIENT_SECRET_ENV, client_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing credential names: {', '.join(missing)}.")

    metadata = _fetch_oauth_metadata(http_client)
    authorization_endpoint = metadata.get("authorization_endpoint")
    if not isinstance(authorization_endpoint, str) or not authorization_endpoint:
        raise RuntimeError("Localo OAuth metadata does not expose authorization_endpoint.")

    verifier = code_verifier or secrets.token_urlsafe(64)
    challenge = _pkce_challenge(verifier)
    state_value = state or secrets.token_urlsafe(16)
    resource = _fetch_resource(http_client)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state_value,
    }
    if resource:
        params["resource"] = resource

    return {
        "authorization_url": f"{authorization_endpoint}?{urlencode(params)}",
        "redirect_uri": redirect_uri,
        "state": state_value,
        "code_verifier": verifier,
        "code_challenge_method": "S256",
        "next_step": (
            "Open authorization_url, approve Localo access, then pass the final "
            "localhost redirect URL and this code_verifier to localo oauth-exchange."
        ),
        "secrets_redacted": True,
        "client_secret_configured": True,  # nosec B105
    }


def exchange_localo_oauth_code(
    *,
    code: str | None = None,
    redirect_url: str | None = None,
    redirect_uri: str = DEFAULT_LOCALO_REDIRECT_URI,
    code_verifier: str,
    write_env: bool = False,
    env_file: Path | None = None,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    load_local_env()
    authorization_code = code or _code_from_redirect_url(redirect_url)
    if not authorization_code:
        raise RuntimeError("Missing OAuth code or redirect URL with a code parameter.")
    if not code_verifier:
        raise RuntimeError("Missing PKCE code verifier from localo oauth-url.")

    client_id = variable_value(LOCALO_CLIENT_ID_ENV)
    client_secret = variable_value(LOCALO_CLIENT_SECRET_ENV)
    missing = [
        name
        for name, value in (
            (LOCALO_CLIENT_ID_ENV, client_id),
            (LOCALO_CLIENT_SECRET_ENV, client_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing credential names: {', '.join(missing)}.")
    if client_id is None or client_secret is None:
        raise RuntimeError("Missing Localo OAuth client pair.")

    metadata = _fetch_oauth_metadata(http_client)
    token_endpoint = metadata.get("token_endpoint")
    if not isinstance(token_endpoint, str) or not token_endpoint:
        raise RuntimeError("Localo OAuth metadata does not expose token_endpoint.")
    resource = _fetch_resource(http_client)

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        if resource:
            data["resource"] = resource
        response = client.post(token_endpoint, data=data)
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            client.close()

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return {
            "status": "blocked",
            "access_token_received": False,  # nosec B105
            "env_written": False,
            "message": "Localo did not return an access token.",
            "secrets_redacted": True,
        }

    refresh_token = payload.get("refresh_token")
    target_env = env_file or local_env_path()
    if write_env:
        _upsert_env_value(target_env, LOCALO_ACCESS_TOKEN_ENV, access_token)
        if isinstance(refresh_token, str) and refresh_token:
            _upsert_env_value(target_env, LOCALO_REFRESH_TOKEN_ENV, refresh_token)

    return {
        "status": "completed",
        "access_token_received": True,  # nosec B105
        "refresh_token_received": isinstance(refresh_token, str) and bool(refresh_token),
        "env_written": write_env,
        "env_file": str(target_env) if write_env else None,
        "env_var": LOCALO_ACCESS_TOKEN_ENV,
        "next_step": (
            "Run `uv run wilq connectors refresh localo --mode vendor_read "
            '--reason "Goal 001 Localo live data proof"`.'
        ),
        "secrets_redacted": True,
    }


def _fetch_oauth_metadata(http_client: httpx.Client | None) -> dict[str, Any]:
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        response = client.get(LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT)
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            client.close()
    return payload if isinstance(payload, dict) else {}


def _fetch_resource(http_client: httpx.Client | None) -> str | None:
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        response = client.get(LOCALO_RESOURCE_METADATA_ENDPOINT)
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            client.close()
    resource = payload.get("resource") if isinstance(payload, dict) else None
    return resource if isinstance(resource, str) and resource else None


def _pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _code_from_redirect_url(redirect_url: str | None) -> str | None:
    if not redirect_url:
        return None
    query = parse_qs(urlparse(redirect_url).query)
    code_values = query.get("code")
    if not code_values:
        return None
    return code_values[0]


def _upsert_env_value(env_file: Path, key: str, value: str) -> None:
    env_file.parent.mkdir(parents=True, exist_ok=True)
    line = f"{key}={_quote_env_value(value)}"
    if not env_file.exists():
        env_file.write_text(f"{line}\n", encoding="utf-8")
        return

    lines = env_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    updated = False
    next_lines: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        candidate = stripped.removeprefix("export ").split("=", 1)[0].strip()
        if candidate == key:
            next_lines.append(line)
            updated = True
        else:
            next_lines.append(raw_line)
    if not updated:
        next_lines.append(line)
    env_file.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
    os.environ[key] = value


def _quote_env_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
