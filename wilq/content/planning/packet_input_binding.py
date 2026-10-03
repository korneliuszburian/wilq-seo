"""Exact packet identity binding for planning-input digests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wilq.content.planning.dynamic_input import ContentPlanningInput

V3_PACKET_ID_PREFIX = "content_research_packet_v3_"


def is_v3_research_packet_id(packet_id: str) -> bool:
    return packet_id.startswith(V3_PACKET_ID_PREFIX)


def bind_research_packet_to_planning_input(
    planning_input: ContentPlanningInput,
    packet: Any,
) -> ContentPlanningInput:
    """Return the exact planning input whose digest includes packet identity."""

    return bind_packet_identity_to_planning_input(
        planning_input,
        work_item_id=packet.current_work_item_id,
        packet_id=packet.packet_id,
        packet_digest=packet.packet_digest,
    )


def bind_packet_identity_to_planning_input(
    planning_input: ContentPlanningInput,
    *,
    work_item_id: str,
    packet_id: str,
    packet_digest: str,
) -> ContentPlanningInput:
    """Bind actual packet identity without assuming a v1 source-pack binding."""

    if planning_input.work_item_id != work_item_id:
        raise ValueError("Research packet and planning input must share the same work item.")
    payload = planning_input.model_dump(mode="json")
    payload.update(
        {
            "research_packet_id": packet_id,
            "research_packet_digest": packet_digest,
        }
    )
    payload.pop("planning_input_digest", None)
    digest = _digest_bound_payload(payload)
    return planning_input.model_copy(
        update={
            "planning_input_digest": digest,
            "research_packet_id": packet_id,
            "research_packet_digest": packet_digest,
        }
    )


def unbind_packet_identity_from_planning_input(
    planning_input: ContentPlanningInput,
) -> ContentPlanningInput:
    """Recover the exact pre-packet input for v2 currentness checks."""
    if planning_input.research_packet_id is None:
        return planning_input
    payload = planning_input.model_dump(mode="json")
    payload["research_packet_id"] = None
    payload["research_packet_digest"] = None
    payload.pop("planning_input_digest", None)
    return planning_input.model_copy(
        update={
            "planning_input_digest": _digest_bound_payload(payload),
            "research_packet_id": None,
            "research_packet_digest": None,
        }
    )


def _digest_bound_payload(payload: dict[str, Any]) -> str:
    from wilq.content.planning.dynamic_input import _digest

    return _digest(
        {
            "schema_name": "wilq_content_planning_input_v7",
            "criteria_version": "wilq_people_first_planning_v5",
            "inventory_mapping_policy": "wilq_inventory_mapping_v7",
            **payload,
        }
    )


__all__ = [
    "V3_PACKET_ID_PREFIX",
    "bind_packet_identity_to_planning_input",
    "bind_research_packet_to_planning_input",
    "is_v3_research_packet_id",
    "unbind_packet_identity_from_planning_input",
]
