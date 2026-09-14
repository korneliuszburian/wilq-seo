from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from wilq.content.workflow.authoring_inventory_receipt import (
    _build_content_authoring_inventory_receipt_from_catalog,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)


def _receipt(
    *,
    section_heading: str = "Zakres",
    evidence_id: str = "ev_wp_current",
    include_second_catalog_item: bool = False,
    recorded_by: str = "current_inventory_reconciler",
):
    item = ContentInventoryCatalogItem(
        catalog_id="content_inventory_bdo",
        work_item_id="content_work_item_inventory_bdo",
        url="https://www.ekologus.pl/bdo/",
        path="/bdo/",
        title="BDO",
        content_type="post",
        content_summary="Aktualny materiał BDO.",
        content_word_count=120,
        section_count=1,
        section_headings=[section_heading],
        material_status="content_and_structure",
        source_connector="wordpress_ekologus",
        evidence_id=evidence_id,
        collected_at=datetime(2026, 9, 13, 10, 0, tzinfo=UTC),
    )
    catalog_items = [item]
    if include_second_catalog_item:
        catalog_items.append(
            item.model_copy(
                update={
                    "catalog_id": "content_inventory_other",
                    "work_item_id": "content_work_item_inventory_other",
                    "url": "https://www.ekologus.pl/other/",
                    "path": "/other/",
                }
            )
        )
    return _build_content_authoring_inventory_receipt_from_catalog(
        item=item,
        catalog=ContentInventoryCatalogResponse(
            total_count=len(catalog_items),
            items=catalog_items,
            source_connectors=["wordpress_ekologus"],
            evidence_ids=[evidence_id],
        ),
        recorded_by=recorded_by,
        recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
    )


def test_store_is_append_only_idempotent_and_keeps_distinct_current_snapshots(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "inventory-receipts.sqlite3")
    baseline = _receipt()

    created = store.record_content_authoring_inventory_receipt(baseline)
    repeated = store.record_content_authoring_inventory_receipt(baseline)
    changed_snapshot = store.record_content_authoring_inventory_receipt(
        _receipt(section_heading="Zmieniony zakres", include_second_catalog_item=True)
    )

    assert created.status == "created"
    assert repeated.status == "idempotent"
    assert changed_snapshot.status == "created"
    assert changed_snapshot.receipt.receipt_digest != baseline.receipt_digest
    assert store.load_content_authoring_inventory_receipt(baseline.receipt_id) == baseline

    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE content_authoring_inventory_receipts SET catalog_id = 'other'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM content_authoring_inventory_receipts")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT OR REPLACE INTO content_authoring_inventory_receipts (
                  receipt_id, receipt_digest, catalog_id, current_work_item_id,
                  canonical_path, public_url, catalog_snapshot_digest, recorded_by,
                  recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    changed_snapshot.receipt.receipt_id,
                    changed_snapshot.receipt.receipt_digest,
                    baseline.catalog_id,
                    changed_snapshot.receipt.current_work_item_id,
                    changed_snapshot.receipt.canonical_path,
                    changed_snapshot.receipt.public_url,
                    baseline.catalog_snapshot_digest,
                    changed_snapshot.receipt.recorded_by,
                    changed_snapshot.receipt.recorded_at.isoformat(),
                    changed_snapshot.receipt.model_dump_json(),
                ),
            )


def test_store_conflicts_on_same_snapshot_with_different_receipt_payload(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "inventory-receipt-conflict.sqlite3")
    baseline = _receipt()
    different_payload = _receipt(recorded_by="different_inventory_writer")

    assert store.record_content_authoring_inventory_receipt(baseline).status == "created"
    result = store.record_content_authoring_inventory_receipt(different_payload)

    assert result.status == "conflict"
    assert result.receipt == baseline
