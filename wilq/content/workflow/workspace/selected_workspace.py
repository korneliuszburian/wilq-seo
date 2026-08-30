from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.pipeline_steps.operator_steps import ContentWorkflowOperatorJourney
from wilq.content.workflow.workspace.document_workspace import (
    ContentDocumentWorkspace,
    ContentDocumentWorkspaceNextAction,
    build_content_document_workspace,
)
from wilq.content.workflow.workspace.production_decision import (
    ContentProductionDecision,
    ContentProductionDecisionMissing,
    ContentProductionDecisionReuse,
    ContentReusableDocumentBlocked,
)


class ContentSelectedWorkspace(BaseModel):
    """Exact route-owned read result for an existing-page workspace.

    Missing selection is data, not a fallback to a catalogue item or a transport
    error that callers have to reinterpret.
    """

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_selected_workspace"] = "content_selected_workspace"
    contract_version: Literal["content_selected_workspace_v2"] = "content_selected_workspace_v2"
    status: Literal["ready", "missing"]
    work_item_id: str = Field(min_length=1)
    requested_work_item_id: str = Field(min_length=1)
    production_decision: ContentProductionDecision
    operator_journey: ContentWorkflowOperatorJourney
    workspace: ContentDocumentWorkspace | None = None
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_state(self) -> ContentSelectedWorkspace:
        if self.status == "ready" and self.workspace is None:
            raise ValueError("Ready selected workspace requires exact workspace data.")
        if self.status == "missing" and self.workspace is not None:
            raise ValueError("Missing selected workspace cannot carry workspace data.")
        if self.workspace is not None and self.workspace.work_item_id != self.work_item_id:
            raise ValueError("Selected workspace must match the exact work item.")
        current_document = (
            None if self.workspace is None else getattr(self.workspace, "canonical_document", None)
        )
        current_revision = (
            None if current_document is None else getattr(current_document, "revision", None)
        )
        if current_revision is not None and current_revision.work_item_id != self.work_item_id:
            raise ValueError("Current canonical document must match the selected work item.")
        production = self.production_decision
        if isinstance(production, ContentProductionDecisionMissing):
            if self.requested_work_item_id != self.work_item_id:
                raise ValueError("Unclassified workspace must preserve its requested identity.")
            return self
        if self.status != "ready" or self.workspace is None:
            raise ValueError("Available production decision requires a ready current workspace.")
        expected_work_item_id = production.current_work_item_id or self.requested_work_item_id
        if self.work_item_id != expected_work_item_id:
            raise ValueError("Selected workspace must use the current production identity.")
        if production.lookup_basis == "current":
            lookup_matches = self.requested_work_item_id == production.current_work_item_id
        elif production.lookup_basis == "retained":
            lookup_matches = self.requested_work_item_id == production.retained_work_item_id
        else:
            lookup_matches = (
                isinstance(production, ContentProductionDecisionReuse)
                and production.revision_binding.identity_reconciliation_status == "retained_missing"
                and self.requested_work_item_id == production.revision_binding.revision_work_item_id
            )
        if not lookup_matches:
            raise ValueError("Production lookup basis does not match the requested identity.")
        if self.workspace.next_action.kind != "none":
            raise ValueError(
                "Generation-disabled production decision requires no workspace action."
            )
        expected_reason, expected_safe_next_step = _production_operator_guidance(production)
        if self.reason != expected_reason:
            raise ValueError("Selected workspace must expose the current production reason.")
        if self.workspace.next_action.reason != expected_reason:
            raise ValueError("Disabled workspace action must explain the production decision.")
        if self.safe_next_step != expected_safe_next_step:
            raise ValueError("Selected workspace must expose the production safe next step.")
        return self


def build_content_selected_workspace(
    work_item_id: str,
    *,
    operator_journey: ContentWorkflowOperatorJourney,
    requested_work_item_id: str | None = None,
    production_decision: ContentProductionDecision | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    item: ContentWorkItem | None = None,
) -> ContentSelectedWorkspace:
    return build_content_selected_workspace_with_context(
        work_item_id,
        operator_journey=operator_journey,
        requested_work_item_id=requested_work_item_id,
        production_decision=production_decision,
        revision_state=revision_state,
        item=item,
    )


def build_content_selected_workspace_with_context(
    work_item_id: str,
    *,
    operator_journey: ContentWorkflowOperatorJourney,
    requested_work_item_id: str | None = None,
    production_decision: ContentProductionDecision | None = None,
    revision_context_current: bool | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    item: ContentWorkItem | None = None,
) -> ContentSelectedWorkspace:
    requested_id = requested_work_item_id or work_item_id
    production = production_decision or ContentProductionDecisionMissing(status="missing")
    workspace = build_content_document_workspace(
        work_item_id,
        revision_context_current=revision_context_current,
        revision_state=revision_state,
        item=item,
        read_material=False,
    )
    if workspace is None:
        return ContentSelectedWorkspace(
            status="missing",
            work_item_id=work_item_id,
            requested_work_item_id=requested_id,
            production_decision=production,
            operator_journey=operator_journey,
            reason="Nie znaleziono istniejącej strony do odświeżenia pod tym dokładnym adresem.",
            safe_next_step=(
                "Wróć do wyboru pracy i wybierz istniejącą stronę albo rozpocznij brief "
                "nowej strony."
            ),
        )
    production_reason, production_safe_next_step = _production_operator_guidance(production)
    if not isinstance(production, ContentProductionDecisionMissing):
        workspace = workspace.model_copy(
            update={
                "next_action": ContentDocumentWorkspaceNextAction(
                    kind="none",
                    label="Generowanie nowej wersji jest wyłączone",
                    reason=production_reason,
                )
            }
        )
    return ContentSelectedWorkspace(
        status="ready",
        work_item_id=work_item_id,
        requested_work_item_id=requested_id,
        production_decision=production,
        operator_journey=operator_journey,
        workspace=workspace,
        reason=(
            "WILQ odczytał dokładny workspace wskazanej strony."
            if isinstance(production, ContentProductionDecisionMissing)
            else production_reason
        ),
        safe_next_step=(
            workspace.next_action.label
            if isinstance(production, ContentProductionDecisionMissing)
            else production_safe_next_step
        ),
    )


def _production_operator_guidance(
    production: ContentProductionDecision,
) -> tuple[str, str]:
    if isinstance(production, ContentProductionDecisionReuse) and isinstance(
        production.reusable_document, ContentReusableDocumentBlocked
    ):
        return (
            production.reusable_document.reason_pl,
            production.reusable_document.safe_next_step_pl,
        )
    if isinstance(production, ContentProductionDecisionMissing):
        return "", ""
    return production.reason_pl, production.safe_next_step_pl


__all__ = [
    "ContentSelectedWorkspace",
    "build_content_selected_workspace",
    "build_content_selected_workspace_with_context",
]
