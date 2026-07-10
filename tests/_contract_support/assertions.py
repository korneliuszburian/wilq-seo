"""Assertions shared by API contract tests, expressed at the operator view-model seam."""

from __future__ import annotations

from typing import Any

_RAW_PREVIEW_ITEM_KEYS = {
    "action_type",
    "api_mutation_ready",
    "apply_allowed",
    "blocked_claims",
    "candidate_id",
    "destructive",
    "evidence_ids",
    "preview_contract",
    "product_id",
    "recommendation_id",
    "sample_product_ids",
    "source_type",
}


def assert_preview_items_are_operator_view_models(items: list[dict[str, Any]]) -> None:
    allowed_keys = {"id", "title_label", "status_label", "rows"}
    for item in items:
        assert set(item) <= allowed_keys
        assert item["id"].startswith("preview_item_")
        assert item["title_label"]
        assert not _RAW_PREVIEW_ITEM_KEYS.intersection(item)
        for row in item["rows"]:
            assert set(row) == {"label", "value"}
            assert row["label"]
            assert isinstance(row["value"], str)


def preview_card_row_values(card: dict[str, Any], label: str) -> list[str]:
    return [
        row["value"]
        for row in card.get("rows", [])
        if row.get("label") == label and isinstance(row.get("value"), str)
    ]


def _string_values_from(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_string_values_from(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_string_values_from(item))
        return strings
    return []


def assert_operator_context_strings_clean(context: dict[str, Any]) -> None:
    context_text = "\n".join(_string_values_from(context))
    forbidden_terms = (
        "Action" + "Object",
        "Command" + " Center",
        "Content" + " Planner",
        "Ads" + " Doctor",
        "evidence" + " IDs",
        "No " + "evidence ID",
        "must not " + "invent metrics",
        "block" + "ery",
        "target" + "_site",
        "mapping" + "_review",
        "mapping" + "-review",
        "migration" + "-map",
        "competitor" + "_page",
        "MERCHANT" + "_ACTION",
        "SHOPPING" + "_ADS",
        "FREE" + "_LISTINGS",
        "NOT" + "_IMPACTED",
        "missing" + "_potentially_required_attribute",
        "wykonanie" + " zmian",
        "tylko do" + " sprawdzenia",
    )
    for forbidden_term in forbidden_terms:
        assert forbidden_term not in context_text
