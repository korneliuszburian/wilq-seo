from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_delivery_identity as route_module
import wilq.content.workflow.decisions.production as production_module
from apps.api.wilq_api.main import app
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_exact_delivery_identity_record_and_read_routes(monkeypatch, tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app)

    created = store.record_content_delivery_identity(
        _command(retained=True, retained_work_item_id=None, retained_usage=None)
    )
    payload = created.model_dump(mode="json")
    assert payload["binding"]["status"] == "exact_current"
    assert payload["delivery_record"]["robot_ready"] is False
    assert payload["current"]["recorded_status"] == "exact_current"
    assert payload["current"]["current_status"] == "exact_current"

    readback = client.get(f"/api/content/delivery-identities/{payload['binding']['binding_id']}")
    assert readback.status_code == 200
    assert readback.json()["binding"] == payload["binding"]

    missing = client.get("/api/content/delivery-identities/content_delivery_identity_missing")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "content_delivery_identity_not_found"}


def test_delivery_identity_get_projects_newer_classification_as_current_blocked(
    monkeypatch, tmp_path: Path
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    recorded_run = exact_public_bdo_run()
    store.record_production_classification(recorded_run)
    created = store.record_content_delivery_identity(
        _command(retained=True, run=recorded_run, retained_work_item_id=None, retained_usage=None)
    )
    newer_packet_sha = "a" * 64
    newer_run = production_module._build_run(
        input_receipt=recorded_run.input.model_copy(
            update={"packet_sha256": newer_packet_sha}
        ),
        counts=recorded_run.counts,
        freshness=recorded_run.freshness,
        source_receipts=recorded_run.source_receipts,
        judge_receipt=recorded_run.judge_receipt.model_copy(
            update={"reviewed_packet_sha256": newer_packet_sha}
        ),
        rows=recorded_run.rows,
        audit=recorded_run.audit.model_copy(
            update={"recorded_at": datetime(2026, 9, 1, 10, 5, tzinfo=UTC)}
        ),
    )
    store.record_production_classification(newer_run)
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)

    response = TestClient(app).get(
        f"/api/content/delivery-identities/{created.binding.binding_id}"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["binding"]["status"] == "exact_current"
    assert payload["current"]["current_status"] == "blocked"
    assert payload["current"]["current_blocker"]["reason"] == (
        "identity_classification_drift"
    )
