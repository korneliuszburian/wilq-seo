from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import (
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewItemViewModel,
    ActionPreviewRowViewModel,
)

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
LabelValue = Callable[[Any], str]


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


def action_preview_item_view_models(
    *,
    action: ActionObject,
    raw_items: list[dict[str, Any]],
    preview_cards: list[ActionPreviewCardViewModel],
    max_items: int,
    preview_row: PreviewRow,
    apply_state_label: LabelValue,
    system_readiness_label: LabelValue,
    preview_contract_label: Callable[[str | None], str],
) -> list[ActionPreviewItemViewModel]:
    if preview_cards:
        return [
            _preview_item_from_card(
                card=card,
                raw_item=raw_items[index] if index < len(raw_items) else None,
                index=index,
                preview_row=preview_row,
            )
            for index, card in enumerate(preview_cards[:max_items])
        ]
    return [
        _preview_item_from_raw_payload(
            action,
            item,
            index,
            preview_row=preview_row,
            apply_state_label=apply_state_label,
            system_readiness_label=system_readiness_label,
            preview_contract_label=preview_contract_label,
        )
        for index, item in enumerate(raw_items[:max_items])
    ]


def _preview_item_from_card(
    *,
    card: ActionPreviewCardViewModel,
    raw_item: dict[str, Any] | None,
    index: int,
    preview_row: PreviewRow,
) -> ActionPreviewItemViewModel:
    rows = list(card.rows[:4])
    if card.apply_state_label:
        rows.append(preview_row("Zapis zmian", card.apply_state_label))
    if card.system_readiness_label:
        rows.append(preview_row("Gotowość systemu", card.system_readiness_label))
    return ActionPreviewItemViewModel(
        id=f"preview_item_{index + 1}",
        preview_contract=_preview_item_contract(raw_item),
        candidate_id=_preview_item_candidate_id(raw_item),
        title_label=card.title_label or f"Pozycja podglądu {index + 1}",
        status_label=card.status_label,
        rows=rows,
    )


def _preview_item_from_raw_payload(
    action: ActionObject,
    item: dict[str, Any],
    index: int,
    *,
    preview_row: PreviewRow,
    apply_state_label: LabelValue,
    system_readiness_label: LabelValue,
    preview_contract_label: Callable[[str | None], str],
) -> ActionPreviewItemViewModel:
    rows = _safe_raw_preview_rows(
        item,
        preview_row=preview_row,
        apply_state_label=apply_state_label,
        system_readiness_label=system_readiness_label,
    )
    if not rows:
        rows = [
            preview_row(
                "Zakres", preview_contract_label(payload_preview_contract(action.payload, [item]))
            ),
        ]
    return ActionPreviewItemViewModel(
        id=f"preview_item_{index + 1}",
        preview_contract=_preview_item_contract(item),
        candidate_id=_preview_item_candidate_id(item),
        title_label=_raw_preview_title(item, index),
        status_label=_raw_preview_status(item),
        rows=rows[:6],
    )


def _preview_item_contract(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    value = item.get("preview_contract")
    if isinstance(value, str) and value == "wordpress_draft_payload_preview_v1":
        return value
    return None


def _preview_item_candidate_id(item: dict[str, Any] | None) -> str | None:
    if not item or item.get("preview_contract") != "wordpress_draft_payload_preview_v1":
        return None
    value = item.get("candidate_id")
    return value if isinstance(value, str) and value else None


def _safe_raw_preview_rows(
    item: dict[str, Any],
    *,
    preview_row: PreviewRow,
    apply_state_label: LabelValue,
    system_readiness_label: LabelValue,
) -> list[ActionPreviewRowViewModel]:
    rows: list[ActionPreviewRowViewModel] = []
    for label, value in _raw_preview_label_values(item):
        rows.append(preview_row(label, value))
        if len(rows) >= 4:
            break
    if "apply_allowed" in item:
        rows.append(preview_row("Zapis zmian", apply_state_label(item.get("apply_allowed"))))
    if "api_mutation_ready" in item:
        rows.append(
            preview_row("Gotowość systemu", system_readiness_label(item.get("api_mutation_ready")))
        )
    return rows


def _raw_preview_label_values(item: dict[str, Any]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for key, value in item.items():
        if not key.endswith("_label") or key in {"id_label", "preview_contract_label"}:
            continue
        label = _raw_preview_row_label(key)
        if isinstance(value, str) and value:
            values.append((label, value))
        elif isinstance(value, list):
            values.extend((label, entry) for entry in value if isinstance(entry, str) and entry)
    return values


def _raw_preview_row_label(key: str) -> str:
    labels = {
        "affected_attribute_label": "Atrybut",
        "issue_type_label": "Problem",
        "mode_label": "Tryb",
        "operation_type_label": "Operacja",
        "readiness_label": "Gotowość",
        "recommendation_type_label": "Rekomendacja",
        "reason_label": "Powód",
        "risk_label": "Ryzyko",
        "status_label": "Status",
        "validation_status_label": "Walidacja",
    }
    return labels.get(key, "Szczegół")


def _raw_preview_title(item: dict[str, Any], index: int) -> str:
    for key in (
        "title_label",
        "issue_type_label",
        "recommendation_type_label",
        "operation_type_label",
        "mode_label",
    ):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return f"Pozycja podglądu {index + 1}"


def _raw_preview_status(item: dict[str, Any]) -> str:
    for key in ("status_label", "validation_status_label", "readiness_label"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return ""
