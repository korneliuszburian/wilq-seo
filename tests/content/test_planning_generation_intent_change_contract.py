"""Parent-safe public contract observer for exact local generation intent."""

from __future__ import annotations

from apps.api.wilq_api.main import app
from wilq.actions.mutation_readiness import vendor_write_possible
from wilq.actions.mutation_requirements import _connector_readiness_requirement
from wilq.schemas import ActionMode, ActionObject


def _assert_v3_intent_readiness_is_local_only() -> None:
    action = ActionObject.model_construct(
        id="act_content_planning_generation_intent_v3_contract",
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        payload={
            "action_type": "content_planning_generation_intent_v3",
            "local_authority_only": True,
            "apply_allowed": True,
            "api_mutation_ready": True,
        },
    )
    adapter = "synthetic_local_intent_adapter"

    assert vendor_write_possible(action, adapter) is False
    connector = _connector_readiness_requirement(
        action,
        configured=False,
        evidence="missing_credentials",
    )
    assert connector.satisfied is True
    assert connector.evidence == "local_authority_only; no vendor write"


def test_public_generation_intent_exposes_typed_blocked_preview_contract() -> None:
    _assert_v3_intent_readiness_is_local_only()

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

    v3_preview = app.openapi()["paths"].get(
        "/api/content/work-items/{work_item_id}/planning-generation-intent-v3/preview"
    )
    assert v3_preview is not None
    v3_post = v3_preview["post"]
    assert v3_post["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PlanningGenerationIntentV3Response")
    assert v3_post["responses"]["409"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PlanningGenerationIntentV3BlockedResponse")

    v3_read = app.openapi()["paths"].get(
        "/api/content/work-items/{work_item_id}/planning-generation-intent-v3/{action_id}"
    )
    assert v3_read is not None
    assert v3_read["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PlanningGenerationIntentV3Response")
