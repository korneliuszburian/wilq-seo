from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_source_pack_binding as route_module
from apps.api.wilq_api.main import app
from tests.content.test_delivery_identity_binding import _command as identity_command
from tests.content.test_source_pack_binding import _setup_store, _source_command


def test_exact_source_pack_binding_record_and_read_routes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app)

    created = client.post(
        "/api/content/source-pack-bindings",
        json=_source_command(identity).model_dump(mode="json"),
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["binding"]["status"] == "exact_current"
    assert payload["binding"]["source_facts_digest"]

    readback = client.get(f"/api/content/source-pack-bindings/{payload['binding']['binding_id']}")
    assert readback.status_code == 200
    assert readback.json()["status"] == "found"
    assert readback.json()["binding"] == payload["binding"]

    prerequisites = client.get(
        f"/api/content/source-pack-bindings/prerequisites/{payload['binding']['identity_binding_id']}"
    )
    assert prerequisites.status_code == 200
    prerequisite_payload = prerequisites.json()
    assert prerequisite_payload["identity_binding_id"] == payload["binding"]["identity_binding_id"]
    assert (
        prerequisite_payload["current_work_item_id"] == payload["binding"]["current_work_item_id"]
    )
    assert prerequisite_payload["approved_source_fact_ids"]
    assert prerequisite_payload["source_fact_registry_receipt"]["registry_digest"]
    assert prerequisite_payload["fresh_context_digest"]

    round_trip_payload = {
        "source_pack_id": "source_pack_round_trip",
        "source_pack_sha256": "b" * 64,
        "identity_binding_id": prerequisite_payload["identity_binding_id"],
        "identity_binding_digest": prerequisite_payload["identity_binding_digest"],
        "current_work_item_id": prerequisite_payload["current_work_item_id"],
        "source_fact_ids": prerequisite_payload["approved_source_fact_ids"][:2],
        "evidence_ids": prerequisite_payload["fresh_context_attestation"]["evidence_ids"],
        "fresh_context_digest": prerequisite_payload["fresh_context_digest"],
        "source_fact_registry_receipt": prerequisite_payload["source_fact_registry_receipt"],
        "fresh_context_attestation": prerequisite_payload["fresh_context_attestation"],
        "recorded_by": "api_round_trip_test",
        "recorded_at": prerequisite_payload["source_fact_registry_receipt"]["checked_at"],
    }
    round_trip = client.post("/api/content/source-pack-bindings", json=round_trip_payload)
    assert round_trip.status_code == 201
    assert round_trip.json()["binding"]["status"] == "exact_current"

    conflict_payload = {
        **round_trip_payload,
        "source_fact_ids": [prerequisite_payload["approved_source_fact_ids"][0]],
    }
    conflict = client.post("/api/content/source-pack-bindings", json=conflict_payload)
    assert conflict.status_code == 409
    conflict_binding = conflict.json()["binding"]
    assert conflict_binding["status"] == "blocked"
    assert (
        client.get(f"/api/content/source-pack-bindings/{conflict_binding['binding_id']}").json()[
            "binding"
        ]
        == conflict_binding
    )

    missing = client.get("/api/content/source-pack-bindings/source_pack_binding_missing")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "content_source_pack_binding_not_found"}


def test_prerequisites_route_reports_blocked_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = _setup_store(tmp_path)[0]
    blocked = store.record_content_delivery_identity(
        identity_command(retained=False, public_url="https://www.ekologus.pl/inny/")
    ).binding
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)

    response = TestClient(app).get(
        f"/api/content/source-pack-bindings/prerequisites/{blocked.binding_id}"
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "content_source_pack_prerequisites_identity_blocked"}
