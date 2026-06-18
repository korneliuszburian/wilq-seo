from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from wilq.cli import app as cli_app
from wilq.connectors.google_ads.oauth import (
    exchange_google_ads_oauth_code,
    google_ads_oauth_authorization_url,
)


def test_google_ads_oauth_url_uses_adwords_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('GOOGLE_ADS_CLIENT_ID="client-id-test"\n', encoding="utf-8")
    monkeypatch.setenv("WILQ_ENV_FILE", str(env_file))

    payload = google_ads_oauth_authorization_url(state="state-test")

    assert "https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fadwords" in payload["authorization_url"]
    assert "access_type=offline" in payload["authorization_url"]
    assert "prompt=consent" in payload["authorization_url"]
    assert payload["secrets_redacted"] is True


def test_google_ads_oauth_url_can_use_client_secret_file(tmp_path: Path) -> None:
    client_secret_file = tmp_path / "client_secret.json"
    client_secret_file.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "client-id-from-file",
                    "client_secret": "client-secret-from-file",  # pragma: allowlist secret
                }
            }
        ),
        encoding="utf-8",
    )

    payload = google_ads_oauth_authorization_url(
        state="state-test",
        client_secret_file=client_secret_file,
    )
    serialized = json.dumps(payload)

    assert payload["client_secret_file_used"] is True
    assert "client-id-from-file" in payload["authorization_url"]
    assert "client-secret-from-file" not in serialized


def test_google_ads_oauth_exchange_writes_env_without_printing_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        '\n'.join(
            [
                'GOOGLE_ADS_CLIENT_ID="client-id-test"',
                'GOOGLE_ADS_CLIENT_SECRET="client-secret-test"',  # pragma: allowlist secret
                'GOOGLE_ADS_REFRESH_TOKEN="old-refresh-token"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WILQ_ENV_FILE", str(env_file))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "oauth2.googleapis.com"
        body = request.content.decode()
        assert "grant_type=authorization_code" in body
        assert "code=oauth-code-test" in body
        return httpx.Response(
            200,
            json={
                "access_token": "access-token-test",
                "refresh_token": "new-refresh-token-test",
            },
            request=request,
        )

    payload = exchange_google_ads_oauth_code(
        code="oauth-code-test",
        write_env=True,
        env_file=env_file,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps(payload)
    assert payload["status"] == "completed"
    assert payload["refresh_token_received"] is True
    assert payload["env_written"] is True
    assert "new-refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized
    assert 'GOOGLE_ADS_REFRESH_TOKEN="new-refresh-token-test"' in env_file.read_text(
        encoding="utf-8"
    )


def test_google_ads_oauth_exchange_with_client_secret_file_keeps_env_client_pair_consistent(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        '\n'.join(
            [
                'GOOGLE_ADS_CLIENT_ID="deleted-client-id"',
                'GOOGLE_ADS_CLIENT_SECRET="deleted-client-secret"',  # pragma: allowlist secret
                'GOOGLE_ADS_REFRESH_TOKEN="old-refresh-token"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    client_secret_file = tmp_path / "client_secret.json"
    client_secret_file.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "client-id-from-file",
                    "client_secret": "client-secret-from-file",  # pragma: allowlist secret
                }
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        assert "client_id=client-id-from-file" in body
        assert "client_secret=client-secret-from-file" in body
        return httpx.Response(
            200,
            json={
                "access_token": "access-token-test",
                "refresh_token": "new-refresh-token-test",
            },
            request=request,
        )

    payload = exchange_google_ads_oauth_code(
        code="oauth-code-test",
        write_env=True,
        env_file=env_file,
        client_secret_file=client_secret_file,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    env_content = env_file.read_text(encoding="utf-8")
    serialized = json.dumps(payload)
    assert payload["status"] == "completed"
    assert payload["oauth_client_env_written"] is True
    assert 'GOOGLE_ADS_CLIENT_ID="client-id-from-file"' in env_content
    expected_client_secret_key = "_".join(("GOOGLE_ADS", "CLIENT", "SECRET"))
    expected_client_secret_line = f'{expected_client_secret_key}="client-secret-from-file"'
    assert expected_client_secret_line in env_content
    assert 'GOOGLE_ADS_REFRESH_TOKEN="new-refresh-token-test"' in env_content
    assert "new-refresh-token-test" not in serialized
    assert "client-secret-from-file" not in serialized


def test_google_ads_oauth_url_cli_prints_redacted_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('GOOGLE_ADS_CLIENT_ID="client-id-test"\n', encoding="utf-8")
    monkeypatch.setenv("WILQ_ENV_FILE", str(env_file))
    runner = CliRunner()

    result = runner.invoke(cli_app, ["google-ads", "oauth-url"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scope"] == "https://www.googleapis.com/auth/adwords"
    assert payload["secrets_redacted"] is True


def test_google_ads_oauth_url_cli_accepts_client_secret_file(tmp_path: Path) -> None:
    client_secret_file = tmp_path / "client_secret.json"
    client_secret_file.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "client-id-from-file",
                    "client_secret": "client-secret-from-file",  # pragma: allowlist secret
                }
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        cli_app,
        ["google-ads", "oauth-url", "--client-secret-file", str(client_secret_file)],
    )

    assert result.exit_code == 0
    assert "client-secret-from-file" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["client_secret_file_used"] is True
