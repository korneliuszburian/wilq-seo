from __future__ import annotations

from fastapi import HTTPException

from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics_cached,
    build_content_freshness_assessment_fast,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.decisions.inventory_binding import (
    inventory_decision_for_work_item,
)
from wilq.content.workflow.workspace.document_workspace import (
    content_work_item_has_persisted_material,
)


def selected_workspace_snapshot_for_work_item_or_404(
    work_item_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Build a vendor-free selected projection without entering the planning cache."""

    diagnostics = build_content_diagnostics_cached()
    decision_id = work_item_id.removeprefix("content_work_item_")
    persisted = next(
        (item for item in diagnostics.decision_queue if item.id == decision_id),
        None,
    )
    metadata = inventory_decision_for_work_item(
        work_item_id,
        read_material=False,
        include_all_metric_facts=True,
    )
    selected = persisted if persisted is not None else metadata
    if selected is None:
        raise HTTPException(
            status_code=404,
            detail="Wybrany element pracy nad treścią nie jest dostępny w tym obszarze roboczym.",
        )
    has_persisted_material = content_work_item_has_persisted_material(selected)
    selected = selected.model_copy(
        update={
            "wordpress_content_inventory_status": (
                "available" if has_persisted_material else "missing"
            ),
            "wordpress_content_inventory_note": (
                "Materiał pochodzi z zapisanego snapshotu; ten odczyt nie potwierdza, "
                "że odpowiada on aktualnej treści w WordPressie."
                if has_persisted_material
                else "Bieżący snapshot nie zawiera materiału strony; aktualna treść "
                "w WordPressie nie została w tym odczycie sprawdzona."
            ),
        }
    )
    return snapshot_for_work_item_or_404(
        work_item_id,
        selected_decision_override=selected,
        selected_freshness_override=build_content_freshness_assessment_fast(
            relevant_connector_ids=selected.source_connectors,
        ),
        resolve_planning_proposal=False,
    )


__all__ = ["selected_workspace_snapshot_for_work_item_or_404"]
