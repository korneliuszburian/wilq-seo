"""A drifted delivery identity exposes one typed recovery step, never 'usable'."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_delivery_identity as identity_router
from tests.content.delivery_identity_fixtures import (
    ROW_DIGEST,
    WORK_ITEM_ID,
    classification_lookup,
    reconciled_binding,
)
from wilq.content.workflow.delivery_identity import (
    build_content_delivery_identity_current_projection,
)
from wilq.content.workflow.delivery_identity_recovery import (
    CLASSIFICATION_MISSING_SAFE_NEXT_STEP,
    CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE,
    CURRENT_SAFE_NEXT_STEP,
    DRIFT_SAFE_NEXT_STEP,
    REBIND_BLOCKER_CODE,
    build_content_delivery_identity_drift_recovery,
    build_content_delivery_identity_rebind_action,
    build_content_delivery_identity_rebind_command,
    build_content_delivery_identity_supersession,
    delivery_identity_rebind_action_id,
)


def test_current_binding_reports_no_recovery_step() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup()
    )

    assert recovery.status == "current"
    assert recovery.current_classification_run_id is None
    assert recovery.safe_next_step == CURRENT_SAFE_NEXT_STEP


def test_superseded_classification_reports_drift_with_the_exact_current_row() -> None:
    binding = reconciled_binding()
    lookup = classification_lookup(
        row_digest="f" * 64,
        run_id="content_production_classification_new",
        run_digest="9" * 64,
    )

    recovery = build_content_delivery_identity_drift_recovery(binding, lookup)

    assert recovery.status == "drift"
    assert recovery.current_work_item_id == WORK_ITEM_ID
    assert recovery.current_classification_run_id == "content_production_classification_new"
    assert recovery.current_classification_run_digest == "9" * 64
    assert recovery.current_classification_source_row_digest == "f" * 64
    assert recovery.binding_classification_source_row_digest == ROW_DIGEST
    assert recovery.safe_next_step == DRIFT_SAFE_NEXT_STEP


def test_missing_classification_keeps_the_binding_unusable_without_a_row() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup(row_status="missing")
    )

    assert recovery.status == "classification_missing"
    assert recovery.current_classification_run_id is None
    assert recovery.safe_next_step == CLASSIFICATION_MISSING_SAFE_NEXT_STEP


def test_route_exposes_the_typed_recovery_and_404_for_an_unknown_binding(monkeypatch) -> None:
    binding = reconciled_binding()

    class _Store:
        def load_content_delivery_identity_record(self, binding_id: str):
            if binding_id != binding.binding_id:
                return None
            return SimpleNamespace(binding=binding)

        def load_content_delivery_classification_lookup(self, _binding):
            return classification_lookup(row_digest="f" * 64)

    monkeypatch.setattr(identity_router, "content_workflow_store", _Store)
    app = FastAPI()
    identity_router.register_content_delivery_identity_routes(app.router)

    found = TestClient(app).get(
        f"/api/content/delivery-identities/{binding.binding_id}/drift-recovery"
    )
    assert found.status_code == 200
    assert found.json()["status"] == "drift"
    assert found.json()["current_classification_source_row_digest"] == "f" * 64

    missing = TestClient(app).get(
        "/api/content/delivery-identities/content_delivery_identity_absent/drift-recovery"
    )
    assert missing.status_code == 404


def test_stale_freshness_cannot_report_a_binding_as_current() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(),
        classification_lookup(freshness_state="stale", requires_refresh=True),
    )

    assert recovery.status == "drift"
    assert recovery.current_work_item_id == WORK_ITEM_ID
    assert recovery.safe_next_step == DRIFT_SAFE_NEXT_STEP


def test_supersession_requires_a_drifted_identity() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup(row_digest="f" * 64)
    )
    receipt = build_content_delivery_identity_supersession(
        recovery, recorded_by="wilku"
    )

    assert receipt.superseded_binding_id == recovery.binding_id
    assert receipt.superseded_binding_digest == recovery.superseded_binding_digest
    assert receipt.rebound_work_item_id == WORK_ITEM_ID
    assert receipt.rebound_classification_source_row_digest == "f" * 64
    assert receipt.receipt_id.startswith("content_delivery_identity_supersession_")

    for blocked in (
        build_content_delivery_identity_drift_recovery(
            reconciled_binding(), classification_lookup()
        ),
        build_content_delivery_identity_drift_recovery(
            reconciled_binding(), classification_lookup(row_status="missing")
        ),
    ):
        with pytest.raises(ValueError, match="Only a drifted delivery identity"):
            build_content_delivery_identity_supersession(blocked, recorded_by="wilku")


def test_rebind_command_matches_the_recovered_row() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(),
        classification_lookup(
            row_digest="f" * 64,
            run_id="content_production_classification_new",
            run_digest="9" * 64,
        ),
    )
    command = build_content_delivery_identity_rebind_command(
        recovery, recorded_by="wilku"
    )

    assert command.canonical_path == recovery.current_canonical_path
    assert command.public_url == recovery.current_public_url
    assert command.current_work_item_id == WORK_ITEM_ID
    assert command.classification_run_id == "content_production_classification_new"
    assert command.classification_decision_set_digest == "b" * 64
    assert command.classification_source_row_digest == "f" * 64
    assert command.inventory_evidence_ids == ("ev_current",)

    for blocked in (
        build_content_delivery_identity_drift_recovery(
            reconciled_binding(), classification_lookup()
        ),
        build_content_delivery_identity_drift_recovery(
            reconciled_binding(), classification_lookup(row_status="missing")
        ),
    ):
        with pytest.raises(ValueError, match="Only a drifted delivery identity"):
            build_content_delivery_identity_rebind_command(blocked, recorded_by="wilku")


def test_rebind_action_is_ready_with_receipt_and_command_payload() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup(row_digest="f" * 64)
    )
    action = build_content_delivery_identity_rebind_action(recovery, recorded_by="wilku")

    assert action.status == "ready_to_apply"
    assert action.id == delivery_identity_rebind_action_id(
        action.payload["supersession"]["receipt_digest"]
    )
    assert action.payload["action_type"] == CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE
    assert action.payload["local_authority_only"] is True
    assert action.payload["rebind_command"]["classification_source_row_digest"] == "f" * 64
    assert action.evidence_ids == ["ev_current"]


def test_rebind_action_is_blocked_for_a_non_drifted_identity() -> None:
    recovery = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup()
    )
    action = build_content_delivery_identity_rebind_action(recovery, recorded_by="wilku")

    assert action.status == "blocked"
    assert action.payload["blocker_code"] == REBIND_BLOCKER_CODE
    assert action.payload["safe_next_step"] == recovery.safe_next_step
    assert "supersession" not in action.payload


def test_rebind_action_readiness_markers_follow_the_status() -> None:
    drifted = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup(row_digest="f" * 64)
    )
    ready = build_content_delivery_identity_rebind_action(drifted, recorded_by="wilku")
    assert ready.payload["apply_allowed"] is True
    assert ready.payload["api_mutation_ready"] is True
    assert ready.payload["preview_contract"] == "content_delivery_identity_rebind_v1"
    assert all(
        item["apply_allowed"] is True and item["api_mutation_ready"] is True
        for item in ready.payload["payload_preview"]
    )

    current = build_content_delivery_identity_drift_recovery(
        reconciled_binding(), classification_lookup()
    )
    blocked = build_content_delivery_identity_rebind_action(current, recorded_by="wilku")
    assert blocked.payload["apply_allowed"] is False
    assert blocked.payload["api_mutation_ready"] is False


def test_superseded_binding_can_never_render_as_usable() -> None:
    binding = reconciled_binding()
    lookup = classification_lookup()
    assert (
        build_content_delivery_identity_current_projection(
            binding, lookup, assessed_at=datetime(2026, 9, 27, tzinfo=UTC)
        ).current_status
        == "exact_current"
    )

    superseded = build_content_delivery_identity_current_projection(
        binding, lookup, assessed_at=datetime(2026, 9, 27, tzinfo=UTC), superseded=True
    )
    assert superseded.current_status == "blocked"
    assert superseded.current_blocker is not None
    assert superseded.current_blocker.reason == "identity_superseded"
    assert superseded.current_safe_next_step == superseded.current_blocker.next_step
