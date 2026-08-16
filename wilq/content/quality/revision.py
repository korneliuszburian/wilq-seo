from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.operator_copy import build_blocker
from wilq.content.quality.review import ContentQualityReview, ContentRevisionInstruction
from wilq.content.workflow.contracts.models import ContentWorkItem

ContentRevisionPlanStatus = Literal["blocked", "ready", "no_changes_needed"]
ContentRevisionPlanBlockerCode = Literal[
    "missing_quality_review",
    "quality_review_mismatch",
    "quality_review_blocked",
    "missing_revision_instructions",
]


class ContentRevisionPlanBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentRevisionPlanBlockerCode
    label: str
    reason: str
    next_step: str


class ContentRevisionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    work_item_id: str
    quality_review_id: str | None = None
    status: ContentRevisionPlanStatus
    draft_revision_allowed: bool = False
    instructions: list[ContentRevisionInstruction] = Field(default_factory=list)
    blockers: list[ContentRevisionPlanBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    safe_next_step: str


def build_content_revision_plan(
    *,
    item: ContentWorkItem,
    quality_review: ContentQualityReview | None,
) -> ContentRevisionPlan:
    blockers = _revision_plan_blockers(item=item, quality_review=quality_review)
    if quality_review is None:
        return _plan(
            item=item,
            quality_review=None,
            status="blocked",
            blockers=blockers,
            safe_next_step=blockers[0].next_step,
        )
    if blockers:
        return _plan(
            item=item,
            quality_review=quality_review,
            status="blocked",
            blockers=blockers,
            safe_next_step=blockers[0].next_step,
        )
    if not quality_review.revision_instructions:
        return _plan(
            item=item,
            quality_review=quality_review,
            status="no_changes_needed",
            safe_next_step=(
                "Szkic nie wymaga planu poprawki. Przekaż go do sprawdzenia człowieka."
            ),
        )
    return _plan(
        item=item,
        quality_review=quality_review,
        status="ready",
        draft_revision_allowed=True,
        instructions=quality_review.revision_instructions,
        safe_next_step="Wykonaj tylko wskazane poprawki i uruchom ocenę jakości ponownie.",
    )


def _revision_plan_blockers(
    *,
    item: ContentWorkItem,
    quality_review: ContentQualityReview | None,
) -> list[ContentRevisionPlanBlocker]:
    if quality_review is None:
        return [
            build_blocker(
                ContentRevisionPlanBlocker,
                code="missing_quality_review",
                label="Brakuje oceny jakości",
                reason="Plan poprawki musi wynikać z oceny jakości WILQ, nie z wolnego promptu.",
                next_step="Najpierw uruchom ocenę jakości szkicu.",
            )
        ]
    blockers: list[ContentRevisionPlanBlocker] = []
    if quality_review.work_item_id != item.id:
        blockers.append(
            build_blocker(
                ContentRevisionPlanBlocker,
                code="quality_review_mismatch",
                label="Ocena dotyczy innego tematu",
                reason="Nie wolno poprawiać szkicu na podstawie oceny innego work itemu.",
                next_step="Użyj oceny jakości przypisanej do aktualnego tematu.",
            )
        )
    if quality_review.verdict == "blocked":
        blockers.append(
            build_blocker(
                ContentRevisionPlanBlocker,
                code="quality_review_blocked",
                label="Ocena jakości blokuje poprawkę",
                reason="Najpierw trzeba usunąć blokady: dowody, claimy, duplikację albo pomiar.",
                next_step=quality_review.safe_next_step,
            )
        )
    if quality_review.verdict == "needs_changes" and not quality_review.revision_instructions:
        blockers.append(
            build_blocker(
                ContentRevisionPlanBlocker,
                code="missing_revision_instructions",
                label="Brakuje instrukcji poprawki",
                reason="Nie wolno regenerować szkicu bez ograniczonej listy zmian.",
                next_step="Wygeneruj ocenę jakości z konkretnymi instrukcjami poprawki.",
            )
        )
    return blockers


def _plan(
    *,
    item: ContentWorkItem,
    quality_review: ContentQualityReview | None,
    status: ContentRevisionPlanStatus,
    blockers: list[ContentRevisionPlanBlocker] | None = None,
    instructions: list[ContentRevisionInstruction] | None = None,
    draft_revision_allowed: bool = False,
    safe_next_step: str,
) -> ContentRevisionPlan:
    return ContentRevisionPlan(
        id=f"revision_plan_{item.id}",
        work_item_id=item.id,
        quality_review_id=None if quality_review is None else quality_review.review_id,
        status=status,
        draft_revision_allowed=draft_revision_allowed,
        instructions=instructions or [],
        blockers=blockers or [],
        evidence_ids=[] if quality_review is None else quality_review.evidence_ids,
        source_connectors=item.source_connectors
        if quality_review is None
        else quality_review.source_connectors,
        safe_next_step=safe_next_step,
    )
