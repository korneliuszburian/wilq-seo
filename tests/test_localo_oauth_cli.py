from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from wilq.cli import app as cli_app
from wilq.connectors.localo.oauth import (
    exchange_localo_oauth_code,
    localo_oauth_authorization_url,
)


def test_localo_oauth_url_uses_discovery_and_pkce_without_printing_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_localo_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                'LOCALO_ORGANIZATION_ID="localo-org-test"',
                'LOCALO_API_TOKEN="localo-client-secret-test"',  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WILQ_ENV_FILE", str(env_file))

    payload = localo_oauth_authorization_url(
        state="state-test",
        code_verifier="verifier-test",
        http_client=_localo_mock_client(),
    )
    serialized = json.dumps(payload)

    assert payload["secrets_redacted"] is True
    assert payload["code_challenge_method"] == "S256"
    assert "https://api.localo.com/oauth/authorize?" in payload["authorization_url"]
    assert "response_type=code" in payload["authorization_url"]
    assert "client_id=localo-org-test" in payload["authorization_url"]
    assert "code_challenge_method=S256" in payload["authorization_url"]
    assert "localo-client-secret-test" not in serialized


def test_localo_oauth_exchange_writes_access_token_without_printing_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_localo_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                'LOCALO_ORGANIZATION_ID="localo-org-test"',
                'LOCALO_API_TOKEN="localo-client-secret-test"',  # pragma: allowlist secret
                'LOCALO_ACCESS_TOKEN="old-access-token"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WILQ_ENV_FILE", str(env_file))

    payload = exchange_localo_oauth_code(
        code="localo-code-test",
        code_verifier="verifier-test",
        write_env=True,
        env_file=env_file,
        http_client=_localo_mock_client(),
    )

    env_content = env_file.read_text(encoding="utf-8")
    serialized = json.dumps(payload)
    assert payload["status"] == "completed"
    assert payload["access_token_received"] is True
    assert payload["env_written"] is True
    assert 'LOCALO_ACCESS_TOKEN="new-localo-access-token"' in env_content
    assert 'LOCALO_REFRESH_TOKEN="new-localo-refresh-token"' in env_content
    assert "new-localo-access-token" not in serialized
    assert "new-localo-refresh-token" not in serialized
    assert "localo-client-secret-test" not in serialized


def test_localo_oauth_url_cli_prints_redacted_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wilq.cli.localo_oauth_authorization_url",
        lambda redirect_uri: {
            "authorization_url": f"https://api.localo.com/oauth/authorize?redirect_uri={redirect_uri}",
            "redirect_uri": redirect_uri,
            "state": "state-test",
            "code_verifier": "verifier-test",
            "secrets_redacted": True,
        },
    )
    runner = CliRunner()

    result = runner.invoke(cli_app, ["localo", "oauth-url"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["secrets_redacted"] is True
    assert "code_verifier" in payload


def test_localo_oauth_exchange_cli_writes_redacted_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wilq.cli.exchange_localo_oauth_code",
        lambda **kwargs: {
            "status": "completed",
            "access_token_received": True,
            "env_written": kwargs["write_env"],
            "env_var": "LOCALO_ACCESS_TOKEN",
            "secrets_redacted": True,
        },
    )
    runner = CliRunner()

    result = runner.invoke(
        cli_app,
        [
            "localo",
            "oauth-exchange",
            "--code",
            "localo-code-test",
            "--code-verifier",
            "verifier-test",
            "--write-env",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["env_var"] == "LOCALO_ACCESS_TOKEN"
    assert payload["secrets_redacted"] is True


def _localo_mock_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://api.localo.com/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": "https://api.localo.com/oauth/authorize",
                    "token_endpoint": "https://api.localo.com/oauth/token",
                    "grant_types_supported": ["authorization_code"],
                    "code_challenge_methods_supported": ["S256"],
                    "token_endpoint_auth_methods_supported": ["client_secret_post"],
                },
                request=request,
            )
        if str(request.url) == "https://api.localo.com/.well-known/oauth-protected-resource":
            return httpx.Response(
                200,
                json={"resource": "https://api.localo.com"},
                request=request,
            )
        if str(request.url) == "https://api.localo.com/oauth/token":
            body = request.content.decode()
            assert "client_id=localo-org-test" in body
            assert "client_secret=localo-client-secret-test" in body
            assert "grant_type=authorization_code" in body
            assert "code=localo-code-test" in body
            assert "code_verifier=verifier-test" in body
            return httpx.Response(
                200,
                json={
                    "access_token": "new-localo-access-token",
                    "refresh_token": "new-localo-refresh-token",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _clear_localo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LOCALO_ORGANIZATION_ID",
        "LOCALO_API_TOKEN",
        "LOCALO_ACCESS_TOKEN",
        "LOCALO_REFRESH_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
