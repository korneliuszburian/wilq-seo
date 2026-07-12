from wilq.actions.mutation_readiness import mutation_readiness_next_step
from wilq.schemas import ActionMode, ActionMutationReadinessBlocker, ActionObject


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
