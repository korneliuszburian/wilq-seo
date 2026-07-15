from __future__ import annotations

import asyncio

import httpx
import pytest

from apps.api.wilq_api.main import app


def test_api_authorizes_socket_peer_and_ignores_spoofed_host_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WILQ_ALLOW_REMOTE_API", "true")

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        remote_transport = httpx.ASGITransport(app=app, client=("203.0.113.10", 45123))
        local_transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 45124))
        async with httpx.AsyncClient(
            transport=remote_transport,
            base_url="http://127.0.0.1",
        ) as remote_client:
            remote_response = await remote_client.get(
                "/api/health",
                headers={"host": "127.0.0.1"},
            )
        async with httpx.AsyncClient(
            transport=local_transport,
            base_url="http://malicious.example",
        ) as local_client:
            local_response = await local_client.get("/api/health")
        return remote_response, local_response

    remote_response, local_response = asyncio.run(exercise())

    assert remote_response.status_code == 403
    assert "loopback" in remote_response.json()["detail"]
    assert local_response.status_code == 200
