"""Public route observer; remove when research packet v2 preview is retired."""

from __future__ import annotations

import importlib
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from wilq.content.workflow.source_pack_v2 import SourcePackV2Blocker, SourcePackV2Preview


def test_public_v2_packet_preview_preserves_exact_source_blocker() -> None:
    app = FastAPI()
    router = APIRouter()
    route_path = (
        Path(__file__).resolve().parents[2]
        / "apps/api/wilq_api/routers/content_research_packet_v2_preview.py"
    )
    if route_path.is_file():
        module = importlib.import_module(
            "apps.api.wilq_api.routers.content_research_packet_v2_preview"
        )
        blocked = SourcePackV2Preview(
            status="blocked",
            work_item_id="wi_exact",
            blocker=SourcePackV2Blocker(
                code="material_review_missing_or_stale",
                owner="WILQ content workflow",
                evidence_ids=("ev_current_page",),
                safe_next_step="Przejrzyj dokładny materiał strony.",
            ),
        )
        module.register_content_research_packet_v2_preview_route(
            router,
            source_pack_loader=lambda _work_item_id: blocked,
        )
    app.include_router(router)
    response = TestClient(app).get(
        "/api/content/work-items/wi_exact/research-packet-v2-preview"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["blocker"]["code"] == "material_review_missing_or_stale"
    assert payload["blocker"]["owner"] == "WILQ content workflow"
    assert payload["blocker"]["evidence_ids"] == ["ev_current_page"]
    assert payload["blocker"]["safe_next_step"]
    assert payload["generation_allowed"] is False
    assert payload["packet_write_allowed"] is False
