from __future__ import annotations

from typing import Any

import httpx

from wilq.connectors.vendor import MetricSummaryValue, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

LOCALO_MCP_ENDPOINT = "https://api.localo.com/api/mcp"
LOCALO_RESOURCE_METADATA_ENDPOINT = "https://api.localo.com/.well-known/oauth-protected-resource"
LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT = (
    "https://api.localo.com/.well-known/oauth-authorization-server"
)


def refresh_localo_visibility_summary(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    organization_id = variable_value("LOCALO_ORGANIZATION_ID")
    api_token = variable_value("LOCALO_API_TOKEN")
    access_token = variable_value("LOCALO_ACCESS_TOKEN")
    missing = [
        name
        for name, value in (
            ("LOCALO_ORGANIZATION_ID", organization_id),
            ("LOCALO_API_TOKEN", api_token),
        )
        if not value
    ]
    if missing:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Localo MCP vendor read blocked by missing credential names: "
                f"{', '.join(missing)}."
            ),
            errors=[f"Localo missing credential names: {', '.join(missing)}."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        try:
            oauth_metadata = _fetch_oauth_metadata(client)
            initialize_status = _mcp_initialize_status(client, access_token)
        except httpx.HTTPStatusError as exc:
            return _http_failure_result(exc)
        except httpx.HTTPError as exc:
            return _transport_failure_result(exc)
    finally:
        if owns_client:
            client.close()

    metric_summary: dict[str, MetricSummaryValue] = {
        "api": "localo_mcp_oauth_probe",
        "mcp_initialize_status": initialize_status,
        "authorization_code_supported": int(
            "authorization_code" in oauth_metadata.get("grant_types_supported", [])
        ),
        "pkce_s256_supported": int(
            "S256" in oauth_metadata.get("code_challenge_methods_supported", [])
        ),
        "access_token_present": int(bool(access_token)),
    }
    if initialize_status == 200:
        return VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Localo MCP initialize completed with local OAuth access token.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary=metric_summary,
        )

    if not access_token:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Localo MCP endpoint is reachable, but WILQ has no LOCALO_ACCESS_TOKEN. "
                "Localo requires OAuth authorization_code with PKCE before local visibility "
                "metrics can be collected."
            ),
            external_call_attempted=True,
            vendor_data_collected=False,
            metric_summary=metric_summary,
            errors=[
                "Localo MCP OAuth authorization is incomplete: missing LOCALO_ACCESS_TOKEN."
            ],
        )

    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Localo MCP initialize failed with HTTP {initialize_status}.",
        external_call_attempted=True,
        vendor_data_collected=False,
        metric_summary=metric_summary,
        errors=[f"Localo MCP initialize HTTP {initialize_status}."],
    )


def _fetch_oauth_metadata(client: httpx.Client) -> dict[str, Any]:
    resource_response = client.get(LOCALO_RESOURCE_METADATA_ENDPOINT)
    resource_response.raise_for_status()
    resource_payload = resource_response.json()
    authorization_servers = resource_payload.get("authorization_servers", [])
    if LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT and authorization_servers:
        metadata_url = f"{authorization_servers[0]}/.well-known/oauth-authorization-server"
    else:
        metadata_url = LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT
    response = client.get(metadata_url)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _mcp_initialize_status(client: httpx.Client, access_token: str | None) -> int:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    response = client.post(
        LOCALO_MCP_ENDPOINT,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "wilq", "version": "0.1.0"},
            },
        },
    )
    return response.status_code


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Localo MCP OAuth discovery failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"Localo MCP OAuth discovery HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Localo MCP OAuth discovery failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Localo MCP OAuth discovery {type(exc).__name__}."],
    )
