from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
MoneyLabel = Callable[..., str]
StateLabel = Callable[[Any], str]


def budget_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    micros_money_label: MoneyLabel,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render marketer-facing Google Ads budget cards without exposing IDs."""
    preview_items = [
        item for item in payload.get("budget_payload_preview", []) if isinstance(item, dict)
    ]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        safety_review_value = item.get("safety_review")
        safety_review = safety_review_value if isinstance(safety_review_value, dict) else {}
        rows = [
            preview_row("Kampania", str(item.get("campaign_name") or "kampania do sprawdzenia")),
            preview_row(
                "Budżet",
                str(item.get("campaign_budget_name") or "budżet kampanii do sprawdzenia"),
            ),
            preview_row(
                "Obecny budżet",
                micros_money_label(item.get("current_budget_amount_micros")),
            ),
            preview_row(
                "Propozycja",
                micros_money_label(
                    item.get("proposed_budget_amount_micros"),
                    missing_label=(
                        "brak proponowanej kwoty; WILQ pokazuje tylko obecny "
                        "budżet i blokuje zapis"
                    ),
                ),
            ),
            preview_row(
                "Bezpieczeństwo",
                str(safety_review.get("status_label") or "wymaga sprawdzenia"),
            ),
        ]
        missing_requirement_labels = string_list(safety_review.get("missing_requirement_labels"))
        if missing_requirement_labels:
            rows.append(preview_row("Braki", ", ".join(missing_requirement_labels[:4])))
        requirement_labels = string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
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
                id=f"ads_budget_preview_{index}",
                kind="google_ads_budget_review",
                title_label="Budżet kampanii do sprawdzenia",
                subtitle_label=str(
                    item.get("operation_type_label") or "ocena budżetu bez zapisu zmian"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards
