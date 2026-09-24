from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_per_url_disposition_authority
from tests.content.test_per_url_decision_authority import _identity, _policy_facts
from wilq.content.workflow import per_url_decision_authority as decision_authority
from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlDecisionObservation,
    build_content_per_url_decision_observation,
)
from wilq.content.workflow.per_url_disposition_authority import (
    PER_URL_DISPOSITION_ACTION_TYPE,
    PerUrlDispositionCandidate,
    prepare_per_url_disposition_preview,
    read_per_url_disposition_authority,
)
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def _record_observation(
    store: ContentWorkflowStore,
    *,
    material_digest: str,
    fact_digest: str,
    evidence_suffix: str,
    observed_at: datetime,
    wave_id: str,
    page_key: str = "disposition-page",
    work_item_id: str | None = None,
) -> ContentPerUrlDecisionObservation:
    identity = _identity(
        work_item_id or f"work-item-{page_key}",
        f"/{page_key}/",
        material_digest,
        evidence_suffix=evidence_suffix,
    )
    facts = _policy_facts(
        decision_authority,
        identity,
        fact_digest=fact_digest,
        evidence_suffix=evidence_suffix,
        checked_at=observed_at,
    )
    observation = build_content_per_url_decision_observation(
        identity, facts, observed_at=observed_at, source_wave_id=wave_id
    )
    status, recorded = store.record_content_per_url_decision_observation(observation)
    assert status == "created"
    return recorded


def _run_public_lifecycle(client: TestClient, action_id: str) -> str:
    assert client.post(f"/api/actions/{action_id}/validate").json()["valid"]
    preview = client.post(f"/api/actions/{action_id}/preview", json={})
    assert preview.status_code == 200, preview.text
    preview_audit_id = preview.json()["audit_event"]["id"]
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "synthetic_wilku",
            "notes": "Review exact semantic row.",
        },
    )
    assert review.status_code == 200, review.text
    confirm = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "synthetic_wilku",
            "notes": "Confirm local receipt only.",
            "preview_acknowledged": True,
        },
    )
    assert confirm.status_code == 200, confirm.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={
            "checked_by": "synthetic_wilku",
            "notes": "No external mutation is available.",
        },
    )
    assert impact.status_code == 200, impact.text
    assert impact.json()["status"] == "checked"
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic_wilku"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied"] is True
    return preview_audit_id


def test_public_per_url_action_runs_audited_local_lifecycle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = tmp_path / "workflow.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(database))
    store = ContentWorkflowStore(database)
    now = datetime.now(UTC)
    observation = _record_observation(
        store,
        material_digest="a" * 64,
        fact_digest="b" * 64,
        evidence_suffix="first",
        observed_at=now,
        wave_id="wave-a",
    )
    audit = LocalStateStore(database)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        content_per_url_disposition_authority, "content_workflow_store", lambda: store
    )
    from wilq.actions import service as action_service

    monkeypatch.setattr(action_service, "local_state_store", lambda: audit)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)

    client = TestClient(app)
    preview_response = client.post(
        "/api/content/per-url-disposition-authorities/preview",
        json={"observation_id": observation.observation_id},
    )
    assert preview_response.status_code == 200, preview_response.text
    action_id = preview_response.json()["action"]["id"]
    action_response = client.get(f"/api/actions/{action_id}")
    assert action_response.status_code == 200, action_response.text
    action = action_response.json()
    assert action["payload"]["action_type"] == PER_URL_DISPOSITION_ACTION_TYPE
    snapshot = action["payload"]["per_url_disposition_authority"]
    assert snapshot["semantic_row_digest"] == observation.semantic_row_digest
    assert snapshot["observation_id"] == observation.observation_id
    assert "classification_run_digest" not in snapshot
    assert "google_search_console" not in snapshot

    preview_audit_id = _run_public_lifecycle(client, action_id)
    receipt = store.load_per_url_disposition_receipt(action_id)
    assert receipt is not None
    assert receipt.snapshot.semantic_row_digest == observation.semantic_row_digest
    assert receipt.preview_audit_id == preview_audit_id
    assert receipt.reviewed_by == "local_operator"
    readback = client.get(f"/api/content/per-url-disposition-authorities/{action_id}")
    assert readback.status_code == 200, readback.text
    assert readback.json()["status"] == "current"
    assert readback.json()["receipt"]["receipt_id"] == receipt.receipt_id

    with sqlite3.connect(store.path) as connection:
        for statement in (
            "UPDATE content_per_url_disposition_receipts "
            "SET payload_json = '{}' WHERE action_id = ?",
            "DELETE FROM content_per_url_disposition_receipts WHERE action_id = ?",
        ):
            try:
                connection.execute(statement, (action_id,))
            except sqlite3.DatabaseError as error:
                assert "append-only" in str(error)
            else:
                raise AssertionError("Per-URL disposition receipts accepted mutation.")


def test_changed_semantic_row_blocks_old_per_url_disposition_and_is_append_only(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    now = datetime.now(UTC)
    first = _record_observation(
        store,
        material_digest="a" * 64,
        fact_digest="b" * 64,
        evidence_suffix="first",
        observed_at=now,
        wave_id="wave-a",
    )
    preview = prepare_per_url_disposition_preview(
        store, PerUrlDispositionCandidate(observation_id=first.observation_id), now=now
    )
    assert preview.status == "preview_ready"
    assert preview.action is not None

    _record_observation(
        store,
        material_digest="c" * 64,
        fact_digest="d" * 64,
        evidence_suffix="second",
        observed_at=now + timedelta(minutes=1),
        wave_id="wave-b",
    )
    readback = read_per_url_disposition_authority(store, action_id=preview.action.id, now=now)
    assert readback.status == "blocked"
    assert readback.blockers[0].code == "per_url_semantic_row_superseded"
    assert readback.action is not None
    assert readback.action.status.value == "blocked"
    assert store.load_per_url_disposition_receipt(preview.action.id) is None

    with sqlite3.connect(store.path) as connection:
        for statement in (
            "UPDATE content_per_url_disposition_proposals "
            "SET payload_json = '{}' WHERE action_id = ?",
            "DELETE FROM content_per_url_disposition_proposals WHERE action_id = ?",
        ):
            try:
                connection.execute(statement, (preview.action.id,))
            except sqlite3.DatabaseError as error:
                assert "append-only" in str(error)
            else:
                raise AssertionError("Per-URL disposition proposals accepted mutation.")


def test_expired_per_url_evidence_blocks_new_disposition_preview(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    now = datetime.now(UTC)
    observation = _record_observation(
        store,
        material_digest="a" * 64,
        fact_digest="b" * 64,
        evidence_suffix="expired",
        observed_at=now - timedelta(hours=49),
        wave_id="old-wave",
    )

    preview = prepare_per_url_disposition_preview(
        store,
        PerUrlDispositionCandidate(observation_id=observation.observation_id),
        now=now,
    )

    assert preview.status == "blocked"
    assert preview.action is None
    assert preview.blockers[0].code == "per_url_freshness_assessment_expired"


def test_other_url_semantic_change_does_not_supersede_per_url_disposition(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    now = datetime.now(UTC)
    observation = _record_observation(
        store,
        material_digest="a" * 64,
        fact_digest="b" * 64,
        evidence_suffix="page-a",
        observed_at=now,
        wave_id="wave-a",
    )
    preview = prepare_per_url_disposition_preview(
        store, PerUrlDispositionCandidate(observation_id=observation.observation_id), now=now
    )
    assert preview.action is not None

    _record_observation(
        store,
        material_digest="c" * 64,
        fact_digest="d" * 64,
        evidence_suffix="page-b",
        observed_at=now + timedelta(minutes=1),
        wave_id="wave-b",
        page_key="unrelated-page",
    )

    readback = read_per_url_disposition_authority(store, action_id=preview.action.id, now=now)
    assert readback.status == "preview_ready"
    assert readback.blockers == ()


def test_moved_same_work_item_supersedes_old_per_url_disposition(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    now = datetime.now(UTC)
    first = _record_observation(
        store,
        material_digest="a" * 64,
        fact_digest="b" * 64,
        evidence_suffix="original-url",
        observed_at=now,
        wave_id="wave-a",
        page_key="original-page",
        work_item_id="work-item-stable",
    )
    preview = prepare_per_url_disposition_preview(
        store, PerUrlDispositionCandidate(observation_id=first.observation_id), now=now
    )
    assert preview.action is not None

    _record_observation(
        store,
        material_digest="c" * 64,
        fact_digest="d" * 64,
        evidence_suffix="moved-url",
        observed_at=now + timedelta(minutes=1),
        wave_id="wave-b",
        page_key="moved-page",
        work_item_id="work-item-stable",
    )

    readback = read_per_url_disposition_authority(store, action_id=preview.action.id, now=now)
    assert readback.status == "blocked"
    assert readback.blockers[0].code == "per_url_semantic_row_superseded"


def test_non_keep_per_url_disposition_has_typed_technical_seo_blocker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    observation = _record_observation(
        store,
        material_digest="a" * 64,
        fact_digest="b" * 64,
        evidence_suffix="page-a",
        observed_at=datetime.now(UTC),
        wave_id="wave-a",
    )

    monkeypatch.setattr(
        content_per_url_disposition_authority, "content_workflow_store", lambda: store
    )
    response = TestClient(app).post(
        "/api/content/per-url-disposition-authorities/preview",
        json={
            "observation_id": observation.observation_id,
            "proposed_final_disposition": "noindex",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "blocked"
    assert response.json()["action"] is None
    assert response.json()["blockers"][0]["owner"] == "WILQ technical SEO"
    with sqlite3.connect(store.path) as connection:
        proposal_count = connection.execute(
            "SELECT COUNT(*) FROM content_per_url_disposition_proposals"
        ).fetchone()[0]
    assert proposal_count == 0
