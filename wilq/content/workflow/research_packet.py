"""Immutable, redacted per-URL research packet reconciliation policy."""

from __future__ import annotations

from datetime import datetime

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.research_packet_contracts import (
    _MAX_FRESHNESS_AGE,
    RESEARCH_PACKET_SCHEMA_VERSION,
    ContentResearchPacket,
    ContentResearchPacketBlocker,
    ContentResearchPacketCommand,
    ContentResearchPacketContextReceipt,
    ContentResearchPacketCurrentProjection,
    ContentResearchPacketFreshness,
    ContentResearchPacketInternalLink,
    ContentResearchPacketReadResult,
    ContentResearchPacketRecordResult,
    ResearchPacketBlockerReason,
    ResearchPacketBlockerSeam,
    ResearchPacketCurrentStatus,
    ResearchPacketStatus,
    _is_safe_path,
    research_packet_digest,
    research_packet_input_digest,
    research_packet_logical_id,
    source_ids_digest,
)
from wilq.content.workflow.research_packet_preparation_receipt import (
    ContentResearchPacketPreparationReceipt,
    preparation_receipt_matches_command,
)
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    source_fact_registry_digest,
)


def reconcile_content_research_packet(
    command: ContentResearchPacketCommand,
    identity: ContentDeliveryIdentityBinding | None,
    source_pack: ContentSourcePackBinding | None,
    *,
    preparation_receipt: ContentResearchPacketPreparationReceipt | None = None,
    now: datetime | None = None,
) -> ContentResearchPacket:
    accepted = ContentResearchPacketCommand.model_validate_json(
        command.model_dump_json(), strict=True
    )
    timestamp = now or accepted.recorded_at
    blocker = _research_packet_blocker(
        accepted,
        identity,
        source_pack,
        timestamp,
        preparation_receipt=preparation_receipt,
    )
    status: ResearchPacketStatus = "blocked" if blocker else "exact_current"
    identity_fields = _identity_fields(identity)
    registry_digest = ""
    if source_pack is not None:
        registry_digest = source_pack.source_fact_registry_receipt.registry_digest
    payload: dict[str, object] = {
        "schema_version": RESEARCH_PACKET_SCHEMA_VERSION,
        "status": status,
        "source_pack_binding_id": accepted.source_pack_binding_id,
        "source_pack_binding_digest": accepted.source_pack_binding_digest,
        "identity_binding_id": accepted.identity_binding_id,
        "identity_binding_digest": accepted.identity_binding_digest,
        "current_work_item_id": accepted.current_work_item_id,
        "preparation_receipt_id": accepted.preparation_receipt_id,
        "preparation_receipt_digest": accepted.preparation_receipt_digest,
        **identity_fields,
        "content_kind": accepted.content_kind,
        "intent": accepted.intent,
        "query_cluster": accepted.query_cluster,
        "canonical_owner": accepted.canonical_owner,
        "target_audience": accepted.target_audience,
        "buyer_problem": accepted.buyer_problem,
        "buyer_trigger": accepted.buyer_trigger,
        "approved_source_fact_ids": accepted.approved_source_fact_ids,
        "blocked_claims": accepted.blocked_claims,
        "evidence_ids": accepted.evidence_ids,
        "source_fact_registry_digest": registry_digest,
        "source_facts_digest": source_ids_digest(accepted.approved_source_fact_ids),
        "evidence_ids_digest": source_ids_digest(accepted.evidence_ids),
        "freshness": tuple(item.model_dump(mode="json") for item in accepted.freshness),
        "legal_source_requirements": accepted.legal_source_requirements,
        "cta_destination": accepted.cta_destination,
        "internal_links": tuple(
            item.model_dump(mode="json") for item in accepted.internal_links
        ),
        "context_receipt": (
            None
            if accepted.context_receipt is None
            else accepted.context_receipt.model_dump(mode="json")
        ),
        "input_digest": research_packet_input_digest(accepted),
        "blocker": None if blocker is None else blocker.model_dump(mode="json"),
        "recorded_by": accepted.recorded_by,
        "recorded_at": accepted.recorded_at.isoformat(),
    }
    digest = research_packet_digest(payload)
    logical_id = research_packet_logical_id(payload)
    return ContentResearchPacket.model_validate(
        {
            "packet_id": f"content_research_packet_{logical_id[:24]}",
            "packet_digest": digest,
            **payload,
        }
    )


def _identity_fields(identity: ContentDeliveryIdentityBinding | None) -> dict[str, object]:
    if identity is None:
        return {
            "classification_source_row_digest": "",
            "canonical_path": "",
            "public_url": "",
            "final_disposition": "keep",
        }
    return {
        "classification_source_row_digest": identity.classification_source_row_digest,
        "canonical_path": identity.canonical_path,
        "public_url": identity.public_url,
        "final_disposition": identity.final_disposition,
    }


def _research_packet_blocker(
    command: ContentResearchPacketCommand,
    identity: ContentDeliveryIdentityBinding | None,
    source_pack: ContentSourcePackBinding | None,
    now: datetime,
    *,
    preparation_receipt: ContentResearchPacketPreparationReceipt | None = None,
) -> ContentResearchPacketBlocker | None:
    evidence = command.evidence_ids
    if source_pack is None:
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_missing",
            evidence,
            "Najpierw zapisz exact source-pack binding dla tego identity bindingu.",
        )
    if (
        source_pack.binding_id != command.source_pack_binding_id
        or source_pack.binding_digest != command.source_pack_binding_digest
    ):
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_digest_mismatch",
            evidence,
            "Użyj ID i digestu z tego same persisted source-pack bindingu.",
        )
    if (
        source_pack.identity_binding_id != command.identity_binding_id
        or source_pack.identity_binding_digest != command.identity_binding_digest
        or source_pack.current_work_item_id != command.current_work_item_id
    ):
        return _blocker(
            "source_pack_binding",
            "source_pack_identity_mismatch",
            source_pack.evidence_ids,
            "Użyj source-pack bindingu należącego do tego samego identity i work itemu.",
        )
    if source_pack.status == "blocked":
        return _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            source_pack.evidence_ids,
            "Usuń typed blocker source-pack bindingu i odśwież packet.",
        )
    if identity is None:
        return _blocker(
            "identity_binding",
            "identity_binding_missing",
            source_pack.evidence_ids,
            "Najpierw zapisz exact delivery identity binding.",
        )
    if (
        identity.binding_id != command.identity_binding_id
        or identity.binding_digest != command.identity_binding_digest
    ):
        return _blocker(
            "identity_binding",
            "identity_binding_digest_mismatch",
            source_pack.evidence_ids,
            "Użyj ID i digestu z tego same persisted identity bindingu.",
        )
    if identity.status == "blocked":
        return _blocker(
            "identity_binding",
            "identity_binding_blocked",
            identity.inventory_evidence_ids,
            "Usuń typed blocker identity bindingu i odśwież packet.",
        )
    if identity.current_work_item_id != command.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            identity.inventory_evidence_ids,
            "Wskaż current work item z exact identity bindingu.",
        )
    if identity.final_disposition != "keep":
        return _blocker(
            "work_item_identity",
            "disposition_not_keep",
            identity.inventory_evidence_ids,
            "Packet produkcyjny twórz wyłącznie dla URL-a z decyzją keep.",
        )
    context_blocker = _context_receipt_blocker(command, identity, source_pack)
    if context_blocker is not None:
        return context_blocker
    preparation_blocker = _preparation_receipt_blocker(command, preparation_receipt)
    if preparation_blocker is not None:
        return preparation_blocker
    return (
        _semantic_blocker(command, source_pack, identity, now)
        or _source_fact_blocker(command, source_pack)
        or _evidence_blocker(command, source_pack)
        or _freshness_blocker(command, source_pack, now)
    )


def _preparation_receipt_blocker(
    command: ContentResearchPacketCommand,
    preparation_receipt: ContentResearchPacketPreparationReceipt | None,
) -> ContentResearchPacketBlocker | None:
    if command.preparation_receipt_id is None or preparation_receipt is None:
        return _blocker(
            "preparation_receipt",
            "preparation_receipt_missing",
            command.evidence_ids,
            "Przygotuj server-owned preparation receipt przed zapisaniem packetu.",
        )
    if not preparation_receipt_matches_command(preparation_receipt, command):
        return _blocker(
            "preparation_receipt",
            "preparation_receipt_mismatch",
            command.evidence_ids,
            "Użyj preparation receipt wygenerowanego dla tego exact kontekstu.",
        )
    return None


def _context_receipt_blocker(
    command: ContentResearchPacketCommand,
    identity: ContentDeliveryIdentityBinding,
    source_pack: ContentSourcePackBinding,
) -> ContentResearchPacketBlocker | None:
    context = command.context_receipt
    if context is None:
        return _blocker(
            "identity_binding",
            "context_receipt_missing",
            identity.inventory_evidence_ids,
            "Przygotuj exact typed context receipt przed zapisaniem packetu.",
        )
    if (
        context.classification_run_id != identity.classification_run_id
        or context.classification_run_digest != identity.classification_run_digest
        or context.identity_binding_id != identity.binding_id
        or context.identity_binding_digest != identity.binding_digest
        or context.classification_source_row_digest
        != identity.classification_source_row_digest
        or context.source_fact_authority_receipt_id
        != source_pack.source_fact_authority_receipt_id
        or context.source_fact_authority_receipt_digest
        != source_pack.source_fact_authority_receipt_digest
        or context.source_fact_authority_snapshot_digest
        != source_pack.source_fact_authority_snapshot_digest
        or context.source_fact_authority_provenance_digest
        != source_pack.source_fact_authority_provenance_digest
        or context.cta_destination != command.cta_destination
    ):
        return _blocker(
            "identity_binding",
            "context_receipt_mismatch",
            identity.inventory_evidence_ids,
            "Odśwież server-owned context receipt dla bieżącego identity i klasyfikacji.",
        )
    context_evidence = set(context.evidence_ids)
    if not context_evidence.issubset(command.evidence_ids):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            context.evidence_ids,
            "Context receipt może wskazywać wyłącznie evidence packetu.",
        )
    trusted_context_evidence = _trusted_context_evidence_ids(context)
    if trusted_context_evidence and not trusted_context_evidence.issubset(context_evidence):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            tuple(sorted(trusted_context_evidence)),
            "Typed receipts contextu muszą należeć do jego assertion evidence.",
        )
    if trusted_context_evidence and set(command.evidence_ids) != trusted_context_evidence:
        return _blocker(
            "evidence",
            "evidence_not_bound",
            tuple(sorted(set(command.evidence_ids) ^ trusted_context_evidence)),
            "Każde evidence packetu musi należeć do osobnej typed partycji contextu.",
        )
    source_pack_evidence = set(source_pack.evidence_ids) | set(
        source_pack.source_fact_registry_receipt.evidence_ids
    )
    if not set(context.source_pack_evidence_ids).issubset(source_pack_evidence):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            context.source_pack_evidence_ids,
            "Source-pack receipt może wskazywać wyłącznie evidence exact source-packu.",
        )
    if not set(context.planning_evidence_ids).issubset(set(identity.inventory_evidence_ids)):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            context.planning_evidence_ids,
            "Planning receipt może wskazywać wyłącznie evidence exact identity.",
        )
    source_fact_evidence = {
        evidence_id
        for fact in ekologus_source_facts()
        if fact.source_id in source_pack.source_fact_ids
        for evidence_id in fact.evidence_ids
    }
    source_fact_evidence.update(source_pack.source_fact_registry_receipt.evidence_ids)
    if not set(context.source_fact_evidence_ids).issubset(source_fact_evidence):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            context.source_fact_evidence_ids,
            "Source-fact receipt może wskazywać wyłącznie evidence exact source-packu.",
        )
    return None


def _trusted_context_evidence_ids(
    context: ContentResearchPacketContextReceipt,
) -> set[str]:
    return {
        evidence_id
        for values in (
            context.source_pack_evidence_ids,
            context.source_fact_evidence_ids,
            context.demand_evidence_ids,
            context.measurement_evidence_ids,
            context.verified_link_evidence_ids,
            context.cta_evidence_ids,
            context.regulatory_evidence_ids,
            context.planning_evidence_ids,
        )
        for evidence_id in values
    }


def _semantic_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
    identity: ContentDeliveryIdentityBinding,
    now: datetime,
) -> ContentResearchPacketBlocker | None:
    del source_pack, identity, now
    checks: tuple[
        tuple[ResearchPacketBlockerSeam, ResearchPacketBlockerReason, bool, str], ...
    ] = (
        (
            "content_kind",
            "content_kind_ambiguous",
            command.content_kind not in {"service", "editorial", "landing_or_hub"},
            "Ustal exact content kind z inventory i nie używaj ambiguous.",
        ),
        (
            "intent",
            "intent_missing",
            not command.intent,
            "Uzupełnij exact intent dla tego URL-a.",
        ),
        (
            "intent",
            "query_cluster_missing",
            not command.query_cluster,
            "Uzupełnij exact query cluster z aktualnego evidence.",
        ),
        (
            "audience",
            "audience_missing",
            not command.target_audience,
            "Uzupełnij exact target audience.",
        ),
        (
            "audience",
            "buyer_problem_missing",
            not command.buyer_problem,
            "Uzupełnij problem kupującego.",
        ),
        (
            "audience",
            "buyer_trigger_missing",
            not command.buyer_trigger,
            "Uzupełnij trigger/problem moment.",
        ),
        (
            "canonical_owner",
            "canonical_owner_missing",
            not command.canonical_owner,
            "Ustal canonical owner bez fuzzy joinu.",
        ),
        (
            "legal_requirements",
            "legal_requirements_missing",
            not command.legal_source_requirements,
            "Zapisz wymagania źródłowe albo jawne none_identified.",
        ),
        (
            "cta",
            "cta_destination_missing",
            not command.cta_destination,
            "Ustal jedną bezpieczną destynację CTA.",
        ),
    )
    for seam, reason, failed, next_step in checks:
        if failed:
            return _blocker(seam, reason, (), next_step)
    if not _is_safe_path(command.cta_destination):
        return _blocker(
            "cta",
            "cta_destination_invalid",
            (),
            "Użyj wyłącznie bezpiecznej ścieżki CTA na stronie Ekologus.",
        )
    if not command.internal_links:
        return _blocker(
            "internal_links",
            "internal_links_missing",
            (),
            "Dodaj co najmniej jeden exact internal link albo zablokuj packet.",
        )
    if any(link.verification != "exact_verified" for link in command.internal_links):
        return _blocker(
            "internal_links",
            "internal_link_not_verified",
            (),
            "Potwierdź exact destination każdego internal linku.",
        )
    return None


def _source_fact_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
) -> ContentResearchPacketBlocker | None:
    if not command.approved_source_fact_ids:
        return _blocker(
            "source_facts",
            "source_facts_missing",
            source_pack.evidence_ids,
            "Wskaż approved source-fact IDs.",
        )
    if not set(command.approved_source_fact_ids).issubset(set(source_pack.source_fact_ids)):
        return _blocker(
            "source_facts",
            "source_fact_not_bound",
            source_pack.evidence_ids,
            "Użyj wyłącznie fact IDs z exact source-pack whitelisty.",
        )
    facts = {fact.source_id: fact for fact in ekologus_source_facts()}
    if set(command.approved_source_fact_ids) - set(facts):
        return _blocker(
            "source_facts",
            "source_fact_not_registered",
            source_pack.evidence_ids,
            "Odśwież current source-fact registry.",
        )
    if any(
        facts[item].review_status != "approved"
        for item in command.approved_source_fact_ids
    ):
        return _blocker(
            "source_facts",
            "source_fact_not_approved",
            source_pack.evidence_ids,
            "Użyj tylko source facts ze statusem approved.",
        )
    required_blocked_claims = {
        claim
        for item in command.approved_source_fact_ids
        for claim in facts[item].blocked_claims
    }
    if not required_blocked_claims.issubset(set(command.blocked_claims)):
        return _blocker(
            "source_facts",
            "source_fact_not_approved",
            source_pack.evidence_ids,
            "Przenieś wszystkie blocked claims z fact registry do packetu.",
        )
    current_digest = source_fact_registry_digest(ekologus_source_facts())
    if source_pack.source_fact_registry_receipt.registry_digest != current_digest:
        return _blocker(
            "source_facts",
            "source_fact_registry_stale",
            source_pack.evidence_ids,
            "Odśwież source-pack binding względem aktualnego registry.",
        )
    return None


def _evidence_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
) -> ContentResearchPacketBlocker | None:
    if not command.evidence_ids:
        return _blocker(
            "evidence", "evidence_missing", (), "Wskaż evidence IDs z exact source packa."
        )
    allowed = set(source_pack.evidence_ids) | set(
        source_pack.source_fact_registry_receipt.evidence_ids
    )
    if command.context_receipt is not None:
        allowed.update(_trusted_context_evidence_ids(command.context_receipt))
    if not set(command.evidence_ids).issubset(allowed):
        return _blocker(
            "evidence",
            "evidence_not_bound",
            source_pack.evidence_ids,
            "Usuń evidence spoza source-pack whitelisty.",
        )
    return None


def _freshness_blocker(
    command: ContentResearchPacketCommand,
    source_pack: ContentSourcePackBinding,
    now: datetime,
) -> ContentResearchPacketBlocker | None:
    del source_pack
    if not command.freshness:
        return _blocker(
            "freshness",
            "freshness_missing",
            command.evidence_ids,
            "Dodaj freshness receipt dla każdego source factu.",
        )
    facts = set(command.approved_source_fact_ids)
    freshness_by_source = {item.source_id: item for item in command.freshness}
    if set(freshness_by_source) != facts:
        return _blocker(
            "freshness",
            "freshness_missing",
            command.evidence_ids,
            "Zwiąż freshness dokładnie z każdym approved source factem.",
        )
    for item in command.freshness:
        if not item.evidence_ids:
            return _blocker(
                "freshness",
                "evidence_missing",
                command.evidence_ids,
                "Każdy freshness receipt musi wskazywać evidence ID.",
            )
        if (
            item.status != "fresh"
            or item.checked_at > now
            or now - item.checked_at > _MAX_FRESHNESS_AGE
        ):
            return _blocker(
                "freshness",
                "freshness_stale",
                item.evidence_ids,
                "Odśwież stale/unknown source evidence przed packetem.",
            )
        if not set(item.evidence_ids).issubset(set(command.evidence_ids)):
            return _blocker(
                "freshness",
                "evidence_not_bound",
                item.evidence_ids,
                "Zwiąż freshness tylko z evidence packetu.",
            )
    return None


def _blocker(
    seam: ResearchPacketBlockerSeam,
    reason: ResearchPacketBlockerReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentResearchPacketBlocker:
    return ContentResearchPacketBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids)))[:256],
        next_step_pl=next_step,
    )


__all__ = [
    "ContentResearchPacket",
    "ContentResearchPacketBlocker",
    "ContentResearchPacketCommand",
    "ContentResearchPacketContextReceipt",
    "ContentResearchPacketCurrentProjection",
    "ContentResearchPacketFreshness",
    "ContentResearchPacketInternalLink",
    "ContentResearchPacketReadResult",
    "ContentResearchPacketRecordResult",
    "RESEARCH_PACKET_SCHEMA_VERSION",
    "ResearchPacketBlockerReason",
    "ResearchPacketBlockerSeam",
    "ResearchPacketCurrentStatus",
    "ResearchPacketStatus",
    "reconcile_content_research_packet",
    "research_packet_digest",
    "research_packet_input_digest",
    "research_packet_logical_id",
    "source_ids_digest",
]
