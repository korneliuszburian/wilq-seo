from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.workflow import current_page_evidence as current_page_evidence_module
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import (
    ConnectorCapability,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
)
from wilq.storage.local_state import LocalStateStore


def _evidence(
    work_item_id: str,
    digest: str,
    current_ids: list[str],
    catalog_ids: list[str],
) -> CurrentPageEvidenceResponse:
    slug = "a" if work_item_id == "wi_a" else "b"
    return CurrentPageEvidenceResponse(
        status="observed_material_current",
        decision="Materiał ma dokładny bieżący odczyt.",
        work_item_id=work_item_id,
        page_url=f"https://www.ekologus.pl/{slug}/",
        material_meaning_digest=digest,
        current_evidence_ids=current_ids,
        catalog_evidence_ids=catalog_ids,
        safe_next_step="Sprawdź exact adres.",
    )


def _prepare_action(client: TestClient, action_id: str) -> None:
    validation = client.post(f"/api/actions/{action_id}/validate")
    assert validation.status_code == 200, validation.text
    assert validation.json()["valid"] is True
    readiness = client.get(f"/api/actions/{action_id}/mutation-readiness")
    assert readiness.status_code == 200, readiness.text
    connector_requirement = next(
        item for item in readiness.json()["requirements"] if item["code"] == "connector_configured"
    )
    assert connector_requirement["satisfied"] is True
    assert connector_requirement["evidence"] == "local_authority_only; no vendor write"
    preview = client.post(f"/api/actions/{action_id}/preview", json={})
    assert preview.status_code == 200, preview.text
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "wilku",
            "notes": "Sprawdzono exact snapshot KEEP.",
        },
    )
    assert review.status_code == 200, review.text
    confirmation = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "wilku",
            "notes": "Potwierdzam lokalny receipt KEEP.",
            "preview_acknowledged": True,
        },
    )
    assert confirmation.status_code == 200, confirmation.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "wilku", "notes": "Wpływ lokalny sprawdzony."},
    )
    assert impact.status_code == 200, impact.text


def _preview(client: TestClient, work_item_id: str, digest: str) -> dict[str, Any]:
    response = client.post(
        "/api/content/current-page-dispositions/preview",
        json={
            "work_item_id": work_item_id,
            "expected_material_meaning_digest": digest,
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


@pytest.fixture
def public_v2_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    TestClient,
    ContentWorkflowStore,
    dict[str, CurrentPageEvidenceResponse],
    pytest.MonkeyPatch,
]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    current = {
        "wi_a": _evidence("wi_a", "a" * 64, ["wp_a_1"], ["catalog_1"]),
        "wi_b": _evidence("wi_b", "b" * 64, ["wp_b_1"], ["catalog_1"]),
    }
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: current[work_item_id],
        raising=False,
    )
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)

    import apps.api.wilq_api.routers.actions as actions_router
    import wilq.actions.action_catalog as action_catalog
    import wilq.actions.action_validation as action_validation_module
    import wilq.actions.audit_store as audit_store_module
    import wilq.actions.service as action_service

    unconfigured_wordpress = ConnectorStatus(
        id="wordpress_ekologus",
        label="WordPress Ekologus",
        status=ConnectorStatusValue.missing_credentials,
        configured=False,
        freshness=FreshnessState(state="unknown"),
        capabilities=ConnectorCapability(read=True, write=False),
        health_check="Unconfigured test connector.",
    )

    def connector_status(connector_id: str) -> ConnectorStatus | None:
        return unconfigured_wordpress if connector_id == "wordpress_ekologus" else None

    monkeypatch.setattr(action_validation_module, "get_connector_status", connector_status)
    monkeypatch.setattr(action_service, "get_connector_status", connector_status)
    monkeypatch.setattr(action_catalog, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_validation_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(audit_store_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(actions_router, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(
        action_service,
        "wordpress_draft_apply_capability",
        lambda *_args, **_kwargs: pytest.fail("Local KEEP must not reach WordPress."),
    )
    return TestClient(app), store, current, monkeypatch


def test_public_http_lifecycle_keeps_unchanged_url_and_blocks_changed_material(
    public_v2_runtime: tuple[
        TestClient,
        ContentWorkflowStore,
        dict[str, CurrentPageEvidenceResponse],
        pytest.MonkeyPatch,
    ],
) -> None:
    client, store, current, monkeypatch = public_v2_runtime
    action_a = _preview(client, "wi_a", "a" * 64)
    if hasattr(current_page_evidence_module, "read_current_page_evidence_current"):
        monkeypatch.setattr(
            current_page_evidence_module,
            "read_current_page_evidence_current",
            lambda work_item_id: current[work_item_id],
        )
    action_a_id = action_a["action_id"]
    original_a_snapshot = action_a["proposal"]["snapshot"]
    _assert_stale_preview_does_not_write(client, store, monkeypatch)
    current["wi_a"] = _evidence("wi_a", "a" * 64, ["wp_a_rotated"], ["catalog_rotated"])
    repeated_a = _preview(client, "wi_a", "a" * 64)
    assert repeated_a["action_id"] == action_a_id
    assert repeated_a["proposal"]["snapshot"] == original_a_snapshot
    action_b_old_id = _preview(client, "wi_b", "b" * 64)["action_id"]
    assert action_b_old_id != action_a_id
    _prepare_action(client, action_a_id)
    _prepare_action(client, action_b_old_id)
    applied_a = _apply_unchanged_a_after_b_changes(client, current, action_a_id)
    _assert_old_b_is_blocked(client, store, action_b_old_id)
    action_b_new_id, _applied_b = _apply_new_b(client, action_b_old_id)
    _assert_current_receipts_and_audit(client, action_a_id, action_b_new_id)
    assert applied_a["adapter_result"]["external_write_attempted"] is False


def _assert_stale_preview_does_not_write(
    client: TestClient,
    store: ContentWorkflowStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_writer = getattr(store, "record_current_page_disposition_v2_proposal", None)
    assert proposal_writer is not None
    writes: list[bool] = []

    def record_proposal(proposal: Any) -> Any:
        writes.append(True)
        return proposal_writer(proposal)

    monkeypatch.setattr(store, "record_current_page_disposition_v2_proposal", record_proposal)
    stale_preview = client.post(
        "/api/content/current-page-dispositions/preview",
        json={"work_item_id": "wi_a", "expected_material_meaning_digest": "c" * 64},
    )
    assert stale_preview.status_code == 409, stale_preview.text
    assert stale_preview.json()["status"] == "blocked"
    assert stale_preview.json()["safe_next_step"] == (
        "Odczytaj nowy material_meaning_digest i przygotuj nowy preview dla tego URL-a."
    )
    assert writes == []


def _apply_unchanged_a_after_b_changes(
    client: TestClient,
    current: dict[str, CurrentPageEvidenceResponse],
    action_a_id: str,
) -> dict[str, Any]:
    current["wi_b"] = _evidence("wi_b", "d" * 64, ["wp_b_changed"], ["catalog_rotated"])
    applied_a = client.post(
        f"/api/actions/{action_a_id}/apply",
        json={"confirm": True, "confirmed_by": "wilku"},
    )
    assert applied_a.status_code == 200, applied_a.text
    current["wi_a"] = _evidence("wi_a", "e" * 64, ["wp_a_changed"], ["catalog_rotated"])
    blocked_readback_a = client.get(f"/api/content/current-page-dispositions/{action_a_id}")
    assert blocked_readback_a.status_code == 200, blocked_readback_a.text
    assert blocked_readback_a.json()["status"] == "blocked"
    assert (
        blocked_readback_a.json()["receipt"]["receipt_id"]
        == applied_a.json()["adapter_result"]["receipt_id"]
    )
    current["wi_a"] = _evidence("wi_a", "a" * 64, ["wp_a_rotated"], ["catalog_rotated"])
    return cast(dict[str, Any], applied_a.json())


def _assert_old_b_is_blocked(
    client: TestClient,
    store: ContentWorkflowStore,
    action_b_old_id: str,
) -> None:
    stale_apply_b = client.post(
        f"/api/actions/{action_b_old_id}/apply",
        json={"confirm": True, "confirmed_by": "wilku"},
    )
    assert stale_apply_b.status_code == 409, stale_apply_b.text
    assert store.load_current_page_disposition_v2_receipt(action_b_old_id) is None
    stale_readback_b = client.get(f"/api/content/current-page-dispositions/{action_b_old_id}")
    assert stale_readback_b.status_code == 200, stale_readback_b.text
    assert stale_readback_b.json()["status"] == "blocked"
    assert stale_readback_b.json()["proposal"] is not None
    assert stale_readback_b.json()["receipt"] is None
    assert stale_readback_b.json()["safe_next_step"] == (
        "Odczytaj nowy material_meaning_digest i przygotuj nowy preview dla tego URL-a."
    )


def _apply_new_b(client: TestClient, action_b_old_id: str) -> tuple[str, dict[str, Any]]:
    action_b_new_id = _preview(client, "wi_b", "d" * 64)["action_id"]
    assert action_b_new_id != action_b_old_id
    _prepare_action(client, action_b_new_id)
    applied_b = client.post(
        f"/api/actions/{action_b_new_id}/apply",
        json={"confirm": True, "confirmed_by": "wilku"},
    )
    assert applied_b.status_code == 200, applied_b.text
    assert applied_b.json()["adapter_result"]["external_write_attempted"] is False
    return action_b_new_id, cast(dict[str, Any], applied_b.json())


def _assert_current_receipts_and_audit(
    client: TestClient,
    action_a_id: str,
    action_b_new_id: str,
) -> None:
    readback_a = client.get(f"/api/content/current-page-dispositions/{action_a_id}")
    readback_b = client.get(f"/api/content/current-page-dispositions/{action_b_new_id}")
    assert readback_a.status_code == readback_b.status_code == 200
    assert readback_a.json()["status"] == readback_b.json()["status"] == "current"
    assert readback_a.json()["receipt"]["snapshot"]["material_meaning_digest"] == "a" * 64
    assert readback_a.json()["receipt"]["snapshot"]["current_evidence_ids"] == ["wp_a_1"]
    assert readback_a.json()["receipt"]["verification_evidence_ids"] == [
        "catalog_rotated",
        "wp_a_rotated",
    ]
    assert readback_a.json()["receipt"]["verified_at"].endswith("Z")
    assert readback_a.json()["receipt"]["generation_allowed"] is False
    events = client.get("/api/audit/events", params={"action_id": action_b_new_id}).json()
    assert {event["event_type"] for event in events} >= {
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
        "apply_succeeded",
    }
    assert all(
        event["details"]["current_disposition_snapshot_digest"]
        == readback_b.json()["proposal"]["snapshot"]["context_digest"]
        and event["details"]["current_disposition_action_payload_digest"]
        == readback_b.json()["receipt"]["action_payload_digest"]
        for event in events
        if event["event_type"] != "apply_succeeded"
    )
