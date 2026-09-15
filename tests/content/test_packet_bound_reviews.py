from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.quality.independent_review_service as independent_service
import wilq.content.quality.semantic_review_service as semantic_service
from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_independent_review import (
    register_content_independent_review_routes,
)
from apps.api.wilq_api.routers.content_semantic_review import (
    register_content_semantic_review_routes,
)
from tests.content.test_independent_review_runs import _run
from tests.content.test_packet_plan_draft_http import (
    _assert_plan_and_draft_chain,
    _authorize_refresh,
    _loader_with_typed_cta,
    _public_chain_app,
    _record_authority_source_pack,
    _seed_http_identity,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.deterministic_revision_gate import (
    ContentDeterministicRevisionGate,
)
from wilq.content.quality.review_packet_binding import (
    ContentReviewBindingBlocker,
    ContentReviewInputResolution,
    ContentReviewInputs,
)
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewRequest
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


def _review_app(
    monkeypatch: pytest.MonkeyPatch,
    loader: Any,
    store: Any,
) -> FastAPI:
    application = _public_chain_app(monkeypatch, loader, store)
    router = APIRouter()

    def review_loader(work_item_id: str) -> Any:
        snapshot = loader(work_item_id)
        return snapshot.model_copy(
            update={
                "revision_workspace": snapshot.revision_workspace.model_copy(
                    update={"context_current": True}
                )
            }
        )
    register_content_semantic_review_routes(
        router,
        snapshot_loader=review_loader,
    )
    register_content_independent_review_routes(
        router,
        snapshot_loader=review_loader,
    )
    application.include_router(router)
    return application


def _revision(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/initial-draft")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["revision"] is not None, payload
    return payload["revision"]


def test_public_packet_bound_revision_reaches_semantic_and_independent_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, identity, runtime = _seed_http_identity(tmp_path, monkeypatch)
    _record_authority_source_pack(TestClient(app), identity)
    loader = _loader_with_typed_cta(monkeypatch)
    client = TestClient(_review_app(monkeypatch, loader, store))
    work_item_id = identity.current_work_item_id
    before = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals").json()
    authorization = _authorize_refresh(client, work_item_id, before["planning_input_digest"])
    packet_id = _assert_plan_and_draft_chain(
        client,
        work_item_id,
        before["planning_input_digest"],
        authorization,
    )
    revision = _revision(client, work_item_id)
    assert revision["research_packet_id"] == packet_id
    semantic_path = (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision['revision_id']}/semantic-review"
    )
    semantic = client.post(
        semantic_path,
        json={
            "expected_revision_digest": revision["content_digest"],
            "requested_by": "wilku",
        },
    )
    assert semantic.status_code == 200, semantic.text
    semantic_body = semantic.json()
    assert semantic_body["status"] == "created", semantic.text
    assert semantic_body["research_packet_id"] == packet_id
    assert semantic_body["research_packet_digest"] == revision["research_packet_digest"]
    assert semantic_body["review"]["research_packet_id"] == packet_id
    semantic_read = client.get(semantic_path)
    assert semantic_read.status_code == 200, semantic_read.text
    assert semantic_read.json()["research_packet_id"] == packet_id
    assert runtime.calls >= 3

    evidence_ids = [
        evidence_id
        for section in revision["sections"]
        for evidence_id in section["evidence_ids"]
    ]
    gate = ContentDeterministicRevisionGate.model_construct(
        status="passed",
        work_item_id=work_item_id,
        revision_id=revision["revision_id"],
        revision_digest=revision["content_digest"],
        quality_review_verdict="ready_for_human_review",
        evidence_ids=evidence_ids,
        source_connectors=["public_site"],
        safe_next_step="Uruchom role.",
    )
    monkeypatch.setattr(independent_service, "deterministic_gate_for_snapshot", lambda **_: gate)
    independent_path = (
        f"/api/content/work-items/{work_item_id}/draft-revisions/"
        f"{revision['revision_id']}/independent-reviews"
    )
    run = _run().model_copy(
        update={
            "work_item_id": work_item_id,
            "revision_id": revision["revision_id"],
            "revision_digest": revision["content_digest"],
            "research_packet_id": packet_id,
            "research_packet_digest": revision["research_packet_digest"],
            "evidence_ids": evidence_ids,
            "findings": [
                _run().findings[0].model_copy(
                    update={"evidence_ids": [evidence_ids[0]]}
                )
            ],
        }
    )
    independent = client.post(
        independent_path,
        json={
            "expected_revision_digest": revision["content_digest"],
            "run": run.model_dump(mode="json"),
        },
    )
    assert independent.status_code == 200, independent.text
    independent_body = independent.json()
    assert independent_body["status"] == "created"
    assert independent_body["research_packet_id"] == packet_id
    assert independent_body["research_packet_digest"] == revision["research_packet_digest"]
    assert independent_body["run"]["research_packet_id"] == packet_id
    independent_read = client.get(independent_path)
    assert independent_read.status_code == 200, independent_read.text
    assert independent_read.json()["research_packet_id"] == packet_id


def test_packet_identity_drift_blocks_semantic_before_model_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id="work_packet_review",
        revision_id="revision_packet_review",
        content_digest="a" * 64,
        planning_digest="b" * 64,
        planning_input_digest="c" * 64,
        research_packet_id="content_research_packet_missing",
        research_packet_digest="d" * 64,
    )
    proposal = type(
        "Proposal",
        (),
        {
            "work_item_id": revision.work_item_id,
            "planning_digest": revision.planning_digest,
            "planning_input_digest": revision.planning_input_digest,
            "research_packet_id": revision.research_packet_id,
            "research_packet_digest": revision.research_packet_digest,
            "content_kind": "service",
            "service_card_id": "service_packet_review",
        },
    )()
    snapshot = type(
        "Snapshot",
        (),
        {
            "preflight": type(
                "Preflight",
                (),
                {"item": type("Item", (), {"id": revision.work_item_id})()},
            )(),
            "revision_workspace": type(
                "RevisionWorkspace",
                (),
                {"latest_revision": revision, "context_current": True},
            )(),
            "planning_workspace": type("PlanningWorkspace", (), {"proposal": proposal})(),
        },
    )()

    class Store:
        def load_content_research_packet(self, _packet_id: str) -> None:
            return None

    class Client:
        calls = 0

        def run_structured_turn(self, _request: Any) -> Any:
            self.calls += 1
            raise AssertionError("missing packet must stop before model")

    review_store = type(
        "ReviewStore",
        (),
        {
            "for_revision": lambda *_args: None,
            "write_ready": lambda _self: (_ for _ in ()).throw(
                AssertionError("missing packet must stop before review storage")
            ),
        },
    )()
    monkeypatch.setattr(semantic_service, "content_workflow_store", lambda: Store())
    monkeypatch.setattr(semantic_service, "build_content_planning_input", lambda *_a, **_k: None)
    result = semantic_service.generate_content_semantic_review(
        snapshot=snapshot,
        revision_id=revision.revision_id,
        request=ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="wilku",
        ),
        client=Client(),
        store=review_store,
        run_store=type("RunStore", (), {})(),
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "research_packet_missing"


def test_packet_context_drift_blocks_independent_before_review_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id="work_packet_review",
        revision_id="revision_packet_review",
        content_digest="a" * 64,
        planning_digest="b" * 64,
        planning_input_digest="c" * 64,
        content_kind="service",
        service_card_id="service_packet_review",
        research_packet_id="content_research_packet_current",
        research_packet_digest="d" * 64,
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=revision.work_item_id,
        planning_digest=revision.planning_digest,
        planning_input_digest=revision.planning_input_digest,
        content_kind=revision.content_kind,
        service_card_id=revision.service_card_id,
        research_packet_id=revision.research_packet_id,
        research_packet_digest=revision.research_packet_digest,
    )
    snapshot = type(
        "Snapshot",
        (),
        {
            "revision_workspace": type(
                "RevisionWorkspace",
                (),
                {"latest_revision": revision, "context_current": True},
            )(),
            "planning_workspace": type("PlanningWorkspace", (), {"proposal": proposal})(),
        },
    )()
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=revision.work_item_id,
        planning_input_digest=revision.planning_input_digest,
    )
    packet = type(
        "Packet",
        (),
        {
            "packet_id": revision.research_packet_id,
            "packet_digest": revision.research_packet_digest,
        },
    )()
    exact = ContentReviewInputResolution(
        inputs=ContentReviewInputs(
            revision=revision,
            planning_input=planning_input,
            proposal=proposal,
            packet=packet,
        )
    )
    drifted = ContentReviewInputResolution(
        blocker=ContentReviewBindingBlocker(
            code="research_packet_conflict",
            label="Research packet nie jest aktualny",
            reason="Source pack zmienił się przed zapisem.",
            next_step="Odśwież exact packet.",
        )
    )
    resolutions = iter((exact, drifted))
    monkeypatch.setattr(
        independent_service,
        "resolve_content_review_inputs",
        lambda **_kwargs: next(resolutions),
    )
    gate = ContentDeterministicRevisionGate.model_construct(
        status="passed",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        quality_review_verdict="ready_for_human_review",
        evidence_ids=["ev_1"],
        source_connectors=["public_site"],
        safe_next_step="Uruchom role.",
    )
    monkeypatch.setattr(independent_service, "deterministic_gate_for_snapshot", lambda **_: gate)
    run = _run().model_copy(
        update={
            "work_item_id": revision.work_item_id,
            "revision_id": revision.revision_id,
            "revision_digest": revision.content_digest,
        }
    )
    class NeverWriteStore:
        def write_ready(self) -> bool:
            raise AssertionError("context drift must stop before review storage")

    with pytest.raises(independent_service.IndependentReviewConflict, match="Odśwież exact"):
        independent_service.persist_independent_review_run(
            snapshot=snapshot,
            revision_id=revision.revision_id,
            expected_revision_digest=revision.content_digest,
            run=run,
            store=NeverWriteStore(),
        )
