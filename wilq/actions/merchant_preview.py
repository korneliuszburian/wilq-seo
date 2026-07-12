from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.merchant import (
    MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
)
from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]


def merchant_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render Merchant feed issue cards without exposing technical payloads."""
    preview_items = [
        item
        for item in payload.get("payload_preview", [])
        if isinstance(item, dict)
        and item.get("preview_contract") == MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(_prioritized_preview_items(preview_items)[:4]):
        sample_titles = string_list(item.get("sample_titles"))
        rows = [
            preview_row("Problem", str(item.get("issue_type_label") or "problem do sprawdzenia")),
            preview_row(
                "Atrybut",
                str(item.get("affected_attribute_label") or "atrybut do sprawdzenia"),
            ),
            preview_row("Zgłoszenia", _issue_count_label(item.get("metric_snapshot"))),
            preview_row("Próbki produktów", _sample_summary(item, string_list)),
        ]
        if sample_titles:
            rows.append(preview_row("Tytuły próbek", ", ".join(sample_titles[:2])))
        cards.append(
            ActionPreviewCardViewModel(
                id=str(item.get("id") or f"merchant_preview_{index}"),
                kind="merchant_feed_issue_review",
                title_label="Problem pliku produktowego do sprawdzenia",
                subtitle_label=_preview_subtitle(item),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def _preview_subtitle(item: dict[str, Any]) -> str:
    issue_label = str(item.get("issue_type_label") or "problem pliku produktowego")
    attribute_label = str(item.get("affected_attribute_label") or "").strip()
    if attribute_label and attribute_label not in {"atrybut", "atrybut do sprawdzenia"}:
        return f"{attribute_label} - {issue_label}"
    return issue_label


def _prioritized_preview_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            0
            if _string_list(item.get("sample_titles"))
            or _string_list(item.get("sample_product_ids"))
            else 1,
            str(item.get("id") or ""),
        ),
    )


def _issue_count_label(value: Any) -> str:
    if isinstance(value, dict):
        issue_count = value.get("issue_product_count")
        if isinstance(issue_count, int | float):
            count = int(issue_count)
            if count == 1:
                return "1 zgłoszenie problemu"
            if 2 <= count <= 4:
                return f"{count} zgłoszenia problemu"
            return f"{count} zgłoszeń problemu"
    return "brak liczby zgłoszeń"


def _sample_summary(item: dict[str, Any], string_list: StringList) -> str:
    titles = string_list(item.get("sample_titles"))
    product_ids = string_list(item.get("sample_product_ids"))
    if titles:
        count = len(titles)
        if count == 1:
            return "1 próbka z nazwą produktu"
        if 2 <= count <= 4:
            return f"{count} próbki z nazwami produktów"
        return f"{count} próbek z nazwami produktów"
    if product_ids:
        count = len(product_ids)
        if count == 1:
            return "1 próbka produktu bez nazwy"
        if 2 <= count <= 4:
            return f"{count} próbki produktów bez nazw"
        return f"{count} próbek produktów bez nazw"
    reason = item.get("sample_unavailable_reason_label") or item.get("sample_unavailable_reason")
    if isinstance(reason, str) and reason:
        return reason
    return "brak próbek produktów"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
