from __future__ import annotations

from collections.abc import Iterable

from wilq.content.workflow.decisions.planning import ContentPlanningSection
from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection


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
        if (
            section.get("inventory_disposition")
            if isinstance(section, dict)
            else getattr(section, "inventory_disposition", None)
        )
        != "remove_review_required"
    ]


def bind_draftable_planning_sections(
    proposal_sections: Iterable[ContentPlanningSection],
    revision_sections: Iterable[ContentDraftRevisionSection],
) -> dict[str, ContentPlanningSection]:
    """Bind every draftable plan section to exactly one revision target."""

    bound = {
        section.section_id: section
        for section in draftable_planning_sections(proposal_sections)
    }
    revision_ids = {
        section_id
        for section in revision_sections
        if (section_id := section.section_id) is not None
    }
    if set(bound) != revision_ids:
        raise ValueError("Semantic review proposal sections do not bind to the revision.")
    return bound


__all__ = ["bind_draftable_planning_sections", "draftable_planning_sections"]
