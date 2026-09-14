"""Private fail-closed guards for source-pack reconciliation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow._source_pack_binding_constants import (
    _MAX_RECEIPT_AGE,
    _MAX_RECORDED_AT_AGE,
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    SOURCE_FACT_REGISTRY_ID,
    ContentSourcePackBindingReason,
    ContentSourcePackBindingSeam,
)
from wilq.content.workflow._source_pack_binding_hashing import (
    content_source_pack_context_digest,
    source_fact_registry_digest,
)
from wilq.content.workflow._source_pack_binding_models import (
    ContentSourcePackBindingBlocker,
    ContentSourcePackBindingCommand,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding


def _binding_request_blocker(
    command: ContentSourcePackBindingCommand,
    *,
    evidence: tuple[str, ...],
    prior_pack_hashes: tuple[str, ...],
    now: datetime,
) -> ContentSourcePackBindingBlocker | None:
    if command.recorded_at > now + timedelta(minutes=5):
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            evidence,
            "Użyj server-owned recorded_at z bieżącego okna czasu.",
        )
    if now - command.recorded_at > _MAX_RECORDED_AT_AGE:
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            evidence,
            "Użyj recorded_at z ostatnich 24 godzin albo pobierz nowe prerequisites.",
        )
    if not command.source_pack_id.strip() or not command.source_pack_sha256:
        return _blocker(
            "source_pack_identity",
            "source_pack_identity_missing",
            evidence,
            "Podaj jednocześnie exact source-pack ID i jego SHA-256.",
        )
    if prior_pack_hashes and command.source_pack_sha256 not in set(prior_pack_hashes):
        return _blocker(
            "source_pack_identity",
            "source_pack_hash_mismatch",
            evidence,
            "Zweryfikuj hash tej samej wersji source packa; nie zastępuj istniejącego receiptu.",
        )
    return None


def _binding_identity_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
    evidence: tuple[str, ...],
) -> ContentSourcePackBindingBlocker | None:
    if identity is None:
        return _blocker(
            "delivery_identity",
            "delivery_identity_missing",
            evidence,
            "Najpierw zapisz exact S1 identity binding dla tego source packa.",
        )
    if (
        identity.binding_id != command.identity_binding_id
        or identity.binding_digest != command.identity_binding_digest
    ):
        return _blocker(
            "delivery_identity",
            "delivery_identity_digest_mismatch",
            evidence,
            "Użyj ID i digestu z tego samego persisted S1 identity bindingu.",
        )
    if identity.status == "blocked":
        return _blocker(
            "delivery_identity",
            "delivery_identity_blocked",
            (*evidence, *identity.inventory_evidence_ids),
            "Usuń typed blocker S1 i dopiero potem wiąż source pack.",
        )
    if identity.current_work_item_id != command.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            (*evidence, *identity.inventory_evidence_ids),
            "Wskaż current work item zapisany w exact S1 identity bindingu.",
        )
    return None


def _binding_evidence_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding,
    authority_receipt: Any | None,
    evidence: tuple[str, ...],
) -> ContentSourcePackBindingBlocker | None:
    input_evidence = command.evidence_ids
    if not set(identity.inventory_evidence_ids).issubset(set(input_evidence)):
        return _blocker(
            "evidence_whitelist",
            "evidence_not_bound",
            (*evidence, *identity.inventory_evidence_ids),
            "Dodaj do whitelisty evidence dokładnie zakotwiczone w S1 inventory bindingu.",
        )
    allowed_evidence = (
        set(identity.inventory_evidence_ids)
        | set(command.source_fact_registry_receipt.evidence_ids)
        | set(command.fresh_context_attestation.evidence_ids)
    )
    authority_evidence = _authority_evidence_ids(authority_receipt)
    allowed_evidence.update(authority_evidence)
    if set(input_evidence) - allowed_evidence:
        return _blocker(
            "evidence_whitelist",
            "evidence_not_bound",
            evidence,
            "Usuń evidence spoza exact S1, registry i context attestation whitelisty.",
        )
    if authority_evidence and not authority_evidence.issubset(set(input_evidence)):
        return _blocker(
            "evidence_whitelist",
            "evidence_not_bound",
            tuple(sorted(authority_evidence | set(evidence))),
            "Dodaj evidence wszystkich wybranych faktów z exact row-authority receipt.",
        )
    return None


def _binding_history_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding,
    authority_receipt: Any | None,
    evidence: tuple[str, ...],
    prior_source_fact_sets: tuple[tuple[str, ...], ...],
    prior_evidence_sets: tuple[tuple[str, ...], ...],
) -> ContentSourcePackBindingBlocker | None:
    context_blocker = _context_blocker(command, identity, evidence, authority_receipt)
    if context_blocker is not None:
        return context_blocker
    registry_receipt = command.source_fact_registry_receipt
    if prior_source_fact_sets and tuple(command.source_fact_ids) not in set(prior_source_fact_sets):
        return _blocker(
            "source_fact_whitelist",
            "source_facts_mismatch",
            _known_evidence_ids(
                (*evidence, *registry_receipt.evidence_ids), identity, authority_receipt
            ),
            "Nie zmieniaj source-fact whitelisty istniejącego receipt; utwórz nowy exact pack.",
        )
    if prior_evidence_sets and tuple(command.evidence_ids) not in set(prior_evidence_sets):
        return _blocker(
            "evidence_whitelist",
            "evidence_set_mismatch",
            evidence,
            "Zachowaj exact evidence whitelistę z zatwierdzonego source-pack contextu.",
        )
    return None


def _binding_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
    *,
    authority_receipt: Any | None,
    classification: Any | None,
    prior_pack_hashes: tuple[str, ...],
    prior_source_fact_sets: tuple[tuple[str, ...], ...],
    prior_evidence_sets: tuple[tuple[str, ...], ...],
    now: datetime,
) -> ContentSourcePackBindingBlocker | None:
    input_evidence = command.evidence_ids
    evidence = _known_evidence_ids(input_evidence, identity, authority_receipt)
    request_blocker = _binding_request_blocker(
        command, evidence=evidence, prior_pack_hashes=prior_pack_hashes, now=now
    )
    if request_blocker is not None:
        return request_blocker
    identity_blocker = _binding_identity_blocker(command, identity, evidence)
    if identity_blocker is not None:
        return identity_blocker
    assert identity is not None
    classification_blocker = _classification_blocker(identity, classification)
    if classification_blocker is not None:
        return classification_blocker
    evidence_blocker = _binding_evidence_blocker(
        command, identity, authority_receipt, evidence
    )
    if evidence_blocker is not None:
        return evidence_blocker
    history_blocker = _binding_history_blocker(
        command,
        identity,
        authority_receipt,
        evidence,
        prior_source_fact_sets,
        prior_evidence_sets,
    )
    if history_blocker is not None:
        return history_blocker
    registry_blocker = _source_fact_blocker(command)
    if registry_blocker is not None:
        return registry_blocker
    authority_blocker = _source_fact_authority_blocker(
        command,
        identity,
        authority_receipt,
        classification=classification,
        now=now,
    )
    if authority_blocker is not None:
        return authority_blocker
    # The authority receipt is the only source of a row-scoped fact set.  A
    # global approved registry cannot establish row scope on its own.
    return None


def _classification_blocker(
    identity: ContentDeliveryIdentityBinding,
    classification: Any | None,
) -> ContentSourcePackBindingBlocker | None:
    if classification is None:
        return _blocker(
            "classification",
            "classification_current_missing",
            identity.inventory_evidence_ids,
            "Odczytaj bieżącą klasyfikację exact wiersza przed source-pack zapisem.",
        )
    freshness = getattr(classification, "freshness", None)
    if freshness is None or getattr(freshness, "requires_refresh", True) or getattr(
        freshness, "state", None
    ) != "fresh":
        row = getattr(classification, "row", None)
        evidence_ids = identity.inventory_evidence_ids if row is None else row.primary_evidence_ids
        return _blocker(
            "classification",
            "classification_stale",
            tuple(evidence_ids),
            "Odśwież bieżącą klasyfikację przed związaniem source packa.",
        )
    if (
        getattr(classification, "run_id", None) != identity.classification_run_id
        or getattr(classification, "run_digest", None) != identity.classification_run_digest
        or getattr(classification, "decision_set_digest", None)
        != identity.classification_decision_set_digest
    ):
        row = getattr(classification, "row", None)
        evidence_ids = identity.inventory_evidence_ids if row is None else row.primary_evidence_ids
        return _blocker(
            "classification",
            "classification_identity_drift",
            tuple(evidence_ids),
            "Użyj klasyfikacji z tego samego exact runu co identity binding.",
        )
    row = getattr(classification, "row", None)
    if row is None or (
        row.current_work_item_id != identity.current_work_item_id
        or row.canonical_path != identity.canonical_path
        or row.public_url != identity.public_url
        or row.source_packet_row_digest != identity.classification_source_row_digest
    ):
        evidence_ids = identity.inventory_evidence_ids if row is None else row.primary_evidence_ids
        return _blocker(
            "classification",
            "classification_identity_drift",
            tuple(evidence_ids),
            "Ponownie zwiąż source pack z bieżącym wierszem klasyfikacji.",
        )
    return None


def _authority_snapshot(authority_receipt: Any | None) -> Any | None:
    if authority_receipt is None:
        return None
    snapshot = getattr(authority_receipt, "authority_snapshot", None)
    return snapshot


def _authority_evidence_ids(authority_receipt: Any | None) -> set[str]:
    snapshot = _authority_snapshot(authority_receipt)
    evidence_ids = getattr(snapshot, "evidence_ids", ())
    return {value for value in evidence_ids if isinstance(value, str)}


def _authority_binding_payload(authority_receipt: Any | None) -> dict[str, object]:
    """Persist only receipt identity/digests, never source fact text."""

    snapshot = _authority_snapshot(authority_receipt)
    return {
        "source_fact_authority_receipt_id": (
            getattr(authority_receipt, "receipt_id", None)
            if snapshot is not None
            else None
        ),
        "source_fact_authority_receipt_digest": (
            getattr(authority_receipt, "receipt_digest", None)
            if snapshot is not None
            else None
        ),
        "source_fact_authority_snapshot_digest": (
            getattr(snapshot, "context_digest", None) if snapshot is not None else None
        ),
        "source_fact_authority_provenance_digest": (
            getattr(snapshot, "source_fact_provenance_digest", None)
            if snapshot is not None
            else None
        ),
    }


def _parse_authority_receipt(authority_receipt: Any) -> Any | None:
    try:
        from wilq.content.workflow.source_fact_authority import (
            ContentSourceFactAuthorityReceipt,
        )
        return ContentSourceFactAuthorityReceipt.model_validate_json(
            authority_receipt.model_dump_json()
            if isinstance(authority_receipt, BaseModel)
            else json.dumps(
                authority_receipt,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            strict=True,
        )
    except Exception:
        return None


def _authority_context_blocker(
    accepted: Any,
    identity: ContentDeliveryIdentityBinding,
    authority_evidence: set[str],
    now: datetime,
) -> ContentSourcePackBindingBlocker | None:
    snapshot = accepted.authority_snapshot
    if accepted.recorded_at > now or now - accepted.recorded_at > _MAX_RECEIPT_AGE:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_stale",
            tuple(sorted(authority_evidence)),
            "Odśwież row-authority receipt przed związaniem source packa.",
        )
    if (
        snapshot.identity_binding_id != identity.binding_id
        or snapshot.identity_binding_digest != identity.binding_digest
        or snapshot.current_work_item_id != identity.current_work_item_id
        or snapshot.canonical_path != identity.canonical_path
        or snapshot.public_url != identity.public_url
        or snapshot.classification_run_id != identity.classification_run_id
        or snapshot.classification_run_digest != identity.classification_run_digest
        or snapshot.classification_decision_set_digest
        != identity.classification_decision_set_digest
        or snapshot.classification_source_row_digest != identity.classification_source_row_digest
    ):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_drift",
            tuple(sorted(authority_evidence | set(identity.inventory_evidence_ids))),
            "Odśwież authority dla aktualnego identity/classification wiersza.",
        )
    return None


def _authority_command_blocker(
    command: ContentSourcePackBindingCommand,
    accepted: Any,
    authority_evidence: set[str],
) -> ContentSourcePackBindingBlocker | None:
    snapshot = accepted.authority_snapshot
    if snapshot.source_fact_ids != command.source_fact_ids:
        return _blocker(
            "source_fact_whitelist",
            "source_facts_mismatch",
            tuple(sorted(authority_evidence)),
            "Użyj dokładnie source-fact IDs z bieżącego row-authority receipt.",
        )
    if command.source_fact_authority_receipt_id is not None and (
        command.source_fact_authority_receipt_id != accepted.receipt_id
    ):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_mismatch",
            tuple(sorted(authority_evidence)),
            "Użyj receipt ID odczytanego dla tego exact work itemu.",
        )
    if command.source_fact_authority_receipt_digest is not None and (
        command.source_fact_authority_receipt_digest != accepted.receipt_digest
    ):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_mismatch",
            tuple(sorted(authority_evidence)),
            "Użyj receipt digest odczytanego dla tego exact work itemu.",
        )
    if command.source_fact_authority_snapshot_digest is not None and (
        command.source_fact_authority_snapshot_digest != snapshot.context_digest
    ):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_drift",
            tuple(sorted(authority_evidence)),
            "Odśwież source-pack prerequisites dla bieżącego authority snapshotu.",
        )
    return None


def _authority_registry_blocker(
    accepted: Any,
    identity: ContentDeliveryIdentityBinding,
    authority_evidence: set[str],
    *,
    classification: Any | None,
) -> ContentSourcePackBindingBlocker | None:
    from wilq.content.workflow.source_fact_authority import (
        authority_source_fact_provenance,
        build_source_fact_authority_snapshot,
    )

    snapshot = accepted.authority_snapshot
    facts = ekologus_source_facts()
    if snapshot.source_fact_registry_id != SOURCE_FACT_REGISTRY_ID or (
        snapshot.source_fact_registry_digest != source_fact_registry_digest(facts)
    ):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_stale",
            tuple(sorted(authority_evidence)),
            "Odśwież row-authority receipt względem bieżącego source-fact registry.",
        )
    facts_by_id = {fact.source_id: fact for fact in facts}
    expected_provenance = tuple(
        authority_source_fact_provenance(facts_by_id[item])
        for item in snapshot.source_fact_ids
        if item in facts_by_id
    )
    if len(expected_provenance) != len(snapshot.source_fact_ids) or (
        snapshot.source_fact_provenance != expected_provenance
    ):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_drift",
            tuple(sorted(authority_evidence)),
            "Odśwież authority, bo provenance wybranych faktów zmieniło się.",
        )
    if classification is not None:
        expected_snapshot, blockers = build_source_fact_authority_snapshot(
            identity,
            classification,
            snapshot.source_fact_ids,
            facts=facts,
            identity_binding_id=identity.binding_id,
        )
        if blockers or expected_snapshot is None or expected_snapshot != snapshot:
            return _blocker(
                "source_fact_whitelist",
                "source_fact_authority_drift",
                tuple(sorted(authority_evidence | set(identity.inventory_evidence_ids))),
                "Odśwież authority dla bieżącej klasyfikacji i karty usługi.",
            )
    return None


def _source_fact_authority_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding,
    authority_receipt: Any | None,
    *,
    classification: Any | None,
    now: datetime,
) -> ContentSourcePackBindingBlocker | None:
    """Require one exact, still-current row-authority receipt for this pack."""

    authority_evidence = _authority_evidence_ids(authority_receipt)
    if authority_receipt is None:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_row_binding_missing",
            _known_evidence_ids(
                tuple(
                    set(command.source_fact_registry_receipt.evidence_ids)
                    | set(identity.inventory_evidence_ids)
                ),
                identity,
            ),
            "Zapisz exact per-work-item source-fact receipt związany z bieżącym wierszem S1.",
        )
    accepted = _parse_authority_receipt(authority_receipt)
    if accepted is None:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_authority_invalid",
            tuple(sorted(authority_evidence)),
            "Odtwórz i zastosuj nowy exact row-authority receipt.",
        )
    context_blocker = _authority_context_blocker(accepted, identity, authority_evidence, now)
    if context_blocker is not None:
        return context_blocker
    command_blocker = _authority_command_blocker(command, accepted, authority_evidence)
    if command_blocker is not None:
        return command_blocker
    return _authority_registry_blocker(
        accepted,
        identity,
        authority_evidence,
        classification=classification,
    )


def _effective_evidence_ids(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
    authority_receipt: Any | None = None,
) -> tuple[str, ...]:
    """Persist only evidence from known S1/registry owners, including blocked attempts."""

    allowed = {
        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    }
    if identity is not None:
        allowed.update(identity.inventory_evidence_ids)
    allowed.update(_authority_evidence_ids(authority_receipt))
    selected = tuple(sorted(set(command.evidence_ids) & allowed))
    return selected


def _known_evidence_ids(
    evidence_ids: tuple[str, ...],
    identity: ContentDeliveryIdentityBinding | None,
    authority_receipt: Any | None = None,
) -> tuple[str, ...]:
    allowed = {
        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    }
    if identity is not None:
        allowed.update(identity.inventory_evidence_ids)
    allowed.update(_authority_evidence_ids(authority_receipt))
    return tuple(sorted(set(evidence_ids) & allowed))


def _source_fact_blocker(
    command: ContentSourcePackBindingCommand,
) -> ContentSourcePackBindingBlocker | None:
    receipt = command.source_fact_registry_receipt
    if receipt.checked_at > command.recorded_at:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_stale",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Registry receipt nie może pochodzić z przyszłości względem zapisu.",
        )
    if command.recorded_at - receipt.checked_at > _MAX_RECEIPT_AGE:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_stale",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Odśwież source-fact registry receipt w dozwolonym oknie 30 dni.",
        )
    if receipt.registry_id != SOURCE_FACT_REGISTRY_ID:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_mismatch",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Użyj receiptu aktualnego WILQ source-fact registry.",
        )
    facts = ekologus_source_facts()
    if receipt.registry_digest != source_fact_registry_digest(facts):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_mismatch",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Odśwież exact source-fact registry receipt przed związaniem source packa.",
        )
    expected_evidence_ids = tuple(
        sorted(
            {
                APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
            }
        )
    )
    if receipt.evidence_ids != expected_evidence_ids:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_mismatch",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Dołącz exact evidence registry i zatwierdzonego manifestu źródeł.",
        )
    facts_by_id = {fact.source_id: fact for fact in facts}
    if set(command.source_fact_ids) - set(facts_by_id):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_not_registered",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Usuń fakty spoza exact source-fact registry; nie twórz ich z listy caller-a.",
        )
    if any(facts_by_id[item].review_status != "approved" for item in command.source_fact_ids):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_not_approved",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Użyj wyłącznie source facts ze statusem approved w aktualnym registry.",
        )
    return None


def _context_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding,
    evidence: tuple[str, ...],
    authority_receipt: Any | None = None,
) -> ContentSourcePackBindingBlocker | None:
    attestation = command.fresh_context_attestation
    if attestation.checked_at > command.recorded_at:
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            _known_evidence_ids(
                (*evidence, *attestation.evidence_ids), identity, authority_receipt
            ),
            "Context attestation nie może pochodzić z przyszłości względem zapisu.",
        )
    if command.recorded_at - attestation.checked_at > _MAX_RECEIPT_AGE:
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            _known_evidence_ids((*evidence, *attestation.evidence_ids), identity),
            "Odśwież context attestation w dozwolonym oknie 30 dni.",
        )
    if (
        attestation.source == "content_delivery_identity_binding"
        and attestation.run_id == identity.classification_run_id
        and attestation.evidence_ids == identity.inventory_evidence_ids
        and command.fresh_context_digest
        == content_source_pack_context_digest(identity, attestation)
    ):
        return None
    return _blocker(
        "fresh_context",
        "fresh_context_mismatch",
        _known_evidence_ids(
            (*evidence, *attestation.evidence_ids), identity, authority_receipt
        ),
        ("Zapisz świeży context attestation z exact S1 identity, digestem, checked_at i evidence."),
    )


def _blocker(
    seam: ContentSourcePackBindingSeam,
    reason: ContentSourcePackBindingReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentSourcePackBindingBlocker:
    return ContentSourcePackBindingBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids)))[:256],
        next_step=next_step,
    )
