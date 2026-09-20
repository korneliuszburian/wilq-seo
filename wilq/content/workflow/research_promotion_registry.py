"""Read-only projection of approved research-promotion receipts into facts."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from wilq.content.knowledge.source_facts import (
    OFFICIAL_GUIDANCE_TARGET_CARD_ID,
    OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
    OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
    ContentSourceFact,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.evidence_acquisition_contracts import (
    OfficialGuidanceObservationReceipt,
)
from wilq.content.workflow.official_guidance import (
    official_guidance_receipt_is_fresh,
    resolve_official_guidance_candidate,
)
from wilq.content.workflow.research_promotion_authority import (
    ContentOfficialGuidanceFactPromotionSnapshot,
)


def approved_research_promotion_facts(
    base_facts: tuple[ContentSourceFact, ...],
) -> tuple[ContentSourceFact, ...]:
    """Return only current, exact, non-conflicting dynamic source facts."""

    from wilq.content.knowledge.cards import (
        compile_source_facts_to_knowledge_cards,
        ekologus_seed_content_knowledge_cards,
    )
    from wilq.content.workflow.evidence_acquisition_snapshot import (
        current_page_receipt_is_fresh,
    )
    from wilq.content.workflow.store.store import content_workflow_store

    store = content_workflow_store()
    cards = (
        *ekologus_seed_content_knowledge_cards(),
        *compile_source_facts_to_knowledge_cards(base_facts),
    )
    now = datetime.now(UTC)
    candidates = [
        receipt.source_fact
        for receipt in store.list_research_fact_promotion_receipts()
        if _receipt_is_current(
            receipt,
            base_facts=base_facts,
            cards=cards,
            store=store,
            now=now,
            current_page_receipt_is_fresh=current_page_receipt_is_fresh,
        )
    ]
    return _merge_non_conflicting_facts(base_facts, candidates)


def _receipt_is_current(
    receipt: Any,
    *,
    base_facts: tuple[ContentSourceFact, ...],
    cards: tuple[Any, ...],
    store: Any,
    now: datetime,
    current_page_receipt_is_fresh: Callable[..., bool],
) -> bool:
    try:
        snapshot = receipt.snapshot
        source_fact = receipt.source_fact
        if isinstance(snapshot, ContentOfficialGuidanceFactPromotionSnapshot):
            return _official_guidance_receipt_is_current(
                receipt,
                source_fact=source_fact,
                snapshot=snapshot,
                base_facts=base_facts,
                store=store,
                now=now,
            )
        if receipt.recorded_at.tzinfo is None or receipt.recorded_at.utcoffset() is None:
            return False
        if not _source_fact_matches_snapshot(source_fact, snapshot, base_facts):
            return False
        if not _proposal_is_current(store, snapshot):
            return False
        observation = _current_observation(store, snapshot)
        if observation is None or not current_page_receipt_is_fresh(observation, now=now):
            return False
        if not _identity_and_classification_are_current(store, snapshot):
            return False
        return _card_policy_is_current(cards, snapshot)
    except Exception:
        return False


def _official_guidance_receipt_is_current(
    receipt: Any,
    *,
    source_fact: ContentSourceFact,
    snapshot: ContentOfficialGuidanceFactPromotionSnapshot,
    base_facts: tuple[ContentSourceFact, ...],
    store: Any,
    now: datetime,
) -> bool:
    if receipt.recorded_at.tzinfo is None or receipt.recorded_at.utcoffset() is None:
        return False
    if source_fact.source_id in {fact.source_id for fact in base_facts}:
        return False
    if not _official_source_fact_matches_snapshot(source_fact, snapshot):
        return False
    if not _proposal_is_current(store, snapshot):
        return False
    observation = _current_observation(store, snapshot)
    if not isinstance(observation, OfficialGuidanceObservationReceipt):
        return False
    if not official_guidance_receipt_is_fresh(observation, now=now):
        return False
    if not _identity_and_classification_are_current(store, snapshot):
        return False
    return _official_policy_is_current(snapshot, observation)


def _source_fact_matches_snapshot(
    source_fact: ContentSourceFact,
    snapshot: Any,
    base_facts: tuple[ContentSourceFact, ...],
) -> bool:
    base_ids = {fact.source_id for fact in base_facts}
    return (
        source_fact.review_status == "approved"
        and bool(source_fact.reviewer)
        and source_fact.source_id not in base_ids
        and source_fact.target_card_id == snapshot.target_card_id
        and source_fact.target_card_type == snapshot.target_card_type
        and source_fact.target_card_title == snapshot.target_card_title
        and source_fact.extracted_fact == snapshot.proposed_claim
        and source_fact.scope == snapshot.proposed_scope
        and source_fact.confidence == snapshot.proposed_confidence
        and source_fact.freshness_date == snapshot.freshness_date
        and tuple(sorted(source_fact.evidence_ids)) == tuple(snapshot.evidence_ids)
        and tuple(sorted(source_fact.source_connectors)) == tuple(snapshot.source_connectors)
        and source_fact.source_url_or_path == snapshot.source_url
    )


def _official_source_fact_matches_snapshot(
    source_fact: ContentSourceFact,
    snapshot: ContentOfficialGuidanceFactPromotionSnapshot,
) -> bool:
    if not source_fact.reviewer:
        return False
    try:
        from wilq.content.workflow.research_promotion_authority import (
            _official_guidance_source_fact,
        )

        expected = _official_guidance_source_fact(snapshot, source_fact.reviewer)
    except Exception:
        return False
    return source_fact == expected


def _proposal_is_current(store: Any, snapshot: Any) -> bool:
    proposal = store.get_research_proposal(snapshot.proposal_id)
    return proposal is not None and all(
        (
            proposal.status == "ready_for_review",
            proposal.approved is False,
            proposal.proposal_digest == snapshot.proposal_digest,
            proposal.acquisition_run_id == snapshot.acquisition_run_id,
            proposal.acquisition_run_digest == snapshot.acquisition_run_digest,
            proposal.observation_id == snapshot.observation_id,
            tuple(proposal.evidence_ids) == tuple(snapshot.evidence_ids),
        )
    )


def _current_observation(store: Any, snapshot: Any) -> Any | None:
    run = store.get_evidence_acquisition_run(snapshot.acquisition_run_id)
    if run is None or run.status != "ready_for_researcher":
        return None
    observation = run.observation
    if observation is None:
        return None
    if run.run_digest != snapshot.acquisition_run_digest:
        return None
    if observation.observation_id != snapshot.observation_id:
        return None
    if observation.source_url != snapshot.source_url:
        return None
    if tuple(observation.evidence_ids) != tuple(snapshot.evidence_ids):
        return None
    if tuple(observation.source_connectors) != tuple(snapshot.source_connectors):
        return None
    if isinstance(snapshot, ContentOfficialGuidanceFactPromotionSnapshot):
        if not isinstance(observation, OfficialGuidanceObservationReceipt):
            return None
        candidate = resolve_official_guidance_candidate(snapshot.candidate_id)
        if (
            candidate is None
            or observation.candidate_id != candidate.candidate_id
            or observation.candidate_digest != candidate.candidate_digest
            or observation.canonical_path != snapshot.candidate_canonical_path
            or observation.source_url != candidate.source_url
        ):
            return None
    return observation


def _identity_and_classification_are_current(store: Any, snapshot: Any) -> bool:
    identity = store.load_content_delivery_identity(snapshot.identity_binding_id)
    if identity is None or identity.status != "exact_current":
        return False
    if identity.binding_digest != snapshot.identity_binding_digest:
        return False
    if identity.classification_run_digest != snapshot.classification_run_digest:
        return False
    classification = store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    if isinstance(snapshot, ContentOfficialGuidanceFactPromotionSnapshot):
        candidate = resolve_official_guidance_candidate(snapshot.candidate_id)
        if candidate is None or identity.canonical_path != candidate.canonical_path:
            return False
        if (
            identity.classification_run_id != snapshot.classification_run_id
            or identity.classification_decision_set_digest
            != snapshot.classification_decision_set_digest
            or identity.classification_source_row_digest
            != snapshot.classification_source_row_digest
        ):
            return False
    return (
        classification is not None
        and classification.run_digest == snapshot.classification_run_digest
        and (
            not isinstance(snapshot, ContentOfficialGuidanceFactPromotionSnapshot)
            or (
                classification.run_id == snapshot.classification_run_id
                and classification.decision_set_digest
                == snapshot.classification_decision_set_digest
                and classification.row.source_packet_row_digest
                == snapshot.classification_source_row_digest
                and classification.row.canonical_path == snapshot.candidate_canonical_path
            )
        )
    )


def _official_policy_is_current(
    snapshot: ContentOfficialGuidanceFactPromotionSnapshot,
    observation: OfficialGuidanceObservationReceipt,
) -> bool:
    candidate = resolve_official_guidance_candidate(snapshot.candidate_id)
    if candidate is None:
        return False
    if (
        snapshot.promotion_kind != "official_guidance"
        or snapshot.policy_version != "official_guidance_policy_v1"
        or snapshot.candidate_digest != candidate.candidate_digest
        or snapshot.candidate_canonical_path != candidate.canonical_path
        or snapshot.candidate_title != candidate.title
        or snapshot.candidate_allowed_claims != candidate.allowed_claim_scope
        or snapshot.candidate_blocked_claims != candidate.blocked_claims
        or snapshot.target_card_id != OFFICIAL_GUIDANCE_TARGET_CARD_ID
        or snapshot.target_card_type != OFFICIAL_GUIDANCE_TARGET_CARD_TYPE
        or snapshot.target_card_title != OFFICIAL_GUIDANCE_TARGET_CARD_TITLE
        or snapshot.proposed_scope != "claim_policy"
        or snapshot.proposed_claim not in candidate.allowed_claim_scope
        or snapshot.blocked_claims != candidate.blocked_claims
        or snapshot.allowed_claims != candidate.allowed_claim_scope
        or snapshot.card_freshness != "official_guidance_policy_v1"
        or tuple(snapshot.card_evidence_ids) != tuple(observation.evidence_ids)
        or tuple(snapshot.card_source_connectors) != tuple(observation.source_connectors)
        or snapshot.evidence_requirements
        != ("exact_official_guidance_observation", "human_review")
        or tuple(snapshot.evidence_ids) != tuple(observation.evidence_ids)
        or tuple(snapshot.source_connectors) != tuple(observation.source_connectors)
        or snapshot.source_url != observation.source_url
        or snapshot.observation_id != observation.observation_id
    ):
        return False
    expected_policy_payload = {
        "promotion_kind": "official_guidance",
        "policy_version": "official_guidance_policy_v1",
        "candidate_id": candidate.candidate_id,
        "candidate_digest": candidate.candidate_digest,
        "candidate_canonical_path": candidate.canonical_path,
        "candidate_title": candidate.title,
        "candidate_allowed_claims": candidate.allowed_claim_scope,
        "candidate_blocked_claims": candidate.blocked_claims,
        "target_card_id": OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        "target_card_type": OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
        "target_card_title": OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
        "allowed_claims": candidate.allowed_claim_scope,
        "blocked_claims": candidate.blocked_claims,
        "evidence_requirements": snapshot.evidence_requirements,
    }
    return snapshot.policy_source_digest == canonical_json_digest(expected_policy_payload)


def _card_policy_is_current(cards: tuple[Any, ...], snapshot: Any) -> bool:
    card = next((item for item in cards if item.id == snapshot.target_card_id), None)
    if card is None or card.lifecycle_status != "approved_current":
        return False
    return (
        card.card_type == snapshot.target_card_type
        and card.title == snapshot.target_card_title
        and tuple(sorted(card.evidence_ids)) == tuple(snapshot.card_evidence_ids)
        and tuple(sorted(card.source_connectors)) == tuple(snapshot.card_source_connectors)
        and card.freshness == snapshot.card_freshness
        and _research_policy_digest(card) == snapshot.policy_source_digest
    )


def _research_policy_digest(card: Any) -> str:
    payload = card.model_dump(mode="json")
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _merge_non_conflicting_facts(
    base_facts: tuple[ContentSourceFact, ...],
    candidates: list[ContentSourceFact],
) -> tuple[ContentSourceFact, ...]:
    base_ids = {fact.source_id for fact in base_facts}
    grouped: dict[str, list[ContentSourceFact]] = {}
    for fact in candidates:
        if fact.source_id not in base_ids:
            grouped.setdefault(fact.source_id, []).append(fact)
    return tuple(
        fact
        for source_id in sorted(grouped)
        if len(grouped[source_id]) == 1
        for fact in grouped[source_id]
    )


__all__ = ["approved_research_promotion_facts"]
