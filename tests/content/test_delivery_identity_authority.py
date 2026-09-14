from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.actions as actions_router
import apps.api.wilq_api.routers.content_delivery_identity as delivery_identity_router
import apps.api.wilq_api.routers.content_delivery_identity_authority as delivery_authority_router
import wilq.actions.action_validation as action_validation_module
import wilq.actions.audit_store as audit_store_module
import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.store.store as workflow_store_module
from apps.api.wilq_api.main import app
from tests.content.test_current_blocked_classification import (
    _build as _build_current_classification,
)
from tests.content.test_current_blocked_classification import (
    _catalog as _current_catalog,
)
from tests.content.test_current_blocked_classification import (
    _freshness as _current_freshness,
)
from wilq.actions import action_catalog
from wilq.actions import service as action_service
from wilq.actions.apply_lifecycle import ApplyDependencies
from wilq.actions.apply_lifecycle import apply_action as apply_action_lifecycle
from wilq.actions.authority_audit_context import stamp_authority_audit_context
from wilq.actions.mutation_contract import mutation_apply_contract
from wilq.actions.mutation_readiness import vendor_write_possible
from wilq.actions.payloads import validate_action_payload
from wilq.content.workflow.authoring_inventory_receipt import (
    _build_content_authoring_inventory_receipt_from_catalog,
)
from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionCandidate,
    current_disposition_action_for_proposal,
    execute_current_disposition_authority,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityRecordResult
from wilq.content.workflow.delivery_identity_authority import (
    DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
    ContentDeliveryIdentityAuthorityCandidate,
    build_delivery_identity_authority_snapshot,
    delivery_identity_authority_action_for_proposal,
    delivery_identity_authority_action_payload_digest,
    execute_delivery_identity_authority,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import ActionApplyRequest, AuditEvent
from wilq.storage.local_state import LocalStateStore


def _events(action: object) -> list[AuditEvent]:
    return [
        AuditEvent(
            id=f"audit_{event_type}",
            action_id=action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
        )
        for event_type in (
            "action_preview_generated",
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        )
    ]


def _ready_authority(tmp_path) -> tuple[ContentWorkflowStore, object]:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    catalog = _current_catalog().model_copy(
        update={
            "items": [
                item.model_copy(
                    update={
                        "url": (
                            "https://www.ekologus.pl/"
                            if item.path == "/"
                            else f"https://www.ekologus.pl{item.path}/"
                        ),
                        "material_status": "content_and_structure",
                        "content_summary": "Aktualny materiał testowy.",
                    }
                )
                for item in _current_catalog().items
            ]
        }
    )
    receipts = {
        item.path.rstrip("/") or "/": _build_content_authoring_inventory_receipt_from_catalog(
            item=item,
            catalog=catalog,
            recorded_by="current_inventory_reconciler",
            recorded_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        )
        for item in catalog.items
    }
    run = _build_current_classification(
        catalog=catalog,
        freshness=_current_freshness(),
        inventory_receipts=receipts,
    )
    store.record_production_classification(run)
    row = next(
        item
        for item in run.rows
        if item.canonical_path == "/bdo-co-musi-wiedziec-przedsiebiorca"
    )
    disposition_proposal = store.record_content_current_disposition_proposal(
        ContentCurrentDispositionCandidate(
            current_work_item_id=row.current_work_item_id,
            proposed_final_disposition="keep",
        )
    )
    disposition_action = current_disposition_action_for_proposal(store, disposition_proposal)
    disposition_events = _events(disposition_action)
    for event in disposition_events:
        stamp_authority_audit_context(disposition_action, event)
    result, errors = execute_current_disposition_authority(
        disposition_action, store=store, audit_events=disposition_events
    )
    assert errors == []
    assert result is not None
    disposition = store.load_content_current_disposition_receipt(disposition_action.id)
    assert disposition is not None
    inventory = row.source_receipt
    assert getattr(inventory, "binding_state", None) == "registered_current_inventory"
    proposal = store.record_content_delivery_identity_authority_proposal(
        ContentDeliveryIdentityAuthorityCandidate(
            current_disposition_receipt_id=disposition.receipt_id,
            inventory_receipt_id=inventory.receipt_id,
        )
    )
    return store, delivery_identity_authority_action_for_proposal(store, proposal)


def test_identity_authority_accepts_only_exact_receipts_and_not_url_claims(tmp_path) -> None:
    store, action = _ready_authority(tmp_path)

    snapshot = build_delivery_identity_authority_snapshot(
        store,
        ContentDeliveryIdentityAuthorityCandidate(
            current_disposition_receipt_id=action.payload["delivery_identity_authority"][
                "current_disposition_receipt_id"
            ],
            inventory_receipt_id=action.payload["delivery_identity_authority"][
                "inventory_receipt_id"
            ],
        ),
    )

    assert snapshot.context_digest != "0" * 64
    assert snapshot.authority_mapping == DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT
    assert validate_action_payload("wordpress_ekologus", action.payload) == []
    assert action.payload["authority_mapping"] == DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT
    assert action.payload["preview_contract"] == DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT
    contract = mutation_apply_contract(action, "content_delivery_identity_store")
    assert contract is not None
    assert DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT in contract.required_input_contracts
    assert vendor_write_possible(action, None) is False
    with pytest.raises(ValueError, match="extra"):
        ContentDeliveryIdentityAuthorityCandidate.model_validate(
            {
                "current_disposition_receipt_id": snapshot.current_disposition_receipt_id,
                "inventory_receipt_id": snapshot.inventory_receipt_id,
                "public_url": snapshot.authority_snapshot.public_url,
            }
        )


def test_identity_authority_snapshot_is_exact_registered_row_receipt(tmp_path) -> None:
    store, action = _ready_authority(tmp_path)
    run = store.load_latest_production_classification()
    assert run is not None
    row = next(
        item
        for item in run.rows
        if item.current_work_item_id
        == action.payload["delivery_identity_authority"]["authority_snapshot"][
            "current_work_item_id"
        ]
    )
    receipt = row.source_receipt
    snapshot = build_delivery_identity_authority_snapshot(
        store,
        ContentDeliveryIdentityAuthorityCandidate(
            current_disposition_receipt_id=action.payload["delivery_identity_authority"][
                "current_disposition_receipt_id"
            ],
            inventory_receipt_id=receipt.receipt_id,
        ),
    )

    assert snapshot.inventory_receipt == receipt
    assert snapshot.inventory_receipt_id == receipt.receipt_id
    assert snapshot.inventory_receipt_digest == receipt.receipt_digest
    assert snapshot.inventory_catalog_item_digest == receipt.catalog_item_digest
    assert snapshot.inventory_catalog_snapshot_digest == receipt.catalog_snapshot_digest
    assert snapshot.inventory_evidence_ids == receipt.catalog_snapshot_evidence_ids


def test_identity_binding_executor_requires_exact_lifecycle_and_materializes_no_vendor_write(
    tmp_path,
) -> None:
    store, action = _ready_authority(tmp_path)

    result, errors = execute_delivery_identity_authority(action, store=store, audit_events=[])

    assert result is None
    assert errors == ["Exact preview, approved review, confirmation and impact check are required."]
    events = _events(action)
    for event in events:
        stamp_authority_audit_context(action, event)
    result, errors = execute_delivery_identity_authority(action, store=store, audit_events=events)

    assert errors == []
    assert result is not None
    assert result["external_write_attempted"] is False
    binding = store.load_content_delivery_identity(result["binding_id"])
    assert binding is not None
    assert binding.status == "exact_current"
    assert binding.final_disposition == "keep"
    assert binding.inventory_evidence_ids == tuple(
        action.payload["delivery_identity_authority"]["inventory_evidence_ids"]
    )


def test_identity_executor_rejects_receipt_context_drift_before_binding(tmp_path) -> None:
    store, action = _ready_authority(tmp_path)
    action.payload["runtime_blockers"] = ["forged_runtime_blocker"]
    events = _events(action)
    for event in events:
        stamp_authority_audit_context(action, event)

    result, errors = execute_delivery_identity_authority(action, store=store, audit_events=events)

    assert result is None
    assert errors == ["Delivery identity authority context changed before apply."]
    assert store.load_content_delivery_identity_record("content_delivery_identity_missing") is None


def test_identity_authority_rebuild_returns_blocked_action_when_classification_changes(
    tmp_path,
) -> None:
    store, action = _ready_authority(tmp_path)
    proposal = store.load_content_delivery_identity_authority_proposal(action.id)
    assert proposal is not None
    current = store.load_latest_production_classification()
    assert current is not None
    changed = production_module._build_run(
        input_receipt=current.input.model_copy(update={"packet_sha256": "a" * 64}),
        counts=current.counts,
        freshness=current.freshness,
        source_receipts=current.source_receipts,
        judge_receipt=current.judge_receipt.model_copy(
            update={"reviewed_packet_sha256": "a" * 64}
        ),
        rows=current.rows,
        audit=current.audit.model_copy(
            update={"recorded_at": datetime(2026, 9, 14, 10, 5, tzinfo=UTC)}
        ),
    )
    store.record_production_classification(changed)

    rebuilt = delivery_identity_authority_action_for_proposal(store, proposal)

    assert rebuilt.status == "blocked"
    assert rebuilt.payload["runtime_blockers"]
    assert rebuilt.payload["apply_allowed"] is False
    assert rebuilt.payload["api_mutation_ready"] is False


def test_blocked_current_identity_action_cannot_apply(tmp_path) -> None:
    store, action = _ready_authority(tmp_path)
    proposal = store.load_content_delivery_identity_authority_proposal(action.id)
    assert proposal is not None
    current = store.load_latest_production_classification()
    assert current is not None
    changed = production_module._build_run(
        input_receipt=current.input.model_copy(update={"packet_sha256": "a" * 64}),
        counts=current.counts,
        freshness=current.freshness,
        source_receipts=current.source_receipts,
        judge_receipt=current.judge_receipt.model_copy(
            update={"reviewed_packet_sha256": "a" * 64}
        ),
        rows=current.rows,
        audit=current.audit.model_copy(
            update={"recorded_at": datetime(2026, 9, 14, 10, 5, tzinfo=UTC)}
        ),
    )
    store.record_production_classification(changed)
    blocked_action = delivery_identity_authority_action_for_proposal(store, proposal)
    blocked_action.validation_status = "valid"

    dependencies = ApplyDependencies(
        review_gate=lambda value: value.review_gate,
        wordpress_apply_capability=lambda *_args: pytest.fail(
            "blocked local identity must not resolve WordPress capability"
        ),
        mutation_adapter=lambda _action: "content_delivery_identity_store",
        execute_mutation_adapter=lambda *_args: pytest.fail(
            "blocked current identity must not reach its executor"
        ),
        connector_status=lambda _connector: SimpleNamespace(configured=False),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=lambda *_args: pytest.fail(
            "blocked local identity must not claim WordPress"
        ),
        finish_wordpress_apply_claim=lambda *_args: pytest.fail(
            "blocked local identity must not finish a WordPress claim"
        ),
        status_label=lambda status: status,
        audit_event_label=lambda event: event,
    )

    result = apply_action_lifecycle(
        blocked_action,
        ActionApplyRequest(confirm=True, confirmed_by="wilku"),
        dependencies=dependencies,
    )

    assert result.applied is False
    assert result.status == "blocked"
    assert result.adapter_result is None
    assert result.mutation_audit.external_write_attempted is False
    assert any("delivery_identity_authority_classification" in error for error in result.errors)


def test_missing_classification_is_exposed_as_typed_blocked_authority_action(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "missing-classification.sqlite3")
    candidate = ContentDeliveryIdentityAuthorityCandidate(
        current_disposition_receipt_id="content_current_disposition_missing",
        inventory_receipt_id="content_authoring_inventory_missing",
    )

    proposal = store.record_content_delivery_identity_authority_proposal(candidate)
    action = delivery_identity_authority_action_for_proposal(store, proposal)

    assert action.status == "blocked"
    assert action.payload["runtime_blockers"] == [
        "delivery_identity_authority_disposition_receipt_missing"
    ]
    assert validate_action_payload("wordpress_ekologus", action.payload) == []


def test_service_dispatches_only_local_receipt_bound_identity_binding(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _ready_authority(tmp_path)
    events = _events(action)
    for event in events:
        stamp_authority_audit_context(action, event)
    action.audit_events = events
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)

    result, errors = action_service._execute_supported_mutation_adapter(
        action, "content_delivery_identity_store"
    )

    assert errors == []
    assert result is not None
    assert result["external_write_attempted"] is False


def test_identity_binding_uses_canonical_lifecycle_without_wordpress_capability(tmp_path) -> None:
    store, action = _ready_authority(tmp_path)
    action.validation_status = "valid"
    events = _events(action)
    for event in events:
        stamp_authority_audit_context(action, event)
    action.audit_events = events
    dependencies = ApplyDependencies(
        review_gate=lambda value: value.review_gate,
        wordpress_apply_capability=lambda *_args: pytest.fail(
            "local identity must not resolve WordPress capability"
        ),
        mutation_adapter=lambda _action: "content_delivery_identity_store",
        execute_mutation_adapter=lambda value, _adapter, _capability: (
            execute_delivery_identity_authority(
                value, store=store, audit_events=value.audit_events
            )
        ),
        connector_status=lambda _connector: SimpleNamespace(configured=False),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=lambda *_args: pytest.fail(
            "local identity must not claim WordPress"
        ),
        finish_wordpress_apply_claim=lambda *_args: pytest.fail(
            "local identity must not finish a WordPress claim"
        ),
        status_label=lambda status: status,
        audit_event_label=lambda event: event,
    )

    result = apply_action_lifecycle(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="wilku"),
        dependencies=dependencies,
    )

    assert result.applied is True
    assert result.errors == []
    assert result.adapter_result is not None
    assert result.adapter_result["external_write_attempted"] is False


def test_identity_authority_api_exposes_only_receipt_bound_preview() -> None:
    methods = app.openapi()["paths"][
        "/api/content/delivery-identity-authorities/preview"
    ]

    assert set(methods) >= {"post"}
    assert "get" not in methods


def test_action_catalog_rebuilds_identity_action_from_persisted_receipt_ids(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _ready_authority(tmp_path)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)

    rebuilt = action_catalog.get_action(action.id)

    assert rebuilt is not None
    assert rebuilt.id == action.id
    assert rebuilt.payload["runtime_blockers"] == []


def test_delivery_identity_authority_proposal_cannot_be_replaced(tmp_path) -> None:
    store, action = _ready_authority(tmp_path)
    proposal = store.load_content_delivery_identity_authority_proposal(action.id)
    assert proposal is not None

    with store._connect() as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "INSERT OR REPLACE INTO content_delivery_identity_authority_proposals "
            "(action_id, proposal_digest, current_disposition_receipt_id, "
            "inventory_receipt_id, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                proposal.action_id,
                proposal.proposal_digest,
                proposal.current_disposition_receipt_id,
                proposal.inventory_receipt_id,
                proposal.model_dump_json(),
            ),
        )

    assert store.load_content_delivery_identity_authority_proposal(action.id) == proposal


def test_delivery_identity_authority_reuses_persisted_audit_chain_and_is_idempotent(
    tmp_path,
) -> None:
    store, action = _ready_authority(tmp_path)
    events = _events(action)
    for event in events:
        stamp_authority_audit_context(action, event)
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    for event in events:
        audit_store.save_audit_event(event)

    persisted = audit_store.list_audit_events(action_id=action.id)
    assert {event.event_type for event in persisted} == {
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    }
    first, first_errors = execute_delivery_identity_authority(
        action, store=store, audit_events=persisted
    )
    second, second_errors = execute_delivery_identity_authority(
        action, store=store, audit_events=persisted
    )

    assert first_errors == []
    assert second_errors == []
    assert first is not None and second is not None
    assert first["status"] == "created"
    assert second["status"] == "idempotent"
    with store._connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_delivery_identity_bindings"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM content_delivery_records"
        ).fetchone()[0] == 1


def test_delivery_identity_authority_conflict_blocks_execution(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _ready_authority(tmp_path)
    events = _events(action)
    for event in events:
        stamp_authority_audit_context(action, event)
    created, created_errors = execute_delivery_identity_authority(
        action, store=store, audit_events=events
    )
    assert created_errors == []
    assert created is not None
    existing = store.load_content_delivery_identity_record(created["binding_id"])
    assert existing is not None

    monkeypatch.setattr(
        store,
        "record_content_delivery_identity",
        lambda _command: ContentDeliveryIdentityRecordResult(
            status="conflict",
            binding=existing.binding,
            delivery_record=existing.delivery_record,
            current=existing.current,
        ),
    )
    result, errors = execute_delivery_identity_authority(action, store=store, audit_events=events)

    assert result is None
    assert errors == ["Delivery identity binding conflicts with an existing append-only identity."]


def test_public_http_lifecycle_persists_exact_identity_and_no_vendor_write(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, prepared = _ready_authority(tmp_path)
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    monkeypatch.setattr(delivery_authority_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(delivery_identity_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(
        action_service,
        "get_connector_status",
        lambda _connector: SimpleNamespace(configured=True, label="WordPress"),
    )
    monkeypatch.setattr(action_validation_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(
        action_validation_module,
        "get_connector_status",
        lambda _connector: SimpleNamespace(configured=True, label="WordPress"),
    )
    monkeypatch.setattr(audit_store_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(actions_router, "local_state_store", lambda: audit_store)
    client = TestClient(app)
    authority = prepared.payload["delivery_identity_authority"]

    preview = client.post(
        "/api/content/delivery-identity-authorities/preview",
        json={
            "current_disposition_receipt_id": authority["current_disposition_receipt_id"],
            "inventory_receipt_id": authority["inventory_receipt_id"],
        },
    )
    assert preview.status_code == 200, preview.text
    action_id = preview.json()["id"]

    validation = client.post(f"/api/actions/{action_id}/validate")
    assert validation.status_code == 200, validation.text
    assert validation.json()["valid"] is True
    action_preview = client.post(f"/api/actions/{action_id}/preview", json={})
    assert action_preview.status_code == 200, action_preview.text
    assert action_preview.json()["status"] == "blocked"
    assert "impact_sanity_check_required" in action_preview.json()["blockers"]
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "wilku",
            "notes": "Sprawdzono dwa exact receipt-y.",
        },
    )
    assert review.status_code == 200, review.text
    confirmation = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "wilku",
            "notes": "Potwierdzam zapis lokalnego identity.",
            "preview_acknowledged": True,
        },
    )
    assert confirmation.status_code == 200, confirmation.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "wilku", "notes": "Sprawdzono wpływ lokalny."},
    )
    assert impact.status_code == 200, impact.text
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "wilku"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied"] is True
    assert applied.json()["adapter_result"]["external_write_attempted"] is False

    binding_id = applied.json()["adapter_result"]["binding_id"]
    readback = client.get(f"/api/content/delivery-identities/{binding_id}")
    assert readback.status_code == 200, readback.text
    payload = readback.json()
    assert payload["current"]["current_status"] == "exact_current"
    assert payload["binding"]["status"] == "exact_current"
    assert payload["binding"]["inventory_receipt_id"] == authority["inventory_receipt_id"]
    assert payload["binding"]["inventory_receipt_digest"] == authority[
        "inventory_receipt_digest"
    ]
    assert payload["binding"]["inventory_catalog_id"] == authority["inventory_receipt"][
        "catalog_id"
    ]
    assert payload["binding"]["inventory_receipt"] == authority["inventory_receipt"]
    audit_events = client.get(
        "/api/audit/events", params={"action_id": action_id}
    ).json()
    assert {
        event["event_type"] for event in audit_events
    } == {
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
        "apply_succeeded",
    }
    assert all(
        event["details"]["delivery_identity_authority_snapshot_digest"]
        == authority["context_digest"]
        and event["details"]["delivery_identity_authority_action_payload_digest"]
        == delivery_identity_authority_action_payload_digest(prepared)
        for event in audit_events
        if event["event_type"] != "apply_succeeded"
    )
