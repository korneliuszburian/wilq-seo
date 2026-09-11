"""Staleness preview for classified refresh preparation."""

from __future__ import annotations

from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationStale,
)
from wilq.content.workflow.refresh_preparation_models import RefreshClassificationContext
from wilq.content.workflow.refresh_preparation_resolution import blocker


def stale_preview(
    work_item_id: str,
    classified: RefreshClassificationContext,
) -> ContentRefreshPreparationStale | None:
    if not classified.run.freshness.requires_refresh:
        return None
    item = blocker(
        "stale_production_classification",
        "Klasyfikacja produkcyjna wymaga odświeżenia",
        "Najświeższa zaakceptowana klasyfikacja wskazuje konieczność odświeżenia źródeł.",
        "Odśwież klasyfikację z aktualnych źródeł, a następnie ponów przygotowanie.",
        source_codes=list(classified.run.freshness.connector_ids),
    )
    return ContentRefreshPreparationStale(
        status="stale",
        work_item_id=work_item_id,
        classification=classified.binding,
        blockers=[item],
        safe_next_step=item.next_step,
    )


__all__ = ["stale_preview"]
