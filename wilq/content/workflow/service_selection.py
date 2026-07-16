from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)

ContentPlanningServiceSelectionErrorCode = Literal[
    "candidate_not_allowed",
    "missing_recommendation",
]


class ContentPlanningServiceSelectionError(ValueError):
    def __init__(self, code: ContentPlanningServiceSelectionErrorCode) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ContentPlanningServiceSelection:
    service_card_id: str
    service_label: str
    human_override_review_required: bool


def resolve_content_planning_service_selection(
    context: ContentWorkItemServiceProfileContext,
    requested_service_card_id: str | None,
) -> ContentPlanningServiceSelection:
    selected_service_card_id = requested_service_card_id or context.service_card_id
    selected = next(
        (
            candidate
            for candidate in context.service_candidates
            if candidate.service_card_id == selected_service_card_id
        ),
        None,
    )
    if selected is None:
        raise ContentPlanningServiceSelectionError("candidate_not_allowed")
    recommended = next(
        (candidate for candidate in context.service_candidates if candidate.recommended),
        None,
    )
    if recommended is None:
        raise ContentPlanningServiceSelectionError("missing_recommendation")
    return ContentPlanningServiceSelection(
        service_card_id=selected.service_card_id,
        service_label=selected.service_label,
        human_override_review_required=(
            selected.service_card_id != recommended.service_card_id
        ),
    )
