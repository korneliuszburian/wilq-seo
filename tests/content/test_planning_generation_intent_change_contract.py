"""Parent-safe public contract observer for exact local generation intent."""

from __future__ import annotations

from apps.api.wilq_api.main import app


def test_public_generation_intent_exposes_typed_blocked_preview_contract() -> None:
    path = "/api/content/work-items/{work_item_id}/planning-generation-intent/preview"
    route = app.openapi()["paths"].get(path)

    assert route is not None
    post = route["post"]
    assert post["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PlanningGenerationIntentResponse"
    )
    assert post["responses"]["409"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PlanningGenerationIntentBlockedResponse"
    )
