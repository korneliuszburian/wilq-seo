from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
from pydantic import ValidationError

from wilq.content.workflow.operator_steps import (
    CONTENT_WORKFLOW_OPERATOR_STEP_ORDER,
    ContentDraftRevisionWorkspaceStatus,
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
        scope_review_current=True,
        section_map_review_current=True,
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
            "scope",
            ("current", "pending", "pending", "pending", "pending"),
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

    assert journey.current_step_id == "scope"
    assert steps["scope"].safe_next_step == (
        "Uruchom generowanie planu — mapa sekcji zostanie wyliczona automatycznie."
    )
    assert steps["section_map"].readiness == "blocked"
    assert steps["draft"].readiness == "blocked"
    assert steps["draft"].blocker is not None
    assert steps["draft"].blocker.code == "blocked_by_section_map"
    assert steps["draft"].safe_next_step == facts.section_map_safe_next_step


def test_operator_journey_uses_generated_section_map_without_manual_section_approval() -> None:
    facts = _facts(
        sales_brief_present=True,
        sales_brief_signal_status="strong",
        section_map_present=True,
        structured_contract_present=True,
    )
    facts = replace(facts, section_map_review_current=False)

    journey = build_content_workflow_operator_journey(facts)
    steps = {step.id: step for step in journey.steps}

    assert journey.current_step_id == "draft"
    assert steps["section_map"].phase == "complete"
    assert steps["section_map"].readiness == "ready"
    assert steps["section_map"].blocker is None
    assert steps["draft"].can_submit is True


@pytest.mark.parametrize(
    (
        "revision_status",
        "current_step_id",
        "current_can_submit",
        "dev_blocker_code",
    ),
    [
        ("empty", "draft", True, "missing_revision_bound_draft"),
        ("unreviewed", "review", True, "missing_revision_bound_review"),
        ("needs_changes", "draft", True, "missing_revision_bound_draft"),
        ("approved", "dev_draft", False, "missing_revision_bound_wordpress_seam"),
        ("rejected", "draft", True, "missing_revision_bound_draft"),
        ("deferred", "review", True, "missing_revision_bound_review"),
    ],
)
def test_operator_journey_uses_only_exact_revision_state_for_later_steps(
    revision_status: ContentDraftRevisionWorkspaceStatus,
    current_step_id: ContentWorkflowOperatorStepId,
    current_can_submit: bool,
    dev_blocker_code: str,
) -> None:
    facts = _facts(
        sales_brief_present=True,
        sales_brief_signal_status="strong",
        section_map_present=True,
        structured_contract_present=True,
    )
    facts = replace(facts, revision_workspace_status=revision_status)

    journey = build_content_workflow_operator_journey(facts)
    steps = {step.id: step for step in journey.steps}

    assert journey.current_step_id == current_step_id
    assert steps[current_step_id].can_submit is current_can_submit
    assert steps["dev_draft"].readiness == "blocked"
    assert steps["dev_draft"].can_submit is False
    assert steps["dev_draft"].blocker is not None
    assert steps["dev_draft"].blocker.code == dev_blocker_code


def test_operator_journey_returns_to_draft_when_revision_context_changed() -> None:
    facts = replace(
        _facts(
            sales_brief_present=True,
            sales_brief_signal_status="strong",
            section_map_present=True,
            structured_contract_present=True,
        ),
        revision_workspace_status="approved",
        revision_context_current=False,
    )

    journey = build_content_workflow_operator_journey(facts)
    steps = {step.id: step for step in journey.steps}

    assert journey.current_step_id == "draft"
    assert steps["draft"].can_submit is True
    assert steps["draft"].blocker is not None
    assert steps["draft"].blocker.code == "revision_context_changed"
    assert steps["review"].blocker is not None
    assert steps["review"].blocker.code == "revision_context_changed"
    assert steps["dev_draft"].blocker is not None
    assert steps["dev_draft"].blocker.code == "revision_context_changed"
    assert steps["dev_draft"].can_submit is False
    assert steps["draft"].safe_next_step == (
        "Zatwierdź aktualny plan, a następnie wygeneruj świeżą pełną wersję tekstu."
    )
    assert steps["review"].safe_next_step == (
        "Wygeneruj świeżą wersję powiązaną z aktualnym planem i adresem strony."
    )


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
