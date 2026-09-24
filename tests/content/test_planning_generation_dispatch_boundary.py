"""Dispatch is public only after the exact intent ActionObject apply audit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_unknown_intent_dispatch_returns_typed_blocker_without_starting_model() -> None:
    response = TestClient(app).post(
        "/api/content/planning-generation-intents/"
        "act_content_planning_generation_intent_v2_missing/dispatch"
    )

    assert response.status_code == 409
    assert response.json()["blocker"]["code"] == "planning_generation_intent_missing"
    assert response.json()["blocker"]["owner"] == "WILQ content workflow"
    assert response.json()["external_write_attempted"] is False
