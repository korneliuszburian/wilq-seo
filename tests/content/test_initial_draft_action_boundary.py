"""Public initial-draft generation cannot bypass an exact ActionObject."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_initial_draft as draft_route
from apps.api.wilq_api.main import app


def test_public_initial_draft_post_blocks_before_snapshot_queue_or_model(monkeypatch) -> None:
    entered_writer = False

    def fake_submit(*_args, **_kwargs):
        nonlocal entered_writer
        entered_writer = True
        return JSONResponse(status_code=202, content={"status": "unsafe_writer_reached"})

    monkeypatch.setattr(
        draft_route,
        "_submit_initial_draft",
        fake_submit,
    )

    response = TestClient(app).post(
        "/api/content/work-items/wi_exact/initial-draft",
        json={
            "expected_proposal_id": "proposal_exact",
            "expected_planning_digest": "a" * 64,
            "expected_planning_input_digest": "b" * 64,
            "research_packet_id": "content_research_packet_v2_" + "c" * 24,
            "research_packet_digest": "c" * 64,
            "requested_by": "synthetic-operator",
        },
    )

    assert entered_writer is False
    assert response.status_code == 409
    assert response.json()["blockers"][0]["code"] == "initial_draft_action_required"
    assert response.json()["blockers"][0]["owner"] == "WILQ content workflow"
    assert response.json()["runtime"]["external_call_attempted"] is False

    reuse = TestClient(app).post(
        "/api/content/work-items/wi_exact/initial-draft",
        json={
            "expected_production_classification_run_digest": "d" * 64,
            "requested_by": "synthetic-operator",
        },
    )
    assert entered_writer is False
    assert reuse.status_code == 409
    assert reuse.json()["blockers"][0]["code"] == "initial_draft_action_required"
