"""Pure request, response and exact-binding contracts for disposition approval."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_ACTION_TYPE,
    ContentCurrentDispositionBlocker,
    ContentCurrentDispositionProposal,
    ContentCurrentDispositionReadProjection,
    ContentCurrentDispositionReceipt,
    ContentCurrentDispositionSnapshot,
    current_disposition_action_payload_digest,
)
from wilq.schemas import ActionObject, AuditEvent

_HEX64 = r"^[0-9a-f]{64}$"


class ContentCurrentDispositionApprovalRequest(BaseModel):
    """Exact optimistic-concurrency acknowledgement for one preview."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_snapshot_digest: str = Field(pattern=_HEX64)
    expected_action_payload_digest: str = Field(pattern=_HEX64)
    expected_preview_audit_id: str = Field(min_length=1, max_length=240)
    confirm: Literal[True]
    notes: str = Field(min_length=1, max_length=2000)


class ContentCurrentDispositionApprovalResponse(BaseModel):
    """Authoritative approval result and the read model used by the dashboard."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["current", "blocked"]
    projection: ContentCurrentDispositionReadProjection
    action: ActionObject | None = None
    receipt: ContentCurrentDispositionReceipt | None = None
    blockers: tuple[ContentCurrentDispositionBlocker, ...] = ()
    safe_next_step: str = "Odśwież exact current disposition i wykonaj nowy lifecycle."
    audit_ids: dict[str, str] = Field(default_factory=dict)
    external_write_attempted: Literal[False] = False

    @model_validator(mode="after")
    def require_projection_alignment(self) -> ContentCurrentDispositionApprovalResponse:
        if self.status != self.projection.status:
            raise ValueError("Approval response status must match its read projection.")
        if self.status == "current" and (self.receipt is None or self.action is None):
            raise ValueError("Current approval response requires its receipt and action.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked approval response requires a typed blocker.")
        if self.status == "blocked" and self.safe_next_step != self.blockers[0].next_step:
            raise ValueError("Blocked approval response must expose the blocker next step.")
        return self


class CurrentDispositionApprovalError(ValueError):
    """Stable typed conflict returned by the HTTP route as status 409."""

    def __init__(
        self,
        blocker: ContentCurrentDispositionBlocker,
        *,
        projection: ContentCurrentDispositionReadProjection | None = None,
        action: ActionObject | None = None,
        receipt: ContentCurrentDispositionReceipt | None = None,
        audit_ids: dict[str, str] | None = None,
    ) -> None:
        self.blocker = blocker
        self.projection = projection
        self.action = action
        self.receipt = receipt
        self.audit_ids = dict(audit_ids or {})
        super().__init__(blocker.reason)

    def response(self) -> ContentCurrentDispositionApprovalResponse:
        projection = self.projection
        if projection is None:
            projection = ContentCurrentDispositionReadProjection(
                status="blocked",
                action=self.action,
                receipt=self.receipt,
                blockers=(self.blocker,),
                safe_next_step=self.blocker.next_step,
            )
        return ContentCurrentDispositionApprovalResponse(
            status="blocked",
            projection=projection,
            action=self.action,
            receipt=self.receipt,
            blockers=(self.blocker,),
            safe_next_step=self.blocker.next_step,
            audit_ids=self.audit_ids,
        )


def validate_exact_current_disposition_request(
    *,
    proposal: ContentCurrentDispositionProposal,
    action: ActionObject,
    receipt: ContentCurrentDispositionReceipt | None,
    events: list[AuditEvent],
    request: ContentCurrentDispositionApprovalRequest,
) -> None:
    """Fail closed unless the request names the current action and preview."""

    if action.id != proposal.action_id:
        raise _lifecycle_error(
            "current_disposition_action_mismatch",
            "ActionObject nie pasuje do zapisanej propozycji.",
            "Przygotuj nowy exact preview.",
            action=action,
            receipt=receipt,
        )
    if action.payload.get("action_type") != CURRENT_DISPOSITION_ACTION_TYPE:
        raise _lifecycle_error(
            "current_disposition_action_type_invalid",
            "ActionObject nie jest akcją bieżącej disposition.",
            "Użyj wyłącznie server-built current disposition preview.",
            action=action,
            receipt=receipt,
        )
    if action.payload.get("local_authority_only") is not True:
        raise _lifecycle_error(
            "current_disposition_local_authority_required",
            "Ta akcja nie ma lokalnego authority-only kontraktu.",
            "Nie wykonuj jej; przygotuj nowy local-only preview.",
            action=action,
            receipt=receipt,
        )
    try:
        snapshot = ContentCurrentDispositionSnapshot.model_validate(
            action.payload.get("current_disposition_authority")
        )
    except Exception as error:
        raise _lifecycle_error(
            "current_disposition_snapshot_invalid",
            "Snapshot bieżącej disposition jest nieprawidłowy.",
            "Przygotuj nowy exact preview.",
            action=action,
            receipt=receipt,
        ) from error
    payload_digest = current_disposition_action_payload_digest(action)
    if snapshot.context_digest != request.expected_snapshot_digest:
        raise _lifecycle_error(
            "current_disposition_snapshot_drift",
            "Approval wskazuje inną wersję bieżącego snapshotu.",
            "Odśwież preview bieżącej disposition.",
            action=action,
            receipt=receipt,
        )
    if payload_digest != request.expected_action_payload_digest:
        raise _lifecycle_error(
            "current_disposition_action_payload_drift",
            "Approval wskazuje inną wersję payloadu ActionObject.",
            "Odśwież preview bieżącej disposition.",
            action=action,
            receipt=receipt,
        )
    if receipt is not None and (
        receipt.action_payload_digest != payload_digest
        or receipt.authority_snapshot.context_digest != snapshot.context_digest
        or receipt.preview_audit_id != request.expected_preview_audit_id
    ):
        raise _lifecycle_error(
            "current_disposition_receipt_conflict",
            "Istniejący receipt nie pasuje do żądanej exact wersji.",
            "Odśwież current disposition i użyj aktualnego receiptu.",
            action=action,
            receipt=receipt,
        )
    matching_previews = [
        event
        for event in events
        if event.action_id == action.id
        and event.event_type == "action_preview_generated"
        and _event_binding(event) == (snapshot.context_digest, payload_digest)
    ]
    requested_preview = next(
        (event for event in matching_previews if event.id == request.expected_preview_audit_id),
        None,
    )
    if requested_preview is None:
        raise _lifecycle_error(
            "current_disposition_preview_mismatch",
            "Approval wskazuje obcy albo nieaktualny preview audytu.",
            "Wykonaj preview dla aktualnego ActionObject i użyj jego audit ID.",
            action=action,
            receipt=receipt,
        )
    latest_preview = max(matching_previews, key=lambda event: (event.created_at, event.id))
    if receipt is None and latest_preview.id != requested_preview.id:
        raise _lifecycle_error(
            "current_disposition_preview_not_current",
            "Approval nie wskazuje najnowszego exact preview.",
            "Odśwież preview i ponów approval.",
            action=action,
            receipt=receipt,
        )


def _event_binding(event: AuditEvent) -> tuple[str, str] | None:
    snapshot = event.details.get("current_disposition_snapshot_digest")
    payload = event.details.get("current_disposition_action_payload_digest")
    if not isinstance(snapshot, str) or not isinstance(payload, str):
        return None
    return snapshot, payload


def _lifecycle_error(
    reason: str,
    message: str,
    next_step: str,
    *,
    action: ActionObject | None = None,
    receipt: ContentCurrentDispositionReceipt | None = None,
) -> CurrentDispositionApprovalError:
    del message
    return CurrentDispositionApprovalError(
        ContentCurrentDispositionBlocker(
            seam="receipt" if "receipt" in reason or "apply" in reason else "current_context",
            reason=reason,
            next_step=next_step,
        ),
        action=action,
        receipt=receipt,
    )


__all__ = [
    "ContentCurrentDispositionApprovalRequest",
    "ContentCurrentDispositionApprovalResponse",
    "CurrentDispositionApprovalError",
    "validate_exact_current_disposition_request",
]
