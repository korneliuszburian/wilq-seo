import pytest

from wilq.actions.mutation_readiness import mutation_readiness_next_step
from wilq.actions.wordpress_mutation_requirements import (
    wordpress_draft_write_readiness_requirements,
)
from wilq.content.workflow.contracts import ContentWordPressDraftWriteReadinessResponse
from wilq.schemas import ActionMode, ActionMutationReadinessBlocker, ActionObject


def test_wordpress_draft_write_env_reader_is_owned_by_mutation_requirements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.actions.wordpress_mutation_requirements import wordpress_draft_writes_enabled

    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "true")
    assert wordpress_draft_writes_enabled() is True
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES", "false")
    assert wordpress_draft_writes_enabled() is False


def test_mutation_readiness_next_step_keeps_wordpress_safe_order() -> None:
    action = ActionObject.model_construct(id="act_apply_wordpress_draft_handoff")
    blocker = ActionMutationReadinessBlocker(
        code="missing_wordpress_draft_package_ready",
        label="brak paczki",
        reason="brak paczki",
        next_step="next step fallback",
    )

    assert "WordPress handoff" in mutation_readiness_next_step(action, [blocker])
    assert "osobnego POST" in mutation_readiness_next_step(action, [])


def test_vendor_write_possible_requires_apply_and_both_payload_readiness_flags() -> None:
    from wilq.actions.mutation_readiness import vendor_write_possible

    action = ActionObject.model_construct(
        mode=ActionMode.apply,
        payload={"apply_allowed": True, "api_mutation_ready": True},
    )

    assert vendor_write_possible(action, "wordpress_draft_execution_boundary") is True
    assert vendor_write_possible(action, None) is False
    action.payload["api_mutation_ready"] = False
    assert vendor_write_possible(action, "wordpress_draft_execution_boundary") is False


def test_wordpress_write_readiness_requirements_keep_fail_closed_contract() -> None:
    action = ActionObject.model_construct(id="act_apply_wordpress_draft_handoff")
    readiness = ContentWordPressDraftWriteReadinessResponse(operator_next_step="review")

    requirements = wordpress_draft_write_readiness_requirements(
        action,
        wordpress_draft_readiness=readiness,
    )

    assert [requirement.code for requirement in requirements] == [
        "wordpress_draft_write_readiness",
        "wordpress_draft_live_write_env",
        "wordpress_rest_adapter_configured",
        "wordpress_write_authorization",
    ]
    assert all(requirement.satisfied is False for requirement in requirements)
