"""Keep exact authority snapshots untouched while adding operator labels."""

from __future__ import annotations

from typing import Any

from wilq.actions.operator_labels import payload_with_operator_labels
from wilq.content.workflow.research_promotion_authority import (
    CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
)
from wilq.content.workflow.source_fact_authority import SOURCE_FACT_AUTHORITY_ACTION_TYPE


def payload_with_authority_snapshot_labels(payload: dict[str, Any]) -> dict[str, Any]:
    action_type = payload.get("action_type")
    if action_type not in {
        CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
        SOURCE_FACT_AUTHORITY_ACTION_TYPE,
    }:
        return payload_with_operator_labels(payload)
    snapshot_key = (
        "promotion_snapshot"
        if action_type == CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE
        else "source_fact_authority"
    )
    snapshot = payload.get(snapshot_key)
    enriched = payload_with_operator_labels(
        {key: value for key, value in payload.items() if key != snapshot_key}
    )
    enriched[snapshot_key] = snapshot
    return enriched
