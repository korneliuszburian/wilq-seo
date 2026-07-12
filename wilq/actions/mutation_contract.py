from __future__ import annotations

from wilq.schemas import ActionMutationApplyContract, ActionObject


def mutation_apply_contract(
    action: ActionObject,
    mutation_adapter: str | None,
) -> ActionMutationApplyContract | None:
    if action.id not in {
        "act_apply_wordpress_draft_handoff",
        "act_prepare_wordpress_draft_handoff",
    }:
        return None
    action_type = action.payload.get("action_type")
    required_input_contracts = [
        value
        for value in action.payload.get("required_input_contracts", [])
        if isinstance(value, str)
    ]
    return ActionMutationApplyContract(
        action_id=action.id,
        action_type=action_type if isinstance(action_type, str) else "wordpress_draft_handoff",
        connector=action.connector,
        allowed_operation="create_wordpress_draft",
        draft_only=True,
        publication_allowed=False,
        destructive_allowed=False,
        adapter_status="implemented" if mutation_adapter is not None else "not_implemented",
        required_env_flags=["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        required_input_contracts=required_input_contracts,
        required_audit_events=[
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
        ],
        blocked_outputs=[
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_publish_ready_claim",
        ],
        operator_summary=(
            "Ten kontrakt może w przyszłości zapisać wyłącznie szkic WordPress. "
            "Nie wolno publikować, aktualizować istniejącego wpisu ani omijać "
            "preview, review, confirm i audytu ActionObject."
        ),
    )
