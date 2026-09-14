"""Pure builders for the exact source-fact authority snapshot."""

from __future__ import annotations

from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow._source_fact_authority_contracts import (
    ContentSourceFactAuthorityBlocker,
    ContentSourceFactAuthorityCandidateProjection,
    ContentSourceFactAuthoritySnapshot,
    authority_evidence_ids_digest,
    authority_source_fact_ids_digest,
    authority_source_fact_provenance,
    authority_source_fact_provenance_digest,
    source_fact_authority_snapshot_digest,
)
from wilq.content.workflow._source_pack_binding_constants import (
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    SOURCE_FACT_REGISTRY_ID,
)
from wilq.content.workflow._source_pack_binding_hashing import source_fact_registry_digest
from wilq.content.workflow.decisions.production import ContentProductionClassificationProjection
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.source_fact_candidate_projection import (
    build_content_source_fact_authority_candidate_projection,
)


def _blocker(
    seam: str,
    reason: str,
    evidence_ids: tuple[str, ...] = (),
    next_step: str = "Odśwież exact dane i przygotuj nowy preview.",
) -> ContentSourceFactAuthorityBlocker:
    return ContentSourceFactAuthorityBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step=next_step,
    )


def _identity_blocker(
    identity: ContentDeliveryIdentityBinding | None,
    expected_binding_id: str | None,
) -> ContentSourceFactAuthorityBlocker | None:
    if identity is None:
        return _blocker(
            "s1_identity",
            "identity_binding_missing",
            next_step="Najpierw zapisz exact S1 identity binding.",
        )
    if expected_binding_id is not None and identity.binding_id != expected_binding_id:
        return _blocker(
            "s1_identity",
            "identity_binding_id_mismatch",
            identity.inventory_evidence_ids,
            "Użyj dokładnie tego identity bindingu, którego dotyczy żądanie.",
        )
    if identity.status != "exact_current":
        return _blocker(
            "s1_identity",
            "identity_binding_not_exact_current",
            identity.inventory_evidence_ids,
            "Usuń typed blocker S1 i odśwież preview authority.",
        )
    return None


def _classification_blocker(
    identity: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection | None,
) -> ContentSourceFactAuthorityBlocker | None:
    if classification is None:
        return _blocker(
            "classification",
            "classification_current_missing",
            identity.inventory_evidence_ids,
            "Wskaż bieżącą klasyfikację dla exact work itemu.",
        )
    row = classification.row
    if classification.freshness.requires_refresh or classification.freshness.state != "fresh":
        return _blocker(
            "classification",
            "classification_stale",
            row.primary_evidence_ids,
            "Odśwież i zaakceptuj bieżącą klasyfikację przed preview.",
        )
    if (
        classification.run_id != identity.classification_run_id
        or classification.run_digest != identity.classification_run_digest
        or classification.decision_set_digest != identity.classification_decision_set_digest
    ):
        return _blocker(
            "classification",
            "classification_identity_drift",
            row.primary_evidence_ids,
            "Użyj identity i classification z tego samego exact runu.",
        )
    if (
        row.current_work_item_id != identity.current_work_item_id
        or row.canonical_path != identity.canonical_path
        or row.public_url != identity.public_url
        or row.source_packet_row_digest != identity.classification_source_row_digest
    ):
        return _blocker(
            "classification",
            "classification_source_row_digest_mismatch",
            row.primary_evidence_ids,
            "Ponownie zwiąż work item, path, URL i source-row digest.",
        )
    return None


def _candidate_blocker(
    projection: ContentSourceFactAuthorityCandidateProjection,
    identity: ContentDeliveryIdentityBinding,
) -> tuple[ContentSourceFactAuthorityBlocker, ...] | None:
    if projection.status == "eligible":
        return None
    return projection.blockers or (
        _blocker(
            "source_fact_review",
            "source_fact_candidates_unavailable",
            identity.inventory_evidence_ids,
            "Pozyskaj i zatwierdź exact source fact przed preview authority.",
        ),
    )


def _selection_blocker(
    selected_ids: tuple[str, ...],
    projection: ContentSourceFactAuthorityCandidateProjection,
    facts: tuple[ContentSourceFact, ...],
    identity: ContentDeliveryIdentityBinding,
) -> ContentSourceFactAuthorityBlocker | None:
    eligible_ids = {item.source_fact_id for item in projection.eligible_candidates}
    if foreign := tuple(item for item in selected_ids if item not in eligible_ids):
        evidence_ids = tuple(
            sorted(
                {
                    evidence_id
                    for item in projection.review_required_candidates
                    if item.source_fact_id in foreign
                    for evidence_id in item.evidence_ids
                }
            )
        )
        return _blocker(
            "source_fact_review",
            "source_fact_candidate_not_eligible",
            evidence_ids or identity.inventory_evidence_ids,
            "Użyj wyłącznie eligible candidates z bieżącej exact projekcji.",
        )
    facts_by_id = {fact.source_id: fact for fact in facts}
    missing = tuple(item for item in selected_ids if item not in facts_by_id)
    if missing:
        return _blocker(
            "source_fact_registry",
            "source_fact_not_registered",
            _registry_evidence_ids(),
            "Wybierz wyłącznie fact ID z bieżącego source-fact registry.",
        )
    unapproved = tuple(
        item for item in selected_ids if facts_by_id[item].review_status != "approved"
    )
    if unapproved:
        return _blocker(
            "source_fact_review",
            "source_fact_not_approved",
            tuple(sorted({e for item in unapproved for e in facts_by_id[item].evidence_ids})),
            "Użyj wyłącznie source facts z zatwierdzeniem człowieka.",
        )
    return None


def _registry_evidence_ids() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
            }
        )
    )


def _assemble_snapshot(
    identity: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection,
    projection: ContentSourceFactAuthorityCandidateProjection,
    selected_ids: tuple[str, ...],
    facts: tuple[ContentSourceFact, ...],
) -> ContentSourceFactAuthoritySnapshot:
    facts_by_id = {fact.source_id: fact for fact in facts}
    selected_facts = tuple(facts_by_id[item] for item in selected_ids)
    provenance = tuple(authority_source_fact_provenance(fact) for fact in selected_facts)
    registry_evidence_ids = _registry_evidence_ids()
    evidence_ids = tuple(
        sorted(
            {
                *identity.inventory_evidence_ids,
                *registry_evidence_ids,
                *(evidence_id for fact in selected_facts for evidence_id in fact.evidence_ids),
            }
        )
    )
    row = classification.row
    provisional = ContentSourceFactAuthoritySnapshot.model_construct(
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        current_work_item_id=identity.current_work_item_id,
        canonical_path=identity.canonical_path,
        public_url=identity.public_url,
        classification_run_id=classification.run_id,
        classification_run_digest=classification.run_digest,
        classification_decision_set_digest=classification.decision_set_digest,
        classification_source_row_digest=row.source_packet_row_digest,
        source_fact_registry_id=SOURCE_FACT_REGISTRY_ID,
        source_fact_registry_digest=source_fact_registry_digest(facts),
        source_fact_registry_evidence_ids=registry_evidence_ids,
        source_fact_ids=selected_ids,
        source_facts_digest=authority_source_fact_ids_digest(selected_ids),
        source_fact_provenance=provenance,
        source_fact_provenance_digest=authority_source_fact_provenance_digest(provenance),
        evidence_ids=evidence_ids,
        evidence_ids_digest=authority_evidence_ids_digest(evidence_ids),
        context_digest="0" * 64,
        service_binding=projection.service_binding,
    )
    return ContentSourceFactAuthoritySnapshot.model_validate(
        provisional.model_copy(
            update={"context_digest": source_fact_authority_snapshot_digest(provisional)}
        )
    )


def build_source_fact_authority_snapshot(
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    source_fact_ids: tuple[str, ...],
    *,
    facts: tuple[ContentSourceFact, ...] | None = None,
    identity_binding_id: str | None = None,
) -> tuple[
    ContentSourceFactAuthoritySnapshot | None,
    tuple[ContentSourceFactAuthorityBlocker, ...],
]:
    """Build current exact state without inferring any URL, slug or card."""

    current_facts = ekologus_source_facts() if facts is None else facts
    identity_blocker = _identity_blocker(identity, identity_binding_id)
    if identity_blocker is not None:
        return None, (identity_blocker,)
    assert identity is not None
    classification_blocker = _classification_blocker(identity, classification)
    if classification_blocker is not None:
        return None, (classification_blocker,)
    assert classification is not None
    projection = build_content_source_fact_authority_candidate_projection(
        identity.binding_id,
        identity=identity,
        classification=classification,
        facts=current_facts,
    )
    candidate_blocker = _candidate_blocker(projection, identity)
    if candidate_blocker is not None:
        return None, candidate_blocker
    selection_blocker = _selection_blocker(
        tuple(source_fact_ids), projection, current_facts, identity
    )
    if selection_blocker is not None:
        return None, (selection_blocker,)
    return _assemble_snapshot(
        identity, classification, projection, tuple(source_fact_ids), current_facts
    ), ()


__all__ = ["build_source_fact_authority_snapshot"]
