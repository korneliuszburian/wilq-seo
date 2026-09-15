from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.current_preparation_readiness import (
    ContentCurrentPreparationReadiness,
    ContentCurrentPreparationReadyForRefreshAuthorization,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityRecordResult,
    content_delivery_identity_logical_id,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.pipeline_steps.operator_steps import ContentWorkflowOperatorJourney
from wilq.content.workflow.workspace.document_workspace import (
    ContentDocumentWorkspace,
    ContentDocumentWorkspaceNextAction,
    build_content_document_workspace,
)
from wilq.content.workflow.workspace.production_decision import (
    ContentProductionDecision,
    ContentProductionDecisionBlocked,
    ContentProductionDecisionMissing,
    ContentProductionDecisionReuse,
    ContentReusableDocumentBlocked,
)


class ContentSelectedWorkspaceIdentityReadiness(BaseModel):
    """Read-only S1 identity state; it never upgrades production authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["bound", "missing", "mismatch", "not_applicable"]
    binding_id: str | None = None
    reason_pl: str = Field(min_length=1)
    safe_next_step_pl: str = Field(min_length=1)
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_binding_shape(self) -> Self:
        if (self.status == "bound") != (self.binding_id is not None):
            raise ValueError("Only an exact S1 identity may expose a binding ID.")
        if self.status != "bound" and self.binding_id is not None:
            raise ValueError("Blocked S1 identity states cannot expose a binding ID.")
        return self


class ContentSelectedWorkspace(BaseModel):
    """Exact route-owned read result for an existing-page workspace.

    Missing selection is data, not a fallback to a catalogue item or a transport
    error that callers have to reinterpret.
    """

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_selected_workspace"] = "content_selected_workspace"
    contract_version: Literal["content_selected_workspace_v3"] = "content_selected_workspace_v3"
    status: Literal["ready", "missing"]
    work_item_id: str = Field(min_length=1)
    requested_work_item_id: str = Field(min_length=1)
    production_decision: ContentProductionDecision
    identity_readiness: ContentSelectedWorkspaceIdentityReadiness
    current_preparation_readiness: ContentCurrentPreparationReadiness | None = Field(
        default=None,
        exclude=True,
    )
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
        readiness = self.current_preparation_readiness
        if isinstance(readiness, ContentCurrentPreparationReadyForRefreshAuthorization):
            _validate_ready_refresh_state(
                production,
                self.identity_readiness,
                readiness,
                work_item_id=self.work_item_id,
            )
            if self.workspace.next_action.kind != "prepare_document":
                raise ValueError("Ready current refresh requires a preparation action.")
        elif self.workspace.next_action.kind != "none":
            raise ValueError(
                "Generation-disabled production decision requires no workspace action."
            )
        expected_reason, expected_safe_next_step = _production_operator_guidance(
            production,
            readiness,
        )
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
    identity_record: ContentDeliveryIdentityRecordResult | None = None,
    current_preparation_readiness: ContentCurrentPreparationReadiness | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    item: ContentWorkItem | None = None,
) -> ContentSelectedWorkspace:
    return build_content_selected_workspace_with_context(
        work_item_id,
        operator_journey=operator_journey,
        requested_work_item_id=requested_work_item_id,
        production_decision=production_decision,
        identity_record=identity_record,
        current_preparation_readiness=current_preparation_readiness,
        revision_state=revision_state,
        item=item,
    )


def build_content_selected_workspace_with_context(
    work_item_id: str,
    *,
    operator_journey: ContentWorkflowOperatorJourney,
    requested_work_item_id: str | None = None,
    production_decision: ContentProductionDecision | None = None,
    identity_record: ContentDeliveryIdentityRecordResult | None = None,
    current_preparation_readiness: ContentCurrentPreparationReadiness | None = None,
    revision_context_current: bool | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    item: ContentWorkItem | None = None,
) -> ContentSelectedWorkspace:
    requested_id = requested_work_item_id or work_item_id
    production = production_decision or ContentProductionDecisionMissing(status="missing")
    identity_readiness = _identity_readiness(
        production,
        identity_record,
        current_preparation_readiness,
    )
    workspace = build_content_document_workspace(
        work_item_id,
        revision_context_current=revision_context_current,
        revision_state=revision_state,
        item=item,
        # Opening a workspace must be bounded by WILQ-owned state.  A live
        # public WordPress read is an explicit freshness operation, not a
        # prerequisite for rendering this decision screen: it can otherwise
        # stall the whole API worker on a remote TLS read.  The document
        # projection shows persisted source material (and labels it as such)
        # when the exact work item carries it.
        read_material=False,
    )
    if workspace is None:
        return ContentSelectedWorkspace(
            status="missing",
            work_item_id=work_item_id,
            requested_work_item_id=requested_id,
            production_decision=production,
            identity_readiness=identity_readiness,
            current_preparation_readiness=current_preparation_readiness,
            operator_journey=operator_journey,
            reason="Nie znaleziono istniejącej strony do odświeżenia pod tym dokładnym adresem.",
            safe_next_step=(
                "Wróć do wyboru pracy i wybierz istniejącą stronę albo rozpocznij brief "
                "nowej strony."
            ),
        )
    production_reason, production_safe_next_step = _production_operator_guidance(
        production,
        current_preparation_readiness,
    )
    if not isinstance(production, ContentProductionDecisionMissing):
        workspace = workspace.model_copy(
            update={
                "next_action": _production_next_action(
                    production_reason,
                    current_preparation_readiness,
                ),
            }
        )
    return ContentSelectedWorkspace(
        status="ready",
        work_item_id=work_item_id,
        requested_work_item_id=requested_id,
        production_decision=production,
        identity_readiness=identity_readiness,
        current_preparation_readiness=current_preparation_readiness,
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
    current_preparation_readiness: ContentCurrentPreparationReadiness | None = None,
) -> tuple[str, str]:
    if isinstance(
        current_preparation_readiness,
        ContentCurrentPreparationReadyForRefreshAuthorization,
    ):
        return (
            current_preparation_readiness.reason_pl,
            current_preparation_readiness.safe_next_step_pl,
        )
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


def _validate_ready_refresh_state(
    production: ContentProductionDecision,
    identity_readiness: ContentSelectedWorkspaceIdentityReadiness,
    readiness: ContentCurrentPreparationReadyForRefreshAuthorization,
    *,
    work_item_id: str,
) -> None:
    if not isinstance(production, ContentProductionDecisionBlocked):
        raise ValueError("Ready current refresh requires a blocked production decision.")
    if (
        production.decision != "blocked"
        or len(production.blockers) != 1
        or production.blockers[0].code != "current_content_binding_missing"
    ):
        raise ValueError(
            "Ready current refresh requires the sole current_content_binding_missing blocker."
        )
    if (
        readiness.work_item_id != work_item_id
        or readiness.work_item_id != production.current_work_item_id
        or readiness.classification_run_id != production.run_id
        or readiness.classification_run_digest != production.run_digest
        or readiness.decision_set_digest != production.decision_set_digest
        or readiness.source_packet_row_digest != production.source_packet_row_digest
        or production.source_packet_row_digest is None
    ):
        raise ValueError("Ready current refresh does not match production classification.")
    if (
        identity_readiness.status != "bound"
        or identity_readiness.binding_id != readiness.identity_binding_id
    ):
        raise ValueError("Ready current refresh does not match exact identity readiness.")


def _production_next_action(
    reason: str,
    current_preparation_readiness: ContentCurrentPreparationReadiness | None,
) -> ContentDocumentWorkspaceNextAction:
    if isinstance(
        current_preparation_readiness,
        ContentCurrentPreparationReadyForRefreshAuthorization,
    ):
        return ContentDocumentWorkspaceNextAction(
            kind="prepare_document",
            label="Autoryzuj bieżący refresh",
            reason=reason,
        )
    return ContentDocumentWorkspaceNextAction(
        kind="none",
        label="Generowanie nowej wersji jest wyłączone",
        reason=reason,
    )


def selected_workspace_identity_binding_id(
    production: ContentProductionDecision,
) -> str | None:
    """Return only the deterministic lookup key for an already-recorded S1 binding."""

    if isinstance(production, ContentProductionDecisionMissing):
        return None
    current_work_item_id = production.current_work_item_id
    if current_work_item_id is None:
        return None
    logical_id = content_delivery_identity_logical_id(
        {
            "canonical_path": production.canonical_path,
            "public_url": production.public_url,
            "current_work_item_id": current_work_item_id,
            "classification_run_id": production.run_id,
        }
    )
    return f"content_delivery_identity_{logical_id[:24]}"


def _identity_readiness(
    production: ContentProductionDecision,
    identity_record: ContentDeliveryIdentityRecordResult | None,
    current_preparation_readiness: ContentCurrentPreparationReadiness | None = None,
) -> ContentSelectedWorkspaceIdentityReadiness:
    if isinstance(production, ContentProductionDecisionMissing):
        return ContentSelectedWorkspaceIdentityReadiness(
            status="not_applicable",
            reason_pl="Brakuje bieżącej klasyfikacji do sprawdzenia tożsamości S1.",
            safe_next_step_pl="Najpierw uzyskaj bieżącą klasyfikację dla tej strony.",
        )
    if production.current_work_item_id is None:
        return ContentSelectedWorkspaceIdentityReadiness(
            status="not_applicable",
            reason_pl="Bieżąca klasyfikacja nie ma exact current work item dla tej strony.",
            safe_next_step_pl="Zarejestruj exact inventory identity z autorytatywnego źródła.",
        )
    if identity_record is None:
        return ContentSelectedWorkspaceIdentityReadiness(
            status="missing",
            reason_pl="Nie ma exact S1 identity dla bieżącej klasyfikacji tej strony.",
            safe_next_step_pl=(
                "Zarejestruj S1 wyłącznie z exact current classification i inventory evidence."
            ),
        )
    binding = identity_record.binding
    current = getattr(identity_record, "current", None)
    if current is not None and current.current_status != "exact_current":
        return ContentSelectedWorkspaceIdentityReadiness(
            status="mismatch",
            reason_pl=(
                "Zapisana S1 identity nie odpowiada dokładnie bieżącej klasyfikacji strony."
            ),
            safe_next_step_pl=current.current_safe_next_step,
        )
    matches = (
        binding.status == "exact_current"
        and binding.current_work_item_id == production.current_work_item_id
        and binding.canonical_path == production.canonical_path
        and binding.public_url == production.public_url
        and binding.classification_run_id == production.run_id
        and binding.classification_run_digest == production.run_digest
        and binding.classification_decision_set_digest == production.decision_set_digest
    )
    if not matches:
        return ContentSelectedWorkspaceIdentityReadiness(
            status="mismatch",
            reason_pl="Zapisana S1 identity nie odpowiada dokładnie bieżącej klasyfikacji strony.",
            safe_next_step_pl=(
                "Sprawdź exact run, work item i evidence przed kolejną rejestracją S1."
            ),
        )
    return ContentSelectedWorkspaceIdentityReadiness(
        status="bound",
        binding_id=binding.binding_id,
        reason_pl=(
            current_preparation_readiness.reason_pl
            if isinstance(
                current_preparation_readiness,
                ContentCurrentPreparationReadyForRefreshAuthorization,
            )
            else "Exact S1 identity jest związana z bieżącą klasyfikacją."
        ),
        safe_next_step_pl=(
            current_preparation_readiness.safe_next_step_pl
            if isinstance(
                current_preparation_readiness,
                ContentCurrentPreparationReadyForRefreshAuthorization,
            )
            else (
                "S1 nie uruchamia generowania: nadal wymagaj source-pack, review "
                "i pozostałych bramek."
            )
        ),
    )


__all__ = [
    "ContentSelectedWorkspace",
    "ContentSelectedWorkspaceIdentityReadiness",
    "build_content_selected_workspace",
    "build_content_selected_workspace_with_context",
    "selected_workspace_identity_binding_id",
]
