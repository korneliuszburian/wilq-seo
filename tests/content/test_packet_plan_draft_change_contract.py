from __future__ import annotations

from pathlib import Path


def test_research_packet_public_surface_is_read_only() -> None:
    from fastapi import APIRouter, FastAPI
    from fastapi.testclient import TestClient

    from apps.api.wilq_api.routers.content_research_packet import (
        register_content_research_packet_routes,
    )

    router = APIRouter()
    register_content_research_packet_routes(router)
    application = FastAPI()
    application.include_router(router)

    response = TestClient(application).post(
        "/api/content/research-packets",
        json={"packet_id": "content_research_packet_contract"},
    )

    assert response.status_code in {404, 405}


def test_research_packet_identifier_contract_keeps_regulatory_prefix_and_secret_guard() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "wilq/content/workflow/research_packet_contracts.py").read_text(
        encoding="utf-8"
    )

    assert '"regulatory_source_fact_"' in source
    assert "_SECRET_LIKE = re.compile(" in source
    assert "sk-[A-Za-z0-9_-]{20,}" in source
    assert "gho_[A-Za-z0-9_]{20,}" in source
    assert "ya29\\.[A-Za-z0-9._-]{20,}" in source
