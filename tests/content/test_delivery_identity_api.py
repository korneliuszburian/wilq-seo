from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_delivery_identity as route_module
from apps.api.wilq_api.main import app
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_exact_delivery_identity_record_and_read_routes(monkeypatch, tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app)

    created = client.post(
        "/api/content/delivery-identities",
        json=_command(retained=False).model_dump(mode="json"),
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["binding"]["status"] == "exact_current"
    assert payload["delivery_record"]["robot_ready"] is False

    readback = client.get(f"/api/content/delivery-identities/{payload['binding']['binding_id']}")
    assert readback.status_code == 200
    assert readback.json()["binding"] == payload["binding"]

    missing = client.get("/api/content/delivery-identities/content_delivery_identity_missing")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "content_delivery_identity_not_found"}
