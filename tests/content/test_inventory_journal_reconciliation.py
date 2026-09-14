from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from wilq.content.workflow.workspace.catalog import ContentInventoryCatalogItem
from wilq.content.workflow.workspace.journal_reconciliation import (
    build_content_inventory_journal_reconciliation,
)


def test_reconciliation_counts_only_exact_normalized_paths_and_never_mints_bindings(
    tmp_path,
) -> None:
    journal = tmp_path / "content-status.csv"
    with journal.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "content_kind"])
        writer.writeheader()
        writer.writerows(
            [
                {"path": "/matched", "content_kind": "editorial"},
                {"path": "/service-missing", "content_kind": "service"},
            ]
        )

    reconciliation = build_content_inventory_journal_reconciliation(
        [_catalog_item("/matched/")],
        authoring_source_paths=["https://ekologus.dev.proudsite.pl/service-missing/"],
        journal_path=journal,
    )

    assert reconciliation.status == "incomplete"
    assert reconciliation.journal_record_count == 2
    assert reconciliation.matched_catalog_count == 1
    assert reconciliation.missing_inventory_binding_count == 1
    assert reconciliation.catalog_outside_journal_count == 0
    assert reconciliation.matched_authoring_source_count == 1
    assert reconciliation.missing_authoring_source_count == 1
    assert reconciliation.missing_inventory_by_content_kind == {"service": 1}
    assert "work_item_id" not in reconciliation.model_dump()


def test_reconciliation_does_not_claim_complete_for_partial_canonical_journal(
    tmp_path,
) -> None:
    journal = tmp_path / "content-status.csv"
    with journal.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "content_kind"])
        writer.writeheader()
        writer.writerow({"path": "/matched", "content_kind": "editorial"})

    reconciliation = build_content_inventory_journal_reconciliation(
        [_catalog_item("/matched/")],
        journal_path=journal,
    )

    assert reconciliation.status == "incomplete"
    assert reconciliation.journal_record_count == 1
    assert "214" in reconciliation.caveat
    assert "214" in reconciliation.safe_next_step


def test_reconciliation_rejects_same_count_substituted_path(
    tmp_path: Path,
) -> None:
    canonical_path = Path(__file__).resolve().parents[2] / "docs" / "content-status-214.csv"
    with canonical_path.open(encoding="utf-8", newline="") as handle:
        canonical_paths = [row["path"] for row in csv.DictReader(handle)]
    substituted_paths = ["/substituted-path", *canonical_paths[1:]]
    journal = tmp_path / "same-count-substituted.csv"
    with journal.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "content_kind"])
        writer.writeheader()
        writer.writerows(
            {"path": path, "content_kind": "editorial"} for path in substituted_paths
        )

    reconciliation = build_content_inventory_journal_reconciliation(
        [_catalog_item(path) for path in substituted_paths],
        journal_path=journal,
    )

    assert reconciliation.journal_record_count == 214
    assert reconciliation.matched_catalog_count == 214
    assert reconciliation.missing_inventory_binding_count == 0
    assert reconciliation.status == "incomplete"
    assert "dokładnie" in reconciliation.caveat


def _catalog_item(path: str) -> ContentInventoryCatalogItem:
    return ContentInventoryCatalogItem(
        catalog_id="content_inventory_test",
        work_item_id="content_work_item_test",
        url=f"https://www.ekologus.pl{path}",
        path=path,
        content_type="post",
        material_status="content_summary",
        source_connector="wordpress_ekologus",
        evidence_id="ev_inventory_test",
        collected_at=datetime(2026, 9, 12, tzinfo=UTC),
    )
