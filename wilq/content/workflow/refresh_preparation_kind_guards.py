"""Fail-closed content-kind guards for classified refresh preparation."""

from __future__ import annotations

from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBlocker,
    inventory_missing_blocker,
    landing_hub_required_blocker,
)


def preview_content_kind_blocker(
    inventory_binding: ContentKindInventoryBinding | None,
) -> ContentRefreshPreparationBlocker | None:
    if inventory_binding is None:
        return inventory_missing_blocker()
    if inventory_binding.content_kind == "landing_or_hub":
        return landing_hub_required_blocker()
    return None


def runtime_content_kind_blocker(
    content_kind: str,
    inventory_binding: ContentKindInventoryBinding | None,
) -> ContentRefreshPreparationBlocker | None:
    if inventory_binding is not None and inventory_binding.content_kind == "landing_or_hub":
        return landing_hub_required_blocker()
    if content_kind == "service" and inventory_binding is None:
        return inventory_missing_blocker()
    return None


__all__ = ["preview_content_kind_blocker", "runtime_content_kind_blocker"]
