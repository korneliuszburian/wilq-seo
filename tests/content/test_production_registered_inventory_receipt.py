from __future__ import annotations

from datetime import UTC, datetime

import pytest

from wilq.content.workflow.decisions.production import (
    ContentProductionRegisteredInventoryReceipt,
)


def test_registered_inventory_receipt_rejects_a_forged_digest() -> None:
    with pytest.raises(ValueError, match="self-authenticating"):
        ContentProductionRegisteredInventoryReceipt(
            binding_state="registered_current_inventory",
            schema_version="wilq_content_authoring_inventory_receipt_v1",
            receipt_id="content_authoring_inventory_forged",
            receipt_digest="0" * 64,
            catalog_id="content_inventory_bdo",
            current_work_item_id="content_work_item_inventory_bdo",
            public_url="https://www.ekologus.pl/bdo/",
            canonical_path="/bdo",
            source_connector="wordpress_ekologus",
            collected_at=datetime(2026, 9, 13, 10, 0, tzinfo=UTC).isoformat(),
            catalog_item_digest="a" * 64,
            catalog_snapshot_digest="b" * 64,
            evidence_id="ev_wp_current",
            catalog_snapshot_evidence_ids=("ev_wp_current",),
            inventory_complete=False,
            generation_allowed=False,
            delivery_identity_available=False,
            source_pack_available=False,
            missing_sources=("delivery_identity_binding", "source_pack_binding"),
        )
