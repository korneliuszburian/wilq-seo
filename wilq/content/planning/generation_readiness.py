from __future__ import annotations

from typing import Protocol


class _PlanningBlocker(Protocol):
    code: str


def planning_generation_blockers[Blocker: _PlanningBlocker](
    blockers: list[Blocker],
) -> list[Blocker]:
    """Keep only blockers that make a planning turn unsafe.

    A public rendered ``the_content`` read can support a reviewable plan. Its
    REST/ACF provenance remains a draft-generation gate in the draft seam.
    """

    return [
        blocker
        for blocker in blockers
        if blocker.code != "wordpress_material_review_required"
    ]
