"""A drifted delivery identity exposes one typed recovery step, never 'usable'."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_delivery_identity as identity_router
from tests.content.delivery_identity_fixtures import (
    ROW_DIGEST,
    WORK_ITEM_ID,
    classification_lookup,
    reconciled_binding,
)
from wilq.content.workflow.delivery_identity_recovery import (
    CLASSIFICATION_MISSING_SAFE_NEXT_STEP,
    CURRENT_SAFE_NEXT_STEP,
    DRIFT_SAFE_NEXT_STEP,
    build_content_delivery_identity_drift_recovery,
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
