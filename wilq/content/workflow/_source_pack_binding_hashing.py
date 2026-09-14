"""Pure hashing and payload canonicalization for source-pack receipts."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow._source_pack_binding_constants import SOURCE_FACT_REGISTRY_ID
from wilq.content.workflow.decisions.production import canonical_json_digest

if TYPE_CHECKING:
    from wilq.content.workflow._source_pack_binding_models import (
        ContentSourcePackBinding,
        ContentSourcePackBindingCommand,
        ContentSourcePackContextAttestation,
    )
    from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding


def _payload(value: Any) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return cast(dict[str, object], value.model_dump(mode="json"))

def content_source_pack_binding_logical_id(
    value: ContentSourcePackBinding | ContentSourcePackBindingCommand | dict[str, object],
) -> str:
    if not isinstance(value, dict):
        from wilq.content.workflow._source_pack_binding_models import (
            ContentSourcePackBinding,
            ContentSourcePackBindingCommand,
        )

        if isinstance(value, (ContentSourcePackBinding, ContentSourcePackBindingCommand)):
            return _content_source_pack_binding_logical_id_from_model(value)
    payload = _payload(value)
    source_fact_values = payload.get("source_fact_ids")
    evidence_values = payload.get("evidence_ids")
    receipt_value = payload.get("source_fact_registry_receipt")
    blocker_value = payload.get("blocker")
    logical_payload: dict[str, object] = {
        "source_pack_id": payload["source_pack_id"],
        "source_pack_sha256": payload["source_pack_sha256"],
        "identity_binding_id": payload["identity_binding_id"],
        "identity_binding_digest": payload["identity_binding_digest"],
        "current_work_item_id": payload["current_work_item_id"],
        "source_facts_digest": source_fact_ids_digest(
            tuple(source_fact_values) if isinstance(source_fact_values, (list, tuple)) else ()
        ),
        "evidence_ids_digest": evidence_ids_digest(
            tuple(evidence_values) if isinstance(evidence_values, (list, tuple)) else ()
        ),
        "fresh_context_digest": payload["fresh_context_digest"],
        "source_fact_registry_digest": (
            receipt_value.get("registry_digest") if isinstance(receipt_value, dict) else None
        ),
        "status": payload.get("status"),
        "blocker_reason": (
            blocker_value.get("reason") if isinstance(blocker_value, dict) else None
        ),
    }
    for key in (
        "source_fact_authority_receipt_id",
        "source_fact_authority_receipt_digest",
        "source_fact_authority_snapshot_digest",
    ):
        if key in payload:
            logical_payload[key] = payload[key]
    return canonical_json_digest(logical_payload)


def _content_source_pack_binding_logical_id_from_model(
    value: ContentSourcePackBinding | ContentSourcePackBindingCommand,
) -> str:
    from wilq.content.workflow._source_pack_binding_models import ContentSourcePackBinding

    receipt = value.source_fact_registry_receipt
    status = value.status if isinstance(value, ContentSourcePackBinding) else None
    blocker_reason = (
        value.blocker.reason
        if isinstance(value, ContentSourcePackBinding) and value.blocker is not None
        else None
    )
    logical_payload: dict[str, object] = {
        "source_pack_id": value.source_pack_id,
        "source_pack_sha256": value.source_pack_sha256,
        "identity_binding_id": value.identity_binding_id,
        "identity_binding_digest": value.identity_binding_digest,
        "current_work_item_id": value.current_work_item_id,
        "source_facts_digest": source_fact_ids_digest(value.source_fact_ids),
        "evidence_ids_digest": evidence_ids_digest(value.evidence_ids),
        "fresh_context_digest": value.fresh_context_digest,
        "source_fact_registry_digest": receipt.registry_digest,
        "status": status,
        "blocker_reason": blocker_reason,
    }
    optional_fields = {
        name
        for name in (
            "source_fact_authority_receipt_id",
            "source_fact_authority_receipt_digest",
            "source_fact_authority_snapshot_digest",
        )
        if name in value.__pydantic_fields_set__
    }
    for name in optional_fields:
        logical_payload[name] = getattr(value, name)
    return canonical_json_digest(logical_payload)


def source_fact_ids_digest(source_fact_ids: tuple[str, ...]) -> str:
    """Digest the exact ordered, allow-listed source fact IDs."""

    return canonical_json_digest({"source_fact_ids": source_fact_ids})


def evidence_ids_digest(evidence_ids: tuple[str, ...]) -> str:
    """Digest the exact ordered, allow-listed evidence IDs."""

    return canonical_json_digest({"evidence_ids": evidence_ids})


def source_fact_registry_digest(
    facts: tuple[ContentSourceFact, ...] | None = None,
) -> str:
    """Digest the exact currently readable source-fact registry projection."""

    facts = ekologus_source_facts() if facts is None else facts
    return canonical_json_digest(
        {
            "registry_id": SOURCE_FACT_REGISTRY_ID,
            "fact_count": len(facts),
            "facts": [fact.model_dump(mode="json") for fact in facts],
        }
    )


def content_source_pack_context_digest(
    identity: ContentDeliveryIdentityBinding,
    attestation: ContentSourcePackContextAttestation,
) -> str:
    """Digest the exact current S1 identity and its context attestation."""

    return canonical_json_digest(
        {
            "identity_binding_id": identity.binding_id,
            "identity_binding_digest": identity.binding_digest,
            "current_work_item_id": identity.current_work_item_id,
            "classification_run_id": identity.classification_run_id,
            "classification_run_digest": identity.classification_run_digest,
            "classification_decision_set_digest": identity.classification_decision_set_digest,
            "classification_source_row_digest": identity.classification_source_row_digest,
            "inventory_evidence_ids": identity.inventory_evidence_ids,
            "inventory_evidence_digest": identity.inventory_evidence_digest,
            "attestation": {
                "run_id": attestation.run_id,
                "source": attestation.source,
                "checked_at": attestation.checked_at.isoformat(),
                "evidence_ids": attestation.evidence_ids,
            },
        }
    )


def content_source_pack_binding_digest(
    value: ContentSourcePackBinding | dict[str, object],
) -> str:
    if isinstance(value, dict):
        payload = dict(value)
        binding_fields: set[str] = set()
    else:
        from wilq.content.workflow._source_pack_binding_models import ContentSourcePackBinding

        payload = _payload(value)
        binding_fields = (
            value.__pydantic_fields_set__ if isinstance(value, ContentSourcePackBinding) else set()
        )
    if binding_fields:
        for name in (
            "source_fact_authority_receipt_id",
            "source_fact_authority_receipt_digest",
            "source_fact_authority_snapshot_digest",
            "source_fact_authority_provenance_digest",
        ):
            if name not in binding_fields:
                payload.pop(name, None)
    for name in ("binding_id", "binding_digest", "recorded_by", "recorded_at"):
        payload.pop(name, None)
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
def source_fact_provenance_digest(provenance: tuple[Any, ...]) -> str:
    return canonical_json_digest(
        {"source_fact_provenance": [item.model_dump(mode="json") for item in provenance]}
    )
