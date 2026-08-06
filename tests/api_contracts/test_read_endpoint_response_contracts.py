"""Typed response contracts for read-only API endpoints."""

from __future__ import annotations

from tests._contract_support.api_client import client


def test_read_endpoints_publish_their_typed_response_contracts() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    expected_schemas = {
        "/api/knowledge/search": ("get", "KnowledgeCard"),
        "/api/metrics/status": ("get", "MetricStoreStatus"),
        "/api/workflows": ("get", "Workflow"),
    }

    for path, (method, schema_name) in expected_schemas.items():
        schema = paths[path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        schema_ref = schema.get("items", schema).get("$ref", "")
        assert schema_ref.endswith(f"/{schema_name}")
