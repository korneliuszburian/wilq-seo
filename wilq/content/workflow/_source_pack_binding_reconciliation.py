"""Private source-pack reconciliation implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from wilq.content.workflow._source_pack_binding_guards import (
    _authority_binding_payload,
    _binding_blocker,
    _effective_evidence_ids,
    _known_evidence_ids,
)
from wilq.content.workflow._source_pack_binding_hashing import (
    content_source_pack_binding_digest,
    content_source_pack_binding_logical_id,
    content_source_pack_context_digest,
    evidence_ids_digest,
    source_fact_ids_digest,
)
from wilq.content.workflow._source_pack_binding_models import (
    ContentSourcePackBinding,
    ContentSourcePackBindingCommand,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding


def reconcile_content_source_pack_binding(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
    *,
    authority_receipt: Any | None = None,
    classification: Any | None = None,
    prior_pack_hashes: tuple[str, ...] = (),
    prior_source_fact_sets: tuple[tuple[str, ...], ...] = (),
    prior_evidence_sets: tuple[tuple[str, ...], ...] = (),
    now: datetime | None = None,
) -> ContentSourcePackBinding:
    """Build one exact receipt; all joins are explicit and fail closed.

    Prior values are supplied by the store, not looked up by fuzzy path or
    implicit latest state.  They prevent a changed source pack/context/evidence
    set from silently replacing an earlier immutable receipt.
    """

    accepted = ContentSourcePackBindingCommand.model_validate_json(
        command.model_dump_json(), strict=True
    )
    blocker = _binding_blocker(
        accepted,
        identity,
        authority_receipt=authority_receipt,
        classification=classification,
        prior_pack_hashes=prior_pack_hashes,
        prior_source_fact_sets=prior_source_fact_sets,
        prior_evidence_sets=prior_evidence_sets,
        now=datetime.now(UTC) if now is None else now,
    )
    status: Literal["exact_current", "blocked"] = "blocked" if blocker else "exact_current"
    persisted_evidence_ids = _effective_evidence_ids(accepted, identity, authority_receipt)
    persisted_registry_evidence_ids = _known_evidence_ids(
        accepted.source_fact_registry_receipt.evidence_ids, None, authority_receipt
    )
    persisted_context_attestation = accepted.fresh_context_attestation.model_copy(
        update={
            "evidence_ids": _known_evidence_ids(
                accepted.fresh_context_attestation.evidence_ids, identity, authority_receipt
            )
        }
    )
    persisted_context_digest = (
        content_source_pack_context_digest(identity, persisted_context_attestation)
        if identity is not None
        else accepted.fresh_context_digest
    )
    persisted_context_attestation = persisted_context_attestation.model_copy(
        update={"context_digest": persisted_context_digest}
    )
    payload: dict[str, object] = {
        "schema_version": "wilq_content_source_pack_binding_v1",
        "status": status,
        "source_pack_id": accepted.source_pack_id,
        "source_pack_sha256": accepted.source_pack_sha256,
        "identity_binding_id": accepted.identity_binding_id,
        "identity_binding_digest": accepted.identity_binding_digest,
        "current_work_item_id": accepted.current_work_item_id,
        "source_fact_ids": accepted.source_fact_ids,
        "evidence_ids": persisted_evidence_ids,
        "source_facts_digest": source_fact_ids_digest(accepted.source_fact_ids),
        "evidence_ids_digest": evidence_ids_digest(persisted_evidence_ids),
        "fresh_context_digest": persisted_context_digest,
        "source_fact_registry_receipt": accepted.source_fact_registry_receipt.model_copy(
            update={"evidence_ids": persisted_registry_evidence_ids}
        ).model_dump(mode="json"),
        "fresh_context_attestation": persisted_context_attestation.model_dump(mode="json"),
        **_authority_binding_payload(authority_receipt),
        "blocker": None if blocker is None else blocker.model_dump(mode="json"),
        "recorded_by": accepted.recorded_by,
        "recorded_at": accepted.recorded_at.isoformat(),
    }
    digest = content_source_pack_binding_digest(payload)
    logical_id = content_source_pack_binding_logical_id(payload)
    return ContentSourcePackBinding.model_validate(
        {
            "binding_id": f"content_source_pack_binding_{logical_id[:24]}",
            "binding_digest": digest,
            **payload,
        }
    )
