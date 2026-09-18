"""Read-only projection of approved research-promotion receipts into facts."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from wilq.content.knowledge.source_facts import ContentSourceFact


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
    return (
        classification is not None
        and classification.run_digest == snapshot.classification_run_digest
    )


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
