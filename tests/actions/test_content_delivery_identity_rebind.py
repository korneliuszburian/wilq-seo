"""The rebind adapter records the supersession and mints the rebound identity."""

from __future__ import annotations

from tests.content.delivery_identity_fixtures import (
    classification_lookup,
    reconciled_binding,
)
from wilq.actions.local_content_mutation_adapters import (
    execute_local_content_mutation_adapter,
)
from wilq.content.workflow.delivery_identity_recovery import (
    CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER,
    build_content_delivery_identity_drift_recovery,
    build_content_delivery_identity_rebind_action,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def _drifted_action():
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup(row_digest="f" * 64)
    )
    return build_content_delivery_identity_rebind_action(recovery, recorded_by="wilku")


def test_rebind_adapter_records_supersession_and_mints_the_identity(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    action = _drifted_action()

    result, blockers = execute_local_content_mutation_adapter(
        action,
        CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER,
        workflow_store=store,
        audit_store_factory=lambda: None,
    )

    assert blockers == []
    assert result is not None
    assert result["supersession_status"] == "created"
    assert result["rebound_binding_status"] == "created"
    assert result["external_write_attempted"] is False
    assert (
        store.load_content_delivery_identity_supersession(result["supersession_receipt_id"])
        is not None
    )

    again, again_blockers = execute_local_content_mutation_adapter(
        action,
        CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER,
        workflow_store=store,
        audit_store_factory=lambda: None,
    )
    assert again_blockers == []
    assert again is not None
    assert again["supersession_status"] == "idempotent"
    assert again["rebound_binding_status"] == "idempotent"


def test_blocked_rebind_action_never_applies(tmp_path) -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup()
    )
    action = build_content_delivery_identity_rebind_action(recovery, recorded_by="wilku")
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")

    result, blockers = execute_local_content_mutation_adapter(
        action,
        CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER,
        workflow_store=store,
        audit_store_factory=lambda: None,
    )

    assert result is None
    assert blockers
    assert store.load_content_delivery_identity_supersession(action.id) is None


def test_rebind_adapter_rejects_a_non_ready_action_without_writing(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    action = _drifted_action().model_copy(update={"status": "blocked"})

    result, blockers = execute_local_content_mutation_adapter(
        action,
        CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER,
        workflow_store=store,
        audit_store_factory=lambda: None,
    )

    assert result is None
    assert blockers == ["Delivery identity rebind action is not a ready local authority action."]
    assert store.load_content_delivery_identity_supersession(action.id) is None
