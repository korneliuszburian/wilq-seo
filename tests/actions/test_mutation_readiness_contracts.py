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


def test_wordpress_execution_errors_keep_blocker_labels_and_reasons() -> None:
    from wilq.content.handoff.wordpress_execution import (
        execute_content_wordpress_draft_handoff,
        wordpress_draft_execution_errors,
    )

    execution = execute_content_wordpress_draft_handoff(
        handoff=None,
        draft_package=None,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )

    errors = wordpress_draft_execution_errors(execution)
    assert execution.status == "blocked"
    assert errors
    assert "Brakuje zatwierdzonego przekazania" in errors[0]


def test_supported_mutation_adapter_is_limited_to_canonical_wordpress_draft() -> None:
    from wilq.actions.mutation_contract import supported_mutation_adapter

    action = ActionObject.model_construct(
        id="act_apply_wordpress_draft_handoff",
        connector="wordpress_ekologus",
        payload={"allowed_operation": "create_wordpress_draft"},
    )
    assert supported_mutation_adapter(action) == "wordpress_draft_execution_boundary"

    action.payload["allowed_operation"] = "wordpress_publish"
    assert supported_mutation_adapter(action) is None
