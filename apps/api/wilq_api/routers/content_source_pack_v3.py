"""Public read-only source pack from current identity and approved official facts."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v3 import resolve_current_page_identity_v3
from wilq.content.workflow.source_fact_candidate_v3 import (
    build_content_source_fact_candidates_v3_projection,
)
from wilq.content.workflow.source_pack_v3 import SourcePackV3Preview, build_source_pack_v3_preview

EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]
FactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
CardsLoader = Callable[[], tuple[ContentKnowledgeCard, ...]]


def register_content_source_pack_v3_route(
    router: APIRouter,
    *,
    evidence_loader: EvidenceLoader | None = None,
    facts_loader: FactsLoader | None = None,
    cards_loader: CardsLoader | None = None,
) -> None:
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
    def read_source_pack_v3_preview(work_item_id: str) -> SourcePackV3Preview:
        facts = load_facts()
        cards = load_cards()
        identity = resolve_current_page_identity_v3(work_item_id, load_evidence(work_item_id))
        candidates = build_content_source_fact_candidates_v3_projection(
            identity=identity, facts=facts, cards=cards
        )
        return build_source_pack_v3_preview(
            work_item_id, identity=identity, candidates=candidates, facts=facts
        )
