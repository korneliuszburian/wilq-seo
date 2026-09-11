from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_independent_review
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import independent_review_service
from wilq.content.quality.deterministic_revision_gate import ContentDeterministicRevisionGate
from wilq.content.quality.independent_review_contracts import (
    ROLE_CRITERIA_VERSIONS,
    ContentIndependentFindingDispositionRequest,
    ContentIndependentReviewFinding,
    ContentIndependentReviewRun,
    ContentIndependentReviewRunSubmission,
)
from wilq.content.quality.independent_review_store import (
    ContentIndependentReviewStore,
    IndependentReviewConflict,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


def _run(*, role: str = "content_ux", severity: str = "critical") -> ContentIndependentReviewRun:
    finding = ContentIndependentReviewFinding(
        finding_id="finding_1",
        code="unsupported_claim",
        severity=severity,
        label="Nieudowodnione twierdzenie",
        reason="Twierdzenie wymaga dokładnego źródła.",
        instruction="Usuń albo podepnij dowód.",
        affected_targets=["section_1"],
        evidence_ids=["ev_1"],
    )
    return ContentIndependentReviewRun(
        run_id=f"run_{role}",
        work_item_id="work_item_review",
        revision_id="revision_review",
        revision_digest="a" * 64,
        role=role,
        model_provider="opencode-go",
        model_id="deepseek-v4.1-flash",
        model_variant="max",
        criteria_version=ROLE_CRITERIA_VERSIONS[role],
        findings=[finding],
        evidence_ids=["ev_1"],
        source_connectors=["public_site"],
        requested_by="wilku",
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
    )


def test_run_contract_freezes_role_model_and_criteria() -> None:
    run = _run(role="seo")

    assert run.role == "seo"
    assert run.model_id == "deepseek-v4.1-flash"
    assert run.model_variant == "max"
    assert run.criteria_version == "wilq_independent_seo_review_v1"
    with pytest.raises(ValueError, match="criteria"):
        ContentIndependentReviewRun.model_validate(
            {
                **run.model_dump(mode="json"),
                "criteria_version": "wilq_independent_content_ux_review_v1",
            }
        )


def test_finding_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="evidence_ids"):
        ContentIndependentReviewFinding(
            finding_id="finding_without_evidence",
            code="unsupported_claim",
            severity="critical",
            label="Brak dowodu",
            reason="Brakuje evidence.",
            instruction="Dodaj evidence.",
            affected_targets=["section_1"],
        )


def test_store_persists_one_run_per_role_and_exact_revision(tmp_path) -> None:
    store = ContentIndependentReviewStore(tmp_path / "reviews.sqlite3")
    run = _run()

    assert store.save_run(run) == "created"
    assert store.save_run(run) == "idempotent"
    assert store.save_run(_run(role="seo")) == "created"
    assert store.save_run(_run(role="factual_regulatory")) == "created"
    assert len(store.for_revision(run.work_item_id, run.revision_id, run.revision_digest)) == 3
    with pytest.raises(IndependentReviewConflict, match="role"):
        store.save_run(run.model_copy(update={"run_id": "run_content_ux_second"}))


def test_critical_acceptance_requires_exact_child_revision_and_is_idempotent(tmp_path) -> None:
    store = ContentIndependentReviewStore(tmp_path / "reviews.sqlite3")
    run = _run()
    store.save_run(run)
    request = ContentIndependentFindingDispositionRequest(
        expected_revision_digest=run.revision_digest,
        disposition="accept_and_fix",
        reason="Wymaga poprawki w child revision.",
        disposed_by="wilku",
        evidence_ids=["ev_1"],
    )

    first = store.record_disposition(
        work_item_id=run.work_item_id,
        revision_id=run.revision_id,
        run_id=run.run_id,
        finding_id="finding_1",
        request=request,
    )
    second = store.record_disposition(
        work_item_id=run.work_item_id,
        revision_id=run.revision_id,
        run_id=run.run_id,
        finding_id="finding_1",
        request=request,
    )

    assert first.status == "recorded"
    assert first.finding.disposition == "accept_and_fix"
    assert second.status == "idempotent"
    assert store.save_run(run) == "idempotent"
    with pytest.raises(IndependentReviewConflict, match="immutable"):
        store.record_disposition(
            work_item_id=run.work_item_id,
            revision_id=run.revision_id,
            run_id=run.run_id,
            finding_id="finding_1",
            request=request.model_copy(
                update={"disposition": "deferred", "reason": "Odłożone."}
            ),
        )


def test_disposition_identity_and_evidence_fail_before_mutation(tmp_path) -> None:
    store = ContentIndependentReviewStore(tmp_path / "reviews.sqlite3")
    run = _run()
    store.save_run(run)
    before = store.for_revision(run.work_item_id, run.revision_id, run.revision_digest)
    request = ContentIndependentFindingDispositionRequest(
        expected_revision_digest=run.revision_digest,
        disposition="accept_and_fix",
        reason="Wymaga poprawki.",
        disposed_by="wilku",
        evidence_ids=["ev_1"],
    )

    with pytest.raises(IndependentReviewConflict, match="identity"):
        store.record_disposition(
            work_item_id="other_work_item",
            revision_id=run.revision_id,
            run_id=run.run_id,
            finding_id="finding_1",
            request=request,
        )
    with pytest.raises(IndependentReviewConflict, match="evidence"):
        store.record_disposition(
            work_item_id=run.work_item_id,
            revision_id=run.revision_id,
            run_id=run.run_id,
            finding_id="finding_1",
            request=request.model_copy(update={"evidence_ids": ["ev_new"]}),
        )

    assert store.for_revision(run.work_item_id, run.revision_id, run.revision_digest) == before


def test_store_redacts_finding_text_before_persistence(tmp_path) -> None:
    store = ContentIndependentReviewStore(tmp_path / "reviews.sqlite3")
    run = _run().model_copy(
        update={
            "findings": [
                _run().findings[0].model_copy(
                    update={"reason": "Nie loguj tokenu sk-abcdefghijklmnopqrstuvwxyz123456."}
                )
            ]
        }
    )

    store.save_run(run)
    stored = store.for_run(run.run_id)

    assert stored is not None
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in stored.findings[0].reason


def test_redacted_disposition_retry_is_idempotent(tmp_path) -> None:
    store = ContentIndependentReviewStore(tmp_path / "reviews.sqlite3")
    run = _run()
    store.save_run(run)
    request = ContentIndependentFindingDispositionRequest(
        expected_revision_digest=run.revision_digest,
        disposition="deferred",
        reason="Odłożone po sprawdzeniu sk-abcdefghijklmnopqrstuvwxyz123456.",
        disposed_by="wilku",
        evidence_ids=["ev_1"],
    )

    first = store.record_disposition(
        work_item_id=run.work_item_id,
        revision_id=run.revision_id,
        run_id=run.run_id,
        finding_id="finding_1",
        request=request,
    )
    second = store.record_disposition(
        work_item_id=run.work_item_id,
        revision_id=run.revision_id,
        run_id=run.run_id,
        finding_id="finding_1",
        request=request,
    )

    assert first.status == "recorded"
    assert second.status == "idempotent"


def test_reject_with_evidence_requires_disposition_evidence() -> None:
    with pytest.raises(ValueError, match="evidence"):
        ContentIndependentFindingDispositionRequest(
            expected_revision_digest="a" * 64,
            disposition="reject_with_evidence",
            reason="Odrzucone.",
            disposed_by="wilku",
        )


def test_run_submission_cannot_smuggle_a_human_disposition() -> None:
    run = _run()
    disposed = run.findings[0].model_copy(
        update={
            "disposition": "accept_and_fix",
            "disposition_reason": "Nie wolno wstępnie rozstrzygać.",
            "disposed_by": "wilku",
            "disposed_at": datetime(2026, 9, 1, tzinfo=UTC),
        }
    )
    payload = run.model_dump(mode="json")
    payload["findings"] = [disposed.model_dump(mode="json")]

    with pytest.raises(ValueError, match="disposition"):
        ContentIndependentReviewRunSubmission.model_validate(
            {
                "expected_revision_digest": run.revision_digest,
                "run": payload,
            }
        )


def test_review_attribution_and_finding_text_reject_whitespace() -> None:
    run = _run()
    with pytest.raises(ValueError, match="blank"):
        ContentIndependentReviewRun.model_validate(
            {**run.model_dump(mode="json"), "requested_by": "   "}
        )
    with pytest.raises(ValueError, match="blank"):
        ContentIndependentReviewFinding.model_validate(
            {
                **run.findings[0].model_dump(mode="json"),
                "reason": "   ",
            }
        )


def test_deterministic_gate_precedes_independent_run_persistence(monkeypatch) -> None:
    revision = ContentDraftRevision.model_construct(
        work_item_id="work_item_review",
        revision_id="revision_review",
        content_digest="a" * 64,
        planning_input_digest="b" * 64,
    )
    snapshot = SimpleNamespace(
        revision_workspace=SimpleNamespace(latest_revision=revision),
        planning_workspace=SimpleNamespace(
            proposal=ContentPlanningProposal.model_construct(
                service_card_id=None,
                planning_input_digest="b" * 64,
            )
        ),
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=revision.work_item_id,
        planning_input_digest="b" * 64,
    )
    monkeypatch.setattr(
        independent_review_service,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(planning_input=planning_input, blockers=[]),
    )
    monkeypatch.setattr(
        independent_review_service,
        "deterministic_gate_for_snapshot",
        lambda **_kwargs: ContentDeterministicRevisionGate.model_construct(
            status="blocked",
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            quality_review_verdict="blocked",
            safe_next_step="Popraw gate.",
        ),
    )

    class Store:
        def write_ready(self):
            raise AssertionError("blocked gate must stop before storage")

        def save_run(self, _run):
            raise AssertionError("blocked gate must not persist a run")

    with pytest.raises(IndependentReviewConflict, match="Deterministic gate"):
        independent_review_service.persist_independent_review_run(
            snapshot=snapshot,
            revision_id=revision.revision_id,
            expected_revision_digest=revision.content_digest,
            run=_run(),
            store=Store(),
        )


def test_api_records_run_and_critical_disposition(tmp_path, monkeypatch) -> None:
    app = FastAPI()
    store = ContentIndependentReviewStore(tmp_path / "reviews.sqlite3")
    revision = ContentDraftRevision.model_construct(
        work_item_id="work_item_review",
        revision_id="revision_review",
        content_digest="a" * 64,
        planning_input_digest="b" * 64,
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=revision.work_item_id,
        planning_input_digest="b" * 64,
    )
    snapshot = SimpleNamespace(
        revision_workspace=SimpleNamespace(latest_revision=revision),
        planning_workspace=SimpleNamespace(
            proposal=ContentPlanningProposal.model_construct(
                service_card_id=None,
                planning_input_digest="b" * 64,
            )
        ),
    )
    monkeypatch.setattr(
        content_independent_review,
        "content_independent_review_store",
        lambda: store,
    )
    monkeypatch.setattr(
        independent_review_service,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(planning_input=planning_input, blockers=[]),
    )
    monkeypatch.setattr(
        independent_review_service,
        "deterministic_gate_for_snapshot",
        lambda **_kwargs: ContentDeterministicRevisionGate.model_construct(
            status="passed",
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            quality_review_verdict="ready_for_human_review",
            evidence_ids=["ev_1"],
            source_connectors=["public_site"],
            safe_next_step="Uruchom role.",
        ),
    )
    content_independent_review.register_content_independent_review_routes(
        app,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    client = TestClient(app)
    run = _run()
    payload = ContentIndependentReviewRunSubmission(
        expected_revision_digest=revision.content_digest,
        run=run,
    ).model_dump(mode="json")

    created = client.post(
        "/api/content/work-items/work_item_review/draft-revisions/revision_review/independent-reviews",
        json=payload,
    )
    assert created.status_code == 200
    assert created.json()["status"] == "created"
    disposed = client.post(
        "/api/content/work-items/work_item_review/draft-revisions/revision_review/independent-reviews/run_content_ux/findings/finding_1/disposition",
        json={
            "expected_revision_digest": revision.content_digest,
            "disposition": "accept_and_fix",
            "reason": "Poprawka wymaga child revision.",
            "disposed_by": "wilku",
            "evidence_ids": ["ev_1"],
        },
    )
    assert disposed.status_code == 200
    assert disposed.json()["status"] == "child_revision_required"
    assert disposed.json()["requires_child_revision"] is True
    repeated = client.post(
        "/api/content/work-items/work_item_review/draft-revisions/revision_review/independent-reviews",
        json=payload,
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["run"]["findings"][0]["disposition"] == "accept_and_fix"


def test_api_read_exposes_storage_activation_state(monkeypatch) -> None:
    app = FastAPI()
    revision = ContentDraftRevision.model_construct(
        work_item_id="work_item_review",
        revision_id="revision_review",
        content_digest="a" * 64,
    )
    snapshot = SimpleNamespace(
        revision_workspace=SimpleNamespace(latest_revision=revision),
    )

    class NotReadyStore:
        def write_ready(self):
            return False

        def for_revision(self, *_args):
            raise AssertionError("unactivated storage must not be queried")

    monkeypatch.setattr(
        content_independent_review,
        "content_independent_review_store",
        lambda: NotReadyStore(),
    )
    content_independent_review.register_content_independent_review_routes(
        app,
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    response = TestClient(app).get(
        "/api/content/work-items/work_item_review/draft-revisions/revision_review/independent-reviews"
    )

    assert response.status_code == 200
    assert response.json()["storage_status"] == "activation_required"
    assert response.json()["runs"] == []
