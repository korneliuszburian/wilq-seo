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


def payload_preview_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "wordpress_draft_payload_preview",
        "budget_payload_preview",
        "custom_segment_payload_preview",
        "negative_keyword_payload_preview",
        "ngram_preview",
    ):
        preview = payload.get(key)
        if isinstance(preview, list):
            items = [item for item in preview if isinstance(item, dict)]
            if items:
                return items
        if isinstance(preview, dict):
            return [preview]
    preview = payload.get("payload_preview")
    if isinstance(preview, list):
        return [item for item in preview if isinstance(item, dict)]
    if isinstance(preview, dict):
        return [preview]
    preview_items: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, list):
            preview_items.extend(
                item for item in value if isinstance(item, dict) and "apply_allowed" in item
            )
    return preview_items


def payload_preview_contract(
    payload: dict[str, Any], preview_items: list[dict[str, Any]]
) -> str | None:
    if isinstance(payload.get("preview_contract"), str):
        return str(payload["preview_contract"])
    for item in preview_items:
        contract = item.get("preview_contract")
        if isinstance(contract, str):
            return contract
    return None
