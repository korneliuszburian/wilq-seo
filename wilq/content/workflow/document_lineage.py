from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.cards import (
    ContentKnowledgeCardType,
    ekologus_content_knowledge_cards,
)
from wilq.content.workflow.revisions import ContentDraftRevision


class ContentDocumentWorkspaceKnowledgeCard(BaseModel):
    """A knowledge card explicitly carried by the exact document revision."""

    model_config = ConfigDict(extra="forbid")

    id: str
    card_type: ContentKnowledgeCardType
    title: str
    summary: str


class ContentDocumentWorkspaceDocumentLineage(BaseModel):
    """Only sources actually attached to the displayed revision.

    This is deliberately not the global knowledge catalogue or a planning
    suggestion. A document without persisted lineage must say so plainly.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "partial", "not_recorded"]
    source_material_ids: list[str] = Field(default_factory=list)
    knowledge_cards: list[ContentDocumentWorkspaceKnowledgeCard] = Field(default_factory=list)
    unresolved_knowledge_card_ids: list[str] = Field(default_factory=list)
    reason: str


def build_content_document_lineage(
    revision: ContentDraftRevision | None,
) -> ContentDocumentWorkspaceDocumentLineage:
    if revision is None:
        return ContentDocumentWorkspaceDocumentLineage(
            status="not_recorded",
            reason=(
                "Nie ma jeszcze zapisanej rewizji, więc WILQ nie może wskazać "
                "materiałów przypisanych do dokumentu."
            ),
        )
    source_material_ids = list(dict.fromkeys(revision.source_material_ids))
    card_ids = list(dict.fromkeys(revision.knowledge_card_ids))
    cards_by_id = {card.id: card for card in ekologus_content_knowledge_cards()}
    knowledge_cards = [
        ContentDocumentWorkspaceKnowledgeCard(
            id=card.id,
            card_type=card.card_type,
            title=card.title,
            summary=card.summary,
        )
        for card_id in card_ids
        if (card := cards_by_id.get(card_id)) is not None
    ]
    unresolved = [card_id for card_id in card_ids if card_id not in cards_by_id]
    if not source_material_ids and not card_ids:
        return ContentDocumentWorkspaceDocumentLineage(
            status="not_recorded",
            reason=(
                "Ta rewizja nie zawiera jeszcze zapisanej listy materiałów ani kart "
                "wiedzy. Nie pokazujemy globalnego katalogu jako przypisanych źródeł."
            ),
        )
    if unresolved:
        return ContentDocumentWorkspaceDocumentLineage(
            status="partial",
            source_material_ids=source_material_ids,
            knowledge_cards=knowledge_cards,
            unresolved_knowledge_card_ids=unresolved,
            reason=(
                "Rewizja zawiera przypisane materiały, ale część kart wiedzy nie jest "
                "dostępna w aktualnym katalogu."
            ),
        )
    return ContentDocumentWorkspaceDocumentLineage(
        status="available",
        source_material_ids=source_material_ids,
        knowledge_cards=knowledge_cards,
        reason="To są materiały i karty wiedzy zapisane przy dokładnej rewizji dokumentu.",
    )
