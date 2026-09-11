from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.operator_copy import build_blocker

ContentPlanningInputBlockerCode = Literal[
    "unknown_service_card",
    "service_selection_not_confirmed",
    "service_card_not_approved",
    "missing_approved_service_fact",
    "service_context_mismatch",
    "missing_planning_foundation",
    "missing_wordpress_section_inventory",
    "missing_wordpress_full_inventory",
    "wordpress_material_review_required",
    "stale_planning_sources",
    "blocked_planning_sources",
    "new_page_foundation_stale",
    "missing_new_page_service_fact",
    "missing_regulatory_source_coverage",
]


class ContentPlanningInputBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentPlanningInputBlockerCode
    label: str
    reason: str
    next_step: str


def resolve_service_candidate(
    service_profile: ContentWorkItemServiceProfileContext,
    service_card_id: str,
) -> tuple[ContentWorkItemServiceCandidate | None, ContentPlanningInputBlocker | None]:
    candidate = next(
        (
            item
            for item in service_profile.service_candidates
            if item.service_card_id == service_card_id
        ),
        None,
    )
    if candidate is None:
        return None, build_blocker(
            ContentPlanningInputBlocker,
            code="unknown_service_card",
            label="Usługa nie należy do tego work itemu",
            reason="Wybrana karta nie wynika z dokładnego dopasowania strony i wiedzy WILQ.",
            next_step="Wybierz jedną z kandydatur zwróconych przez bieżący snapshot.",
        )
    if service_profile.service_card_id != service_card_id:
        return None, build_blocker(
            ContentPlanningInputBlocker,
            code="service_context_mismatch",
            label="Wybór usługi jest nieaktualny",
            reason="Bieżący snapshot nie jest jeszcze związany z wybraną kartą usługi.",
            next_step="Zapisz wybór usługi w review zakresu i odśwież snapshot.",
        )
    return candidate, None


def foundation_blocker() -> ContentPlanningInputBlocker:
    return build_blocker(
        ContentPlanningInputBlocker,
        code="missing_planning_foundation",
        label="Brakuje kompletnego wejścia do planu",
        reason="Sales Brief, preserve-first package albo plan bazowy jest zablokowany.",
        next_step="Usuń blokery wiedzy, inventory i briefu przed uruchomieniem Codexa.",
    )


def missing_service_blocker() -> ContentPlanningInputBlocker:
    return build_blocker(
        ContentPlanningInputBlocker,
        code="unknown_service_card",
        label="Brakuje dokładnej usługi",
        reason="Treść usługowa wymaga typed karty usługi.",
        next_step="Wybierz usługę wynikającą z bieżącego snapshotu.",
    )


__all__ = [
    "ContentPlanningInputBlocker",
    "ContentPlanningInputBlockerCode",
    "foundation_blocker",
    "missing_service_blocker",
    "resolve_service_candidate",
]
