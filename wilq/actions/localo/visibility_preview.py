from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
MetricRows = Callable[[dict[Any, Any], dict[Any, Any], list[str]], list[ActionPreviewRowViewModel]]
StateLabel = Callable[[Any], str]

LOCAL_VISIBILITY_METRIC_KEYS = [
    "localo_avg_visibility_current",
    "localo_avg_visibility_change",
    "localo_avg_latest_grid_position",
    "localo_tracked_keyword_count",
    "localo_active_place_count",
    "localo_avg_rating",
    "localo_reviews_count",
    "localo_review_reply_rate",
]


def local_visibility_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    metric_snapshot_rows: MetricRows,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render Localo visibility cards without exposing technical payloads."""
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        metric_snapshot = item.get("metric_snapshot")
        metric_snapshot = metric_snapshot if isinstance(metric_snapshot, dict) else {}
        metric_labels = item.get("metric_snapshot_labels")
        metric_labels = metric_labels if isinstance(metric_labels, dict) else {}
        rows = metric_snapshot_rows(metric_snapshot, metric_labels, LOCAL_VISIBILITY_METRIC_KEYS)
        allowed_labels = string_list(item.get("allowed_contract_labels"))
        if allowed_labels:
            rows.append(preview_row("Dozwolone odczyty", ", ".join(allowed_labels[:4])))
        missing_labels = string_list(item.get("missing_read_contract_labels"))
        if missing_labels:
            rows.append(preview_row("Braki", ", ".join(missing_labels[:4])))
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
                id=str(item.get("id") or f"localo_visibility_preview_{index}"),
                kind="localo_visibility_review",
                title_label="Widoczność lokalna do sprawdzenia",
                subtitle_label="ocena lokalna bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def metric_snapshot_preview_rows_for_keys(
    metric_snapshot: dict[Any, Any],
    metric_labels: dict[Any, Any],
    keys: list[str],
) -> list[ActionPreviewRowViewModel]:
    """Build Localo metric rows without exposing unlabelled payload fields."""
    rows: list[ActionPreviewRowViewModel] = []
    for key in keys:
        if key not in metric_snapshot:
            continue
        label = metric_labels.get(key)
        if not isinstance(label, str) or not label:
            continue
        rows.append(
            ActionPreviewRowViewModel(
                label=label,
                value=_metric_snapshot_value_label(key, metric_snapshot[key]),
            )
        )
    return rows


def _metric_snapshot_value_label(key: str, value: Any) -> str:
    percent_metric_keys = {
        "engagement_rate",
        "localo_avg_visibility_change",
        "localo_review_reply_rate",
    }
    if key in percent_metric_keys and isinstance(value, int | float):
        return f"{value * 100:.2f}%"
    if isinstance(value, bool):
        return "tak" if value else "nie"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, str) and value:
        return value
    return "wartość niepotwierdzona"
