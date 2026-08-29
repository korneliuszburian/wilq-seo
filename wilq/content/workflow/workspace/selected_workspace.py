from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.pipeline_steps.operator_steps import ContentWorkflowOperatorJourney
from wilq.content.workflow.workspace.document_workspace import (
    ContentDocumentWorkspace,
    build_content_document_workspace,
)


class ContentSelectedWorkspace(BaseModel):
    """Exact route-owned read result for an existing-page workspace.

    Missing selection is data, not a fallback to a catalogue item or a transport
    error that callers have to reinterpret.
    """

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_selected_workspace"] = "content_selected_workspace"
    contract_version: Literal["content_selected_workspace_v1"] = "content_selected_workspace_v1"
    status: Literal["ready", "missing"]
    work_item_id: str = Field(min_length=1)
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
        return self


def build_content_selected_workspace(
    work_item_id: str,
    *,
    operator_journey: ContentWorkflowOperatorJourney,
    item: ContentWorkItem | None = None,
) -> ContentSelectedWorkspace:
    return build_content_selected_workspace_with_context(
        work_item_id,
        operator_journey=operator_journey,
        item=item,
    )


def build_content_selected_workspace_with_context(
    work_item_id: str,
    *,
    operator_journey: ContentWorkflowOperatorJourney,
    revision_context_current: bool | None = None,
    item: ContentWorkItem | None = None,
) -> ContentSelectedWorkspace:
    workspace = build_content_document_workspace(
        work_item_id,
        revision_context_current=revision_context_current,
        item=item,
        read_material=False,
    )
    if workspace is None:
        return ContentSelectedWorkspace(
            status="missing",
            work_item_id=work_item_id,
            operator_journey=operator_journey,
            reason="Nie znaleziono istniejącej strony do odświeżenia pod tym dokładnym adresem.",
            safe_next_step=(
                "Wróć do wyboru pracy i wybierz istniejącą stronę albo rozpocznij brief "
                "nowej strony."
            ),
        )
    return ContentSelectedWorkspace(
        status="ready",
        work_item_id=work_item_id,
        operator_journey=operator_journey,
        workspace=workspace,
        reason="WILQ odczytał dokładny workspace wskazanej strony.",
        safe_next_step=workspace.next_action.label,
    )


__all__ = [
    "ContentSelectedWorkspace",
    "build_content_selected_workspace",
    "build_content_selected_workspace_with_context",
]
