from __future__ import annotations

from wilq.content.workflow.contracts.contracts import (
    ContentWordPressDraftReadback,
    ContentWordPressDraftReadbackBlocker,
)
from wilq.content.workflow.pipeline_steps.stage_activation import wordpress_draft_readback
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.store.store_new_page_apply import new_page_apply_claim_store
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.schemas import ActionMutationAuditRecord, ActionObject


def last_created_wordpress_draft_readback(
    action: ActionObject,
    mutation_audits: list[ActionMutationAuditRecord],
) -> ContentWordPressDraftReadback | None:
    """Read back the latest successful execution bound to this exact action."""

    if action.payload.get("action_type") == CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE:
        return _new_page_draft_result_readback(action)
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    latest_applied = next(
        (
            audit
            for audit in mutation_audits
            if audit.status == "applied"
            and audit.external_write_attempted
            and audit.wordpress_draft_binding is not None
        ),
        None,
    )
    if latest_applied is None or latest_applied.wordpress_draft_binding is None:
        return None
    binding = latest_applied.wordpress_draft_binding
    execution = content_workflow_store().latest_wordpress_draft_execution(
        binding.work_item_id,
        handoff_id=binding.handoff_id,
        revision_id=binding.revision_id,
        revision_digest=binding.content_digest,
    )
    if (
        execution is None
        or execution.status != "created"
        or not execution.external_write_attempted
        or not execution.wordpress_post_id
    ):
        return None
    return wordpress_draft_readback(execution)


def _new_page_draft_result_readback(
    action: ActionObject,
) -> ContentWordPressDraftReadback | None:
    result = new_page_apply_claim_store().result_for_action(action.id)
    if result is None:
        return None
    return ContentWordPressDraftReadback(
        status="blocked",
        wordpress_post_id=result.wordpress_post_id,
        post_status=result.status,
        link=result.link,
        edit_link=result.edit_link,
        verification_status="blocked",
        blockers=[
            ContentWordPressDraftReadbackBlocker(
                code="wordpress_draft_verification_unavailable",
                label="Odzyskano wynik utworzenia szkicu; treść wymaga sprawdzenia",
                reason=(
                    "WILQ odtworzył ID i bezpieczne linki z zapisanego wyniku adaptera, "
                    "ale ten wynik nie jest ponownym odczytem treści z WordPressa."
                ),
                next_step=(
                    "Otwórz szkic po zapisanym ID i sprawdź jego status oraz treść przed "
                    "dalszą pracą. Nie uruchamiaj ponownie tej samej exact rewizji."
                ),
            )
        ],
    )


__all__ = ["last_created_wordpress_draft_readback"]
