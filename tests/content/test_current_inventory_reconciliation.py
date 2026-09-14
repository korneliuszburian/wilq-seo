from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import wilq.content.workflow.current_inventory_reconciliation as reconciliation_module
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
)
from wilq.schemas import ConnectorCoveredWindow, ContentFreshnessAssessment


def test_reconcile_persists_only_material_keep_receipts_and_a_blocked_run(
    monkeypatch, tmp_path: Path
) -> None:
    checked_at = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    catalog = ContentInventoryCatalogResponse(
        total_count=2,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_bdo",
                work_item_id="content_work_item_inventory_bdo",
                url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                path="/bdo-co-musi-wiedziec-przedsiebiorca/",
                content_type="post",
                content_summary="Materiał BDO.",
                section_headings=["Zakres"],
                material_status="content_and_structure",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_current",
                collected_at=checked_at,
            ),
            ContentInventoryCatalogItem(
                catalog_id="catalog_url_only",
                work_item_id="content_work_item_inventory_url_only",
                url="https://www.ekologus.pl/nieistniejaca-pozycja/",
                path="/nieistniejaca-pozycja/",
                content_type="post",
                material_status="url_only",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_current",
                collected_at=checked_at,
            ),
        ],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_current"],
        coverage=ContentInventoryCoverage(status="unknown", caveat="partial"),
    )
    freshness = ContentFreshnessAssessment(
        state="fresh",
        checked_at=checked_at,
        requires_refresh=False,
        connector_covered_windows={
            "google_search_console": ConnectorCoveredWindow(),
            "wordpress_ekologus": ConnectorCoveredWindow(),
        },
        summary="fresh",
        next_step="continue",
    )
    store = ContentWorkflowStore(tmp_path / "reconciliation.sqlite3")
    monkeypatch.setattr(reconciliation_module, "build_content_inventory_catalog", lambda: catalog)
    fresh_again = freshness.model_copy(
        update={"checked_at": datetime(2026, 9, 13, 12, 5, tzinfo=UTC)}
    )
    freshness_reads = iter((freshness, fresh_again))
    monkeypatch.setattr(
        reconciliation_module,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: next(freshness_reads),
    )
    monkeypatch.setattr(reconciliation_module, "content_workflow_store", lambda: store)

    first = reconciliation_module.reconcile_current_authoring_inventory()
    repeated = reconciliation_module.reconcile_current_authoring_inventory()

    assert first.classification.status == "created"
    assert first.registered_inventory_count == 1
    assert first.missing_inventory_count == 56
    assert first.classification.run.counts.generation_allowed == 0
    bdo = next(
        row
        for row in first.classification.run.rows
        if row.canonical_path == "/bdo-co-musi-wiedziec-przedsiebiorca"
    )
    assert bdo.decision == "blocked"
    assert bdo.current_work_item_id == "content_work_item_inventory_bdo"
    assert bdo.source_receipt.binding_state == "registered_current_inventory"
    assert repeated.classification.status == "idempotent"
    assert repeated.receipt_status_counts == {"created": 0, "idempotent": 1, "conflict": 0}
