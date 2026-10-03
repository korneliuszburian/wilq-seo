"""Exact local full-text authority through the public action lifecycle."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.content_initial_draft import register_content_initial_draft_route
from tests.content import test_v3_packet_planning_status_read as status_fixture
from tests.content.test_full_document_revision_v2 import _draft_package
from tests.content.test_material_review_action_v2 import _configure_local_action_runtime
from tests.content.test_research_packet_v3_action import _apply
from tests.content.test_v3_draft_review_context import _consumers
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts.full_draft_generation_v3_dispatch import dispatch_full_draft_generation_v3
from wilq.content.workflow.research_packet_v3_action import research_packet_v3_action
from wilq.content.workflow.research_packet_v3_receipt import ResearchPacketV3PreviewRecord
from wilq.storage.local_state import LocalStateStore


def _case(tmp_path, monkeypatch):
    def approve(store, packet):
        audit = LocalStateStore(store.path)
        _configure_local_action_runtime(monkeypatch, store, audit)
        from apps.api.wilq_api.routers import content_research_packet_v3_preview

        monkeypatch.setattr(
            content_research_packet_v3_preview,
            "read_current_research_packet_v3_preview",
            lambda *_args, **_kwargs: packet,
        )
        app = FastAPI()
        app.include_router(create_actions_router(lambda: None))
        action = research_packet_v3_action(ResearchPacketV3PreviewRecord.from_preview(packet))
        result = _apply(TestClient(app), action.id)
        assert result["applied"] is True, result
        return store.load_research_packet_v3_approval_receipt(packet.preview_id)

    original_proposal = status_fixture._proposal

    def with_lineage(**kwargs):
        proposal = original_proposal(**kwargs)
        return proposal.model_copy(
            update={
                "cta_blocks": [
                    cta.model_copy(update={"evidence_ids": ["ev_official_fact"]})
                    for cta in proposal.cta_blocks
                ]
            }
        )

    monkeypatch.setattr(status_fixture, "_proposal", with_lineage)
    monkeypatch.setattr(status_fixture, "_approve_exact_packet", approve)
    case = _consumers(tmp_path, monkeypatch)
    from wilq.content.drafts import draft_assurance
    from wilq.content.regulatory.policy import ContentRegulatoryProfile

    coverage = case.frozen.regulatory_coverage
    profile = ContentRegulatoryProfile(
        id=coverage.profile_id,
        version=coverage.profile_version,
        requirements=coverage.requirements,
        official_source_hosts=["eli.gov.pl"],
        service_card_ids=[],
        canonical_paths=[coverage.canonical_path or "/exact"],
        max_source_age_days=180,
    )
    monkeypatch.setattr(draft_assurance, "regulatory_content_profile", lambda **_kwargs: profile)
    package = _draft_package()
    case.snapshot.draft_package = SimpleNamespace(
        draft_package_result=SimpleNamespace(draft_package=package)
    )
    case.snapshot.preflight.item.final_canonical_url = case.packet.page_url
    case.snapshot.preflight.item.intended_final_url = None
    case.audit_store = LocalStateStore(case.store.path)
    _configure_local_action_runtime(monkeypatch, case.workflow_store, case.audit_store)
    case.turns = []

    case.client = _FakeClient(case)
    case.app = FastAPI()
    case.app.include_router(create_actions_router(lambda: None))
    register_content_initial_draft_route(case.app.router, snapshot_loader=lambda _id: case.snapshot)
    from apps.api.wilq_api.routers.content_full_draft_generation_v3 import (
        register_content_full_draft_generation_v3_routes,
    )

    register_content_full_draft_generation_v3_routes(
        case.app.router,
        snapshot_loader=lambda _id: case.snapshot,
        workflow_store_factory=lambda: case.workflow_store,
        proposal_store_factory=lambda: case.store,
        audit_store_factory=lambda: case.audit_store,
        client_factory=lambda: case.client,
        executor=SimpleNamespace(submit=lambda fn, *args: fn(*args)),
    )
    case.http = TestClient(case.app)
    return case


class _FakeClient:
    def __init__(self, case):
        self.case = case

    def run_structured_turn(self, request):
        case = self.case
        case.turns.append(request)
        application = json.loads(request.application_context)
        if application.get("operation") == "assure_regulatory_content_draft":
            return _assurance_result(request, application)
        output = {
            "page_assets": {
                "wordpress_title": "Zakres obowiązku",
                "meta_title": "Zakres obowiązku",
                "meta_description": "Sprawdź zakres obowiązku dla firmy.",
                "h1": "Zakres obowiązku",
                "lead": "Sprawdź zakres obowiązku i ustal kolejne działania.",
            },
            "sections": [
                {
                    "section_id": case.proposal.sections[0].section_id,
                    "heading": case.proposal.sections[0].heading,
                    "body_markdown": case.fact.extracted_fact
                    + " Przedsiębiorca sprawdza zakres obowiązków, porządkuje dokumenty "
                    "i planuje kolejne działania zgodnie z profilem swojej działalności.",
                }
            ],
            "faq": [],
            "cta_blocks": [{"body_markdown": "Skontaktuj się z doradcą Ekologus."}],
            "internal_links": [],
            "publish_ready": False,
        }
        return CodexAppServerTurnResult(status="completed", output_text=json.dumps(output))


def _assurance_result(request, application):
    facts = json.loads(request.untrusted_context)["official_source_facts"]
    checks = []
    for binding in application["constraint_section_bindings"]:
        section = binding["allowed_document_section_ids"][0]
        evidence = sorted(
            {
                evidence_id
                for fact in facts
                if fact.get("assigned_document_section_id", section) == section
                for evidence_id in fact["evidence_ids"]
            }
        )
        checks.append(
            {
                "constraint_id": binding["constraint_id"],
                "status": "pass",
                "reason_code": "supported",
                "reason": "Zgodny z exact źródłem.",
                "document_section_id": section,
                "evidence_ids": evidence,
            }
        )
    return CodexAppServerTurnResult(
        status="completed",
        output_text=json.dumps(
            {
                "checks": checks,
                "language": "pl-PL",
                "publish_ready": False,
                "human_review_required": True,
            }
        ),
    )


def _prepare(case):
    response = case.http.post(
        f"/api/content/work-items/{case.proposal.work_item_id}/full-draft-generation-v3/preview",
        json={"proposal_id": case.proposal.proposal_id},
    )
    assert response.status_code == 200, response.text
    return response.json()["action_id"]


def _authorize(case, action_id):
    for operation, body in [
        ("validate", None),
        ("preview", {}),
        (
            "review",
            {
                "outcome": "approved_for_prepare",
                "reviewed_by": "synthetic-reviewer",
                "notes": "Exact full text.",
                "checked_items": ["reviewed_exact_full_draft_v3"],
            },
        ),
        (
            "confirm",
            {
                "confirmed_by": "synthetic-reviewer",
                "preview_acknowledged": True,
                "notes": "Exact approval.",
            },
        ),
        ("impact-check", {"checked_by": "synthetic-reviewer", "notes": "Local only."}),
        ("apply", {"confirm": True, "confirmed_by": "synthetic-reviewer"}),
    ]:
        response = case.http.post(f"/api/actions/{action_id}/{operation}", json=body)
        assert response.status_code == 200, response.text
        if operation == "apply":
            assert response.json()["applied"] is True, response.text
    assert not case.turns


def test_full_draft_lifecycle_persists_one_revision_and_public_status(tmp_path: Path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    action_id = _prepare(case)
    _authorize(case, action_id)
    path = f"/api/content/full-draft-generations-v3/{action_id}/dispatch"
    generated = case.http.post(path)
    assert generated.status_code == 200, generated.text
    status = case.http.get(f"/api/content/work-items/{case.proposal.work_item_id}/initial-draft")
    assert status.status_code == 200, status.text
    result = status.json()
    assert result["status"] == "created", json.dumps(result, ensure_ascii=False)
    assert result["proposal_id"] == case.proposal.proposal_id
    assert result["revision"]["proposal_metadata"]["codex_run_id"] == result["run_id"]
    assert result["revision"]["generation_authorization"]["action_id"] == action_id
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 1
    )
    turns = len(case.turns)
    assert turns >= 1
    assert case.http.post(path).status_code == 200
    assert (
        case.http.get(f"/api/content/work-items/{case.proposal.work_item_id}/initial-draft").json()
        == result
    )
    assert len(case.turns) == turns


@pytest.mark.parametrize(
    "fault",
    ["packet", "receipt", "fact", "identity", "source_pack", "input", "subject", "proposal"],
)
def test_reviewed_authorization_drift_has_zero_writer_turns(tmp_path, monkeypatch, fault):
    from tests.content.test_v3_draft_review_context import _inject_context_drift

    case = _case(tmp_path, monkeypatch)
    action_id = _prepare(case)
    _authorize(case, action_id)
    if fault == "proposal":
        case.snapshot.planning_workspace.proposal = case.proposal.model_copy(
            update={"proposal_id": "wrong-proposal"}
        )
    else:
        _inject_context_drift(case, monkeypatch, fault)
    response = case.http.post(f"/api/content/full-draft-generations-v3/{action_id}/dispatch")
    assert response.status_code == 409, response.text
    assert not case.turns
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 0
    )


@pytest.mark.parametrize("field", ["reviewed_by", "created_at", "confirmed_by"])
def test_persisted_receipt_must_match_referenced_audit_provenance(tmp_path, monkeypatch, field):
    from wilq.content.workflow.store.store_full_draft_generation_v3 import (
        assert_full_draft_v3_authority,
    )

    case = _case(tmp_path, monkeypatch)
    action_id = _prepare(case)
    _authorize(case, action_id)
    receipt = case.workflow_store.load_full_draft_generation_v3_receipt(action_id)
    assert receipt is not None
    value = receipt.created_at + timedelta(seconds=1) if field == "created_at" else "wrong-actor"
    forged = receipt.model_copy(update={field: value})
    # Corrupt only this temporary database, including the persisted receipt. Comparing
    # a supplied receipt to itself must not replace the referenced audit provenance.
    with case.workflow_store._connect() as connection:
        connection.execute("DROP TRIGGER content_full_draft_generation_v3_receipts_no_update")
        connection.execute(
            "UPDATE content_full_draft_generation_v3_receipts SET payload_json = ? "
            "WHERE action_id = ?",
            (forged.model_dump_json(), action_id),
        )
    with case.workflow_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError):
            assert_full_draft_v3_authority(connection, forged, case.workflow_store.path)


def test_claim_without_worker_can_recover_same_run_once(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    action = _prepare(case)
    _authorize(case, action)
    submissions = []

    def rejected(fn, *args):
        submissions.append("rejected")
        raise RuntimeError("synthetic-before-enqueue")

    def accepted(fn, *args):
        submissions.append("accepted")
        fn(*args)

    kwargs = dict(
        workflow_store=case.workflow_store,
        run_store=case.audit_store,
        snapshot_loader=lambda _: case.snapshot,
        client_factory=lambda: case.client,
    )
    first = dispatch_full_draft_generation_v3(
        action, executor=SimpleNamespace(submit=rejected), **kwargs
    )
    assert first.status == "blocked"
    claim = case.workflow_store.load_full_draft_generation_v3_dispatch(action)
    assert claim is not None and not case.turns
    dispatch_full_draft_generation_v3(action, executor=SimpleNamespace(submit=accepted), **kwargs)
    assert submissions == ["rejected", "accepted"]
    assert case.workflow_store.load_full_draft_generation_v3_dispatch(action) == claim
    assert case.turns
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 1
    )


def _dispatch(case, action_id, submit):
    return dispatch_full_draft_generation_v3(
        action_id,
        workflow_store=case.workflow_store,
        run_store=case.audit_store,
        snapshot_loader=lambda _: case.snapshot,
        client_factory=lambda: case.client,
        executor=SimpleNamespace(submit=submit),
    )


def _queued_case(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    action_id = _prepare(case)
    _authorize(case, action_id)
    tasks = []
    outcome = _dispatch(case, action_id, lambda fn, *args: tasks.append((fn, args)))
    assert outcome.status == "generating"
    claim = case.workflow_store.load_full_draft_generation_v3_dispatch(action_id)
    assert claim is not None
    return case, action_id, claim, tasks


def test_concurrent_dispatch_and_queued_duplicates_have_one_worker(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from wilq.content.workflow.store.store import ContentWorkflowStore

    case = _case(tmp_path, monkeypatch)
    action_id = _prepare(case)
    _authorize(case, action_id)
    tasks = []
    barrier = Barrier(2)

    def submit_claim(_):
        barrier.wait(timeout=10)
        return dispatch_full_draft_generation_v3(
            action_id,
            workflow_store=ContentWorkflowStore(case.workflow_store.path),
            run_store=LocalStateStore(case.workflow_store.path),
            snapshot_loader=lambda _: case.snapshot,
            client_factory=lambda: case.client,
            executor=SimpleNamespace(submit=lambda fn, *args: tasks.append((fn, args))),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit_claim, range(2)))
    assert all(outcome.status == "generating" for outcome in outcomes)
    assert len(tasks) == 2
    barrier = Barrier(2)

    def execute(task):
        barrier.wait(timeout=10)
        fn, args = task
        fn(*args)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(execute, tasks))
    assert len(case.turns) == 2
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 1
    )
    assert (
        len(
            [
                r
                for r in case.audit_store.list_codex_runs()
                if r.hook == "content_initial_full_draft"
            ]
        )
        == 1
    )


def test_enqueue_response_loss_resubmits_same_permit(tmp_path, monkeypatch):
    case, action, claim, tasks = _queued_case(tmp_path, monkeypatch)

    def lost(fn, *args):
        tasks.append((fn, args))
        raise RuntimeError("synthetic-enqueue-response-loss")

    assert _dispatch(case, action, lost).status == "blocked"
    assert (
        _dispatch(case, action, lambda fn, *args: tasks.append((fn, args))).status == "generating"
    )
    for fn, args in tasks:
        fn(*args)
    assert len(case.turns) == 2
    assert case.workflow_store.load_full_draft_generation_v3_dispatch(action) == claim
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 1
    )


@pytest.mark.parametrize(
    "fault", ["failed", "blocked", "expired", "ambiguous", "ambiguous_expired"]
)
def test_terminal_or_started_worker_is_never_resubmitted(tmp_path, monkeypatch, fault):
    from wilq.schemas.core import utc_now

    case, action, claim, _tasks = _queued_case(tmp_path, monkeypatch)
    receipt = case.workflow_store.load_full_draft_generation_v3_receipt(action)
    if fault.startswith("ambiguous"):
        assert case.workflow_store.start_full_draft_generation_v3_worker(
            receipt, claim, lambda: None
        )
    run = next(r for r in case.audit_store.list_codex_runs() if r.id == claim.run_id)
    updates = (
        {"status": fault, "completed_at": utc_now(), "error": "synthetic-terminal"}
        if fault in {"failed", "blocked"}
        else {"deadline_at": utc_now() - timedelta(seconds=1)}
        if fault.endswith("expired")
        else {}
    )
    case.audit_store.save_codex_run(run.model_copy(update=updates))

    def forbidden(*_args):
        raise AssertionError("repeat submission")

    response = _dispatch(case, action, forbidden)
    assert response.status == ("generating" if fault == "ambiguous" else "blocked")
    if fault == "ambiguous_expired":
        assert "full_draft_v3_reconciliation_required" in response.blockers[0].source_codes
    assert _dispatch(case, action, forbidden) == response
    assert not case.turns


def test_drift_after_claim_before_turn_blocks_worker(tmp_path, monkeypatch):
    from tests.content.test_v3_draft_review_context import _inject_context_drift

    case, action, _claim, tasks = _queued_case(tmp_path, monkeypatch)
    _inject_context_drift(case, monkeypatch, "subject")
    fn, args = tasks[0]
    fn(*args)
    assert not case.turns
    assert _dispatch(case, action, lambda *_args: pytest.fail("resubmitted")).status == "blocked"
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 0
    )


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "review",
        "binding",
        "binding_without_packet",
        "metadata",
        "run_status",
        "run_origin",
    ],
)
def test_atomic_append_rejects_post_model_drift(tmp_path, monkeypatch, fault):
    from tests.content.test_v3_draft_review_context import _inject_context_drift
    from wilq.content.workflow.store.store import ContentWorkflowStore

    case = _case(tmp_path, monkeypatch)
    action = _prepare(case)
    _authorize(case, action)
    original = ContentWorkflowStore.append_draft_revision

    def append(store, command, *, completed_codex_run=None):
        if fault == "source":
            _inject_context_drift(case, monkeypatch, "fact")
        elif fault == "review":
            response = case.http.post(
                f"/api/actions/{action}/review",
                json={
                    "outcome": "rejected",
                    "reviewed_by": "synthetic-reviewer",
                    "notes": "Wycofano zgodę.",
                    "checked_items": [],
                },
            )
            assert response.status_code == 200, response.text
        elif fault == "binding":
            command = command.model_copy(update={"generation_authorization": None})
        elif fault == "binding_without_packet":
            command = type(command).model_validate(
                command.model_dump()
                | {
                    "generation_authorization": None,
                    "planning_input_digest": None,
                    "research_packet_id": None,
                    "research_packet_digest": None,
                    "proposal_metadata": None,
                }
            )
        elif fault == "metadata":
            command = command.model_copy(update={"proposal_metadata": None})
        elif fault == "run_status":
            completed_codex_run = completed_codex_run.model_copy(update={"status": "failed"})
        else:
            completed_codex_run = completed_codex_run.model_copy(update={"hook": "wrong-origin"})
        return original(store, command, completed_codex_run=completed_codex_run)

    monkeypatch.setattr(ContentWorkflowStore, "append_draft_revision", append)
    assert _dispatch(case, action, lambda fn, *args: fn(*args)).status == "blocked"
    assert len(case.turns) == 2
    assert (
        case.workflow_store.load_draft_revision_state(case.proposal.work_item_id).revision_count
        == 0
    )
