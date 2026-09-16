from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.planning.proposal_read as proposal_read
import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.workspace.api as workflow_api
from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.content_initial_draft import register_content_initial_draft_route
from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)
from apps.api.wilq_api.routers.content_refresh_preparation import (
    register_content_refresh_preparation_routes,
)
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content import dynamic_planning_test_support as planning_support
from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command as identity_command
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.dynamic_input import ContentPlanningInputSummary
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.planning.input_sources import ContentPlanningSourceAssessment
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    classification_counts,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityCommand
from wilq.content.workflow.documents.revision_children import build_child_draft_revision_command
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBinding,
)
from wilq.content.workflow.refresh_preparation_models import RefreshPreparationRuntimeAuthorized
from wilq.content.workflow.store.refresh_preparation_atomic import RefreshPreparationAtomicityError
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import inventory_work_item_id
from wilq.storage.local_state import local_state_store

BDO_URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
BDO_WORK_ITEM_ID = inventory_work_item_id(BDO_URL)
BDO_SERVICE_CARD_ID = "ekologus_service_bdo_reporting"


def _packet_refresh_binding(
    *,
    work_item_id: str = "work-item",
    planning_input_digest: str = "b" * 64,
) -> ContentRefreshPreparationBinding:
    return ContentRefreshPreparationBinding(
        authorization_id="content_refresh_preparation_authorization_" + "a" * 24,
        authorization_digest="a" * 64,
        classification_run_id="classification_current",
        classification_run_digest="d" * 64,
        decision_set_digest="e" * 64,
        source_packet_row_digest="f" * 64,
        current_work_item_id=work_item_id,
        canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
        public_url=BDO_URL,
        content_kind="editorial",
        planning_input_digest=planning_input_digest,
    )


def _packet_bound_generating_response(
    binding: ContentRefreshPreparationBinding,
    *,
    packet_id: str = "packet-current",
    packet_digest: str = "c" * 64,
    run_id: str = "run-current",
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="generating",
        work_item_id=binding.current_work_item_id,
        content_kind=binding.content_kind,
        planning_input_digest=binding.planning_input_digest,
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
        refresh_preparation_binding=binding,
        runtime=ContentCodexRuntimeTrace(status="not_started", run_id=run_id),
        safe_next_step="Poczekaj na wynik.",
    )


def _packet_input_summary() -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        final_canonical_url=BDO_URL,
        content_kind="editorial",
        inventory_status="available",
        content_inventory_status="available",
        acf_section_inventory_status="not_applicable",
        source_assessments=[
            ContentPlanningSourceAssessment(
                source=source,
                status="not_applicable",
                reason="Testowy stan źródła.",
            )
            for source in (
                "wordpress",
                "service_profile",
                "gsc",
                "ga4",
                "google_ads",
                "ahrefs",
                "keyword_planner",
                "merchant",
                "localo",
                "social",
            )
        ],
        source_fact_count=0,
        evidence_id_count=0,
        knowledge_card_count=0,
    )


class _InlineExecutor:
    def submit(self, fn: Any, /, *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)


def test_classified_refresh_generates_one_bound_plan_and_revision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)

    authorization = _authorize(client)
    proposal = _generate_authorized_plan(client, authorization)
    initial = _generate_authorized_initial_draft(client, proposal, authorization)
    repeated = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_request(proposal, authorization),
    )
    status = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft")

    assert initial.status_code == repeated.status_code == status.status_code == 200
    assert (
        initial.json()["status"]
        == repeated.json()["status"]
        == status.json()["status"]
        == "created"
    )
    stored_proposal = content_planning_proposal_store().latest(BDO_WORK_ITEM_ID)
    revision = store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision
    assert stored_proposal is not None and revision is not None
    assert stored_proposal.refresh_preparation_binding is not None
    assert stored_proposal.refresh_preparation_binding == revision.refresh_preparation_binding
    assert revision.proposal_metadata is not None
    assert (
        revision.proposal_metadata.refresh_preparation_binding
        == revision.refresh_preparation_binding
    )
    assert runtime.calls == 2


def test_classified_refresh_status_prefers_exact_packet_bound_job_over_old_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.api.wilq_api.routers import content_planning_proposals as planning_router

    binding = _packet_refresh_binding()
    current = _packet_bound_generating_response(binding)
    old = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="work-item",
        content_kind="editorial",
        planning_input_digest="1" * 64,
        runtime=ContentCodexRuntimeTrace(status="not_started", run_id="run-old"),
        safe_next_step="Poczekaj na wynik.",
    )
    authorization = SimpleNamespace(planning_input_digest="8" * 64)
    authority_binding = binding.model_copy(
        update={"planning_input_digest": authorization.planning_input_digest}
    )

    class ProposalStore:
        queued_digest_calls: list[str] = []

        def latest_generation_response(self, _work_item_id: str) -> Any:
            return current

        def latest(self, _work_item_id: str) -> Any:
            return old

        def queued_subject_response(
            self, _work_item_id: str, _subject: Any, planning_input_digest: str
        ) -> Any:
            self.queued_digest_calls.append(planning_input_digest)
            return current

        def for_subject_input(self, *_args: Any) -> Any:
            raise AssertionError("exact queued response should avoid proposal fallback")

    resolution = RefreshPreparationRuntimeAuthorized(
        work_item_id="work-item",
        snapshot=object(),
        planning_input=SimpleNamespace(
            work_item_id="work-item",
            planning_input_digest=authorization.planning_input_digest,
        ),
        classification=object(),
        service_candidate=None,
        authorization=SimpleNamespace(binding=authority_binding),
    )

    class Authority:
        def resolve_planning(self, _work_item_id: str, request: Any) -> Any:
            assert request.expected_planning_input_digest == authorization.planning_input_digest
            return resolution

        def planning_block_response(self, _resolution: Any, _request: Any) -> None:
            return None

    class WorkflowStore:
        def load_refresh_preparation_authorization(self, _authorization_id: str) -> Any:
            return authorization

        def load_planning_decisions(self, _work_item_id: str) -> list[Any]:
            return []

        def load_content_research_packet(self, _packet_id: str) -> Any:
            return SimpleNamespace(
                packet_id="packet-current",
                packet_digest="c" * 64,
                current_work_item_id="work-item",
            )

    monkeypatch.setattr(planning_router, "content_planning_proposal_store", ProposalStore)
    monkeypatch.setattr(planning_router, "content_workflow_store", lambda: WorkflowStore())
    monkeypatch.setattr(
        proposal_read,
        "bind_research_packet_to_planning_input",
        lambda planning_input, _packet: SimpleNamespace(
            work_item_id=planning_input.work_item_id,
            planning_input_digest=binding.planning_input_digest,
        ),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.research_packet_preparation.current_research_packet_blocker",
        lambda **_kwargs: None,
    )

    result = planning_router._get_content_work_item_planning_proposal_status(
        work_item_id="work-item",
        snapshot_loader=lambda _work_item_id: (_ for _ in ()).throw(
            AssertionError("old fallback snapshot must not be read")
        ),
        refresh_authority=Authority(),
    )

    assert result.status == "generating"
    assert result.planning_input_digest == binding.planning_input_digest
    assert result.research_packet_id == current.research_packet_id
    assert result.runtime.run_id == current.runtime.run_id
    assert ProposalStore.queued_digest_calls == [binding.planning_input_digest]


def test_refresh_bound_reader_preserves_packet_conflict_runtime_and_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _packet_refresh_binding()
    authority_binding = binding.model_copy(update={"planning_input_digest": "8" * 64})
    queued = _packet_bound_generating_response(binding)
    base_input = SimpleNamespace(
        work_item_id=binding.current_work_item_id,
        planning_input_digest=authority_binding.planning_input_digest,
    )

    class ProposalStore:
        def queued_subject_response(self, *_args: Any) -> Any:
            return queued

    class WorkflowStore:
        def load_content_research_packet(self, _packet_id: str) -> Any:
            return SimpleNamespace(
                packet_id=queued.research_packet_id,
                packet_digest=queued.research_packet_digest,
                current_work_item_id=binding.current_work_item_id,
            )

    monkeypatch.setattr(
        proposal_read,
        "bind_research_packet_to_planning_input",
        lambda planning_input, _packet: SimpleNamespace(
            work_item_id=planning_input.work_item_id,
            planning_input_digest=binding.planning_input_digest,
        ),
    )
    monkeypatch.setattr(
        proposal_read, "content_planning_input_summary", lambda _input: _packet_input_summary()
    )
    monkeypatch.setattr(
        "wilq.content.workflow.research_packet_preparation.current_research_packet_blocker",
        lambda **_kwargs: SimpleNamespace(
            reason="packet_conflict",
            next_step_pl="Nowszy packet zastąpił zapisany packet.",
            evidence_ids=("evidence-packet",),
        ),
    )

    result = proposal_read.read_content_planning_proposal_for_refresh_binding(
        snapshot=object(),
        planning_input=base_input,
        binding=binding,
        authority_binding=authority_binding,
        store=ProposalStore(),
        workflow_store=WorkflowStore(),
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "research_packet_conflict"
    assert result.research_packet_id == queued.research_packet_id
    assert result.research_packet_digest == queued.research_packet_digest
    assert result.refresh_preparation_binding == binding
    assert result.runtime.run_id == queued.runtime.run_id


def test_refresh_bound_reader_returns_typed_conflict_for_completed_missing_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _packet_refresh_binding()
    authority_binding = binding.model_copy(update={"planning_input_digest": "8" * 64})
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=binding.current_work_item_id,
        content_kind=binding.content_kind,
        service_card_id=None,
        planning_input_digest=binding.planning_input_digest,
        research_packet_id="packet-missing",
        research_packet_digest="d" * 64,
        codex_run_id="run-completed",
        generation_status="codex_generated",
    )
    base_input = SimpleNamespace(
        work_item_id=binding.current_work_item_id,
        planning_input_digest=authority_binding.planning_input_digest,
    )

    class ProposalStore:
        def queued_subject_response(self, *_args: Any) -> None:
            return None

        def for_subject_input(self, *_args: Any) -> Any:
            return proposal

    class WorkflowStore:
        def load_content_research_packet(self, _packet_id: str) -> None:
            return None

    summary = _packet_input_summary()
    monkeypatch.setattr(proposal_read, "content_planning_input_summary", lambda _input: summary)

    result = proposal_read.read_content_planning_proposal_for_refresh_binding(
        snapshot=object(),
        planning_input=base_input,
        binding=binding,
        authority_binding=authority_binding,
        store=ProposalStore(),
        workflow_store=WorkflowStore(),
    )

    assert isinstance(result, ContentPlanningProposalResponse)
    assert result.status == "blocked"
    assert result.blockers[0].code == "research_packet_conflict"
    assert result.input_summary is summary
    assert result.research_packet_id == proposal.research_packet_id
    assert result.research_packet_digest == proposal.research_packet_digest
    assert result.refresh_preparation_binding == binding


def test_refresh_initial_draft_status_is_not_masked_as_generation_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    client = _app_client(_authority(store), monkeypatch)

    status = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft")

    assert status.status_code == 200, status.text
    assert status.json()["status"] == "blocked"
    assert status.json()["blockers"][0]["code"] != "production_generation_disabled"
    assert runtime.calls == 0


def test_post_model_classification_drift_persists_no_authorized_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    run = _refresh_run()
    store.record_production_classification(run)
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)
    authorization = _authorize(client)
    _seed_exact_current_packet(client, store)
    original_turn = runtime.run_structured_turn

    def drift_after_model(request: Any) -> Any:
        result = original_turn(request)
        _replace_latest_classification(store, _drifted_run(run))
        return result

    monkeypatch.setattr(runtime, "run_structured_turn", drift_after_model)
    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": preview["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    bound_planning_input_digest = response.json()["planning_input_digest"]
    terminal = _wait_for_plan(client, response)
    queued = content_planning_proposal_store().queued_response(
        BDO_WORK_ITEM_ID,
        BDO_SERVICE_CARD_ID,
        bound_planning_input_digest,
    )

    assert terminal.status_code == 200
    assert terminal.json()["status"] == "blocked"
    assert terminal.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert queued is not None
    assert queued.status == "blocked"
    assert queued.planning_input_digest == bound_planning_input_digest
    assert queued.input_summary is not None
    assert queued.input_summary.model_dump(mode="json") == response.json()["input_summary"]
    assert queued.refresh_preparation_binding is not None
    assert queued.refresh_preparation_binding.authorization_id == authorization["authorization_id"]
    assert _planning_job_status(tmp_path) == "blocked"
    assert _planning_claim_status(tmp_path) == "failed"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None
    assert store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision is None
    assert runtime.calls == 1


def test_worker_pre_model_refresh_drift_persists_bound_blocked_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    run = _refresh_run()
    store.record_production_classification(run)
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)
    authorization = _authorize(client)
    _seed_exact_current_packet(client, store)
    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()

    class HoldingExecutor:
        worker: Any | None = None
        arguments: tuple[Any, ...] = ()

        def submit(self, worker: Any, *arguments: Any, **_kwargs: Any) -> None:
            self.worker = worker
            self.arguments = arguments

    executor = HoldingExecutor()
    monkeypatch.setattr(planning_generation_queue, "_PLANNING_GENERATION_EXECUTOR", executor)
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": preview["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    bound_planning_input_digest = response.json()["planning_input_digest"]
    queued_before_drift = content_planning_proposal_store().queued_response(
        BDO_WORK_ITEM_ID,
        BDO_SERVICE_CARD_ID,
        bound_planning_input_digest,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "generating"
    assert executor.worker is not None
    assert queued_before_drift is not None
    assert queued_before_drift.input_summary is not None
    _replace_latest_classification(store, _drifted_run(run))
    terminal = executor.worker(*executor.arguments)
    queued = content_planning_proposal_store().queued_response(
        BDO_WORK_ITEM_ID,
        BDO_SERVICE_CARD_ID,
        bound_planning_input_digest,
    )
    status = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals")

    assert terminal.status == "blocked"
    assert terminal.blockers[0].code == "refresh_preparation_authorization_stale"
    assert terminal.planning_input_digest == bound_planning_input_digest
    assert terminal.input_summary == queued_before_drift.input_summary
    assert terminal.refresh_preparation_binding == queued_before_drift.refresh_preparation_binding
    assert queued == terminal
    assert _planning_job_status(tmp_path) == "blocked"
    assert _planning_claim_status(tmp_path) == "failed"
    assert status.status_code == 200
    assert status.json()["status"] == "blocked"
    assert status.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None
    assert store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision is None
    assert runtime.calls == 0


def test_post_model_draft_drift_persists_no_revision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    run = _refresh_run()
    store.record_production_classification(run)
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)
    authorization = _authorize(client)
    proposal = _generate_authorized_plan(client, authorization)
    original_turn = runtime.run_structured_turn

    def drift_after_draft_model(request: Any) -> Any:
        result = original_turn(request)
        if runtime.calls == 2:
            _replace_latest_classification(store, _drifted_run(run))
        return result

    monkeypatch.setattr(runtime, "run_structured_turn", drift_after_draft_model)
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_request(proposal, authorization),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is not None
    assert store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision is None
    assert runtime.calls == 2


def test_atomic_store_rejects_unbound_legacy_same_input_before_idempotence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, _runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)
    authorization = _authorize(client)
    _generate_authorized_plan(client, authorization)
    proposal = content_planning_proposal_store().latest(BDO_WORK_ITEM_ID)
    assert proposal is not None and proposal.codex_run_id is not None
    completed_run = local_state_store().get_codex_run(proposal.codex_run_id)
    assert completed_run is not None

    with pytest.raises(RefreshPreparationAtomicityError):
        content_planning_proposal_store().save_generated(
            proposal.model_copy(update={"refresh_preparation_binding": None}),
            completed_run,
        )


def test_atomic_store_rejects_receipt_scalar_path_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, _runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)
    authorization = _authorize(client)
    _generate_authorized_plan(client, authorization)
    proposal = content_planning_proposal_store().latest(BDO_WORK_ITEM_ID)
    assert proposal is not None and proposal.codex_run_id is not None
    completed_run = local_state_store().get_codex_run(proposal.codex_run_id)
    assert completed_run is not None
    with cast(Any, store)._connect() as connection:
        connection.execute(
            """
            UPDATE content_refresh_preparation_authorizations
            SET canonical_path = '/inny-adres'
            WHERE authorization_id = ?
            """,
            (proposal.refresh_preparation_binding.authorization_id,),
        )

    with pytest.raises(RefreshPreparationAtomicityError):
        content_planning_proposal_store().save_generated(proposal, completed_run)


def test_atomic_revision_append_rejects_unbound_refresh_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, _runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority, monkeypatch)
    authorization = _authorize(client)
    proposal = _generate_authorized_plan(client, authorization)
    _generate_authorized_initial_draft(client, proposal, authorization)
    revision = store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision
    assert revision is not None and revision.proposal_metadata is not None
    child = build_child_draft_revision_command(
        revision,
        sections=revision.sections,
        proposal_metadata=revision.proposal_metadata,
        created_by="wilku",
    )
    assert child.refresh_preparation_binding == revision.refresh_preparation_binding
    assert child.proposal_metadata is not None
    assert (
        child.proposal_metadata.refresh_preparation_binding == revision.refresh_preparation_binding
    )
    unbound_metadata = revision.proposal_metadata.model_copy(
        update={"refresh_preparation_binding": None}
    )
    unbound = child.model_copy(
        update={
            "refresh_preparation_binding": None,
            "proposal_metadata": unbound_metadata,
        }
    )

    with pytest.raises(RefreshPreparationAtomicityError):
        store.append_draft_revision(unbound)


def _authority(store: object) -> ContentRefreshPreparationAuthority:
    def service_snapshot(work_item_id: str, service_card_id: str | None):
        baseline = snapshot_for_work_item_or_404(work_item_id)
        snapshot = workflow_api.build_content_work_item_snapshot_response_from_selected_decision(
            planning_support._synthetic_planning_decision(BDO_URL),  # noqa: SLF001
            freshness_assessment=baseline.freshness_assessment,
            service_card_id_override=service_card_id,
        )
        brief = snapshot.sales_brief.sales_brief_result.brief
        if brief is None:
            return snapshot
        brief_result = snapshot.sales_brief.sales_brief_result.model_copy(
            update={"brief": brief.model_copy(update={"cta_destination": "/kontakt/"})}
        )
        return snapshot.model_copy(
            update={
                "sales_brief": snapshot.sales_brief.model_copy(
                    update={"sales_brief_result": brief_result}
                )
            }
        )

    return ContentRefreshPreparationAuthority(
        store=cast(Any, store),
        snapshot_loader=service_snapshot,
        proposal_store=content_planning_proposal_store(),
        content_kind_inventory_loader=lambda work_item_id: ContentKindInventoryBinding(
            work_item_id=work_item_id,
            canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
            public_url=BDO_URL,
            wordpress_content_type="uslugi",
            content_kind="service",
            inventory_evidence_ids=("ev_connector_wordpress_ekologus_status",),
            trusted=True,
        ),
    )


def _app_client(
    authority: ContentRefreshPreparationAuthority,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    app = FastAPI()
    router = APIRouter()
    register_content_refresh_preparation_routes(router, authority_factory=lambda: authority)
    register_content_planning_proposal_routes(
        router,
        snapshot_loader=lambda work_item_id: authority._snapshot_loader(  # noqa: SLF001
            work_item_id, None
        ),
        refresh_authority_factory=lambda: authority,
    )
    register_content_initial_draft_route(
        router,
        snapshot_loader=lambda work_item_id: authority._snapshot_loader(  # noqa: SLF001
            work_item_id, None
        ),
        refresh_authority_factory=lambda: authority,
    )
    from apps.api.wilq_api.routers.content_source_fact_authority import (
        register_content_source_fact_authority_routes,
    )
    from apps.api.wilq_api.routers.content_source_pack_binding import (
        register_content_source_pack_binding_routes,
    )

    register_content_source_fact_authority_routes(router)
    register_content_source_pack_binding_routes(router)
    monkeypatch.setattr(
        planning_generation_queue, "_PLANNING_GENERATION_EXECUTOR", _InlineExecutor()
    )
    app.include_router(router)
    app.include_router(create_actions_router(lambda: None))
    return TestClient(app)


def _authorize(client: TestClient) -> dict[str, str]:
    ready = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    )
    assert ready.status_code == 200, ready.text
    body = cast(dict[str, Any], ready.json())
    assert body["status"] == "ready_to_authorize", body.get("blockers", body)
    classification = cast(dict[str, Any], body["classification"])
    authorized = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation/authorizations",
        json={
            "expected_production_classification_run_digest": classification[
                "classification_run_digest"
            ],
            "expected_production_classification_decision_set_digest": classification[
                "decision_set_digest"
            ],
            "expected_production_classification_source_packet_row_digest": classification[
                "source_packet_row_digest"
            ],
            "expected_planning_input_digest": body["planning_input_digest"],
            "service_card_id": BDO_SERVICE_CARD_ID,
            "authorized_by": "wilku",
            "acknowledged_classification_blocker_codes": classification[
                "classification_blocker_codes"
            ],
        },
    )
    assert authorized.status_code == 201, authorized.text
    return cast(dict[str, str], authorized.json()["authorization"])


def _seed_exact_current_packet(client: TestClient, store: object) -> None:
    run = cast(Any, store).load_production_classification_for_work_item(BDO_WORK_ITEM_ID)
    assert run is not None
    identity_payload = identity_command(retained=True, run=exact_public_bdo_run()).model_dump(
        mode="python"
    )
    identity_payload.update(
        {
            "classification_run_id": run.run_id,
            "classification_run_digest": run.run_digest,
            "classification_source_row_digest": run.row.source_packet_row_digest,
            "retained_work_item_id": None,
            "retained_usage": None,
        }
    )
    identity = (
        cast(Any, store)
        .record_content_delivery_identity(
            ContentDeliveryIdentityCommand.model_validate(identity_payload)
        )
        .binding
    )
    _record_authority_source_pack(client, identity)


def _record_authority_source_pack(client: TestClient, identity: Any) -> None:
    preview = client.post(
        "/api/content/source-fact-authority-reviews/preview",
        json={
            "identity_binding_id": identity.binding_id,
            "proposed_source_fact_ids": ["ekologus_public_bdo_faq_2026_07_01"],
        },
    )
    assert preview.status_code == 200, preview.text
    action_id = preview.json()["action"]["id"]
    assert client.post(f"/api/actions/{action_id}/validate").json()["valid"] is True
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    assert (
        client.post(
            f"/api/actions/{action_id}/review",
            json={"outcome": "approved_for_prepare", "reviewed_by": "wilku", "notes": "exact"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/actions/{action_id}/confirm",
            json={"confirmed_by": "wilku", "notes": "exact", "preview_acknowledged": True},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/actions/{action_id}/impact-check",
            json={"checked_by": "wilku", "notes": "exact"},
        ).status_code
        == 200
    )
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "wilku"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["adapter_result"]["external_write_attempted"] is False
    prerequisites = client.get(
        f"/api/content/source-pack-bindings/prerequisites/{identity.binding_id}"
    )
    assert prerequisites.status_code == 200, prerequisites.text
    payload = prerequisites.json()
    source_pack = client.post(
        "/api/content/source-pack-bindings",
        json={
            "source_pack_id": "source_pack_classified_refresh",
            "source_pack_sha256": "a" * 64,
            "identity_binding_id": payload["identity_binding_id"],
            "identity_binding_digest": payload["identity_binding_digest"],
            "current_work_item_id": payload["current_work_item_id"],
            "source_fact_ids": payload["approved_source_fact_ids"],
            "evidence_ids": payload["row_authority_evidence_ids"],
            "fresh_context_digest": payload["fresh_context_digest"],
            "source_fact_registry_receipt": payload["source_fact_registry_receipt"],
            "fresh_context_attestation": payload["fresh_context_attestation"],
            "recorded_by": "classified_refresh_test",
            "recorded_at": payload["source_fact_registry_receipt"]["checked_at"],
        },
    )
    assert source_pack.status_code == 201, source_pack.text
    assert source_pack.json()["binding"]["status"] == "exact_current"


def _generate_authorized_plan(
    client: TestClient,
    authorization: dict[str, str],
) -> dict[str, Any]:
    _seed_exact_current_packet(client, content_workflow_store())
    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": preview["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    terminal = _wait_for_plan(client, response)
    assert terminal.status_code == 200, terminal.text
    body = cast(dict[str, Any], terminal.json())
    assert body["status"] in {"created", "idempotent", "ready"}, body
    return cast(dict[str, Any], body["proposal"])


def _generate_authorized_initial_draft(
    client: TestClient,
    proposal: dict[str, Any],
    authorization: dict[str, str],
) -> Any:
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_request(proposal, authorization),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "created", response.json()
    return response


def _initial_request(proposal: dict[str, Any], authorization: dict[str, str]) -> dict[str, str]:
    return {
        "expected_proposal_id": proposal["proposal_id"],
        "expected_planning_digest": proposal["planning_digest"],
        "expected_planning_input_digest": proposal["planning_input_digest"],
        "requested_by": "wilku",
        "refresh_preparation_authorization_id": authorization["authorization_id"],
        "expected_refresh_preparation_authorization_digest": authorization["authorization_digest"],
    }


def _wait_for_plan(client: TestClient, response: Any) -> Any:
    for _ in range(100):
        if response.status_code != 200 or response.json().get("status") != "generating":
            return response
        time.sleep(0.02)
        response = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals")
    return response


def _refresh_run():
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    payload.update(
        {
            "decision": "refresh",
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts((row, run.rows[1])),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=(row, run.rows[1]),
        audit=run.audit,
    )


def _drifted_run(run: object):
    payload = cast(Any, run).rows[0].model_dump(mode="python")
    payload["source_packet_row_digest"] = "f" * 64
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=cast(Any, run).input,
        counts=classification_counts((row, cast(Any, run).rows[1])),
        freshness=cast(Any, run).freshness,
        source_receipts=cast(Any, run).source_receipts,
        judge_receipt=cast(Any, run).judge_receipt,
        rows=(row, cast(Any, run).rows[1]),
        audit=cast(Any, run).audit,
    )


def _replace_latest_classification(store: object, run: object) -> None:
    with cast(Any, store)._connect() as connection:
        connection.execute("DELETE FROM content_production_classifications")
    cast(Any, store).record_production_classification(run)


def _planning_job_status(tmp_path: Path) -> str | None:
    with sqlite3.connect(tmp_path / "wilq.sqlite3") as connection:
        row = connection.execute(
            "SELECT status FROM content_planning_generation_jobs ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    return None if row is None else cast(str, row[0])


def _planning_claim_status(tmp_path: Path) -> str | None:
    with sqlite3.connect(tmp_path / "wilq.sqlite3") as connection:
        row = connection.execute(
            "SELECT status FROM content_planning_generation_claims ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    return None if row is None else cast(str, row[0])
