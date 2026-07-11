from __future__ import annotations

from typing import Any


def payload_apply_allowed(
    payload: dict[str, Any],
    preview_items: list[dict[str, Any]],
) -> bool:
    if payload.get("apply_allowed") is True:
        return True
    if not preview_items:
        return False
    return all(item.get("apply_allowed") is True for item in preview_items)


def payload_api_mutation_ready(
    payload: dict[str, Any],
    preview_items: list[dict[str, Any]],
) -> bool:
    if payload.get("api_mutation_ready") is True:
        return True
    if payload.get("api_mutation_ready") is False:
        return False
    if not preview_items:
        return False
    return all(
        item.get("apply_allowed") is True and item.get("api_mutation_ready") is not False
        for item in preview_items
    )
