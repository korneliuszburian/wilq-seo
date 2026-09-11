"""Fail-closed content-kind guards for classified refresh preparation."""

from __future__ import annotations

from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBlocker,
    inventory_missing_blocker,
    landing_hub_required_blocker,
)
from wilq.content.workflow.refresh_preparation_models import (
    ContentKindInventoryLoader,
    RefreshPreparationRuntimeBlocked,
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


def no_receipt_content_kind_blocker(
    content_kind: str,
    work_item_id: str,
    inventory_loader: ContentKindInventoryLoader,
) -> ContentRefreshPreparationBlocker | None:
    inventory_binding = inventory_loader(work_item_id)
    if inventory_binding is None:
        return None
    return runtime_content_kind_blocker(content_kind, inventory_binding)


def no_receipt_content_kind_resolution(
    content_kind: str,
    work_item_id: str,
    inventory_loader: ContentKindInventoryLoader,
) -> RefreshPreparationRuntimeBlocked | None:
    blocker = no_receipt_content_kind_blocker(content_kind, work_item_id, inventory_loader)
    return None if blocker is None else RefreshPreparationRuntimeBlocked(work_item_id, blocker)


__all__ = [
    "no_receipt_content_kind_blocker",
    "no_receipt_content_kind_resolution",
    "preview_content_kind_blocker",
    "runtime_content_kind_blocker",
]
