from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]
ChannelLabel = Callable[[str], str]


def demand_gen_readiness_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    channel_label: ChannelLabel,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render Demand Gen readiness cards without exposing vendor payloads."""
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        channel_counts = item.get("campaign_channel_counts")
        channel_counts = channel_counts if isinstance(channel_counts, dict) else {}
        channel_summary = ", ".join(
            f"{channel_label(str(channel))}: {value}"
            for channel, value in sorted(channel_counts.items())
        )
        rows = [
            preview_row("Kampanie ocenione", str(item.get("campaign_rows_evaluated") or 0)),
            preview_row("Kanały kampanii", channel_summary or "brak kanałów"),
            preview_row(
                "Kampanie Demand Gen",
                str(item.get("demand_gen_campaign_row_count") or 0),
            ),
            preview_row(
                "Grupy reklam Demand Gen",
                str(item.get("demand_gen_ad_group_ad_row_count") or 0),
            ),
            preview_row(
                "Kreacje i zasoby",
                str(item.get("demand_gen_creative_asset_row_count") or 0),
            ),
            preview_row(
                "Odczyty jakości stron wejścia",
                str(item.get("demand_gen_landing_quality_row_count") or 0),
            ),
        ]
        missing_read_contract_labels = string_list(item.get("missing_read_contract_labels"))
        if missing_read_contract_labels:
            rows.append(preview_row("Braki", ", ".join(missing_read_contract_labels[:4])))
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
                id=f"demand_gen_readiness_preview_{index}",
                kind="google_ads_demand_gen_readiness_review",
                title_label="Gotowość Demand Gen do sprawdzenia",
                subtitle_label="ocena gotowości bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards
