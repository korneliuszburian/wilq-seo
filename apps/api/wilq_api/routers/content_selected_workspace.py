from __future__ import annotations

from fastapi import APIRouter

from apps.api.wilq_api.routers.content_selected_snapshot import (
    selected_workspace_snapshot_for_work_item_or_404,
)
from wilq.content.workflow.current_preparation_readiness import (
    resolve_current_preparation_readiness,
)
from wilq.content.workflow.pipeline_steps.operator_steps import ContentWorkflowOperatorJourney
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.production_decision import (
    build_content_production_decision,
    canonical_work_item_id_for_classification,
    reusable_revision_work_item_id,
)
from wilq.content.workflow.workspace.selected_workspace import (
    ContentSelectedWorkspace,
    build_content_selected_workspace_with_context,
    selected_workspace_identity_binding_id,
)


def register_content_selected_workspace_route(router: APIRouter) -> None:
    def content_selected_workspace(work_item_id: str) -> ContentSelectedWorkspace:
        store = content_workflow_store()
        classification = store.load_production_classification_for_work_item(work_item_id)
        current_work_item_id = canonical_work_item_id_for_classification(
            work_item_id,
            classification,
        )
        current_revision_state = store.load_draft_revision_state(current_work_item_id)
        revision_work_item_id = reusable_revision_work_item_id(classification)
        retained_revision_state = (
            None
            if revision_work_item_id is None
            else (
                current_revision_state
                if revision_work_item_id == current_work_item_id
                else store.load_draft_revision_state(revision_work_item_id)
            )
        )
        production_decision = build_content_production_decision(
            work_item_id,
            classification=classification,
            retained_revision_state=retained_revision_state,
        )
        identity_binding_id = selected_workspace_identity_binding_id(production_decision)
        identity_loader = getattr(store, "load_content_delivery_identity_record", None)
        identity_record = (
            None
            if identity_binding_id is None or not callable(identity_loader)
            else identity_loader(identity_binding_id)
        )
        current_preparation_readiness = resolve_current_preparation_readiness(
            store,
            current_work_item_id,
        )
        snapshot = selected_workspace_snapshot_for_work_item_or_404(
            current_work_item_id,
            store=store,
            revision_state=current_revision_state,
        )
        return build_content_selected_workspace_with_context(
            current_work_item_id,
            operator_journey=ContentWorkflowOperatorJourney(
                current_step_id=snapshot.current_step_id,
                steps=snapshot.operator_steps,
            ),
            requested_work_item_id=work_item_id,
            production_decision=production_decision,
            identity_record=identity_record,
            current_preparation_readiness=current_preparation_readiness,
            revision_context_current=snapshot.revision_workspace.context_current,
            revision_state=current_revision_state,
            item=snapshot.preflight.item,
        )

    router.add_api_route(
        "/api/content/work-items/{work_item_id}/selected-workspace",
        content_selected_workspace,
        methods=["GET"],
        response_model=ContentSelectedWorkspace,
    )


__all__ = ["register_content_selected_workspace_route"]
