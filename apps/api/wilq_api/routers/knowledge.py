from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from wilq.knowledge.compilers.playbook_compiler import (
    compile_playbook_cards,
    condense_playbooks,
    get_playbook,
    list_playbooks,
)
from wilq.knowledge.operating_map import build_knowledge_operating_map
from wilq.schemas import (
    KnowledgeCard,
    KnowledgeCompilerResult,
    KnowledgeOperatingMapResponse,
    MarketingPlaybook,
)

router = APIRouter()


@router.get("/api/knowledge/cards", response_model=list[KnowledgeCard])
def knowledge_cards() -> list[KnowledgeCard]:
    return compile_playbook_cards()


@router.get("/api/knowledge/search")
def knowledge_search(q: str = "") -> list[dict[str, Any]]:
    query = q.lower()
    cards = compile_playbook_cards()
    if query:
        cards = [
            card for card in cards if query in card.title.lower() or query in card.summary.lower()
        ]
    return [card.model_dump(mode="json") for card in cards]


@router.get("/api/knowledge/playbooks", response_model=list[MarketingPlaybook])
def knowledge_playbooks() -> list[MarketingPlaybook]:
    return list(list_playbooks())


@router.get("/api/knowledge/playbooks/{playbook_id}", response_model=MarketingPlaybook)
def knowledge_playbook_detail(playbook_id: str) -> MarketingPlaybook:
    playbook = get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail=f"Unknown playbook: {playbook_id}")
    return playbook


@router.get("/api/knowledge/operating-map", response_model=KnowledgeOperatingMapResponse)
def knowledge_operating_map() -> KnowledgeOperatingMapResponse:
    return build_knowledge_operating_map()


@router.post("/api/knowledge/condense", response_model=KnowledgeCompilerResult)
def knowledge_condense() -> KnowledgeCompilerResult:
    return condense_playbooks()
