from wilq.actions.mutation_readiness import mutation_readiness_next_step
from wilq.schemas import ActionMutationReadinessBlocker, ActionObject


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
