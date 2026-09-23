"""Public read-only preview of an exact current v2 source pack."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers.content_current_page_identity_v2 import (
    _read_current_page_evidence,
)
from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v2 import resolve_current_page_identity_v2
from wilq.content.workflow.source_pack_v2 import SourcePackV2Preview, build_source_pack_v2_preview
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store

StoreFactory = Callable[[], ContentWorkflowStore]
EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]
FactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
CardsLoader = Callable[[], tuple[ContentKnowledgeCard, ...]]


def register_content_source_pack_v2_route(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
    facts_loader: FactsLoader | None = None,
    cards_loader: CardsLoader | None = None,
) -> None:
    make_store = store_factory or (lambda: content_workflow_store())
    load_evidence = evidence_loader or _read_current_page_evidence
    load_facts = facts_loader or (lambda: tuple(ekologus_source_facts()))
    load_cards = cards_loader or (lambda: tuple(ekologus_content_knowledge_cards()))

    @router.get(
        "/api/content/work-items/{work_item_id}/source-pack-preview",
        response_model=SourcePackV2Preview,
    )
    def read_source_pack_v2_preview(work_item_id: str) -> SourcePackV2Preview:
        return read_current_source_pack_v2_preview(
            work_item_id,
            store_factory=make_store,
            evidence_loader=load_evidence,
            facts_loader=load_facts,
            cards_loader=load_cards,
        )


def read_current_source_pack_v2_preview(
    work_item_id: str,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
    facts_loader: FactsLoader | None = None,
    cards_loader: CardsLoader | None = None,
) -> SourcePackV2Preview:
    """Read and validate one exact current source pack through the public GET seam."""
    store = (store_factory or content_workflow_store)()
    evidence = (evidence_loader or _read_current_page_evidence)(work_item_id)
    identity = resolve_current_page_identity_v2(work_item_id, store=store, evidence=evidence)
    receipt = store.load_latest_source_fact_authority_v2_receipt_for_work_item(work_item_id)
    return build_source_pack_v2_preview(
        work_item_id,
        identity=identity,
        authority_receipts=() if receipt is None else (receipt,),
        facts=(facts_loader or (lambda: tuple(ekologus_source_facts())))(),
        cards=(cards_loader or (lambda: tuple(ekologus_content_knowledge_cards())))(),
    )


__all__ = ["read_current_source_pack_v2_preview", "register_content_source_pack_v2_route"]
