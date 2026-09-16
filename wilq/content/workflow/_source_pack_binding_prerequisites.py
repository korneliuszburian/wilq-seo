"""Private prerequisite projection for exact source-pack consumption."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow._source_pack_binding_constants import (
    _MAX_RECEIPT_AGE,
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    SOURCE_FACT_REGISTRY_ID,
)
from wilq.content.workflow._source_pack_binding_hashing import (
    content_source_pack_context_digest,
    source_fact_registry_digest,
)
from wilq.content.workflow._source_pack_binding_models import (
    ContentSourceFactRegistryReceipt,
    ContentSourcePackContextAttestation,
    ContentSourcePackFactProvenance,
    ContentSourcePackPrerequisites,
    ContentSourcePackRowAuthorityReceipt,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding


@dataclass(frozen=True)
class _RowAuthorityState:
    status: Literal["missing", "exact_current", "blocked"]
    reason: str
    safe_next_step: str
    blocker_reason: str | None
    projection: ContentSourcePackRowAuthorityReceipt | None
    approved_source_fact_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


def _registry_receipt(
    facts: tuple[Any, ...], timestamp: datetime
) -> ContentSourceFactRegistryReceipt:
    return ContentSourceFactRegistryReceipt(
        registry_id=SOURCE_FACT_REGISTRY_ID,
        registry_digest=source_fact_registry_digest(facts),
        checked_at=timestamp,
        evidence_ids=tuple(
            sorted(
                {
                    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                }
            )
        ),
    )


def _context_attestation(
    identity: ContentDeliveryIdentityBinding, timestamp: datetime
) -> ContentSourcePackContextAttestation:
    attestation = ContentSourcePackContextAttestation(
        run_id=identity.classification_run_id,
        context_digest="1" * 64,
        checked_at=timestamp,
        source="content_delivery_identity_binding",
        evidence_ids=identity.inventory_evidence_ids,
    )
    return attestation.model_copy(
        update={"context_digest": content_source_pack_context_digest(identity, attestation)}
    )


def _authority_input(
    authority_receipt: Any | None,
    authority_receipts: tuple[Any, ...] | None,
) -> Any | None:
    if authority_receipt is None and authority_receipts and len(authority_receipts) == 1:
        return authority_receipts[0]
    return authority_receipt


def _blocked_row_authority_state(
    reason: str,
    message: str,
    next_step: str,
) -> _RowAuthorityState:
    return _RowAuthorityState(
        status="blocked",
        reason=message,
        safe_next_step=next_step,
        blocker_reason=reason,
        projection=None,
    )


def _parse_authority_receipt(value: Any) -> Any:
    from wilq.content.workflow.source_fact_authority import ContentSourceFactAuthorityReceipt

    return ContentSourceFactAuthorityReceipt.model_validate_json(
        value.model_dump_json()
        if isinstance(value, BaseModel)
        else json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        strict=True,
    )


def _authority_context_matches(
    snapshot: Any,
    identity: ContentDeliveryIdentityBinding,
) -> bool:
    return bool(
        snapshot.identity_binding_id == identity.binding_id
        and snapshot.identity_binding_digest == identity.binding_digest
        and snapshot.current_work_item_id == identity.current_work_item_id
        and snapshot.canonical_path == identity.canonical_path
        and snapshot.public_url == identity.public_url
        and snapshot.classification_run_id == identity.classification_run_id
        and snapshot.classification_run_digest == identity.classification_run_digest
        and snapshot.classification_decision_set_digest
        == identity.classification_decision_set_digest
        and snapshot.classification_source_row_digest == identity.classification_source_row_digest
    )


def _current_row_authority_state(
    accepted: Any,
    identity: ContentDeliveryIdentityBinding,
    classification: Any,
    facts: tuple[Any, ...],
    registry_receipt: ContentSourceFactRegistryReceipt,
    timestamp: datetime,
) -> _RowAuthorityState:
    from wilq.content.workflow.source_fact_authority import (
        authority_source_fact_provenance,
        build_source_fact_authority_snapshot,
    )

    snapshot = accepted.authority_snapshot
    expected_snapshot, blockers = build_source_fact_authority_snapshot(
        identity,
        classification,
        snapshot.source_fact_ids,
        facts=facts,
        identity_binding_id=identity.binding_id,
    )
    blocker_reason = blockers[0].reason if blockers else None
    if not _authority_context_matches(snapshot, identity):
        blocker_reason = "source_fact_authority_drift"
    facts_by_id = {fact.source_id: fact for fact in facts}
    expected_provenance = tuple(
        authority_source_fact_provenance(facts_by_id[item])
        for item in snapshot.source_fact_ids
        if item in facts_by_id
    )
    if (
        snapshot.source_fact_registry_id != SOURCE_FACT_REGISTRY_ID
        or snapshot.source_fact_registry_digest != registry_receipt.registry_digest
        or len(expected_provenance) != len(snapshot.source_fact_ids)
        or tuple(snapshot.source_fact_provenance) != expected_provenance
    ):
        blocker_reason = "source_fact_authority_stale"
    if accepted.recorded_at > timestamp or timestamp - accepted.recorded_at > _MAX_RECEIPT_AGE:
        blocker_reason = "source_fact_authority_stale"
    if blocker_reason is None and (expected_snapshot is None or expected_snapshot != snapshot):
        blocker_reason = "source_fact_authority_drift"
    if blocker_reason is not None:
        return _blocked_row_authority_state(
            blocker_reason,
            "Row-authority receipt istnieje, ale nie odpowiada bieżącej tożsamości, "
            "klasyfikacji, registry albo karcie usługi.",
            "Zwiększ attempt, przygotuj exact authority i przejdź nowy pełny lifecycle; "
            "nie ponawiaj tego samego action.",
        )
    provenance = tuple(
        ContentSourcePackFactProvenance.model_validate_json(item.model_dump_json(), strict=True)
        for item in snapshot.source_fact_provenance
    )
    projection = ContentSourcePackRowAuthorityReceipt(
        receipt_id=accepted.receipt_id,
        receipt_digest=accepted.receipt_digest,
        action_id=accepted.action_id,
        authority_snapshot_digest=snapshot.context_digest,
        source_fact_ids=snapshot.source_fact_ids,
        source_facts_digest=snapshot.source_facts_digest,
        source_fact_provenance=provenance,
        source_fact_provenance_digest=snapshot.source_fact_provenance_digest,
        evidence_ids=snapshot.evidence_ids,
        evidence_ids_digest=snapshot.evidence_ids_digest,
        action_payload_digest=accepted.action_payload_digest,
        preview_audit_id=accepted.preview_audit_id,
        review_audit_id=accepted.review_audit_id,
        confirmation_audit_id=accepted.confirmation_audit_id,
        impact_audit_id=accepted.impact_audit_id,
        reviewed_by=accepted.reviewed_by,
        confirmed_by=accepted.confirmed_by,
        recorded_by=accepted.recorded_by,
        recorded_at=accepted.recorded_at,
    )
    return _RowAuthorityState(
        status="exact_current",
        reason="Bieżący wiersz ma exact, zatwierdzony source-fact receipt.",
        safe_next_step="Możesz przygotować source pack wyłącznie z tych faktów i evidence.",
        blocker_reason=None,
        projection=projection,
        approved_source_fact_ids=snapshot.source_fact_ids,
        evidence_ids=snapshot.evidence_ids,
    )


def _row_authority_state(
    identity: ContentDeliveryIdentityBinding,
    classification: Any | None,
    authority_receipt: Any | None,
    authority_receipts: tuple[Any, ...] | None,
    facts: tuple[Any, ...],
    registry_receipt: ContentSourceFactRegistryReceipt,
    timestamp: datetime,
) -> _RowAuthorityState:
    if classification is None:
        return _blocked_row_authority_state(
            "classification_current_missing",
            "Bieżąca klasyfikacja exact wiersza S1 jest niedostępna.",
            "Odczytaj bieżącą klasyfikację i dopiero potem przygotuj authority.",
        )
    if authority_receipt is None and authority_receipts and len(authority_receipts) > 1:
        return _blocked_row_authority_state(
            "source_fact_authority_ambiguous",
            "Dla exact wiersza istnieje więcej niż jeden row-authority receipt.",
            "Wybierz jeden exact receipt albo przygotuj nowy authority preview.",
        )
    if authority_receipt is None:
        return _RowAuthorityState(
            status="missing",
            reason="Bieżący wiersz S1 nie ma exact per-work-item source-fact receiptu.",
            safe_next_step=(
                "Zarejestruj oddzielny, autorytatywny receipt source facts dla tego work itemu."
            ),
            blocker_reason="source_fact_row_binding_missing",
            projection=None,
        )
    try:
        accepted = _parse_authority_receipt(authority_receipt)
    except Exception:
        return _blocked_row_authority_state(
            "source_fact_authority_invalid",
            "Row-authority receipt nie przechodzi walidacji exact bieżącego kontekstu.",
            "Odtwórz preview authority i przejdź nowy pełny lifecycle.",
        )
    return _current_row_authority_state(
        accepted, identity, classification, facts, registry_receipt, timestamp
    )


def build_content_source_pack_prerequisites(
    identity: ContentDeliveryIdentityBinding,
    *,
    checked_at: datetime | None = None,
    authority_receipt: Any | None = None,
    authority_receipts: tuple[Any, ...] | None = None,
    classification: Any | None = None,
) -> ContentSourcePackPrerequisites:
    """Build current registry/context and exact row-authority receipts.

    ``authority_receipt`` is deliberately supplied by the exact-ID store
    lookup.  This function never infers authority from the global approved
    registry or from a URL.
    """

    timestamp = checked_at or datetime.now(UTC)
    authority_receipt = _authority_input(authority_receipt, authority_receipts)
    facts = ekologus_source_facts()
    registry_receipt = _registry_receipt(facts, timestamp)
    attestation = _context_attestation(identity, timestamp)
    row_authority = _row_authority_state(
        identity,
        classification,
        authority_receipt,
        authority_receipts,
        facts,
        registry_receipt,
        timestamp,
    )
    return ContentSourcePackPrerequisites(
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        current_work_item_id=identity.current_work_item_id,
        row_authority_status=row_authority.status,
        row_authority_reason_pl=row_authority.reason,
        safe_next_step_pl=row_authority.safe_next_step,
        approved_source_fact_ids=row_authority.approved_source_fact_ids,
        global_approved_source_fact_count=sum(fact.review_status == "approved" for fact in facts),
        source_fact_registry_receipt=registry_receipt,
        fresh_context_digest=attestation.context_digest,
        fresh_context_attestation=attestation,
        row_authority_receipt=row_authority.projection,
        source_fact_authority_receipt=row_authority.projection,
        row_authority_evidence_ids=row_authority.evidence_ids,
        allowed_evidence_ids=row_authority.evidence_ids,
        row_authority_blocker_reason=row_authority.blocker_reason,
    )
