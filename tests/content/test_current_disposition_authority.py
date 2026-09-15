from __future__ import annotations

import sqlite3
from datetime import timedelta
from types import SimpleNamespace

import pytest

import wilq.content.workflow.decisions.production as production_module
from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import (
    content_current_disposition_authority as authority_router,
)
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.actions import service as action_service
from wilq.actions.action_blockers import action_confirmation_blockers
from wilq.actions.apply_lifecycle import ApplyDependencies
from wilq.actions.apply_lifecycle import apply_action as apply_action_lifecycle
from wilq.actions.authority_audit_context import stamp_authority_audit_context
from wilq.actions.mutation_readiness import vendor_write_possible
from wilq.actions.payloads import validate_action_payload
from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionCandidate,
    ContentCurrentDispositionReceipt,
    build_current_disposition_action,
    build_current_disposition_snapshot,
    current_disposition_action_for_proposal,
    current_disposition_action_payload_digest,
    current_disposition_receipt_digest,
    execute_current_disposition_authority,
    prepare_current_disposition_preview,
    read_current_disposition_authority,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import ActionApplyRequest, AuditEvent
from wilq.storage.local_state import LocalStateStore


def _preview_action(tmp_path) -> tuple[ContentWorkflowStore, object]:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    response = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=run.rows[0].current_work_item_id,
            proposed_final_disposition="keep",
        ),
    )
    return store, response.action


def _lifecycle_events(action) -> list[AuditEvent]:
    events = []
    for event_type in (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    ):
        event = AuditEvent(
            id=f"audit_{event_type}",
            action_id=action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
        )
        stamp_authority_audit_context(action, event)
        events.append(event)
    return events


def test_current_disposition_candidate_is_bound_to_one_exact_current_row(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    row = run.rows[0]

    snapshot = build_current_disposition_snapshot(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=row.current_work_item_id,
            proposed_final_disposition="keep",
        ),
    )

    assert snapshot.current_work_item_id == row.current_work_item_id
    assert snapshot.classification_source_row_digest == row.source_packet_row_digest
    assert snapshot.proposed_final_disposition == "keep"
    assert snapshot.context_digest != "0" * 64
    action = build_current_disposition_action(snapshot)
    assert (
        action.payload["current_disposition_authority"]["context_digest"]
        == snapshot.context_digest
    )
    assert action.payload["local_authority_only"] is True
    changed_snapshot = snapshot.model_copy(update={"context_digest": "f" * 64})
    assert build_current_disposition_action(changed_snapshot).id == action.id


def test_current_disposition_rejects_historical_classification(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    current = exact_public_bdo_run()
    historical = production_module._build_run(
        input_receipt=current.input.model_copy(
            update={
                "policy_id": "content_production_wave0_keep_packet_v1",
                "policy_digest": production_module.canonical_json_digest(
                    production_module.WAVE0_PRODUCTION_ACCEPTANCE_POLICY.model_dump(
                        mode="json"
                    )
                ),
            }
        ),
        counts=current.counts,
        freshness=current.freshness,
        source_receipts=current.source_receipts,
        judge_receipt=current.judge_receipt,
        rows=current.rows,
        audit=current.audit,
    )
    store.record_production_classification(historical)

    with pytest.raises(ValueError, match="Current production classification is unavailable"):
        build_current_disposition_snapshot(
            store,
            ContentCurrentDispositionCandidate(
                current_work_item_id=current.rows[0].current_work_item_id,
                proposed_final_disposition="keep",
            ),
        )


def test_store_persists_only_an_exact_current_disposition_candidate(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    candidate = ContentCurrentDispositionCandidate(
        current_work_item_id=run.rows[0].current_work_item_id,
        proposed_final_disposition="keep",
    )

    proposal = store.record_content_current_disposition_proposal(candidate)

    assert proposal.current_work_item_id == candidate.current_work_item_id
    assert proposal.prepared_snapshot_digest != "0" * 64
    assert store.load_content_current_disposition_proposal(proposal.action_id) == proposal
    action = current_disposition_action_for_proposal(store, proposal)
    assert action.id == proposal.action_id
    assert action.payload["runtime_blockers"] == []
    assert validate_action_payload("wordpress_ekologus", action.payload) == []
    assert vendor_write_possible(action, None) is False
    assert "draft_action_review_required" in action_confirmation_blockers(
        action,
        type("Request", (), {"preview_acknowledged": True})(),
        None,
        ads_target_blockers=lambda _request: [],
    )
    snapshot = build_current_disposition_snapshot(store, candidate)
    receipt = ContentCurrentDispositionReceipt.create(
        action=action,
        snapshot=snapshot,
        preview_audit_id="audit_preview",
        review_audit_id="audit_review",
        confirmation_audit_id="audit_confirmation",
        impact_audit_id="audit_impact",
        reviewed_by="wilku",
        confirmed_by="wilku",
    )
    assert receipt.authority_snapshot.context_digest == snapshot.context_digest
    result, errors = execute_current_disposition_authority(action, store=store, audit_events=[])
    assert result is None
    assert errors
    payload_digest = current_disposition_action_payload_digest(action)
    events = [
        AuditEvent(
            id=f"audit_{event_type}",
            action_id=action.id,
            event_type=event_type,
            actor="wilku",
            summary=event_type,
            details={
                "current_disposition_snapshot_digest": snapshot.context_digest,
                "current_disposition_action_payload_digest": payload_digest,
            },
        )
        for event_type in (
            "action_preview_generated",
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        )
    ]
    result, errors = execute_current_disposition_authority(
        action, store=store, audit_events=events
    )
    assert errors == []
    assert result is not None
    assert result["external_write_attempted"] is False
    assert store.load_content_current_disposition_receipt(action.id) is not None


def test_service_audit_stamp_binds_exact_current_disposition_payload(tmp_path) -> None:
    _store, action = _preview_action(tmp_path)
    event = AuditEvent(
        id="audit_service_stamp",
        action_id=action.id,
        event_type="action_preview_generated",
        actor="wilku",
        summary="preview",
    )

    stamp_authority_audit_context(action, event)

    snapshot = action.payload["current_disposition_authority"]
    assert event.details["current_disposition_snapshot_digest"] == snapshot["context_digest"]
    assert event.details["current_disposition_action_payload_digest"] == (
        current_disposition_action_payload_digest(action)
    )


def test_operator_projection_preserves_current_disposition_authority_digests() -> None:
    event = AuditEvent(
        id="audit_operator_projection",
        action_id="act_current_disposition_operator_projection",
        event_type="action_preview_generated",
        actor="wilq_api",
        summary="preview",
        details={
            "current_disposition_snapshot_digest": "4" * 64,
            "current_disposition_action_payload_digest": "5" * 64,
        },
    )

    projected = action_service._audit_event_with_operator_label(event)

    assert projected.details == event.details


def test_current_disposition_receipt_rejects_out_of_order_audit_chain(tmp_path) -> None:
    store, action = _preview_action(tmp_path)
    events = _lifecycle_events(action)
    events[0] = events[0].model_copy(
        update={"created_at": events[-1].created_at + timedelta(seconds=1)}
    )

    result, errors = execute_current_disposition_authority(
        action, store=store, audit_events=events
    )

    assert result is None
    assert errors == ["Current disposition audit chain is out of order."]
    assert store.load_content_current_disposition_receipt(action.id) is None


def test_service_dispatch_executes_only_local_current_disposition_receipt(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _preview_action(tmp_path)
    action.audit_events = _lifecycle_events(action)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)

    result, errors = action_service._execute_supported_mutation_adapter(
        action, "content_current_disposition_store"
    )

    assert errors == []
    assert result is not None
    assert result["external_write_attempted"] is False
    assert store.load_content_current_disposition_receipt(action.id) is not None


def test_local_current_disposition_receipt_applies_through_canonical_lifecycle(
    tmp_path,
) -> None:
    store, action = _preview_action(tmp_path)
    action.validation_status = "valid"
    action.audit_events = _lifecycle_events(action)
    dependencies = ApplyDependencies(
        review_gate=lambda value: value.review_gate,
        wordpress_apply_capability=lambda *_args: pytest.fail(
            "local receipt must not resolve WordPress capability"
        ),
        mutation_adapter=lambda _action: "content_current_disposition_store",
        execute_mutation_adapter=lambda value, _adapter, _capability: (
            execute_current_disposition_authority(
                value, store=store, audit_events=value.audit_events
            )
        ),
        connector_status=lambda _connector: SimpleNamespace(configured=False),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=lambda *_args: pytest.fail(
            "local receipt must not claim WordPress"
        ),
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
    assert read_current_disposition_authority(store, action_id=action.id).status == "current"


def test_current_disposition_canonical_lifecycle_reads_persisted_digest_chain(
    tmp_path,
) -> None:
    store, action = _preview_action(tmp_path)
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    stamped_events = _lifecycle_events(action)
    for event in stamped_events:
        audit_store.save_audit_event(event)

    persisted_events = audit_store.list_audit_events(action_id=action.id)
    assert len(persisted_events) == 4
    expected_snapshot_digest = action.payload["current_disposition_authority"]["context_digest"]
    expected_payload_digest = current_disposition_action_payload_digest(action)
    assert all(
        event.details["current_disposition_snapshot_digest"] == expected_snapshot_digest
        and event.details["current_disposition_action_payload_digest"] == expected_payload_digest
        for event in persisted_events
    )

    action.validation_status = "valid"
    action.audit_events = persisted_events
    dependencies = ApplyDependencies(
        review_gate=lambda value: value.review_gate,
        wordpress_apply_capability=lambda *_args: pytest.fail(
            "local receipt must not resolve WordPress capability"
        ),
        mutation_adapter=lambda _action: "content_current_disposition_store",
        execute_mutation_adapter=lambda value, _adapter, _capability: (
            execute_current_disposition_authority(
                value,
                store=store,
                audit_events=audit_store.list_audit_events(action_id=value.id),
            )
        ),
        connector_status=lambda _connector: SimpleNamespace(configured=False),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=lambda *_args: pytest.fail(
            "local receipt must not claim WordPress"
        ),
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
    receipt = store.load_content_current_disposition_receipt(action.id)
    assert receipt is not None
    assert receipt.action_payload_digest == expected_payload_digest
    assert receipt.authority_snapshot.context_digest == expected_snapshot_digest


def test_read_projection_does_not_report_current_when_receipt_rebuild_drifts(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _preview_action(tmp_path)
    action.audit_events = _lifecycle_events(action)
    result, errors = execute_current_disposition_authority(
        action, store=store, audit_events=action.audit_events
    )
    assert errors == []
    assert result is not None
    receipt = store.load_content_current_disposition_receipt(action.id)
    assert receipt is not None

    current_run = exact_public_bdo_run()
    changed_rows = tuple(
        row.model_copy(update={"canonical_path": f"{row.canonical_path}-changed"})
        for row in current_run.rows
    )
    monkeypatch.setattr(
        store,
        "load_latest_production_classification",
        lambda: current_run.model_copy(update={"rows": changed_rows}),
    )

    projection = read_current_disposition_authority(store, action_id=action.id)

    assert projection.status == "blocked"
    assert projection.action is not None
    assert projection.action.status == "blocked"
    assert projection.receipt == receipt
    assert projection.blockers[0].reason == "current_disposition_snapshot_drift"


def test_existing_proposal_rebuild_is_blocked_not_preview_ready_after_drift(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _preview_action(tmp_path)
    proposal = store.load_content_current_disposition_proposal(action.id)
    assert proposal is not None
    current_run = exact_public_bdo_run()
    changed_rows = tuple(
        row.model_copy(update={"canonical_path": f"{row.canonical_path}-changed"})
        for row in current_run.rows
    )
    monkeypatch.setattr(
        store,
        "load_latest_production_classification",
        lambda: current_run.model_copy(update={"rows": changed_rows}),
    )

    response = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=proposal.current_work_item_id,
            proposed_final_disposition=proposal.proposed_final_disposition,
        ),
    )

    assert response.status == "blocked"
    assert response.action.status == "blocked"
    assert response.action.payload["runtime_blockers"] == [
        "current_disposition_snapshot_drift"
    ]


def test_read_projection_returns_typed_blocker_when_current_row_disappears(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, action = _preview_action(tmp_path)
    current_run = exact_public_bdo_run()
    current_work_item_id = action.payload["current_disposition_authority"]["current_work_item_id"]
    missing_rows = tuple(
        row for row in current_run.rows if row.current_work_item_id != current_work_item_id
    )
    monkeypatch.setattr(
        store,
        "load_latest_production_classification",
        lambda: current_run.model_copy(update={"rows": missing_rows}),
    )
    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)

    projection = read_current_disposition_authority(store, action_id=action.id)

    assert projection.status == "blocked"
    assert projection.action is None
    assert projection.receipt is None
    assert projection.blockers[0].reason == "current_disposition_row_missing"
    assert authority_router.content_current_disposition_read_endpoint(action.id).status == "blocked"


def test_current_disposition_proposal_replace_cannot_mutate_append_only_row(tmp_path) -> None:
    store, action = _preview_action(tmp_path)
    proposal = store.load_content_current_disposition_proposal(action.id)
    assert proposal is not None
    retry = store.record_content_current_disposition_proposal(
        ContentCurrentDispositionCandidate(
            current_work_item_id=proposal.current_work_item_id,
            proposed_final_disposition=proposal.proposed_final_disposition,
        )
    )
    assert retry == proposal

    replacement = proposal.model_validate(
        proposal.model_dump(mode="json") | {"prepared_snapshot_digest": "f" * 64}
    )
    with store._connect() as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "INSERT OR REPLACE INTO content_current_disposition_proposals "
            "(action_id, proposal_digest, current_work_item_id, payload_json) "
            "VALUES (?, ?, ?, ?)",
            (
                replacement.action_id,
                replacement.proposal_digest,
                replacement.current_work_item_id,
                replacement.model_dump_json(),
            ),
        )

    assert store.load_content_current_disposition_proposal(action.id) == proposal


def test_current_disposition_receipt_replace_cannot_mutate_append_only_row(tmp_path) -> None:
    store, action = _preview_action(tmp_path)
    events = _lifecycle_events(action)
    result, errors = execute_current_disposition_authority(
        action, store=store, audit_events=events
    )
    assert errors == []
    assert result is not None
    receipt = store.load_content_current_disposition_receipt(action.id)
    assert receipt is not None
    status, retried = store.record_content_current_disposition_receipt(receipt)
    assert status == "idempotent"
    assert retried == receipt

    replacement_data = receipt.model_dump(mode="json") | {"confirmed_by": "other_operator"}
    replacement_data["receipt_digest"] = "0" * 64
    replacement_data["receipt_id"] = ""
    replacement_data["receipt_digest"] = current_disposition_receipt_digest(replacement_data)
    replacement_data["receipt_id"] = (
        f"content_current_disposition_{replacement_data['receipt_digest'][:24]}"
    )
    replacement = receipt.model_validate(replacement_data)
    with store._connect() as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "INSERT OR REPLACE INTO content_current_disposition_receipts "
            "(receipt_id, receipt_digest, action_id, current_work_item_id, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                replacement.receipt_id,
                replacement.receipt_digest,
                replacement.action_id,
                replacement.authority_snapshot.current_work_item_id,
                replacement.model_dump_json(),
            ),
        )

    assert store.load_content_current_disposition_receipt(action.id) == receipt


def test_poisoned_stable_action_uses_explicit_append_only_attempt(
    tmp_path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    stable = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id="content_work_item_inventory_5391632ca65d5e8714952a84",
            proposed_final_disposition="keep",
        ),
    )
    stable_proposal = store.load_content_current_disposition_proposal(stable.action.id)
    assert stable_proposal is not None

    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    legacy_events = [
        event.model_copy(
            update={
                "details": {
                    "current_disposition_snapshot_digest": "[REDACTED]",
                    "current_disposition_action_payload_digest": "[REDACTED]",
                }
            }
        )
        for event in _lifecycle_events(stable.action)
    ]
    for event in legacy_events:
        audit_store.save_audit_event(event)

    retry = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=stable_proposal.current_work_item_id,
            proposed_final_disposition=stable_proposal.proposed_final_disposition,
            attempt=1,
        ),
    )
    retry_proposal = store.load_content_current_disposition_proposal(retry.action.id)
    assert retry_proposal is not None
    assert retry.action.id != stable.action.id
    assert retry.action.payload["attempt"] == 1
    assert store.load_content_current_disposition_proposal(stable.action.id) == stable_proposal

    result, errors = execute_current_disposition_authority(
        retry.action,
        store=store,
        audit_events=_lifecycle_events(retry.action),
    )
    assert errors == []
    assert result is not None
    assert result["external_write_attempted"] is False
    assert store.load_content_current_disposition_receipt(stable.action.id) is None
    assert store.load_content_current_disposition_receipt(retry.action.id) is not None

    preserved = audit_store.list_audit_events(action_id=stable.action.id)
    assert {event.id for event in preserved} == {event.id for event in legacy_events}
    assert all(
        event.details["current_disposition_snapshot_digest"] == "[REDACTED]"
        for event in preserved
    )


def test_preview_router_uses_typed_server_side_current_disposition_preview(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)

    response = authority_router.content_current_disposition_preview_endpoint(
        ContentCurrentDispositionCandidate(
            current_work_item_id=run.rows[0].current_work_item_id,
            proposed_final_disposition="keep",
        )
    )

    assert response.status == "preview_ready"
    assert response.action.payload["local_authority_only"] is True
    assert authority_router.content_current_disposition_read_endpoint(
        response.action.id
    ).status == "preview_ready"


def test_current_disposition_api_exposes_preview_and_read_only() -> None:
    preview_methods = app.openapi()["paths"][
        "/api/content/current-disposition-authorities/preview"
    ]
    read_methods = app.openapi()["paths"][
        "/api/content/current-disposition-authorities/{action_id}"
    ]
    approve_methods = app.openapi()["paths"][
        "/api/content/current-disposition-authorities/{action_id}/approve"
    ]

    assert set(preview_methods) >= {"post"}
    assert "get" not in preview_methods
    assert set(read_methods) >= {"get"}
    assert "post" not in read_methods
    assert set(approve_methods) >= {"post"}


def test_current_disposition_latest_rejected_review_blocks_direct_apply(tmp_path) -> None:
    store, action = _preview_action(tmp_path)
    snapshot_digest = action.payload["current_disposition_authority"]["context_digest"]
    payload_digest = current_disposition_action_payload_digest(action)
    events = _lifecycle_events(action)
    rejected = AuditEvent(
        id="audit_latest_rejected",
        action_id=action.id,
        event_type="human_review_rejected",
        actor="local_operator",
        summary="rejected",
        details={
            "current_disposition_snapshot_digest": snapshot_digest,
            "current_disposition_action_payload_digest": payload_digest,
        },
        created_at=events[-1].created_at + timedelta(seconds=1),
    )
    action.audit_events = [rejected, *events]
    assert "draft_action_review_required" in action_confirmation_blockers(
        action,
        type("Request", (), {"preview_acknowledged": True})(),
        events[0],
        ads_target_blockers=lambda _request: [],
    )

    result, errors = execute_current_disposition_authority(
        action,
        store=store,
        audit_events=action.audit_events,
    )

    assert result is None
    assert errors == ["Current disposition audit chain is not valid."]
    assert store.load_content_current_disposition_receipt(action.id) is None
