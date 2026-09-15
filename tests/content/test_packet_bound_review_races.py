from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app as public_app
from apps.api.wilq_api.routers import content_semantic_review as semantic_router
from tests.content.packet_bound_review_fixtures import _packet_bound_snapshot
from tests.content.test_packet_plan_draft_http import (
    _assert_plan_and_draft_chain,
    _authorize_refresh,
    _loader_with_typed_cta,
    _public_chain_app,
    _record_authority_source_pack,
    _seed_http_identity,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput, build_content_planning_input
from wilq.content.quality import semantic_review_queue as semantic_queue
from wilq.content.quality import semantic_review_service as semantic_service
from wilq.content.quality.review_packet_binding import (
    ContentReviewBindingBlocker,
    ContentReviewInputs,
    claim_token_for_review_inputs,
    content_review_inputs_match_revision,
    resolve_content_review_inputs,
)
from wilq.content.quality.semantic_inputs import SemanticInputs
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
)
from wilq.content.quality.semantic_review_store import (
    ContentSemanticReviewStore,
    validate_content_review_claim_token,
)
from wilq.storage.local_state import LocalStateStore


def test_claim_revalidates_packet_currentness_inside_transaction(tmp_path: Path) -> None:
    store = ContentSemanticReviewStore(tmp_path / "state.sqlite3")
    endpoint = "/api/content/work-items/work/draft-revisions/revision/semantic-review"
    blocker = ContentSemanticReviewBlocker(
        code="research_packet_conflict",
        label="Research packet nie jest aktualny",
        reason="Current packet zmienił się przed claimem.",
        next_step="Odśwież exact packet.",
    )

    claim = store.claim_run(
        work_item_id="work",
        revision_id="revision",
        revision_digest="a" * 64,
        endpoint=endpoint,
        evidence_ids=["ev"],
        planning_input_digest="b" * 64,
        timeout_seconds=30,
        claim_guard=lambda _connection: blocker,
    )

    assert claim.blocker == blocker
    assert claim.run is None
    assert LocalStateStore(store.path).list_codex_runs() == []


def test_claim_cas_rejects_second_connection_drift_before_insert(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE packet_guard (status TEXT NOT NULL)")
        connection.execute("INSERT INTO packet_guard (status) VALUES ('preflight')")

    with sqlite3.connect(database) as injector:
        injector.execute("UPDATE packet_guard SET status = 'drifted'")
        injector.commit()

    store = ContentSemanticReviewStore(database)
    blocker = ContentSemanticReviewBlocker(
        code="research_packet_conflict",
        label="Research packet nie jest aktualny",
        reason="Drift został zatwierdzony przed granicą claimu.",
        next_step="Odśwież exact packet.",
    )

    def guard(connection: sqlite3.Connection) -> ContentSemanticReviewBlocker | None:
        status = connection.execute("SELECT status FROM packet_guard").fetchone()[0]
        return blocker if status == "drifted" else None

    claim = store.claim_run(
        work_item_id="work",
        revision_id="revision",
        revision_digest="a" * 64,
        endpoint="/semantic-review",
        evidence_ids=["ev"],
        planning_input_digest="b" * 64,
        timeout_seconds=30,
        claim_guard=guard,
    )

    assert claim.blocker == blocker
    assert claim.run is None
    assert LocalStateStore(database).list_codex_runs() == []


def test_populated_workflow_claim_validator_returns_typed_packet_blocker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workflow_store, identity, _runtime = _seed_http_identity(tmp_path, monkeypatch)
    _record_authority_source_pack(TestClient(public_app), identity)
    loader = _loader_with_typed_cta(monkeypatch)
    client = TestClient(_public_chain_app(monkeypatch, loader, workflow_store))
    work_item_id = identity.current_work_item_id
    before = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals").json()
    authorization = _authorize_refresh(client, work_item_id, before["planning_input_digest"])
    _assert_plan_and_draft_chain(
        client,
        work_item_id,
        before["planning_input_digest"],
        authorization,
    )
    snapshot = loader(work_item_id)
    snapshot = snapshot.model_copy(
        update={
            "revision_workspace": snapshot.revision_workspace.model_copy(
                update={"context_current": True}
            )
        }
    )
    revision = snapshot.revision_workspace.latest_revision
    assert revision is not None
    resolution = resolve_content_review_inputs(
        snapshot=snapshot,
        revision_id=revision.revision_id,
        expected_revision_digest=revision.content_digest,
        workflow_store=workflow_store,
        planning_input_builder=build_content_planning_input,
    )
    assert resolution.inputs is not None, resolution.blocker
    token = claim_token_for_review_inputs(resolution.inputs)
    assert token is not None
    with workflow_store._connect() as connection:
        assert validate_content_review_claim_token(connection, token) is None
        blocker = validate_content_review_claim_token(
            connection,
            replace(token, current_source_pack_binding_id="source_pack_drifted"),
        )

    assert isinstance(blocker, ContentReviewBindingBlocker)
    assert blocker.code == "research_packet_conflict"
    assert blocker.next_step


def test_packet_bound_inputs_require_packet_and_current_projection() -> None:
    snapshot, revision = _packet_bound_snapshot()
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=revision.work_item_id,
        planning_input_digest=revision.planning_input_digest,
        research_packet_id=revision.research_packet_id,
        research_packet_digest=revision.research_packet_digest,
    )
    inputs = ContentReviewInputs(
        revision=revision,
        planning_input=planning_input,
        proposal=snapshot.planning_workspace.proposal,
    )

    assert content_review_inputs_match_revision(revision, inputs) is False
    with pytest.raises(ValueError, match="Packet-bound"):
        claim_token_for_review_inputs(inputs)


def test_packet_bound_idempotent_post_blocks_unbound_stored_review(
    monkeypatch,
) -> None:
    packet_snapshot, packet_revision = _packet_bound_snapshot()
    revision = packet_revision.model_copy(
        update={"research_packet_id": None, "research_packet_digest": None}
    )
    snapshot = SimpleNamespace(
        preflight=packet_snapshot.preflight,
        revision_workspace=SimpleNamespace(latest_revision=revision, context_current=True),
        planning_workspace=packet_snapshot.planning_workspace,
    )
    review = ContentSemanticReview.model_construct(
        review_id="semantic_unbound_idempotent",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        codex_run_id="codex_semantic_unbound_idempotent",
        status="reviewable",
        dimensions=[],
        findings=[],
        requested_by="wilku",
        safe_next_step="Przejdź do review.",
    )

    class ReviewStore:
        def for_revision(self, *_args: Any) -> ContentSemanticReview:
            return review

        def write_ready(self) -> bool:
            return True

    class Client:
        def run_structured_turn(self, _request: Any) -> Any:
            raise AssertionError("idempotency blocker must stop before Codex")

    review_store = ReviewStore()
    monkeypatch.setattr(semantic_router, "content_semantic_review_store", lambda: review_store)
    monkeypatch.setattr(
        semantic_queue,
        "semantic_codex_client",
        lambda _factory: semantic_queue.StdioCodexAppServerClient(),
    )
    monkeypatch.setattr(semantic_router, "content_codex_app_server_client", lambda: Client())
    monkeypatch.setattr(
        semantic_service,
        "_prepare_inputs",
        lambda *_args, **_kwargs: SemanticInputs(
            revision=revision,
            planning_input=SimpleNamespace(),
            proposal=snapshot.planning_workspace.proposal,
        ),
    )
    application = FastAPI()
    semantic_router.register_content_semantic_review_routes(
        application,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    response = TestClient(application).post(
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/semantic-review",
        json={
            "expected_revision_digest": revision.content_digest,
            "requested_by": "wilku",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["blockers"][0]["code"] == "research_packet_conflict"
    assert payload["review"] is None
