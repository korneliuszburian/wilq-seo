"""Public planning must not mint a research packet outside ActionObject."""

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)


def test_public_planning_post_blocks_before_implicit_research_packet_write() -> None:
    calls: list[str] = []

    def source_snapshot(_work_item_id: str) -> None:
        calls.append("source_snapshot")
        raise AssertionError("Planning POST reached source preparation.")

    def refresh_authority() -> None:
        calls.append("refresh_authority")
        raise AssertionError("Planning POST reached refresh authority.")

    router = APIRouter()
    register_content_planning_proposal_routes(
        router,
        snapshot_loader=source_snapshot,  # type: ignore[arg-type]
        refresh_authority_factory=refresh_authority,  # type: ignore[arg-type]
    )
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/content/work-items/content_work_item_bdo/planning-proposals",
        json={
            "content_kind": "service",
            "service_card_id": "ekologus_service_bdo_reporting",
            "expected_planning_input_digest": "a" * 64,
            "requested_by": "wilku",
        },
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["blockers"][0]["code"] == "research_packet_action_required"
    assert body["blockers"][0]["owner"] == "WILQ content workflow"
    assert body["safe_next_step"]
    assert calls == []
