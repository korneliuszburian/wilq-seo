import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_current_verification as verification_api
from wilq.content.workflow.current_verification import ContentCurrentVerificationCommand
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.store.store import ContentWorkflowStore


def _command() -> ContentCurrentVerificationCommand:
    return ContentCurrentVerificationCommand(
        identity_binding_id="content_delivery_identity_missing",
        identity_binding_digest="a" * 64,
        source_pack_binding_id="content_source_pack_binding_missing",
        source_pack_binding_digest="b" * 64,
        revision_id="content_revision_missing",
        revision_digest="c" * 64,
        review_decision_id="content_revision_review_missing",
        wordpress_draft_binding=ContentDraftRevisionBinding(
            work_item_id="work_item_missing",
            handoff_id="wordpress_draft_handoff_missing",
            revision_id="content_revision_missing",
            content_digest="c" * 64,
            draft_package_id="draft_package_missing",
            draft_package_digest="d" * 64,
            planning_digest="e" * 64,
            approval_decision_id="content_revision_review_missing",
            final_canonical_url="https://www.ekologus.pl/missing/",
        ),
        action_id="act_content_dev_draft_missing",
        mutation_audit_id="mutation_missing",
        recorded_by="current_verification_test",
        recorded_at=datetime(2026, 9, 12, tzinfo=UTC),
    )


def test_missing_cross_seam_inputs_persist_only_a_typed_blocker(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")

    result = store.record_current_verification(_command())

    assert result.status == "created"
    assert result.verification.status == "blocked"
    assert result.verification.blocker is not None
    assert result.verification.blocker.seam == "classification"
    assert (
        store.load_current_verification(result.verification.verification_id)
        == result.verification
    )


def test_public_seam_rejects_direct_write_and_preserves_exact_read(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "http-state.sqlite3")
    stored = store.record_current_verification(_command()).verification
    monkeypatch.setattr(verification_api, "content_workflow_store", lambda: store)
    app = FastAPI()
    router = APIRouter()
    verification_api.register_content_current_verification_routes(router)
    app.include_router(router)
    client = TestClient(app)

    openapi_paths = app.openapi()["paths"]
    assert "/api/content/current-verifications" not in openapi_paths
    assert "post" not in openapi_paths[
        "/api/content/current-verifications/{verification_id}"
    ]
    response = client.post(
        "/api/content/current-verifications",
        json=_command().model_dump(mode="json"),
    )

    assert response.status_code == 404
    assert client.get(
        f"/api/content/current-verifications/{stored.verification_id}"
    ).json() == (
        stored.model_dump(mode="json")
    )


def test_sqlite_replace_cannot_overwrite_a_verification_receipt(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "replace-state.sqlite3")
    created = store.record_current_verification(_command()).verification

    with sqlite3.connect(store.path) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT OR REPLACE INTO content_current_verifications (
              verification_id, verification_digest, status, identity_binding_id,
              source_pack_binding_id, current_work_item_id, revision_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created.verification_id,
                created.verification_digest,
                created.status,
                created.identity_binding_id,
                created.source_pack_binding_id,
                created.current_work_item_id,
                created.revision_id,
                created.model_dump_json(),
            ),
        )
