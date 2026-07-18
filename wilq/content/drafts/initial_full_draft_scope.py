from __future__ import annotations

from collections.abc import Iterable

from wilq.content.workflow.planning import ContentPlanningSection


def draftable_planning_sections(
    sections: Iterable[ContentPlanningSection],
) -> list[ContentPlanningSection]:
    """Return only sections allowed to become body content.

    ``remove_review_required`` rows remain in the planning proposal so the
    marketer can see what was excluded from the existing page. They are not
    document targets and must never be sent to the full-draft generator.
    """

    return [
        section
        for section in sections
        if section.inventory_disposition != "remove_review_required"
    ]


__all__ = ["draftable_planning_sections"]
