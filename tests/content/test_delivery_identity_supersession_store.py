"""The supersession receipt is an append-only, idempotent store record."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from tests.content.delivery_identity_fixtures import (
    WORK_ITEM_ID,
    classification_lookup,
    reconciled_binding,
)
from wilq.content.workflow.delivery_identity_recovery import (
    build_content_delivery_identity_drift_recovery,
    build_content_delivery_identity_supersession,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def _receipt():
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup(row_digest="f" * 64)
    )
    return build_content_delivery_identity_supersession(recovery, recorded_by="wilku")


def test_supersession_record_is_created_and_idempotent(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    receipt = _receipt()

    created = store.record_content_delivery_identity_supersession(receipt)
    assert created.status == "created"
    assert created.receipt.rebound_work_item_id == WORK_ITEM_ID

    again = store.record_content_delivery_identity_supersession(receipt)
    assert again.status == "idempotent"

    loaded = store.load_content_delivery_identity_supersession(receipt.receipt_id)
    assert loaded is not None and loaded.receipt_digest == receipt.receipt_digest

    tampered = receipt.model_copy(update={"recorded_by": "someone_else"})
    with pytest.raises(ValidationError):
        store.record_content_delivery_identity_supersession(tampered)


def test_supersession_rows_are_append_only(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    receipt = _receipt()
    store.record_content_delivery_identity_supersession(receipt)

    with store._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE content_delivery_identity_supersessions SET recorded_by = 'x'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM content_delivery_identity_supersessions")
