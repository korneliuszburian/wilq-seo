"""Stamp server-derived current-disposition digests onto audit events."""

from __future__ import annotations

from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_ACTION_TYPE,
    ContentCurrentDispositionSnapshot,
    current_disposition_action_payload_digest,
)
from wilq.content.workflow.delivery_identity_authority import (
    DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE,
    ContentDeliveryIdentityAuthoritySnapshot,
    delivery_identity_authority_action_payload_digest,
)
from wilq.schemas import ActionObject, AuditEvent


def stamp_authority_audit_context(action: ActionObject, event: AuditEvent) -> None:
    """Add exact current-disposition snapshot/payload digests to an audit event."""

    action_type = action.payload.get("action_type")
    if action_type == DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE:
        snapshot_payload = action.payload.get("delivery_identity_authority")
        if not isinstance(snapshot_payload, dict):
            return
        identity_snapshot = ContentDeliveryIdentityAuthoritySnapshot.model_validate(
            snapshot_payload
        )
        event.details = {
            **event.details,
            "delivery_identity_authority_snapshot_digest": identity_snapshot.context_digest,
            "delivery_identity_authority_action_payload_digest": (
                delivery_identity_authority_action_payload_digest(action)
            ),
        }
        return
    if action_type != CURRENT_DISPOSITION_ACTION_TYPE:
        return
    snapshot = ContentCurrentDispositionSnapshot.model_validate(
        action.payload.get("current_disposition_authority", {})
    )
    event.details = {
        **event.details,
        "current_disposition_snapshot_digest": snapshot.context_digest,
        "current_disposition_action_payload_digest": current_disposition_action_payload_digest(
            action
        ),
    }


__all__ = ["stamp_authority_audit_context"]
