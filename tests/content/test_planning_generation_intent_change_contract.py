"""Parent-safe public contract observer for exact local generation intent."""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest

from tests.content.test_generated_proposal_turn_v2 import (
    _planning_input_with_caller_context,
    _ready_inputs,
)
from wilq.actions.mutation_readiness import vendor_write_possible
from wilq.actions.mutation_requirements import _connector_readiness_requirement
from wilq.content.planning import generated_proposal_turn
from wilq.content.planning.generated_proposal_turn import content_planning_turn_request
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


def _assert_v3_packet_cannot_fall_through_to_raw_model_input() -> None:
    _source_pack, planning_input = _ready_inputs()
    planning_input = _planning_input_with_caller_context(planning_input).model_copy(
        update={
            "research_packet_id": "content_research_packet_v3_aaaaaaaaaaaaaaaaaaaaaaaa",
            "research_packet_digest": "a" * 64,
        }
    )
    with patch.object(
        generated_proposal_turn,
        "current_research_packet_for_model",
        return_value=None,
    ):
        try:
            content_planning_turn_request(planning_input, operator_hint="")
        except ValueError as error:
            assert "v3" in str(error).lower() and "approved" in str(error).lower()
            return
    raise AssertionError("Unresolved v3 packet fell through to raw planning input.")


def _api_openapi_paths(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    registry = importlib.import_module("wilq.content.workflow.research_promotion_registry")
    monkeypatch.setattr(registry, "approved_research_promotion_facts", lambda _facts: ())
    main = importlib.import_module("apps.api.wilq_api.main")
    return main.app.openapi()["paths"]


def test_public_generation_intent_exposes_typed_blocked_preview_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_v3_intent_readiness_is_local_only()
    _assert_v3_packet_cannot_fall_through_to_raw_model_input()

    paths = _api_openapi_paths(monkeypatch)
    path = "/api/content/work-items/{work_item_id}/planning-generation-intent/preview"
    route = paths.get(path)

    assert route is not None
    post = route["post"]
    assert post["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PlanningGenerationIntentResponse"
    )
    assert post["responses"]["409"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PlanningGenerationIntentBlockedResponse"
    )

    v3_preview = paths.get(
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

    v3_read = paths.get(
        "/api/content/work-items/{work_item_id}/planning-generation-intent-v3/{action_id}"
    )
    assert v3_read is not None
    assert v3_read["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PlanningGenerationIntentV3Response")

    v3_dispatch = paths.get(
        "/api/content/planning-generation-intents-v3/{action_id}/dispatch"
    )
    assert v3_dispatch is not None
    assert "post" in v3_dispatch
