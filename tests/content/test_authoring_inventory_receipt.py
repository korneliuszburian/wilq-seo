from __future__ import annotations

from datetime import UTC, datetime

import pytest

import wilq.content.workflow.authoring_inventory_receipt as receipt_module
from wilq.content.workflow.authoring_inventory_receipt import (
    _build_content_authoring_inventory_receipt_from_catalog,
    build_current_content_authoring_inventory_receipt,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
)


def _item(**updates: object) -> ContentInventoryCatalogItem:
    values: dict[str, object] = {
        "catalog_id": "content_inventory_bdo",
        "work_item_id": "content_work_item_inventory_bdo",
        "url": "https://www.ekologus.pl/bdo/",
        "path": "/bdo/",
        "title": "BDO",
        "content_type": "post",
        "content_summary": "Aktualny materiał BDO.",
        "content_word_count": 120,
        "section_count": 2,
        "acf_section_count": 1,
        "section_headings": ["Zakres"],
        "acf_field_names": ["service_sections"],
        "material_status": "content_and_structure",
        "acf_section_headings": ["Zakres"],
        "source_connector": "wordpress_ekologus",
        "evidence_id": "ev_wp_current",
        "collected_at": datetime(2026, 9, 13, 10, 0, tzinfo=UTC),
    }
    values.update(updates)
    return ContentInventoryCatalogItem.model_validate(values)


def _receipt(item: ContentInventoryCatalogItem):
    return _build_content_authoring_inventory_receipt_from_catalog(
        item=item,
        catalog=_catalog(item),
        recorded_by="current_inventory_reconciler",
        recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
    )


def _catalog(*items: ContentInventoryCatalogItem) -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        total_count=len(items),
        items=list(items),
        source_connectors=sorted({item.source_connector for item in items}),
        evidence_ids=sorted({item.evidence_id for item in items}),
    )


def test_receipt_binds_full_current_catalog_material_not_just_url_or_work_item() -> None:
    baseline = _receipt(_item())
    changed_material = _receipt(_item(section_headings=["Zmieniony zakres"]))
    changed_evidence = _receipt(_item(evidence_id="ev_wp_new"))

    assert baseline.status == "registered_current_inventory"
    assert baseline.generation_allowed is False
    assert baseline.delivery_identity_available is False
    assert baseline.source_pack_available is False
    assert baseline.inventory_complete is False
    assert baseline.catalog_item_digest != changed_material.catalog_item_digest
    assert baseline.receipt_digest != changed_material.receipt_digest
    assert baseline.catalog_item_digest != changed_evidence.catalog_item_digest
    assert baseline.receipt_digest != changed_evidence.receipt_digest


def test_catalog_snapshot_digest_ignores_derived_journal_but_tracks_source_scope() -> None:
    baseline = _catalog(_item())
    baseline_digest = receipt_module.content_inventory_catalog_snapshot_digest(baseline)
    with_derived_journal = baseline.model_copy(
        update={
            "journal_reconciliation": {"derived": "csv"},
            "journal_readiness": {"derived": "store"},
        }
    )

    assert (
        receipt_module.content_inventory_catalog_snapshot_digest(with_derived_journal)
        == baseline_digest
    )
    assert receipt_module.content_inventory_catalog_snapshot_digest(
        _catalog(
            _item(),
            _item(
                catalog_id="content_inventory_other",
                path="/other/",
                url="https://www.ekologus.pl/other/",
                work_item_id="content_work_item_other",
            ),
        )
    ) != baseline_digest
    assert receipt_module.content_inventory_catalog_snapshot_digest(
        baseline.model_copy(
            update={
                "coverage": ContentInventoryCoverage(
                    status="complete",
                    returned_count=1,
                    caveat="Coverage complete.",
                )
            }
        )
    ) != baseline_digest
    assert receipt_module.content_inventory_catalog_snapshot_digest(
        baseline.model_copy(update={"evidence_ids": ["ev_changed"]})
    ) != baseline_digest


def test_url_only_or_unscoped_evidence_cannot_register_current_inventory_receipt() -> None:
    with pytest.raises(ValueError):
        _receipt(_item(material_status="url_only", content_summary=None))

    with pytest.raises(ValueError):
        _build_content_authoring_inventory_receipt_from_catalog(
            item=_item(),
            catalog=ContentInventoryCatalogResponse(
                total_count=1,
                items=[_item()],
                source_connectors=["wordpress_ekologus"],
                evidence_ids=["ev_other"],
            ),
            recorded_by="current_inventory_reconciler",
            recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
        )


def test_receipt_rejects_item_outside_the_typed_current_catalog_snapshot() -> None:
    item = _item()

    with pytest.raises(ValueError, match="current catalog snapshot"):
        _build_content_authoring_inventory_receipt_from_catalog(
            item=item,
            catalog=_catalog(_item(url="https://www.ekologus.pl/other/", path="/other/")),
            recorded_by="current_inventory_reconciler",
            recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
        )


def test_public_factory_reads_one_exact_item_from_current_catalog(monkeypatch) -> None:
    item = _item()
    monkeypatch.setattr(
        receipt_module,
        "build_content_inventory_catalog_cached",
        lambda: _catalog(item),
    )

    receipt = build_current_content_authoring_inventory_receipt(
        canonical_path="/bdo",
        recorded_by="current_inventory_reconciler",
        recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
    )

    assert receipt.catalog_id == item.catalog_id
    with pytest.raises(ValueError, match="exact current catalog item"):
        build_current_content_authoring_inventory_receipt(
            canonical_path="/other",
            recorded_by="current_inventory_reconciler",
            recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
        )


def test_public_factory_accepts_the_canonical_root_path(monkeypatch) -> None:
    root = _item(url="https://www.ekologus.pl/", path="/")
    monkeypatch.setattr(
        receipt_module,
        "build_content_inventory_catalog_cached",
        lambda: _catalog(root),
    )

    receipt = build_current_content_authoring_inventory_receipt(
        canonical_path="/",
        recorded_by="current_inventory_reconciler",
        recorded_at=datetime(2026, 9, 13, 11, 0, tzinfo=UTC),
    )

    assert receipt.canonical_path == "/"
