from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

import apps.api.wilq_api.routers.actions as actions_router
import wilq.actions.action_validation as action_validation_module
import wilq.actions.audit_store as audit_store_module
import wilq.content.workflow.store.store as workflow_store_module
from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_source_fact_authority as authority_router
from apps.api.wilq_api.routers import content_source_pack_binding as source_pack_router
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command as identity_command
from wilq.actions import service as action_service
from wilq.actions.action_blockers import action_confirmation_blockers, action_impact_check_blockers
from wilq.actions.apply_lifecycle import (
    ApplyDependencies,
    _resolve_apply_capability,
)
from wilq.actions.apply_lifecycle import (
    apply_action as apply_action_lifecycle,
)
from wilq.actions.authority_audit_context import stamp_authority_audit_context
from wilq.actions.mutation_contract import mutation_apply_contract, supported_mutation_adapter
from wilq.actions.mutation_readiness import vendor_write_possible
from wilq.actions.payloads import validate_action_payload
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.source_fact_authority import (
    ContentSourceFactAuthorityPreviewCommand,
    ContentSourceFactAuthoritySnapshot,
    build_content_source_fact_authority_candidate_projection,
    execute_content_source_fact_authority,
    parse_source_fact_authority_snapshot_json,
    prepare_content_source_fact_authority_preview,
    read_content_source_fact_authority,
    source_fact_authority_action_payload_digest,
    validate_source_fact_authority_action_payload,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import ActionApplyRequest, AuditEvent
from wilq.storage.local_state import LocalStateStore


def _exact_bdo_identity_command():
    return identity_command(retained=True).model_copy(
        update={"retained_work_item_id": None, "retained_usage": None}
    )


def _prepared_snapshot(tmp_path: Path) -> ContentSourceFactAuthoritySnapshot:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    response = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    )
    assert response.status == "preview_ready"
    return ContentSourceFactAuthoritySnapshot.model_validate(
        response.action.payload["source_fact_authority"]
    )


def test_exact_eligible_fact_preview_is_ready(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "eligible.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding

    response = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=("ekologus_public_bdo_faq_2026_07_01",),
        ),
    )

    assert response.status == "preview_ready"
    assert response.action.payload["source_fact_authority"]["source_fact_ids"] == [
        "ekologus_public_bdo_faq_2026_07_01"
    ]


def test_preview_blocks_approved_foreign_fact_for_exact_identity(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "foreign.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding

    response = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
                "ekologus_public_consulting_outsourcing_offer_2026_07_01",
            ),
        ),
    )

    assert response.status == "blocked"
    assert "source_fact_candidate_not_eligible" in response.action.payload["runtime_blockers"]


def test_preview_blocks_reconciled_retained_identity(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "retained.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(identity_command(retained=True)).binding

    response = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=("ekologus_public_bdo_faq_2026_07_01",),
        ),
    )

    assert response.status == "blocked"
    assert "identity_binding_not_exact_current" in response.action.payload["runtime_blockers"]


def _homepage_authority_inputs() -> tuple[SimpleNamespace, SimpleNamespace]:
    identity = SimpleNamespace(
        binding_id="content_delivery_identity_homepage",
        binding_digest="a" * 64,
        status="exact_current",
        current_work_item_id="content_work_item_homepage",
        canonical_path="/",
        public_url="https://www.ekologus.pl/",
        classification_run_id="content_production_classification_homepage",
        classification_run_digest="b" * 64,
        classification_decision_set_digest="c" * 64,
        classification_source_row_digest="d" * 64,
        inventory_evidence_ids=("ev_inventory_homepage",),
        final_disposition="keep",
    )
    classification = SimpleNamespace(
        run_id=identity.classification_run_id,
        run_digest=identity.classification_run_digest,
        decision_set_digest=identity.classification_decision_set_digest,
        freshness=SimpleNamespace(requires_refresh=False, state="fresh"),
        row=SimpleNamespace(
            current_work_item_id=identity.current_work_item_id,
            canonical_path=identity.canonical_path,
            public_url=identity.public_url,
            source_packet_row_digest=identity.classification_source_row_digest,
            primary_evidence_ids=identity.inventory_evidence_ids,
        ),
    )
    return identity, classification


def test_candidate_projection_excludes_global_foreign_facts_and_blocks_homepage() -> None:
    identity, classification = _homepage_authority_inputs()

    projection = build_content_source_fact_authority_candidate_projection(
        identity.binding_id,
        identity=identity,
        classification=classification,
        facts=tuple(ekologus_source_facts()),
        cards=tuple(ekologus_content_knowledge_cards()),
        checked_at=datetime(2026, 9, 13, tzinfo=UTC),
    )

    assert projection.status == "evidence_acquisition_needed"
    assert projection.service_binding.status == "exact_bound"
    assert projection.service_binding.card_id == "ekologus_service_homepage_overview"
    assert projection.eligible_candidates == ()
    assert [item.source_fact_id for item in projection.review_required_candidates] == [
        "ekologus_public_homepage_service_overview_2026_07_02"
    ]
    assert "ekologus_public_bdo_faq_2026_07_01" not in {
        item.source_fact_id
        for item in (
            *projection.eligible_candidates,
            *projection.review_required_candidates,
        )
    }
    assert "source_fact_not_approved" in projection.review_required_candidates[0].reasons
    assert projection.review_required_candidates[0].freshness_date == "2026-07-02"
    assert (
        projection.review_required_candidates[0].target_card_id
        == "ekologus_service_homepage_overview"
    )
    assert projection.acquisition_status == "needed"


def test_candidate_projection_rejects_requested_identity_mismatch() -> None:
    identity, classification = _homepage_authority_inputs()

    projection = build_content_source_fact_authority_candidate_projection(
        "content_delivery_identity_foreign",
        identity=identity,
        classification=classification,
        facts=tuple(ekologus_source_facts()),
        cards=tuple(ekologus_content_knowledge_cards()),
    )

    assert projection.status == "blocked"
    assert projection.blockers[0].reason == "identity_binding_id_mismatch"


def test_candidate_projection_route_is_read_only_and_exactly_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity, classification = _homepage_authority_inputs()

    class Store:
        def load_content_delivery_identity(self, binding_id: str):
            assert binding_id == identity.binding_id
            return identity

        def load_production_classification_for_work_item(self, work_item_id: str):
            assert work_item_id == identity.current_work_item_id
            return classification

    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: Store())
    response = authority_router.content_source_fact_authority_candidates_endpoint(
        identity.binding_id
    )

    assert response.response_type == "content_source_fact_authority_candidates"
    assert response.identity_binding_digest == identity.binding_digest
    assert response.eligible_candidates == ()
    assert response.blockers


def test_candidate_route_rejects_unsafe_identity_path() -> None:
    app = FastAPI()
    router = APIRouter()
    authority_router.register_content_source_fact_authority_routes(router)
    app.include_router(router)

    response = TestClient(app).get(
        "/api/content/source-fact-authority-reviews/candidates/bad!"
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_source_row_digest_and_selected_facts_are_self_authenticating(
    tmp_path: Path,
) -> None:
    snapshot = _prepared_snapshot(tmp_path)
    payload = snapshot.model_dump(mode="json")

    with pytest.raises(ValidationError, match="source row digest"):
        ContentSourceFactAuthoritySnapshot.model_validate(
            payload | {"classification_source_row_digest": "f" * 64}
        )

    swapped = dict(payload)
    swapped["source_fact_ids"] = [
        "ekologus_public_bdo_faq_2026_07_01",
        "ekologus_public_homepage_service_overview_2026_07_02",
    ]
    with pytest.raises(ValidationError, match="source facts digest"):
        ContentSourceFactAuthoritySnapshot.model_validate(swapped)


def test_snapshot_json_parser_rejects_non_string_json_scalars(tmp_path: Path) -> None:
    snapshot = _prepared_snapshot(tmp_path)
    payload = snapshot.model_dump(mode="json")
    payload["identity_binding_id"] = 42

    with pytest.raises(ValidationError):
        parse_source_fact_authority_snapshot_json(payload)


def test_json_action_snapshot_passes_its_strict_payload_validator(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action

    assert validate_source_fact_authority_action_payload(action.payload) == []
    assert validate_action_payload("wordpress_ekologus", action.payload) == []
    assert supported_mutation_adapter(action) == "content_source_fact_authority_store"
    contract = mutation_apply_contract(action, supported_mutation_adapter(action))
    assert contract is not None
    assert contract.allowed_operation == "record_source_fact_authority_receipt"
    assert contract.draft_only is False
    assert contract.required_env_flags == []
    assert vendor_write_possible(action, supported_mutation_adapter(action)) is False
    assert "draft_action_review_required" in action_confirmation_blockers(
        action,
        type("Request", (), {"preview_acknowledged": True})(),
        None,
        ads_target_blockers=lambda _request: [],
    )
    assert "metric_facts_required" not in action_impact_check_blockers(action, None)


def test_receipt_requires_complete_exact_audit_chain(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action
    result, errors = execute_content_source_fact_authority(action, store=store, audit_events=[])
    assert result is None
    assert errors
    assert read_content_source_fact_authority(store, action_id=action.id).status == "missing"
    events = [
        AuditEvent(
            id=f"audit_{kind}",
            action_id=action.id,
            event_type=kind,
            actor="wilku",
            summary=kind,
            details={
                "source_fact_authority_snapshot_digest": parse_source_fact_authority_snapshot_json(
                    action.payload["source_fact_authority"]
                ).context_digest,
                "source_fact_authority_action_payload_digest": (
                    source_fact_authority_action_payload_digest(action)
                ),
            },
        )
        for kind in (
            "action_preview_generated",
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        )
    ]
    result, errors = execute_content_source_fact_authority(action, store=store, audit_events=events)
    assert errors == []
    assert result is not None
    assert result["status"] == "created"
    assert result["external_write_attempted"] is False
    assert read_content_source_fact_authority(store, action_id=action.id).status == "current"


def test_receipt_rejects_out_of_order_audit_chain(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action
    snapshot_digest = parse_source_fact_authority_snapshot_json(
        action.payload["source_fact_authority"]
    ).context_digest
    payload_digest = source_fact_authority_action_payload_digest(action)
    event_types = (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    )
    events = [
        AuditEvent(
            id=f"audit_out_of_order_{event_type}",
            action_id=action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
            details={
                "source_fact_authority_snapshot_digest": snapshot_digest,
                "source_fact_authority_action_payload_digest": payload_digest,
            },
        )
        for event_type in event_types
    ]
    events[0] = events[0].model_copy(
        update={"created_at": events[-1].created_at + timedelta(seconds=1)}
    )

    result, errors = execute_content_source_fact_authority(
        action, store=store, audit_events=events
    )

    assert result is None
    assert errors == ["Source fact authority audit chain is out of order."]
    assert read_content_source_fact_authority(store, action_id=action.id).status == "missing"


def test_service_audit_stamp_binds_exact_authority_payload(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action
    event = AuditEvent(
        id="audit_service_stamp",
        action_id=action.id,
        event_type="action_preview_generated",
        actor="wilku",
        summary="preview",
    )

    stamp_authority_audit_context(action, event)

    assert event.details["source_fact_authority_snapshot_digest"] == (
        parse_source_fact_authority_snapshot_json(
            action.payload["source_fact_authority"]
        ).context_digest
    )
    assert event.details["source_fact_authority_action_payload_digest"] == (
        source_fact_authority_action_payload_digest(action)
    )


def test_service_dispatch_executes_only_local_authority_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action
    events = []
    for kind in (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    ):
        event = AuditEvent(
            id=f"audit_dispatch_{kind}",
            action_id=action.id,
            event_type=kind,
            actor="wilku",
            summary=kind,
        )
        stamp_authority_audit_context(action, event)
        events.append(event)
    action.audit_events = events
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)

    result, errors = action_service._execute_supported_mutation_adapter(
        action, "content_source_fact_authority_store"
    )

    assert errors == []
    assert result is not None
    assert result["external_write_attempted"] is False


def test_local_authority_receipt_does_not_resolve_wordpress_capability(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action

    capability = _resolve_apply_capability(
        action,
        request=None,
        wordpress_apply_capability=lambda _action, _request: pytest.fail(
            "local receipt must not resolve WordPress capability"
        ),
    )

    assert capability.capability is None
    assert capability.blockers == []


def test_local_authority_receipt_applies_through_canonical_lifecycle(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    action = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        ),
    ).action
    action.validation_status = "valid"
    events = []
    for event_type in (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    ):
        event = AuditEvent(
            id=f"audit_canonical_{event_type}",
            action_id=action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
        )
        stamp_authority_audit_context(action, event)
        events.append(event)
    action.audit_events = events
    dependencies = ApplyDependencies(
        review_gate=lambda value: value.review_gate,
        wordpress_apply_capability=lambda *_args: pytest.fail(
            "local receipt must not resolve WordPress capability"
        ),
        mutation_adapter=lambda _action: "content_source_fact_authority_store",
        execute_mutation_adapter=lambda value, _adapter, _capability: (
            execute_content_source_fact_authority(
                value, store=store, audit_events=value.audit_events
            )
        ),
        connector_status=lambda _connector: SimpleNamespace(configured=False),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=lambda *_args: pytest.fail("local receipt must not claim WordPress"),
        finish_wordpress_apply_claim=lambda *_args: pytest.fail(
            "local receipt must not finish a WordPress claim"
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
    assert read_content_source_fact_authority(store, action_id=action.id).status == "current"


def test_preview_router_uses_typed_server_side_authority_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)

    response = authority_router.content_source_fact_authority_preview_endpoint(
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(
                "ekologus_public_bdo_faq_2026_07_01",
            ),
        )
    )

    assert response.status == "preview_ready"
    assert response.action.payload["local_authority_only"] is True
    assert authority_router.content_source_fact_authority_read_endpoint(
        response.action.id
    ).status == "missing"


def _assert_source_authority_tables_are_append_only(store_path: Path) -> None:
    with sqlite3.connect(store_path) as connection:
        for table in (
            "content_source_fact_authority_proposals",
            "content_source_fact_authority_receipts",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f"INSERT OR REPLACE INTO {table} SELECT * FROM {table} LIMIT 1"
                )


def test_public_authority_receipt_closes_source_pack_with_exact_current_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact public candidate selection must become an exact source pack."""

    store = ContentWorkflowStore(tmp_path / "authority-to-pack.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding
    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(source_pack_router, "content_workflow_store", lambda: store)
    client = TestClient(app)

    candidates = client.get(
        f"/api/content/source-fact-authority-reviews/candidates/{identity.binding_id}"
    )
    assert candidates.status_code == 200
    candidate_payload = candidates.json()
    assert candidate_payload["status"] == "eligible"
    assert candidate_payload["acquisition_status"] == "not_needed"
    selected_fact_id = "ekologus_public_bdo_faq_2026_07_01"
    assert selected_fact_id in {
        item["source_fact_id"] for item in candidate_payload["eligible_candidates"]
    }
    preview = prepare_content_source_fact_authority_preview(
        store,
        ContentSourceFactAuthorityPreviewCommand(
            identity_binding_id=identity.binding_id,
            proposed_source_fact_ids=(selected_fact_id,),
        ),
    )
    assert preview.status == "preview_ready"
    events = []
    for event_type in (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    ):
        event = AuditEvent(
            id=f"audit_public_authority_pack_{event_type}",
            action_id=preview.action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
        )
        stamp_authority_audit_context(preview.action, event)
        events.append(event)
    applied, errors = execute_content_source_fact_authority(
        preview.action,
        store=store,
        audit_events=events,
    )
    assert errors == []
    assert applied is not None
    assert applied["external_write_attempted"] is False

    prerequisites = client.get(
        f"/api/content/source-pack-bindings/prerequisites/{identity.binding_id}"
    )
    assert prerequisites.status_code == 200
    prerequisite_payload = prerequisites.json()
    assert prerequisite_payload["row_authority_status"] == "exact_current"
    assert prerequisite_payload["approved_source_fact_ids"] == [selected_fact_id]
    assert prerequisite_payload["row_authority_receipt"]["receipt_id"] == applied["receipt_id"]
    selected_fact_evidence_id = next(
        item["evidence_ids"][0]
        for item in candidate_payload["eligible_candidates"]
        if item["source_fact_id"] == selected_fact_id
    )
    assert selected_fact_evidence_id in prerequisite_payload["row_authority_evidence_ids"]

    pack_command = {
        "source_pack_id": "source_pack_authority_closure",
        "source_pack_sha256": "a" * 64,
        "identity_binding_id": prerequisite_payload["identity_binding_id"],
        "identity_binding_digest": prerequisite_payload["identity_binding_digest"],
        "current_work_item_id": prerequisite_payload["current_work_item_id"],
        "source_fact_ids": prerequisite_payload["approved_source_fact_ids"],
        "evidence_ids": prerequisite_payload["row_authority_evidence_ids"],
        "fresh_context_digest": prerequisite_payload["fresh_context_digest"],
        "source_fact_registry_receipt": prerequisite_payload["source_fact_registry_receipt"],
        "fresh_context_attestation": prerequisite_payload["fresh_context_attestation"],
        "recorded_by": "public_authority_pack_test",
        "recorded_at": prerequisite_payload["source_fact_registry_receipt"]["checked_at"],
    }
    created = client.post("/api/content/source-pack-bindings", json=pack_command)
    assert created.status_code == 201
    binding_payload = created.json()["binding"]
    assert binding_payload["status"] == "exact_current"
    assert binding_payload["source_fact_authority_receipt_id"] == applied["receipt_id"]

    readback = client.get(
        f"/api/content/source-pack-bindings/{binding_payload['binding_id']}"
    )
    assert readback.status_code == 200
    assert readback.json()["binding"] == binding_payload

    _assert_source_authority_tables_are_append_only(store.path)


def test_public_http_authority_lifecycle_writes_only_local_row_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "public-workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "public-audit.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    identity = store.record_content_delivery_identity(_exact_bdo_identity_command()).binding

    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(source_pack_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_validation_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(audit_store_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(actions_router, "local_state_store", lambda: audit_store)

    client = TestClient(app)
    preview = client.post(
        "/api/content/source-fact-authority-reviews/preview",
        json={
            "identity_binding_id": identity.binding_id,
            "proposed_source_fact_ids": ["ekologus_public_bdo_faq_2026_07_01"],
        },
    )
    assert preview.status_code == 200, preview.text
    action_id = preview.json()["action"]["id"]

    validation = client.post(f"/api/actions/{action_id}/validate")
    assert validation.status_code == 200, validation.text
    assert validation.json()["valid"] is True
    action_preview = client.post(f"/api/actions/{action_id}/preview", json={})
    assert action_preview.status_code == 200, action_preview.text
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "wilku",
            "notes": "Sprawdzono exact row-authority receipt.",
        },
    )
    assert review.status_code == 200, review.text
    confirmation = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "wilku",
            "notes": "Potwierdzam zapis lokalnego authority.",
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

    receipt = store.load_content_source_fact_authority_receipt(action_id)
    assert receipt is not None
    assert receipt.authority_snapshot.identity_binding_id == identity.binding_id


def test_blocked_authority_without_snapshot_has_no_public_http_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "blocked-authority.sqlite3")
    audit_store = LocalStateStore(tmp_path / "blocked-authority-audit.sqlite3")
    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(source_pack_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_validation_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(audit_store_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(actions_router, "local_state_store", lambda: audit_store)

    client = TestClient(app, raise_server_exceptions=False)
    preview = client.post(
        "/api/content/source-fact-authority-reviews/preview",
        json={
            "identity_binding_id": "content_delivery_identity_missing",
            "proposed_source_fact_ids": ["ekologus_public_bdo_faq_2026_07_01"],
        },
    )
    assert preview.status_code == 200
    action_id = preview.json()["action"]["id"]
    assert preview.json()["action"]["payload"]["source_fact_authority"] is None

    responses = [
        client.post(f"/api/actions/{action_id}/validate"),
        client.post(f"/api/actions/{action_id}/preview", json={}),
        client.post(
            f"/api/actions/{action_id}/review",
            json={"outcome": "approved_for_prepare", "reviewed_by": "wilku", "notes": "blocked"},
        ),
        client.post(
            f"/api/actions/{action_id}/confirm",
            json={"confirmed_by": "wilku", "notes": "blocked", "preview_acknowledged": True},
        ),
        client.post(
            f"/api/actions/{action_id}/impact-check",
            json={"checked_by": "wilku", "notes": "blocked"},
        ),
        client.post(
            f"/api/actions/{action_id}/apply",
            json={"confirm": True, "confirmed_by": "wilku"},
        ),
    ]
    assert all(response.status_code != 500 for response in responses)
