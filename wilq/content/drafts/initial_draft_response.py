"""Shared packet binding for every initial-draft response constructor."""

from __future__ import annotations

from typing import TypedDict

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


class InitialDraftPacketFields(TypedDict):
    research_packet_id: str | None
    research_packet_digest: str | None


def initial_draft_packet_fields(
    *,
    proposal: ContentPlanningProposal | None = None,
    planning_input: ContentPlanningInput | None = None,
    revision: ContentDraftRevision | None = None,
    research_packet_id: str | None = None,
    research_packet_digest: str | None = None,
) -> InitialDraftPacketFields:
    """Resolve one exact packet pair from every response-owned source."""

    pairs: list[tuple[str, str | None, str | None]] = []
    if research_packet_id is not None or research_packet_digest is not None:
        pairs.append(("explicit response binding", research_packet_id, research_packet_digest))
    if proposal is not None:
        pairs.append(
            (
                "planning proposal binding",
                getattr(proposal, "research_packet_id", None),
                getattr(proposal, "research_packet_digest", None),
            )
        )
    if planning_input is not None:
        pairs.append(
            (
                "planning input binding",
                getattr(planning_input, "research_packet_id", None),
                getattr(planning_input, "research_packet_digest", None),
            )
        )
    if revision is not None:
        pairs.append(
            (
                "revision binding",
                getattr(revision, "research_packet_id", None),
                getattr(revision, "research_packet_digest", None),
            )
        )

    for source, packet_id, packet_digest in pairs:
        if (packet_id is None) != (packet_digest is None):
            raise ValueError(f"{source} must carry a complete packet binding")
    distinct_pairs = {(packet_id, packet_digest) for _, packet_id, packet_digest in pairs}
    if len(distinct_pairs) > 1:
        raise ValueError("Initial draft response packet binding sources must match exactly")
    packet_id, packet_digest = next(iter(distinct_pairs), (None, None))
    return {
        "research_packet_id": packet_id,
        "research_packet_digest": packet_digest,
    }


__all__ = ["InitialDraftPacketFields", "initial_draft_packet_fields"]
