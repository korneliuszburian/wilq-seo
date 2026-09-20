"""Stamp server-derived authority digests onto canonical action audit events."""

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
from wilq.content.workflow.research_promotion_authority import (
    CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
    parse_content_research_fact_promotion_snapshot,
    promotion_action_payload_digest,
)
from wilq.content.workflow.source_fact_authority import (
    SOURCE_FACT_AUTHORITY_ACTION_TYPE,
    parse_source_fact_authority_snapshot_json,
    source_fact_authority_action_payload_digest,
)
from wilq.schemas import ActionObject, AuditEvent


def stamp_authority_audit_context(action: ActionObject, event: AuditEvent) -> None:
    """Add exact authority snapshot/payload digests without changing audit identity."""

    action_type = action.payload.get("action_type")
    if action_type == DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE:
        snapshot_payload = action.payload.get("delivery_identity_authority")
        if not isinstance(snapshot_payload, dict):
            # A rebuilt action can be a typed blocked read when the current
            # classification/receipt disappeared.  It has no authority
            # digest to stamp, but lifecycle auditing must still be possible.
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
    if action_type == CURRENT_DISPOSITION_ACTION_TYPE:
        disposition_snapshot = ContentCurrentDispositionSnapshot.model_validate(
            action.payload.get("current_disposition_authority", {})
        )
        event.details = {
            **event.details,
            "current_disposition_snapshot_digest": disposition_snapshot.context_digest,
            "current_disposition_action_payload_digest": current_disposition_action_payload_digest(
                action
            ),
        }
        return
    if action_type == CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE:
        promotion_snapshot = parse_content_research_fact_promotion_snapshot(
            action.payload.get("promotion_snapshot", {})
        )
        event.details = {
            **event.details,
            "research_promotion_snapshot_digest": promotion_snapshot.context_digest,
            "research_promotion_action_payload_digest": promotion_action_payload_digest(action),
            # These canonical digest keys survive the local audit redaction boundary;
            # the descriptive keys above remain the operator-facing contract.
            "context_digest": promotion_snapshot.context_digest,
            "payload_digest": promotion_action_payload_digest(action),
        }
        return
    if action_type != SOURCE_FACT_AUTHORITY_ACTION_TYPE:
        return
    snapshot_payload = action.payload.get("source_fact_authority")
    if not isinstance(snapshot_payload, dict):
        return
    try:
        authority_snapshot = parse_source_fact_authority_snapshot_json(snapshot_payload)
    except Exception:
        # Blocked previews intentionally have no exact snapshot.  Their
        # generic ActionObject lifecycle must remain typed/HTTP-safe.
        return
    event.details = {
        **event.details,
        "source_fact_authority_snapshot_digest": authority_snapshot.context_digest,
        "source_fact_authority_action_payload_digest": source_fact_authority_action_payload_digest(
            action
        ),
    }


__all__ = ["stamp_authority_audit_context"]
