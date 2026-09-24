"""Remaining public model writers require exact ActionObject authority."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_new_page_brief as new_page_route
from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_codex_proposal import (
    register_content_revision_repair_route,
)


def test_new_page_initial_draft_blocks_before_loading_model_inputs(monkeypatch) -> None:
    entered_writer = False

    def old_inputs(_brief_id: str):
        nonlocal entered_writer
        entered_writer = True
        raise HTTPException(status_code=409, detail="unsafe_old_writer_reached")

    monkeypatch.setattr(new_page_route, "_new_page_draft_inputs", old_inputs)
    monkeypatch.setattr(
        new_page_route,
        "new_page_brief_store",
        lambda: SimpleNamespace(
            load_new_page_foundation=lambda _brief_id: SimpleNamespace(
                work_item_id="work_new_exact"
            )
        ),
    )
    response = TestClient(app).post(
        "/api/content/new-page-briefs/brief_exact/initial-draft",
        json={
            "expected_proposal_id": "proposal_exact",
            "expected_planning_digest": "a" * 64,
            "expected_planning_input_digest": "b" * 64,
            "requested_by": "synthetic-operator",
        },
    )

    assert entered_writer is False
    assert response.status_code == 409
    assert response.json()["blockers"][0]["code"] == "initial_draft_action_required"


def test_repair_proposal_blocks_before_snapshot_or_model() -> None:
    entered_writer = False

    def old_snapshot(_work_item_id: str):
        nonlocal entered_writer
        entered_writer = True
        raise HTTPException(status_code=409, detail="unsafe_old_writer_reached")

    test_app = FastAPI()
    register_content_revision_repair_route(test_app.router, snapshot_loader=old_snapshot)
    response = TestClient(test_app).post(
        "/api/content/work-items/wi_exact/draft-revisions/base_exact/repair-proposal",
        json={
            "expected_base_digest": "c" * 64,
            "selected_section_ids": ["section_exact"],
            "requested_by": "synthetic-operator",
        },
    )

    assert entered_writer is False
    assert response.status_code == 409
    assert response.json()["blockers"][0]["code"] == "repair_action_required"
    assert response.json()["blockers"][0]["owner"] == "WILQ content workflow"
