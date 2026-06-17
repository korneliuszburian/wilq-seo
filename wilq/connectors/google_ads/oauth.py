from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from wilq.connectors.google_ads.client import GOOGLE_ADS_SCOPE, OAUTH_ENDPOINT
from wilq.credentials.runtime import load_local_env, local_env_path, variable_value

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8085/oauth2callback"
REFRESH_TOKEN_ENV = "GOOGLE_ADS_REFRESH_TOKEN"  # nosec B105


def google_ads_oauth_authorization_url(
    *,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    state: str | None = None,
    client_secret_file: Path | None = None,
) -> dict[str, Any]:
    load_local_env()
    client_id, _client_secret = _oauth_client_credentials(client_secret_file)
    if not client_id:
        raise RuntimeError("Missing GOOGLE_ADS_CLIENT_ID.")
    state_value = state or secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_ADS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state_value,
        "include_granted_scopes": "true",
    }
    return {
        "authorization_url": f"{AUTH_ENDPOINT}?{urlencode(params)}",
        "redirect_uri": redirect_uri,
        "scope": GOOGLE_ADS_SCOPE,
        "state": state_value,
        "next_step": (
            "Open authorization_url as marketing@rekurencja.com, approve access, "
            "then pass the final localhost redirect URL to oauth-exchange."
        ),
        "secrets_redacted": True,
        "client_secret_file_used": client_secret_file is not None,
    }


def exchange_google_ads_oauth_code(
    *,
    code: str | None = None,
    redirect_url: str | None = None,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    write_env: bool = False,
    env_file: Path | None = None,
    client_secret_file: Path | None = None,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    load_local_env()
    authorization_code = code or _code_from_redirect_url(redirect_url)
    if not authorization_code:
        raise RuntimeError("Missing OAuth code or redirect URL with a code parameter.")

    client_id, client_secret = _oauth_client_credentials(client_secret_file)
    missing = [
        name
        for name, value in (
            ("GOOGLE_ADS_CLIENT_ID", client_id),
            ("GOOGLE_ADS_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing credential names: {', '.join(missing)}.")

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        response = client.post(
            OAUTH_ENDPOINT,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            client.close()

    refresh_token = payload.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        return {
            "status": "blocked",
            "refresh_token_received": False,  # nosec B105
            "env_written": False,
            "message": (
                "Google did not return a refresh token. Re-run oauth-url and approve "
                "with prompt=consent for marketing@rekurencja.com."
            ),
            "secrets_redacted": True,
        }

    target_env = env_file or local_env_path()
    if write_env:
        _upsert_env_value(target_env, REFRESH_TOKEN_ENV, refresh_token)

    return {
        "status": "completed",
        "refresh_token_received": True,  # nosec B105
        "env_written": write_env,
        "env_file": str(target_env) if write_env else None,
        "env_var": REFRESH_TOKEN_ENV,
        "next_step": (
            'Run `uv run wilq connectors refresh google_ads --mode vendor_read '
            '--reason "Goal 001 Google Ads live data proof"`.'
        ),
        "secrets_redacted": True,
        "client_secret_file_used": client_secret_file is not None,
    }


def _oauth_client_credentials(client_secret_file: Path | None) -> tuple[str | None, str | None]:
    if client_secret_file:
        payload = json.loads(client_secret_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("OAuth client JSON must be an object.")
        config = payload.get("installed") or payload.get("web")
        if not isinstance(config, dict):
            raise RuntimeError("OAuth client JSON must contain installed or web config.")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        return (
            client_id if isinstance(client_id, str) and client_id else None,
            client_secret if isinstance(client_secret, str) and client_secret else None,
        )
    return variable_value("GOOGLE_ADS_CLIENT_ID"), variable_value("GOOGLE_ADS_CLIENT_SECRET")


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
