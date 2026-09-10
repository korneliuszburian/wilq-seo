from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_landing_hub_authorization as route_module
import wilq.content.workflow.refresh_preparation_operations as refresh_operations
from apps.api.wilq_api.main import app
from tests.content.test_refresh_preparation_authority import _stored_refresh_run
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.landing_hub import (
    ContentLandingHubAuthorizationRequest,
    build_landing_hub_authorization,
    canonical_source_fact_registry_digest,
    duplicate_gate_receipt_digest,
    inventory_evidence_digest,
    landing_hub_authorization_blocker,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def _context() -> tuple[ContentWorkflowStore, object, object, ContentKindInventoryBinding]:
    run = _stored_refresh_run()
    row = run.rows[0]
    facts = tuple(fact for fact in ekologus_source_facts() if fact.review_status == "approved")
    fact = facts[0]
    inventory = ContentKindInventoryBinding(
        work_item_id=row.current_work_item_id,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        wordpress_content_type="page",
        content_kind="landing_or_hub",
        inventory_evidence_ids=("ev_landing_inventory",),
        trusted=True,
    )
    request = ContentLandingHubAuthorizationRequest(
        expected_classification_run_id=run.run_id,
        expected_classification_run_digest=run.run_digest,
        expected_decision_set_digest=run.input.decision_set_digest,
        expected_source_packet_row_digest=row.source_packet_row_digest,
        intent="hub informacyjny dla przedsiębiorcy",
        approved_source_fact_ids=(fact.source_id,),
        blocked_claims=tuple(sorted(fact.blocked_claims)),
        evidence_ids=tuple(sorted(("ev_landing_inventory", *fact.evidence_ids))),
        cta_destinations=("/kontakt/",),
        duplicate_gate="checked",
        duplicate_gate_evidence_ids=("ev_landing_inventory",),
        duplicate_gate_digest=duplicate_gate_receipt_digest(
            "hub informacyjny dla przedsiębiorcy",
            ("ev_landing_inventory",),
        ),
        authorized_by="wilku operator",
    )
    store = ContentWorkflowStore(Path("/tmp") / "unused")
    return store, run, request, inventory


def _authorization(tmp_path: Path):
    store, run, request, inventory = _context()
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(run)
    row = run.rows[0]
    authorization = build_landing_hub_authorization(
        work_item_id=row.current_work_item_id,
        classification=run,
        row=row,
        inventory_binding=inventory,
        request=request,
        authorized_at=datetime.now(UTC),
    )
    return store, run, request, inventory, authorization


def test_landing_hub_authorization_is_exact_idempotent_and_append_only(tmp_path: Path) -> None:
    store, _run, _request, _inventory, authorization = _authorization(tmp_path)

    created = store.record_landing_hub_authorization(authorization)
    repeated = store.record_landing_hub_authorization(authorization)

    assert created.status == "created"
    assert repeated.status == "idempotent"
    assert store.load_landing_hub_authorization(authorization.authorization_id) == authorization
    with sqlite3.connect(store.path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM content_landing_hub_authorizations "
                "WHERE authorization_id = ?",
                (authorization.authorization_id,),
            ).fetchone()[0]
        )
        assert payload["content_kind"] == "landing_or_hub"
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE content_landing_hub_authorizations SET content_kind = 'editorial'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM content_landing_hub_authorizations WHERE authorization_id = ?",
                (authorization.authorization_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "INSERT OR REPLACE INTO content_landing_hub_authorizations "
                "SELECT * FROM content_landing_hub_authorizations WHERE authorization_id = ?",
                (authorization.authorization_id,),
            )


def test_schema_v10_store_upgrades_landing_hub_authorization_table(tmp_path: Path) -> None:
    path = tmp_path / "schema-v10.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_marker (id TEXT PRIMARY KEY)")
        connection.execute("PRAGMA user_version = 10")

    store = ContentWorkflowStore(path)
    assert store.load_landing_hub_authorization("missing") is None
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (
            SQLITE_SCHEMA_VERSION,
        )
        assert connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'content_landing_hub_authorizations'"
        ).fetchone() == (1,)


def test_landing_hub_mismatch_is_typed_and_never_uses_service_card(
    tmp_path: Path,
) -> None:
    store, run, request, inventory, _authorization_value = _authorization(tmp_path)
    non_landing = inventory.__class__(
        **{**inventory.__dict__, "content_kind": "service"}
    )
    blocker = landing_hub_authorization_blocker(
        work_item_id=run.rows[0].current_work_item_id,
        classification=run,
        row=run.rows[0],
        inventory_binding=non_landing,
        request=request,
    )

    assert blocker is not None
    assert blocker.reason == "content_kind_mismatch"
    assert canonical_source_fact_registry_digest()
    assert inventory_evidence_digest(inventory.inventory_evidence_ids)


def test_blocked_classification_cannot_receive_landing_authorization() -> None:
    run = _stored_refresh_run()
    row = run.rows[1]
    inventory = ContentKindInventoryBinding(
        work_item_id=row.current_work_item_id,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        wordpress_content_type="page",
        content_kind="landing_or_hub",
        inventory_evidence_ids=("ev_landing_inventory",),
        trusted=True,
    )

    blocker = landing_hub_authorization_blocker(
        work_item_id=row.current_work_item_id,
        classification=run,
        row=row,
        inventory_binding=inventory,
    )

    assert blocker is not None
    assert blocker.reason == "classification_decision_blocked"


def test_superseded_classification_receipt_is_not_read_as_current(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wilq.content.workflow.store.store_landing_hub as landing_store_module

    store, run, _request, _inventory, authorization = _authorization(tmp_path)
    store.record_landing_hub_authorization(authorization)
    newer = run.model_copy(update={"run_id": "newer_classification"})
    monkeypatch.setattr(
        landing_store_module,
        "load_latest_production_classification_from_connection",
        lambda _connection: newer,
    )

    with pytest.raises(ValueError, match="no longer matches current classification"):
        store.load_latest_landing_hub_authorization(authorization.work_item_id)


def test_duplicate_gate_requires_its_own_evidence_digest() -> None:
    _store, run, request, inventory = _context()
    missing_receipt = request.model_copy(
        update={"duplicate_gate_evidence_ids": (), "duplicate_gate_digest": ""}
    )

    blocker = landing_hub_authorization_blocker(
        work_item_id=run.rows[0].current_work_item_id,
        classification=run,
        row=run.rows[0],
        inventory_binding=inventory,
        request=missing_receipt,
    )

    assert blocker is not None
    assert blocker.reason == "duplicate_gate_missing"


@pytest.mark.parametrize("secret", ["X" * 32, "a" * 32])
def test_landing_hub_free_text_is_redacted_before_authorization_digest(
    tmp_path: Path,
    secret: str,
) -> None:
    store, _run, request, _inventory, _authorization_value = _authorization(tmp_path)
    redacted_intent = "[REDACTED]"
    request_with_secret = request.model_copy(
        update={
            "intent": secret,
            "duplicate_gate_digest": duplicate_gate_receipt_digest(
                redacted_intent,
                request.duplicate_gate_evidence_ids,
            ),
        }
    )

    authorization = build_landing_hub_authorization(
        work_item_id=_run.rows[0].current_work_item_id,
        classification=_run,
        row=_run.rows[0],
        inventory_binding=_inventory,
        request=request_with_secret,
        authorized_at=datetime.now(UTC),
    )
    stored = store.record_landing_hub_authorization(authorization)

    assert stored.status == "created"
    assert stored.authorization.intent == redacted_intent


def test_landing_hub_preview_surfaces_corrupt_receipt_as_typed_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run, _request, inventory, _authorization_value = _authorization(tmp_path)
    store.record_landing_hub_authorization(_authorization_value)
    monkeypatch.setattr(
        store,
        "load_latest_landing_hub_authorization",
        lambda _work_item_id: (_ for _ in ()).throw(ValueError("corrupt receipt")),
    )
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        route_module,
        "content_kind_inventory_binding_for_work_item",
        lambda _work_item_id: inventory,
    )
    monkeypatch.setattr(store, "load_latest_production_classification", lambda: run)

    client = TestClient(app)
    response = client.get(
        f"/api/content/work-items/{run.rows[0].current_work_item_id}/landing-hub-authorization"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["reason"] == "authorization_conflict"


def test_landing_hub_get_routes_do_not_echo_invalid_path_values() -> None:
    client = TestClient(app)

    preview = client.get(
        "/api/content/work-items/INVALID/landing-hub-authorization"
    )
    receipt = client.get(
        "/api/content/work-items/landing-hub-authorizations/INVALID"
    )

    assert preview.status_code == 422
    assert preview.json() == {"detail": "landing_hub_authorization_request_invalid"}
    assert receipt.status_code == 422
    assert receipt.json() == {"detail": "landing_hub_authorization_request_invalid"}


def test_existing_refresh_path_blocks_landing_instead_of_service_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, run, _request, inventory, _authorization_value = _authorization(tmp_path)
    monkeypatch.setattr(
        refresh_operations,
        "classified_refresh_context",
        lambda *_args: SimpleNamespace(binding=None),
    )
    monkeypatch.setattr(refresh_operations, "stale_preview", lambda *_args: None)

    preview = refresh_operations.preview(
        store=store,
        snapshot_loader=lambda *_args, **_kwargs: None,
        work_item_id=run.rows[0].current_work_item_id,
        service_card_id=None,
        content_kind_inventory_loader=lambda _work_item_id: inventory,
    )

    assert preview.status == "blocked"
    assert preview.blockers[0].code == "refresh_preparation_landing_hub_required"


def test_existing_refresh_path_blocks_when_inventory_identity_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, run, _request, _inventory, _authorization_value = _authorization(tmp_path)
    monkeypatch.setattr(
        refresh_operations,
        "classified_refresh_context",
        lambda *_args: SimpleNamespace(binding=None),
    )
    monkeypatch.setattr(refresh_operations, "stale_preview", lambda *_args: None)

    preview = refresh_operations.preview(
        store=store,
        snapshot_loader=lambda *_args, **_kwargs: None,
        work_item_id=run.rows[0].current_work_item_id,
        service_card_id="service_card",
        content_kind_inventory_loader=lambda _work_item_id: None,
    )

    assert preview.status == "blocked"
    assert preview.blockers[0].code == "refresh_preparation_inventory_missing"

    rebuilt = refresh_operations._rebuild_authorized_preparation(
        snapshot_loader=lambda *_args, **_kwargs: None,
        work_item_id=run.rows[0].current_work_item_id,
        classified=SimpleNamespace(),
        content_kind="service",
        service_card_id="service_card",
        inventory_binding=None,
    )
    assert rebuilt.blocker.code == "refresh_preparation_inventory_missing"


def test_landing_hub_routes_preview_authorize_and_readback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run, request, inventory, _authorization_value = _authorization(tmp_path)
    work_item_id = run.rows[0].current_work_item_id
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        route_module,
        "content_kind_inventory_binding_for_work_item",
        lambda _work_item_id: inventory,
    )
    client = TestClient(app)

    preview = client.get(f"/api/content/work-items/{work_item_id}/landing-hub-authorization")
    created = client.post(
        f"/api/content/work-items/{work_item_id}/landing-hub-authorizations",
        json=request.model_dump(mode="json"),
    )

    assert preview.status_code == 200
    assert preview.json()["status"] == "ready_to_authorize"
    assert created.status_code == 201
    authorization = created.json()["authorization"]
    readback = client.get(
        f"/api/content/work-items/landing-hub-authorizations/{authorization['authorization_id']}"
    )
    after = client.get(f"/api/content/work-items/{work_item_id}/landing-hub-authorization")

    assert readback.status_code == 200
    assert readback.json()["authorization"] == authorization
    assert after.status_code == 200
    assert after.json()["status"] == "authorized"
    invalid = client.post(
        "/api/content/work-items/INVALID/landing-hub-authorizations",
        json=request.model_dump(mode="json"),
    )
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "landing_hub_authorization_request_invalid"}


def test_landing_hub_request_rejects_unsafe_cta() -> None:
    with pytest.raises(ValueError, match="safe local paths"):
        ContentLandingHubAuthorizationRequest(
            expected_classification_run_id="run",
            expected_classification_run_digest="a" * 64,
            expected_decision_set_digest="b" * 64,
            expected_source_packet_row_digest="c" * 64,
            intent="hub",
            approved_source_fact_ids=("fact_one",),
            evidence_ids=("ev_one",),
            cta_destinations=("//evil.example/",),
            duplicate_gate="checked",
            authorized_by="wilku",
        )
