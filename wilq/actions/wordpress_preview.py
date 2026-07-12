from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
Label = Callable[[Any], str]
PrimaryUrl = Callable[[dict[str, Any]], str]


def wordpress_draft_payload_preview_card(
    item: dict[str, Any],
    index: int,
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: Label,
    system_readiness_label: Label,
    content_primary_url_label: PrimaryUrl,
) -> ActionPreviewCardViewModel:
    draft_payload_value = item.get("draft_payload")
    draft_payload = draft_payload_value if isinstance(draft_payload_value, dict) else {}
    rows = [
        preview_row("Temat", str(item.get("topic") or "treść do sprawdzenia")),
        preview_row("Status wpisu", str(item.get("post_status_label") or "szkic")),
        preview_row(
            "Tytuł szkicu",
            str(draft_payload.get("post_title") or "tytuł do sprawdzenia"),
        ),
        preview_row("URL publiczny", content_primary_url_label(item)),
    ]
    for label, key in (
        ("Kontrole treści", "content_gate_status_summary"),
        ("Co blokuje szkic", "draft_blocker_labels"),
        ("Warunki szkicu", "draft_generation_summary"),
        ("Gotowość po sprawdzeniu", "draft_readiness_review_summary"),
        ("Szkic WordPress", "wordpress_draft_handoff_summary"),
        ("Pomiar po publikacji", "post_publication_measurement_summary"),
        ("Warunki sprawdzenia", "required_validation_labels"),
    ):
        values = string_list(item.get(key))
        if values:
            rows.append(preview_row(label, ", ".join(values[:3])))
    blocked_claims = string_list(item.get("blocked_claim_labels"))
    if blocked_claims:
        rows.append(preview_row("Czego nie wolno twierdzić", ", ".join(blocked_claims[:4])))
    return ActionPreviewCardViewModel(
        id=f"wordpress_draft_payload_preview_{index}",
        kind="wordpress_draft_payload_review",
        title_label="Szkic WordPress do sprawdzenia",
        subtitle_label="szkic bez publikacji",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=apply_state_label(item.get("apply_allowed")),
        system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
    )


def wordpress_draft_handoff_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: Label,
    system_readiness_label: Label,
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        rows = [
            preview_row("Temat", str(item.get("topic") or "treść do sprawdzenia")),
            preview_row(
                "URL publiczny",
                str(
                    item.get("source_public_url")
                    or item.get("final_canonical_url")
                    or "URL publiczny niepotwierdzony"
                ),
            ),
            preview_row(
                "URL kanoniczny",
                str(item.get("final_canonical_url") or "URL kanoniczny niepotwierdzony"),
            ),
        ]
        preview_url = item.get("preview_url")
        if isinstance(preview_url, str) and preview_url:
            rows.append(preview_row("Podgląd projektu", preview_url))
        rows.extend(
            [
                preview_row(
                    "Kontrola URL-a",
                    str(item.get("canonical_gate_status_label") or "wymaga sprawdzenia"),
                ),
                preview_row(
                    "Duplikaty",
                    str(item.get("duplicate_gate_status_label") or "wymaga sprawdzenia"),
                ),
                preview_row(
                    "Następny krok",
                    str(item.get("required_next_action_label") or "sprawdzenie szkicu"),
                ),
            ]
        )
        handoff_summary = string_list(item.get("wordpress_draft_handoff_summary"))
        if handoff_summary:
            rows.append(preview_row("Szkic WordPress", ", ".join(handoff_summary[:3])))
        measurement_summary = string_list(item.get("post_publication_measurement_summary"))
        if measurement_summary:
            rows.append(preview_row("Pomiar po publikacji", ", ".join(measurement_summary[:3])))
        validation_labels = string_list(item.get("required_validation_labels"))
        if validation_labels:
            rows.append(preview_row("Warunki sprawdzenia", ", ".join(validation_labels[:4])))
        blocked_claim_labels = string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=f"wordpress_draft_handoff_{index}",
                kind="wordpress_draft_handoff_review",
                title_label="Szkic WordPress do sprawdzenia",
                subtitle_label="podgląd bez zapisu i bez publikacji",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards
