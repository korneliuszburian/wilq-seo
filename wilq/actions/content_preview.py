from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel


def content_refresh_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: Callable[[str, str], ActionPreviewRowViewModel],
    string_list: Callable[[Any], list[str]],
    apply_state_label: Callable[[Any], str],
    system_readiness_label: Callable[[Any], str],
    wordpress_draft_preview_card: Callable[..., ActionPreviewCardViewModel],
) -> list[ActionPreviewCardViewModel]:
    content_items = [
        item for item in payload.get("content_brief_preview", []) if isinstance(item, dict)
    ]
    draft_items = [
        item
        for item in payload.get("wordpress_draft_payload_preview", [])
        if isinstance(item, dict)
    ]
    cards = [
        content_brief_preview_card(
            item,
            index,
            preview_row=preview_row,
            string_list=string_list,
            apply_state_label=apply_state_label,
            system_readiness_label=system_readiness_label,
        )
        for index, item in enumerate(content_items[:3])
    ]
    cards.extend(
        wordpress_draft_preview_card(
            item,
            index,
            preview_row=preview_row,
            string_list=string_list,
            apply_state_label=apply_state_label,
            system_readiness_label=system_readiness_label,
            content_primary_url_label=content_primary_url_label,
        )
        for index, item in enumerate(draft_items[:1])
    )
    return cards


def content_brief_preview_card(
    item: dict[str, Any],
    index: int,
    *,
    preview_row: Callable[[str, str], ActionPreviewRowViewModel],
    string_list: Callable[[Any], list[str]],
    apply_state_label: Callable[[Any], str],
    system_readiness_label: Callable[[Any], str],
) -> ActionPreviewCardViewModel:
    rows = [
        preview_row("Temat", str(item.get("topic") or "treść do sprawdzenia")),
        preview_row("Tryb", str(item.get("mode_label") or "wymaga sprawdzenia")),
        preview_row("URL publiczny", _content_primary_url_label(item)),
    ]
    decision_options = string_list(item.get("decision_option_labels"))
    if decision_options:
        rows.append(preview_row("Opcje", ", ".join(decision_options[:4])))
    brief_goal = item.get("brief_goal")
    if isinstance(brief_goal, str) and brief_goal:
        rows.append(preview_row("Cel planu treści", brief_goal))
    content_angle = item.get("content_angle")
    if isinstance(content_angle, str) and content_angle:
        rows.append(preview_row("Kąt treści", content_angle))
    h1_direction = item.get("h1_direction")
    if isinstance(h1_direction, str) and h1_direction:
        rows.append(preview_row("H1", h1_direction))
    cta_direction = item.get("cta_direction")
    if isinstance(cta_direction, str) and cta_direction:
        rows.append(preview_row("CTA", cta_direction))
    metric_summary = _content_metric_snapshot_label(item.get("metric_snapshot"))
    if metric_summary:
        rows.append(preview_row("Metryki", metric_summary))
    missing_evidence = string_list(item.get("missing_evidence"))
    if missing_evidence:
        rows.append(preview_row("Brakujące dowody", ", ".join(missing_evidence[:3])))
    publication_blockers = string_list(item.get("publication_blocker_labels"))
    if publication_blockers:
        rows.append(preview_row("Blokady publikacji", ", ".join(publication_blockers[:4])))
    validation_labels = string_list(item.get("required_validation_labels"))
    if validation_labels:
        rows.append(preview_row("Warunki sprawdzenia", ", ".join(validation_labels[:4])))
    return ActionPreviewCardViewModel(
        id=f"content_brief_preview_{index}",
        kind="content_brief_review",
        title_label="Plan treści do sprawdzenia",
        subtitle_label="brief bez pisania i bez publikacji",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=apply_state_label(item.get("apply_allowed")),
        system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
    )


def content_primary_url_label(item: dict[str, Any]) -> str:
    return _content_primary_url_label(item)


def _content_primary_url_label(item: dict[str, Any]) -> str:
    for key in ("final_canonical_url", "intended_final_url", "source_public_url"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return "URL niepotwierdzony"


def _content_metric_snapshot_label(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    parts: list[str] = []
    for key, label in (
        ("clicks", "kliknięcia"),
        ("impressions", "wyświetlenia"),
        ("ctr", "CTR"),
        ("average_position", "pozycja"),
    ):
        metric_value = value.get(key)
        if not isinstance(metric_value, int | float):
            continue
        formatted = _content_metric_value_label(metric_value)
        if key == "ctr":
            formatted = f"{metric_value * 100:.2f}%"
        parts.append(f"{label}: {formatted}")
    return "; ".join(parts)


def _content_metric_value_label(value: int | float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
