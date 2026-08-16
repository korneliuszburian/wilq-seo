"""Server-owned section modes for bounded regulatory draft repairs."""

from __future__ import annotations

from wilq.content.drafts.regulatory_patch import RegulatoryPatchMode
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


def regulatory_section_repair_modes(
    proposal: ContentPlanningProposal,
    missing_codes: list[str],
    repair_reasons: dict[str, str],
) -> dict[str, RegulatoryPatchMode]:
    """Choose a safe repair mode from server-owned assurance evidence.

    A semantic requirement failure means the existing section cannot be
    retained as authoritative: appending a qualifier can leave an earlier
    broad, unsupported or incomplete statement intact.  Replace that exact
    requirement section from approved facts.  Literal document-assertion
    omissions remain append-only and are handled by the deterministic repair
    path without a model turn.
    """

    failed_requirement_ids = {
        constraint_id.removeprefix("requirement:")
        for constraint_id, reason_code in repair_reasons.items()
        if constraint_id.startswith("requirement:") and reason_code != "supported"
    }
    missing_requirement_ids = {
        code.removeprefix("requirement:")
        for code in missing_codes
        if code.startswith("requirement:")
    }
    return {
        section.section_id: (
            "replace"
            if failed_requirement_ids.intersection(section.regulatory_requirement_ids)
            else "append"
        )
        for section in proposal.sections
        if missing_requirement_ids.intersection(section.regulatory_requirement_ids)
        or any(
            code.startswith("regulatory_document_assertion:")
            and code.split(":", 2)[1] in section.regulatory_requirement_ids
            for code in missing_codes
        )
    }


__all__ = ["regulatory_section_repair_modes"]
