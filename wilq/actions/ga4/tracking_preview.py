from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
MetricRows = Callable[[dict[Any, Any], dict[Any, Any]], list[ActionPreviewRowViewModel]]
StateLabel = Callable[[Any], str]


def ga4_tracking_quality_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    metric_snapshot_rows: MetricRows,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render GA4 tracking-quality cards without exposing raw payloads."""
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        metric_snapshot = item.get("metric_snapshot")
        metric_snapshot = metric_snapshot if isinstance(metric_snapshot, dict) else {}
        metric_labels = item.get("metric_snapshot_labels")
        metric_labels = metric_labels if isinstance(metric_labels, dict) else {}
        rows = [
            preview_row(
                "Strona wejścia",
                str(
                    item.get("landing_page_label")
                    or item.get("landing_page")
                    or "strona wejścia niepotwierdzona"
                ),
            ),
            preview_row(
                "Źródło",
                str(
                    item.get("source_medium_label")
                    or item.get("source_medium")
                    or "źródło ruchu niepotwierdzone"
                ),
            ),
            preview_row(
                "Kampania",
                str(
                    item.get("campaign_name_label")
                    or item.get("campaign_name")
                    or "kampania niepotwierdzona"
                ),
            ),
        ]
        rows.extend(metric_snapshot_rows(metric_snapshot, metric_labels))
        tracking_gap_labels = string_list(item.get("tracking_dimension_gap_labels"))
        if tracking_gap_labels:
            rows.append(preview_row("Braki wymiarów", ", ".join(tracking_gap_labels[:4])))
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
                id=str(item.get("id") or f"ga4_tracking_quality_preview_{index}"),
                kind="ga4_tracking_quality_review",
                title_label="Jakość pomiaru GA4 do sprawdzenia",
                subtitle_label=str(
                    item.get("operation_type_label") or "ocena pomiaru bez zapisu zmian"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards
