"""Exact packet identity binding for planning-input digests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wilq.content.planning.dynamic_input import ContentPlanningInput


def bind_research_packet_to_planning_input(
    planning_input: ContentPlanningInput,
    packet: Any,
) -> ContentPlanningInput:
    """Return the exact planning input whose digest includes packet identity."""

    if planning_input.work_item_id != packet.current_work_item_id:
        raise ValueError("Research packet and planning input must share the same work item.")
    from wilq.content.planning.dynamic_input import _digest

    payload = planning_input.model_dump(mode="json")
    payload.update(
        {
            "research_packet_id": packet.packet_id,
            "research_packet_digest": packet.packet_digest,
        }
    )
    payload.pop("planning_input_digest", None)
    digest = _digest(
        {
            "schema_name": "wilq_content_planning_input_v7",
            "criteria_version": "wilq_people_first_planning_v5",
            "inventory_mapping_policy": "wilq_inventory_mapping_v7",
            **payload,
        }
    )
    return planning_input.model_copy(
        update={
            "planning_input_digest": digest,
            "research_packet_id": packet.packet_id,
            "research_packet_digest": packet.packet_digest,
        }
    )


__all__ = ["bind_research_packet_to_planning_input"]
