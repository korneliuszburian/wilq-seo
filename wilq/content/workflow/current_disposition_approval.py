"""Canonical local approval lifecycle for a current-disposition ActionObject.

The preview and receipt stores are deliberately kept in the content workflow
store.  This module is the small orchestration seam between that authority and
the existing ActionObject lifecycle helpers.  It never resolves a WordPress
capability and never calls a vendor adapter directly.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from wilq.actions import service as action_service
from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.content.workflow.current_disposition_approval_contract import (
    ContentCurrentDispositionApprovalRequest,
    ContentCurrentDispositionApprovalResponse,
    CurrentDispositionApprovalError,
    validate_exact_current_disposition_request,
)
from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionBlocker,
    ContentCurrentDispositionProposal,
    ContentCurrentDispositionReceipt,
    current_disposition_action_for_proposal,
    read_current_disposition_authority,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionObject,
    ActionReviewRequest,
    AuditEvent,
)
from wilq.storage.local_state import LocalStateStore, local_state_store

_ACTION_LOCKS: dict[str, tuple[threading.Lock, int]] = {}
_ACTION_LOCKS_GUARD = threading.Lock()


@contextmanager
def _action_serialization(action_id: str) -> Iterator[None]:
    """Serialize one approval key while allowing unrelated keys to proceed."""

    with _ACTION_LOCKS_GUARD:
        entry = _ACTION_LOCKS.get(action_id)
        lock = threading.Lock() if entry is None else entry[0]
        _ACTION_LOCKS[action_id] = (lock, 1 if entry is None else entry[1] + 1)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()
        with _ACTION_LOCKS_GUARD:
            current = _ACTION_LOCKS.get(action_id)
            if current is not None and current[0] is lock:
                if current[1] <= 1:
                    del _ACTION_LOCKS[action_id]
                else:
                    _ACTION_LOCKS[action_id] = (lock, current[1] - 1)


def approve_current_disposition_authority(
    store: ContentWorkflowStore,
    *,
    action_id: str,
    request: ContentCurrentDispositionApprovalRequest,
    audit_store: LocalStateStore | None = None,
) -> ContentCurrentDispositionApprovalResponse:
    """Validate and execute one local-only current-disposition lifecycle.

    The caller supplies the exact preview digests; all other action fields and
    the operator identity are rebuilt on the server.  A matching receipt is a
    read-only idempotent result and therefore does not append another lifecycle.
    """

    audit = audit_store or local_state_store()
    with _action_serialization(action_id):
        return _approve_current_disposition_authority_locked(
            store,
            action_id=action_id,
            request=request,
            audit_store=audit,
        )


def _approve_current_disposition_authority_locked(
    store: ContentWorkflowStore,
    *,
    action_id: str,
    request: ContentCurrentDispositionApprovalRequest,
    audit_store: LocalStateStore,
) -> ContentCurrentDispositionApprovalResponse:
    """Implementation run while the action key is held."""

    audit = audit_store
    proposal = store.load_content_current_disposition_proposal(action_id)
    if proposal is None:
        raise CurrentDispositionApprovalError(
            _blocker(
                "receipt",
                "current_disposition_proposal_missing",
                "Nie znaleziono exact propozycji bieżącej disposition.",
                "Przygotuj nowy preview bieżącej disposition.",
            )
        )

    action = _load_current_action(store, proposal)
    receipt = store.load_content_current_disposition_receipt(action_id)
    events = audit.list_audit_events(action_id=action_id)
    validate_exact_current_disposition_request(
        proposal=proposal,
        action=action,
        receipt=receipt,
        events=events,
        request=request,
    )

    # A receipt is immutable.  Return the same read projection without
    # re-recording review, confirm, impact or apply events.
    if receipt is not None:
        return _current_response(
            store,
            action_id=action_id,
            receipt=receipt,
            audit_events=events,
        )

    # The existing service facade owns identity stamping, redaction and audit
    # persistence.  Keep this composition here so the route has one narrow
    # authority seam and service.py remains unchanged.
    validation = action_service.validate_action(action)
    if not validation.valid:
        raise _lifecycle_error(
            "current_disposition_validation_blocked",
            "Walidacja ActionObject nie pozwala zatwierdzić bieżącej disposition.",
            "Usuń blokery walidacji i przygotuj nowy approval.",
            action=action,
            receipt=receipt,
        )

    action_service.record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            notes=request.notes,
        ),
    )
    _rehydrate_action(action, audit)
    confirmation = action_service.confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            notes=request.notes,
            preview_acknowledged=True,
        ),
    )
    _rehydrate_action(action, audit)
    if not confirmation.confirmed:
        raise _lifecycle_error(
            "current_disposition_confirmation_blocked",
            "Potwierdzenie bieżącej disposition jest zablokowane.",
            "Odśwież preview i wykonaj approval dla aktualnego łańcucha.",
            action=action,
            receipt=receipt,
            audit_ids=_audit_ids(action.audit_events),
        )

    impact = action_service.impact_check_action(
        action,
        ActionImpactCheckRequest(
            checked_by=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            notes=request.notes,
        ),
    )
    _rehydrate_action(action, audit)
    if impact.status != "checked":
        raise _lifecycle_error(
            "current_disposition_impact_check_blocked",
            "Sprawdzenie bieżącej disposition jest zablokowane.",
            "Uzupełnij warunki audytu i ponów approval.",
            action=action,
            receipt=receipt,
            audit_ids=_audit_ids(action.audit_events),
        )

    applied = action_service.apply_action(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        ),
    )
    if not applied.applied:
        winner = _matching_receipt(
            store,
            action=action,
            request=request,
        )
        if winner is not None:
            return _current_response(
                store,
                action_id=action_id,
                receipt=winner,
                audit_events=audit.list_audit_events(action_id=action_id),
            )
        raise _lifecycle_error(
            "current_disposition_apply_blocked",
            "Zapis lokalnego receiptu bieżącej disposition jest zablokowany.",
            "Odśwież exact current disposition i wykonaj nowy lifecycle.",
            action=action,
            receipt=receipt,
            audit_ids=_audit_ids(action.audit_events),
        )

    stored_receipt = _matching_receipt(store, action=action, request=request)
    if stored_receipt is None:
        raise _lifecycle_error(
            "current_disposition_receipt_missing",
            "Lifecycle zakończył się bez autorytatywnego receiptu.",
            "Odczytaj stan bieżącej disposition i nie ponawiaj starego żądania.",
            action=action,
            audit_ids=_audit_ids(audit.list_audit_events(action_id=action_id)),
        )
    return _current_response(
        store,
        action_id=action_id,
        receipt=stored_receipt,
        audit_events=audit.list_audit_events(action_id=action_id),
    )


def _rehydrate_action(action: ActionObject, audit_store: LocalStateStore) -> ActionObject:
    """Reload the complete append-only audit stream after each lifecycle step."""

    action.audit_events = audit_store.list_audit_events(action_id=action.id)
    return action


def _load_current_action(
    store: ContentWorkflowStore,
    proposal: ContentCurrentDispositionProposal,
) -> ActionObject:
    try:
        return current_disposition_action_for_proposal(store, proposal)
    except ValueError as error:
        raise _lifecycle_error(
            "current_disposition_context_unavailable",
            str(error),
            "Odśwież exact current disposition i przygotuj nowy preview.",
        ) from error


def _current_response(
    store: ContentWorkflowStore,
    *,
    action_id: str,
    receipt: ContentCurrentDispositionReceipt,
    audit_events: list[AuditEvent],
) -> ContentCurrentDispositionApprovalResponse:
    projection = read_current_disposition_authority(store, action_id=action_id)
    if projection.status != "current" or projection.receipt is None or projection.action is None:
        blocker = projection.blockers[0] if projection.blockers else _blocker(
            "receipt",
            "current_disposition_projection_unavailable",
            "Nie można odczytać autorytatywnego stanu bieżącej disposition.",
            "Odczytaj current disposition i rozstrzygnij blocker.",
        )
        raise CurrentDispositionApprovalError(
            blocker,
            projection=projection,
            action=projection.action,
            receipt=receipt,
            audit_ids=_audit_ids(audit_events),
        )
    return ContentCurrentDispositionApprovalResponse(
        status="current",
        projection=projection,
        action=projection.action,
        receipt=projection.receipt,
        audit_ids=_audit_ids(audit_events, receipt=receipt),
    )


def _matching_receipt(
    store: ContentWorkflowStore,
    *,
    action: ActionObject,
    request: ContentCurrentDispositionApprovalRequest,
) -> ContentCurrentDispositionReceipt | None:
    """Return only a receipt won by the same exact approval request."""

    receipt = store.load_content_current_disposition_receipt(action.id)
    if receipt is None:
        return None
    if (
        receipt.action_id != action.id
        or receipt.action_payload_digest != request.expected_action_payload_digest
        or receipt.authority_snapshot.context_digest != request.expected_snapshot_digest
        or receipt.preview_audit_id != request.expected_preview_audit_id
    ):
        return None
    return receipt


def _audit_ids(
    events: list[AuditEvent],
    *,
    receipt: ContentCurrentDispositionReceipt | None = None,
) -> dict[str, str]:
    ids: dict[str, str] = {}
    latest: dict[str, AuditEvent] = {}
    for event in sorted(events, key=lambda value: (value.created_at, value.id)):
        latest[event.event_type] = event
    mapping = {
        "action_preview_generated": "preview_audit_id",
        "human_review_approved_for_prepare": "review_audit_id",
        "action_apply_confirmed": "confirmation_audit_id",
        "action_impact_check_completed": "impact_audit_id",
        "apply_succeeded": "apply_audit_id",
    }
    for event_type, key in mapping.items():
        latest_event = latest.get(event_type)
        if latest_event is not None:
            ids[key] = latest_event.id
    if receipt is not None:
        ids.update(
            {
                "preview_audit_id": receipt.preview_audit_id,
                "review_audit_id": receipt.review_audit_id,
                "confirmation_audit_id": receipt.confirmation_audit_id,
                "impact_audit_id": receipt.impact_audit_id,
                "receipt_id": receipt.receipt_id,
            }
        )
    return ids


def _blocker(
    seam: Literal["classification", "current_context", "receipt"],
    reason: str,
    message: str,
    next_step: str,
) -> ContentCurrentDispositionBlocker:
    del message
    return ContentCurrentDispositionBlocker(seam=seam, reason=reason, next_step=next_step)


def _lifecycle_error(
    reason: str,
    message: str,
    next_step: str,
    *,
    action: ActionObject | None = None,
    receipt: ContentCurrentDispositionReceipt | None = None,
    audit_ids: dict[str, str] | None = None,
) -> CurrentDispositionApprovalError:
    return CurrentDispositionApprovalError(
        ContentCurrentDispositionBlocker(
            seam="receipt" if "receipt" in reason or "apply" in reason else "current_context",
            reason=reason,
            next_step=next_step,
        ),
        action=action,
        receipt=receipt,
        audit_ids=audit_ids,
    )


__all__ = [
    "ContentCurrentDispositionApprovalRequest",
    "ContentCurrentDispositionApprovalResponse",
    "CurrentDispositionApprovalError",
    "approve_current_disposition_authority",
]
