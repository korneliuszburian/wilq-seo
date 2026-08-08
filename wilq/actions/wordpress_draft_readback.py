from __future__ import annotations

from wilq.content.workflow.contracts.contracts import ContentWordPressDraftReadback
from wilq.content.workflow.pipeline_steps.stage_activation import wordpress_draft_readback
from wilq.content.workflow.store.store import content_workflow_store
from wilq.schemas import ActionMutationAuditRecord, ActionObject


def last_created_wordpress_draft_readback(
    action: ActionObject,
    mutation_audits: list[ActionMutationAuditRecord],
) -> ContentWordPressDraftReadback | None:
    """Read back the latest successful execution bound to this exact action."""

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


__all__ = ["last_created_wordpress_draft_readback"]
