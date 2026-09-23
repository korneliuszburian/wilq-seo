from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_source_pack_binding as route_module
from apps.api.wilq_api.main import app
from tests.content.test_delivery_identity_binding import _command as identity_command
from tests.content.test_source_pack_binding import _setup_store, _source_command


def test_legacy_source_pack_post_requires_an_action_without_persisting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    before = store.list_content_source_pack_bindings(
        current_work_item_id=identity.current_work_item_id
    )

    response = TestClient(app).post(
        "/api/content/source-pack-bindings",
        json=_source_command(identity).model_dump(mode="json"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "legacy_source_pack_action_required"
    assert response.json()["blocker_owner"] == "WILQ content workflow"
    assert response.json()["safe_next_step"]
    assert response.json()["external_write_attempted"] is False
    assert store.list_content_source_pack_bindings(
        current_work_item_id=identity.current_work_item_id
    ) == before


def test_source_pack_route_exposes_global_prerequisites_but_blocks_rowless_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app)

    payload = store.record_content_source_pack_binding(
        _source_command(identity)
    ).model_dump(mode="json")
    assert payload["binding"]["status"] == "blocked"
    assert payload["binding"]["blocker"]["reason"] == "source_fact_row_binding_missing"
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
    assert prerequisite_payload["row_authority_status"] == "missing"
    assert prerequisite_payload["approved_source_fact_ids"] == []
    assert prerequisite_payload["global_approved_source_fact_count"] > 0
    assert prerequisite_payload["source_fact_registry_receipt"]["registry_digest"]
    assert prerequisite_payload["fresh_context_digest"]

    round_trip = store.record_content_source_pack_binding(
        _source_command(
            identity,
            source_pack_id="source_pack_round_trip",
            source_pack_sha256="b" * 64,
        )
    )
    assert round_trip.binding.status == "blocked"
    assert round_trip.binding.blocker is not None
    assert (
        round_trip.binding.blocker.reason
        == "source_fact_row_binding_missing"
    )

    conflict = store.record_content_source_pack_binding(
        _source_command(
            identity,
            source_pack_id="source_pack_round_trip",
            source_pack_sha256="b" * 64,
        ).model_copy(update={"source_fact_ids": ("ekologus_public_bdo_faq_2026_07_01",)})
    )
    conflict_binding = conflict.binding.model_dump(mode="json")
    assert conflict_binding["status"] == "blocked"
    assert conflict_binding["blocker"]["reason"] == "source_fact_row_binding_missing"
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


def test_missing_current_classification_blocks_prerequisites_and_pack_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        connection.execute("DELETE FROM content_production_classifications")
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app, raise_server_exceptions=False)

    prerequisites = client.get(
        f"/api/content/source-pack-bindings/prerequisites/{identity.binding_id}"
    )
    assert prerequisites.status_code == 200
    prerequisite_payload = prerequisites.json()
    assert prerequisite_payload["row_authority_status"] == "blocked"
    assert prerequisite_payload["row_authority_blocker_reason"] == "classification_current_missing"

    created = store.record_content_source_pack_binding(_source_command(identity))
    assert created.binding.status == "blocked"
    assert created.binding.blocker is not None
    assert created.binding.blocker.reason == "classification_current_missing"
