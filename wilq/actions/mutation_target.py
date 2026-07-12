from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.content.workflow.contracts import ContentWordPressDraftActivationPacketResponse
from wilq.schemas import ActionObject

PreviewItems = Callable[[dict[str, Any]], list[dict[str, Any]]]


def mutation_readiness_target(
    action: ActionObject,
    *,
    activation_packet: ContentWordPressDraftActivationPacketResponse | None = None,
    preview_items: PreviewItems,
) -> dict[str, str | None]:
    if activation_packet is not None:
        label_parts = [
            part
            for part in [
                activation_packet.topic,
                activation_packet.final_canonical_url,
            ]
            if isinstance(part, str) and part.strip()
        ]
        return {
            "candidate_id": activation_packet.work_item_id,
            "label": " | ".join(label_parts) if label_parts else activation_packet.topic,
            "url": activation_packet.final_canonical_url,
        }
    items = preview_items(action.payload)
    first = items[0] if items else {}
    candidate_id = first.get("candidate_id")
    topic = first.get("topic")
    url = (
        first.get("final_canonical_url")
        or first.get("intended_final_url")
        or first.get("source_public_url")
    )
    label_parts = [part for part in [topic, url] if isinstance(part, str) and part.strip()]
    return {
        "candidate_id": candidate_id if isinstance(candidate_id, str) else None,
        "label": " | ".join(label_parts) if label_parts else None,
        "url": url if isinstance(url, str) else None,
    }
