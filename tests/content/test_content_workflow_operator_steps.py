from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from wilq.content.workflow.operator_steps import (
    CONTENT_WORKFLOW_OPERATOR_STEP_ORDER,
    ContentWorkflowOperatorFacts,
    ContentWorkflowOperatorJourney,
    ContentWorkflowOperatorStepId,
    ContentWorkflowOperatorStepPhase,
    ContentWorkflowSalesBriefSignalStatus,
    build_content_workflow_operator_journey,
)


def _facts(
    *,
    sales_brief_present: bool = False,
    sales_brief_signal_status: ContentWorkflowSalesBriefSignalStatus | None = None,
    section_map_present: bool = False,
    structured_contract_present: bool = False,
) -> ContentWorkflowOperatorFacts:
    return ContentWorkflowOperatorFacts(
        sales_brief_present=sales_brief_present,
        sales_brief_signal_status=sales_brief_signal_status,
        sales_brief_signal_reason=None,
        sales_brief_safe_next_step="Uzupełnij zakres.",
        sales_brief_blocker=None,
        section_map_present=section_map_present,
        section_map_blocker=None,
        section_map_safe_next_step="Uzupełnij plan sekcji.",
        structured_contract_present=structured_contract_present,
        structured_contract_blocker=None,
        structured_contract_safe_next_step="Uzupełnij kontrakt szkicu.",
    )


@pytest.mark.parametrize(
    ("facts", "expected_current_step_id", "expected_phases"),
    [
        (
            _facts(),
            "scope",
            ("current", "pending", "pending", "pending", "pending"),
        ),
        (
            _facts(sales_brief_present=True, sales_brief_signal_status="strong"),
            "section_map",
            ("complete", "current", "pending", "pending", "pending"),
        ),
        (
            _facts(
                sales_brief_present=True,
                sales_brief_signal_status="strong",
                section_map_present=True,
                structured_contract_present=True,
            ),
            "draft",
            ("complete", "complete", "current", "pending", "pending"),
        ),
    ],
)
def test_operator_journey_builder_uses_canonical_scope_section_map_draft_states(
    facts: ContentWorkflowOperatorFacts,
    expected_current_step_id: ContentWorkflowOperatorStepId,
    expected_phases: tuple[
        ContentWorkflowOperatorStepPhase,
        ContentWorkflowOperatorStepPhase,
        ContentWorkflowOperatorStepPhase,
        ContentWorkflowOperatorStepPhase,
        ContentWorkflowOperatorStepPhase,
    ],
) -> None:
    journey = build_content_workflow_operator_journey(facts)

    assert tuple(step.id for step in journey.steps) == CONTENT_WORKFLOW_OPERATOR_STEP_ORDER
    assert tuple(step.phase for step in journey.steps) == expected_phases
    assert journey.current_step_id == expected_current_step_id
    assert [step.id for step in journey.steps if step.phase == "current"] == [
        expected_current_step_id
    ]


@pytest.mark.parametrize(
    "facts",
    [
        _facts(section_map_present=True, structured_contract_present=True),
        _facts(
            sales_brief_present=True,
            sales_brief_signal_status="thin",
            section_map_present=True,
            structured_contract_present=True,
        ),
    ],
)
def test_operator_journey_blocks_later_artifacts_until_scope_is_complete(
    facts: ContentWorkflowOperatorFacts,
) -> None:
    journey = build_content_workflow_operator_journey(facts)
    steps = {step.id: step for step in journey.steps}

    assert journey.current_step_id == "scope"
    assert steps["section_map"].readiness == "blocked"
    assert steps["section_map"].blocker is not None
    assert steps["section_map"].blocker.code == "blocked_by_scope"
    assert steps["draft"].readiness == "blocked"
    assert steps["draft"].blocker is not None
    assert steps["draft"].blocker.code == "blocked_by_scope"
    assert steps["section_map"].safe_next_step == facts.sales_brief_safe_next_step
    assert steps["draft"].safe_next_step == facts.sales_brief_safe_next_step


def test_operator_journey_blocks_draft_until_section_map_is_complete() -> None:
    facts = _facts(
        sales_brief_present=True,
        sales_brief_signal_status="strong",
        section_map_present=False,
        structured_contract_present=True,
    )

    journey = build_content_workflow_operator_journey(facts)
    steps = {step.id: step for step in journey.steps}

    assert journey.current_step_id == "section_map"
    assert steps["section_map"].readiness == "blocked"
    assert steps["draft"].readiness == "blocked"
    assert steps["draft"].blocker is not None
    assert steps["draft"].blocker.code == "blocked_by_section_map"
    assert steps["draft"].safe_next_step == facts.section_map_safe_next_step


def test_operator_journey_rejects_reordered_steps() -> None:
    payload = _valid_journey_payload()
    reordered_steps = list(payload["steps"])
    reordered_steps[0], reordered_steps[1] = reordered_steps[1], reordered_steps[0]
    payload["steps"] = reordered_steps

    with pytest.raises(ValidationError, match="canonical order"):
        ContentWorkflowOperatorJourney.model_validate(payload)


def test_operator_journey_rejects_duplicate_step_ids() -> None:
    payload = _valid_journey_payload()
    payload["steps"][1]["id"] = "scope"

    with pytest.raises(ValidationError, match="must be unique"):
        ContentWorkflowOperatorJourney.model_validate(payload)


def test_operator_journey_rejects_multiple_current_steps() -> None:
    payload = _valid_journey_payload()
    payload["steps"][3]["phase"] = "current"

    with pytest.raises(ValidationError, match="exactly one current step"):
        ContentWorkflowOperatorJourney.model_validate(payload)


def test_operator_journey_rejects_mismatched_current_step_id() -> None:
    payload = _valid_journey_payload()
    payload["current_step_id"] = "review"

    with pytest.raises(ValidationError, match="must match the current step"):
        ContentWorkflowOperatorJourney.model_validate(payload)


def _valid_journey_payload() -> dict[str, Any]:
    journey = build_content_workflow_operator_journey(
        _facts(
            sales_brief_present=True,
            sales_brief_signal_status="strong",
            section_map_present=True,
            structured_contract_present=True,
        )
    )
    return deepcopy(journey.model_dump(mode="python"))
