from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.actions import service as action_service
from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.workflow.current_disposition_approval import (
    ContentCurrentDispositionApprovalRequest,
    approve_current_disposition_authority,
)
from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionCandidate,
    current_disposition_action_payload_digest,
    execute_current_disposition_authority,
    prepare_current_disposition_preview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import AuditEvent
from wilq.storage.local_state import LocalStateStore


def _prepare(tmp_path, monkeypatch):
    path = tmp_path / "state.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(path))
    store = ContentWorkflowStore(path)
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    preview = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=run.rows[0].current_work_item_id,
            proposed_final_disposition="keep",
        ),
    )
    assert preview.action is not None
    audit = LocalStateStore(path)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    action = preview.action
    preview_result = action_service.preview_action(action)
    return store, audit, action, preview_result.audit_event


def _request(action, preview_event):
    return ContentCurrentDispositionApprovalRequest(
        expected_snapshot_digest=action.payload["current_disposition_authority"]["context_digest"],
        expected_action_payload_digest=current_disposition_action_payload_digest(action),
        expected_preview_audit_id=preview_event.id,
        confirm=True,
        notes="Zatwierdzam exact lokalny receipt.",
    )


def test_approval_creates_local_receipt_and_retry_is_idempotent(tmp_path, monkeypatch) -> None:
    store, audit, action, preview_event = _prepare(tmp_path, monkeypatch)

    first = approve_current_disposition_authority(
        store,
        action_id=action.id,
        request=_request(action, preview_event),
        audit_store=audit,
    )

    assert first.status == "current"
    assert first.receipt is not None
    assert first.external_write_attempted is False
    event_ids = [event.id for event in audit.list_audit_events(action_id=action.id)]
    assert len(event_ids) == 5

    second = approve_current_disposition_authority(
        store,
        action_id=action.id,
        request=_request(action, preview_event),
        audit_store=audit,
    )

    assert second.status == "current"
    assert second.receipt == first.receipt
    assert second.projection == first.projection
    assert [event.id for event in audit.list_audit_events(action_id=action.id)] == event_ids


def test_identical_approval_threads_share_one_lifecycle(tmp_path, monkeypatch) -> None:
    store, audit, action, preview_event = _prepare(tmp_path, monkeypatch)
    request = _request(action, preview_event)

    def approve():
        return approve_current_disposition_authority(
            store,
            action_id=action.id,
            request=request,
            audit_store=audit,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = tuple(executor.map(lambda _index: approve(), (1, 2)))

    assert first.status == second.status == "current"
    assert first.receipt is not None
    assert second.receipt == first.receipt
    events = audit.list_audit_events(action_id=action.id)
    lifecycle_counts = Counter(
        event.event_type
        for event in events
        if event.event_type
        in {
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        }
    )
    assert lifecycle_counts == Counter(
        {
            "human_review_approved_for_prepare": 1,
            "action_apply_confirmed": 1,
            "action_impact_check_completed": 1,
        }
    )
    assert not any(
        event.event_type
        in {
            "human_review_rejected",
            "action_confirmation_blocked",
            "action_impact_check_blocked",
            "apply_blocked",
        }
        for event in events
    )


def test_generic_action_apply_blocks_current_disposition_without_audit_append(
    tmp_path, monkeypatch
) -> None:
    store, audit, action, _preview_event = _prepare(tmp_path, monkeypatch)
    before = [event.id for event in audit.list_audit_events(action_id=action.id)]

    response = TestClient(app).post(
        f"/api/actions/{action.id}/apply",
        json={"confirm": True, "confirmed_by": "local_operator"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "current_disposition_approval_required"
    assert detail["external_write_attempted"] is False
    assert [event.id for event in audit.list_audit_events(action_id=action.id)] == before


def test_action_chain_uses_highest_id_when_created_at_ties() -> None:
    timestamp = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
    events = [
        AuditEvent(
            id="preview_a",
            action_id="action",
            event_type="action_preview_generated",
            actor="local_operator",
            summary="preview",
            created_at=timestamp,
        ),
        AuditEvent(
            id="preview_z",
            action_id="action",
            event_type="action_preview_generated",
            actor="local_operator",
            summary="preview",
            created_at=timestamp,
        ),
        AuditEvent(
            id="review",
            action_id="action",
            event_type="human_review_approved_for_prepare",
            actor="local_operator",
            summary="review",
            created_at=timestamp,
        ),
        AuditEvent(
            id="confirm",
            action_id="action",
            event_type="action_apply_confirmed",
            actor="local_operator",
            summary="confirm",
            created_at=timestamp,
        ),
        AuditEvent(
            id="impact",
            action_id="action",
            event_type="action_impact_check_completed",
            actor="local_operator",
            summary="impact",
            created_at=timestamp,
        ),
    ]

    chain, blockers = revision_bound_action_chain(
        events,
        confirmed_by="local_operator",
    )

    assert blockers == []
    assert chain is not None
    assert chain[0].id == "preview_z"


def test_public_approval_and_readback_are_local_only(tmp_path, monkeypatch) -> None:
    store, audit, action, preview_event = _prepare(tmp_path, monkeypatch)
    client = TestClient(app)
    payload = _request(action, preview_event).model_dump(mode="json")

    response = client.post(
        f"/api/content/current-disposition-authorities/{action.id}/approve",
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "current"
    assert body["receipt"]["action_id"] == action.id
    assert body["external_write_attempted"] is False
    readback = client.get(f"/api/content/current-disposition-authorities/{action.id}")
    assert readback.status_code == 200
    assert readback.json()["status"] == "current"


def test_new_explicit_approval_supersedes_an_older_rejection(tmp_path, monkeypatch) -> None:
    store, audit, action, preview_event = _prepare(tmp_path, monkeypatch)
    audit.save_audit_event(
        AuditEvent(
            id="older_rejection",
            action_id=action.id,
            event_type="human_review_rejected",
            actor="local_operator",
            summary="older rejection",
            created_at=preview_event.created_at - timedelta(seconds=1),
            details={
                "current_disposition_snapshot_digest": action.payload[
                    "current_disposition_authority"
                ]["context_digest"],
                "current_disposition_action_payload_digest": (
                    current_disposition_action_payload_digest(action)
                ),
            },
        )
    )

    result = approve_current_disposition_authority(
        store,
        action_id=action.id,
        request=_request(action, preview_event),
        audit_store=audit,
    )

    assert result.status == "current"
    assert result.receipt is not None
    assert any(
        event.event_type == "human_review_approved_for_prepare"
        for event in audit.list_audit_events(action_id=action.id)
    )


def test_public_approval_returns_typed_409_for_foreign_preview(tmp_path, monkeypatch) -> None:
    store, _audit, action, _preview_event = _prepare(tmp_path, monkeypatch)
    client = TestClient(app)
    payload = _request(action, type("Preview", (), {"id": "foreign_preview"})()).model_dump(
        mode="json"
    )

    response = client.post(
        f"/api/content/current-disposition-authorities/{action.id}/approve",
        json=payload,
    )

    assert response.status_code == 409
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["reason"] == "current_disposition_preview_mismatch"


def test_executor_uses_newest_valid_chain_over_older_invalid_chain(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    preview = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=run.rows[0].current_work_item_id,
            proposed_final_disposition="keep",
        ),
    )
    assert preview.action is not None
    action = preview.action
    snapshot = action.payload["current_disposition_authority"]
    binding = {
        "current_disposition_snapshot_digest": snapshot["context_digest"],
        "current_disposition_action_payload_digest": current_disposition_action_payload_digest(
            action
        ),
    }
    base = _events_for_executor(action, binding=binding)
    old = [
        event.model_copy(
            update={
                "id": f"old_{event.id}",
                "created_at": event.created_at - timedelta(days=1),
                "details": {**binding, "current_disposition_snapshot_digest": "f" * 64},
            }
        )
        for event in base
    ]

    result, errors = execute_current_disposition_authority(
        action,
        store=store,
        audit_events=[*old, *base],
    )

    assert errors == []
    assert result is not None
    assert store.load_content_current_disposition_receipt(action.id) is not None


def test_executor_accepts_full_audit_stream_beyond_ten_events(tmp_path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    preview = prepare_current_disposition_preview(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=run.rows[0].current_work_item_id,
            proposed_final_disposition="keep",
        ),
    )
    assert preview.action is not None
    action = preview.action
    binding = {
        "current_disposition_snapshot_digest": action.payload["current_disposition_authority"][
            "context_digest"
        ],
        "current_disposition_action_payload_digest": current_disposition_action_payload_digest(
            action
        ),
    }
    chain = _events_for_executor(action, binding=binding)
    audit = LocalStateStore(store.path)
    for index in range(12):
        audit.save_audit_event(
            AuditEvent(
                id=f"noise_{index}",
                action_id=action.id,
                event_type="operator_note",
                actor="local_operator",
                summary="noise",
            )
        )
    for event in chain:
        audit.save_audit_event(event)

    result, errors = execute_current_disposition_authority(
        action,
        store=store,
        audit_events=audit.list_audit_events(action_id=action.id),
    )

    assert errors == []
    assert result is not None


def _events_for_executor(action, *, binding: dict[str, str]) -> list[AuditEvent]:
    event_types = (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    )
    return [
        AuditEvent(
            id=f"executor_{event_type}",
            action_id=action.id,
            event_type=event_type,
            actor="local_operator",
            summary=event_type,
            details=binding,
        )
        for event_type in event_types
    ]
