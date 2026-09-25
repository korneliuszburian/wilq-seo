"""Public read-only source pack from current identity and approved official facts."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v3 import resolve_current_page_identity_v3
from wilq.content.workflow.per_url_delivery_identity_authority import (
    PerUrlDeliveryIdentityProjection,
    read_per_url_delivery_identity_authority,
)
from wilq.content.workflow.source_fact_candidate_v3 import (
    build_content_source_fact_candidates_v3_projection,
)
from wilq.content.workflow.source_pack_v3 import (
    SourcePackV3Preview,
    build_source_pack_v3_preview,
    resolve_source_pack_v3_per_url_identity,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store

EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]
FactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
CardsLoader = Callable[[], tuple[ContentKnowledgeCard, ...]]
StoreFactory = Callable[[], ContentWorkflowStore]


def register_content_source_pack_v3_route(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
    facts_loader: FactsLoader | None = None,
    cards_loader: CardsLoader | None = None,
) -> None:
    make_store = store_factory or (lambda: content_workflow_store())
    load_evidence = evidence_loader or (
        lambda work_item_id: content_current_page_evidence.read_current_page_evidence(
            work_item_id=work_item_id
        )
    )
    load_facts = facts_loader or (lambda: tuple(ekologus_source_facts()))
    load_cards = cards_loader or (lambda: tuple(ekologus_content_knowledge_cards()))

    @router.get(
        "/api/content/work-items/{work_item_id}/source-pack-preview-v3",
        response_model=SourcePackV3Preview,
    )
    def read_source_pack_v3_preview(
        work_item_id: str,
        per_url_delivery_identity_action_id: str | None = None,
    ) -> SourcePackV3Preview:
        return read_current_source_pack_v3_preview(
            work_item_id,
            per_url_delivery_identity_action_id=per_url_delivery_identity_action_id,
            store_factory=make_store,
            evidence_loader=load_evidence,
            facts_loader=load_facts,
            cards_loader=load_cards,
        )


def read_current_source_pack_v3_preview(
    work_item_id: str,
    *,
    per_url_delivery_identity_action_id: str | None = None,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
    facts_loader: FactsLoader | None = None,
    cards_loader: CardsLoader | None = None,
) -> SourcePackV3Preview:
    """Resolve one exact pack through the same public read path used by its route."""

    load_evidence = evidence_loader or (
        lambda item_id: content_current_page_evidence.read_current_page_evidence(
            work_item_id=item_id
        )
    )
    store = (store_factory or content_workflow_store)()
    identity = resolve_current_page_identity_v3(work_item_id, load_evidence(work_item_id))
    authority: PerUrlDeliveryIdentityProjection | None = (
        None
        if per_url_delivery_identity_action_id is None
        else read_per_url_delivery_identity_authority(
            store,
            action_id=per_url_delivery_identity_action_id,
        )
    )
    binding = None if authority is None else authority.binding
    observation = (
        None
        if binding is None
        else store.load_content_per_url_decision_observation(
            binding.snapshot.observation_id
        )
    )
    per_url_identity, blocker = resolve_source_pack_v3_per_url_identity(
        work_item_id,
        identity,
        action_id=per_url_delivery_identity_action_id,
        authority=authority,
        observation=observation,
    )
    if blocker is not None:
        return SourcePackV3Preview(
            status="blocked",
            work_item_id=work_item_id,
            blocker=blocker,
        )
    assert per_url_identity is not None
    facts = (facts_loader or (lambda: tuple(ekologus_source_facts())))()
    cards = (cards_loader or (lambda: tuple(ekologus_content_knowledge_cards())))()
    candidates = build_content_source_fact_candidates_v3_projection(
        identity=identity, facts=facts, cards=cards
    )
    return build_source_pack_v3_preview(
        work_item_id,
        identity=identity,
        candidates=candidates,
        facts=facts,
        per_url_identity=per_url_identity,
    )
