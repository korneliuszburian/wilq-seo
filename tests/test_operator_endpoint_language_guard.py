from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


client = TestClient(app)

OPERATOR_ENDPOINTS = (
    "/api/dashboard/command-center",
    "/api/content/diagnostics",
    "/api/merchant/diagnostics",
    "/api/ads/diagnostics",
    "/api/ga4/diagnostics",
    "/api/localo/diagnostics",
)

FORBIDDEN_OPERATOR_TERMS = (
    "ekologus.dev.proudsite.pl",
    "target_site",
    "mapping_review",
    "migration-map",
    "Command Center",
    "Content Planner",
    "Ads Doctor",
    "ActionObject",
    "Dry-run",
    "dry-run",
    "evidence IDs",
    "blockery",
)


def test_operator_endpoints_do_not_expose_stale_or_technical_language() -> None:
    problems: list[str] = []

    for endpoint in OPERATOR_ENDPOINTS:
        response = client.get(endpoint)
        assert response.status_code == 200
        serialized = json.dumps(response.json(), ensure_ascii=False)
        for term in FORBIDDEN_OPERATOR_TERMS:
            if term in serialized:
                problems.append(f"{endpoint}: {term}")

    assert problems == []
