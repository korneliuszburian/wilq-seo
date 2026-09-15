from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.quality.independent_review_service as independent_service
import wilq.content.quality.semantic_review_queue as semantic_queue
import wilq.content.quality.semantic_review_service as semantic_service
from apps.api.wilq_api.routers import content_independent_review as independent_router
from apps.api.wilq_api.routers import content_semantic_review as semantic_router
from tests.content.packet_bound_review_fixtures import _packet_bound_snapshot
from tests.content.test_independent_review_runs import _run
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.deterministic_revision_gate import (
    ContentDeterministicRevisionGate,
)
from wilq.content.quality.independent_review_contracts import (
    ContentIndependentFindingDispositionResponse,
    ContentIndependentReviewRunCollection,
    ContentIndependentReviewRunResponse,
)
from wilq.content.quality.review_packet_binding import (
    ContentReviewBindingBlocker,
    ContentReviewInputResolution,
    ContentReviewInputs,
    same_content_review_inputs,
)
from wilq.content.quality.semantic_inputs import SemanticInputs
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)


def test_embedded_semantic_post_preflights_packet_before_run_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, revision = _packet_bound_snapshot(
        packet_id="content_research_packet_missing",
        packet_digest="e" * 64,
    )

    class WorkflowStore:
        def load_content_research_packet(self, _packet_id: str) -> None:
            return None

    class ReviewStore:
        def __init__(self) -> None:
            self.claim_calls = 0

        def for_revision(self, *_args: Any) -> None:
            return None

        def write_ready(self) -> bool:
            return True

        def claim_run(self, **_kwargs: Any) -> None:
            self.claim_calls += 1
            raise AssertionError("packet preflight must precede the run claim")

    review_store = ReviewStore()
    monkeypatch.setattr(semantic_service, "content_workflow_store", lambda: WorkflowStore())
    monkeypatch.setattr(semantic_router, "content_semantic_review_store", lambda: review_store)
    monkeypatch.setattr(semantic_queue, "content_semantic_review_store", lambda: review_store)
    monkeypatch.setattr(
        semantic_queue,
        "semantic_codex_client",
        lambda _factory: semantic_queue.StdioCodexAppServerClient(),
    )

    class Client:
        calls = 0

        def run_structured_turn(self, _request: Any) -> Any:
            self.calls += 1
            raise AssertionError("packet preflight must precede Codex")

    monkeypatch.setattr(semantic_router, "content_codex_app_server_client", lambda: Client())
    router = APIRouter()
    semantic_router.register_content_semantic_review_routes(
        router,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    application = FastAPI()
    application.include_router(router)
    response = TestClient(application).post(
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/semantic-review",
        json={
            "expected_revision_digest": revision.content_digest,
            "requested_by": "wilku",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "research_packet_missing"
    assert review_store.claim_calls == 0


def test_unknown_planning_blocker_maps_to_stable_semantic_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, revision = _packet_bound_snapshot(packet_id=None, packet_digest=None)
    monkeypatch.setattr(semantic_service, "content_workflow_store", lambda: SimpleNamespace())
    monkeypatch.setattr(
        semantic_service,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(
            planning_input=None,
            blockers=[
                SimpleNamespace(
                    code="unknown_future_planning_blocker",
                    label="Nieznany blocker",
                    reason="Przyszły blocker testowy.",
                    next_step="Sprawdź plan.",
                )
            ],
        ),
    )

    result = semantic_service._prepare_inputs(
        snapshot,
        revision.revision_id,
        ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="wilku",
        ),
        SimpleNamespace(write_ready=lambda: True),
    )

    assert isinstance(result, ContentSemanticReviewResponse)
    assert result.status == "blocked"
    assert result.blockers[0].code == "missing_planning_input"
    assert result.blockers[0].next_step == "Sprawdź plan."


def test_independent_get_keeps_historical_runs_and_exposes_stale_packet_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, revision = _packet_bound_snapshot()
    historical_run = _run().model_copy(
        update={
            "work_item_id": revision.work_item_id,
            "revision_id": revision.revision_id,
            "revision_digest": revision.content_digest,
            "research_packet_id": revision.research_packet_id,
            "research_packet_digest": revision.research_packet_digest,
        }
    )
    resolution = ContentReviewInputResolution(
        blocker=ContentReviewBindingBlocker(
            code="research_packet_conflict",
            label="Research packet nie jest aktualny",
            reason="Nowszy source pack zastąpił packet.",
            next_step="Odśwież exact packet.",
        )
    )

    class ReviewStore:
        def write_ready(self) -> bool:
            return True

        def for_revision(self, *_args: Any) -> list[Any]:
            return [historical_run]

    monkeypatch.setattr(
        independent_router,
        "content_independent_review_store",
        lambda: ReviewStore(),
    )
    monkeypatch.setattr(
        independent_service,
        "resolve_content_review_inputs",
        lambda **_kwargs: resolution,
    )
    router = APIRouter()
    independent_router.register_content_independent_review_routes(
        router,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    application = FastAPI()
    application.include_router(router)
    response = TestClient(application).get(
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/independent-reviews"
    )

    assert response.status_code == 200
    assert len(response.json()["runs"]) == 1
    assert response.json()["blockers"][0]["code"] == "research_packet_conflict"
    assert response.json()["blockers"][0]["next_step"] == "Odśwież exact packet."


def test_unbound_review_cannot_masquerade_as_packet_bound_response() -> None:
    unbound_review = ContentSemanticReview.model_construct(
        review_id="semantic_unbound",
        work_item_id="work_packet_review",
        revision_id="revision_packet_review",
        revision_digest="a" * 64,
        codex_run_id="codex_semantic_unbound",
        status="reviewable",
        dimensions=[],
        findings=[],
        requested_by="wilku",
        safe_next_step="Przejdź do review.",
    )
    with pytest.raises(ValueError, match="bind"):
        ContentSemanticReviewResponse(
            status="ready",
            work_item_id=unbound_review.work_item_id,
            revision_id=unbound_review.revision_id,
            revision_digest=unbound_review.revision_digest,
            research_packet_id="content_research_packet_current",
            research_packet_digest="d" * 64,
            review=unbound_review,
            run_id=unbound_review.codex_run_id,
            safe_next_step=unbound_review.safe_next_step,
        )

    unbound_run = _run()
    packet_id = "content_research_packet_current"
    packet_digest = "d" * 64
    with pytest.raises(ValueError, match="packet"):
        ContentIndependentReviewRunResponse(
            status="created",
            work_item_id=unbound_run.work_item_id,
            revision_id=unbound_run.revision_id,
            revision_digest=unbound_run.revision_digest,
            research_packet_id=packet_id,
            research_packet_digest=packet_digest,
            run=unbound_run,
            safe_next_step="Zachowaj wynik.",
        )
    with pytest.raises(ValueError, match="packet"):
        ContentIndependentReviewRunCollection(
            work_item_id=unbound_run.work_item_id,
            revision_id=unbound_run.revision_id,
            revision_digest=unbound_run.revision_digest,
            research_packet_id=packet_id,
            research_packet_digest=packet_digest,
            runs=[unbound_run],
            safe_next_step="Zachowaj wynik.",
        )
    with pytest.raises(ValueError, match="packet"):
        ContentIndependentFindingDispositionResponse(
            status="recorded",
            work_item_id=unbound_run.work_item_id,
            revision_id=unbound_run.revision_id,
            revision_digest=unbound_run.revision_digest,
            research_packet_id=packet_id,
            research_packet_digest=packet_digest,
            run=unbound_run,
            finding_id="finding_1",
            safe_next_step="Zachowaj decyzję.",
        )


def test_semantic_queue_revalidates_packet_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, revision = _packet_bound_snapshot()
    blocked = ContentSemanticReviewResponse(
        status="blocked",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        research_packet_id=revision.research_packet_id,
        research_packet_digest=revision.research_packet_digest,
        blockers=[
            ContentSemanticReviewBlocker(
                code="research_packet_conflict",
                label="Research packet nie jest aktualny",
                reason="Packet zmienił się po preflight route.",
                next_step="Odśwież exact packet.",
            )
        ],
        safe_next_step="Odśwież exact packet.",
    )

    class ReviewStore:
        claim_calls = 0

        def claim_run(self, **_kwargs: Any) -> None:
            self.claim_calls += 1
            raise AssertionError("queue revalidation must precede claim_run")

    review_store = ReviewStore()
    monkeypatch.setattr(semantic_queue, "content_semantic_review_store", lambda: review_store)
    monkeypatch.setattr(
        semantic_queue,
        "preflight_content_semantic_review",
        lambda **_kwargs: blocked,
    )

    class Client:
        def run_structured_turn(self, _request: Any) -> Any:
            raise AssertionError("packet drift must stop before Codex")

    result = semantic_queue.queue_semantic_review(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision=revision,
        request=ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="wilku",
        ),
        client=Client(),
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "research_packet_conflict"
    assert review_store.claim_calls == 0


def test_semantic_queue_revalidation_rejects_changed_revision_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, revision = _packet_bound_snapshot()
    changed_revision = revision.model_copy(update={"content_digest": "e" * 64})
    preflight_inputs = SemanticInputs(
        revision=changed_revision,
        planning_input=SimpleNamespace(
            work_item_id=changed_revision.work_item_id,
            planning_input_digest=changed_revision.planning_input_digest,
            research_packet_id=changed_revision.research_packet_id,
            research_packet_digest=changed_revision.research_packet_digest,
        ),
        proposal=snapshot.planning_workspace.proposal,
    )

    class ReviewStore:
        claim_calls = 0

        def claim_run(self, **_kwargs: Any) -> None:
            self.claim_calls += 1
            raise AssertionError("changed revision must stop before run claim")

    review_store = ReviewStore()
    monkeypatch.setattr(semantic_queue, "content_semantic_review_store", lambda: review_store)
    monkeypatch.setattr(
        semantic_queue,
        "preflight_content_semantic_review",
        lambda **_kwargs: preflight_inputs,
    )
    result = semantic_queue.queue_semantic_review(
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision=revision,
        request=ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="wilku",
        ),
        client=SimpleNamespace(),
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "stale_revision"
    assert review_store.claim_calls == 0


@pytest.mark.parametrize(
    "stored_packet",
    [(None, None), ("content_research_packet_other", "f" * 64)],
)
def test_packet_bound_semantic_read_blocks_unbound_or_mismatched_review(
    monkeypatch: pytest.MonkeyPatch,
    stored_packet: tuple[str | None, str | None],
) -> None:
    snapshot, revision = _packet_bound_snapshot()
    packet_id, packet_digest = stored_packet
    review = ContentSemanticReview.model_construct(
        review_id="semantic_historical",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
        codex_run_id="codex_semantic_historical",
        status="reviewable",
        dimensions=[],
        findings=[],
        requested_by="wilku",
        safe_next_step="Przejdź do review.",
    )

    class ReviewStore:
        def for_revision(self, *_args: Any) -> ContentSemanticReview:
            return review

        def latest(self, *_args: Any) -> ContentSemanticReview:
            return review

    monkeypatch.setattr(
        semantic_service,
        "_prepare_inputs",
        lambda *_args, **_kwargs: SemanticInputs(
            revision=revision,
            planning_input=SimpleNamespace(),
            proposal=snapshot.planning_workspace.proposal,
        ),
    )
    result = semantic_service.read_content_semantic_review(
        snapshot=snapshot,
        revision_id=revision.revision_id,
        store=ReviewStore(),
    )

    assert result.status == "blocked"
    assert result.review is None
    assert result.blockers[0].code == "research_packet_conflict"
    assert review.research_packet_id == packet_id
    assert review.research_packet_digest == packet_digest


def test_packet_bound_proposal_cannot_make_unbound_read_ready(
    monkeypatch: pytest.MonkeyPatch,
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
        review_id="semantic_unbound_proposal_packet",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        codex_run_id="codex_semantic_unbound_proposal_packet",
        status="reviewable",
        dimensions=[],
        findings=[],
        requested_by="wilku",
        safe_next_step="Przejdź do review.",
    )

    class ReviewStore:
        def for_revision(self, *_args: Any) -> ContentSemanticReview:
            return review

        def latest(self, *_args: Any) -> ContentSemanticReview:
            return review

    monkeypatch.setattr(semantic_router, "content_semantic_review_store", lambda: ReviewStore())
    monkeypatch.setattr(
        semantic_service,
        "_prepare_inputs",
        lambda *_args, **_kwargs: SemanticInputs(
            revision=revision,
            planning_input=SimpleNamespace(),
            proposal=snapshot.planning_workspace.proposal,
        ),
    )
    router = APIRouter()
    semantic_router.register_content_semantic_review_routes(
        router,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    application = FastAPI()
    application.include_router(router)
    response = TestClient(application).get(
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/semantic-review"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "research_packet_conflict"


def test_independent_packet_mismatch_returns_typed_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, revision = _packet_bound_snapshot()
    packet = SimpleNamespace(
        packet_id=revision.research_packet_id,
        packet_digest=revision.research_packet_digest,
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=revision.work_item_id,
        planning_input_digest=revision.planning_input_digest,
    )
    resolution = ContentReviewInputResolution(
        inputs=ContentReviewInputs(
            revision=revision,
            planning_input=planning_input,
            proposal=snapshot.planning_workspace.proposal,
            packet=packet,
            current_packet=SimpleNamespace(
                status="current",
                packet_id=packet.packet_id,
                packet_digest=packet.packet_digest,
                current_work_item_id=revision.work_item_id,
            ),
        )
    )
    monkeypatch.setattr(
        independent_service,
        "resolve_content_review_inputs",
        lambda **_kwargs: resolution,
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
            "research_packet_id": "content_research_packet_other",
            "research_packet_digest": "f" * 64,
            "evidence_ids": ["ev_1"],
            "source_connectors": ["public_site"],
        }
    )

    class ReviewStore:
        def write_ready(self) -> bool:
            return True

        def save_run(self, _run: Any) -> None:
            raise AssertionError("packet mismatch must stop before persistence")

    monkeypatch.setattr(
        independent_router,
        "content_independent_review_store",
        lambda: ReviewStore(),
    )
    router = APIRouter()
    independent_router.register_content_independent_review_routes(
        router,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    application = FastAPI()
    application.include_router(router)
    response = TestClient(application).post(
        f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
        f"{revision.revision_id}/independent-reviews",
        json={
            "expected_revision_digest": revision.content_digest,
            "run": run.model_dump(mode="json"),
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["blockers"][0]["code"] == "research_packet_conflict"
    assert payload["blockers"][0]["next_step"]
    assert payload["run"] is None


def test_same_content_review_inputs_includes_current_packet_projection() -> None:
    snapshot, revision = _packet_bound_snapshot()
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=revision.work_item_id,
        planning_input_digest=revision.planning_input_digest,
    )
    packet = SimpleNamespace(
        packet_id=revision.research_packet_id,
        packet_digest=revision.research_packet_digest,
    )
    proposal = snapshot.planning_workspace.proposal
    current = SimpleNamespace(
        status="current",
        packet_id=packet.packet_id,
        packet_digest=packet.packet_digest,
        current_work_item_id=revision.work_item_id,
        current_source_pack_binding_id="source-pack-current",
        current_source_pack_binding_digest="1" * 64,
        current_identity_binding_id="identity-current",
        current_identity_binding_digest="2" * 64,
        blocker=None,
    )
    first = ContentReviewInputs(
        revision=revision,
        planning_input=planning_input,
        proposal=proposal,
        packet=packet,
        current_packet=current,
    )
    second = ContentReviewInputs(
        revision=revision,
        planning_input=planning_input,
        proposal=proposal,
        packet=packet,
        current_packet=SimpleNamespace(
            **{
                **vars(current),
                "current_identity_binding_digest": "3" * 64,
            }
        ),
    )

    assert same_content_review_inputs(first, second) is False
