from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_research_packet import (
    register_content_research_packet_routes,
)


def test_research_packet_public_surface_is_read_only() -> None:
    router = APIRouter()
    register_content_research_packet_routes(router)
    application = FastAPI()
    application.include_router(router)

    response = TestClient(application).post(
        "/api/content/research-packets",
        json={"packet_id": "content_research_packet_contract"},
    )

    assert response.status_code in {404, 405}
