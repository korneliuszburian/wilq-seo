"""Default v3 dispatch readers and legacy no-identity dispatch blockers."""

from __future__ import annotations

import importlib
import inspect
import sqlite3
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

from tests.content.test_generated_proposal_turn_v2 import (
    _planning_input_with_caller_context,
    _ready_inputs,
)
from tests.content.test_planning_generation_intent_v3 import (
    _approve_exact_packet,
    _client,
    _preview,
)
from tests.content.test_research_packet_v3_preview import _pack
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_intent_v3 import (
    ApprovedPacketV3PlanningProjection,
    PlanningGenerationIntentV3Proposal,
    PlanningGenerationIntentV3Snapshot,
    planning_generation_intent_v3_action_id,
    planning_generation_intent_v3_context_digest,
    planning_generation_intent_v3_digest,
)
from wilq.content.planning.generation_intent_v3_dispatch import (
    PlanningGenerationIntentV3DispatchOutcome,
    _proposal_blocked,
    dispatch_applied_planning_intent_v3,
)
from wilq.content.planning.planning_generation_queue import enqueue_planning_generation
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Blocker
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def _legacy_snapshot_without_identity(
    snapshot: PlanningGenerationIntentV3Snapshot,
) -> PlanningGenerationIntentV3Snapshot:
    excluded = {
        "schema_version",
        "intent_digest",
        "context_digest",
        "generation_performed",
        "model_enqueued",
        "external_write_attempted",
    }
    projection_payload = snapshot.model_dump(mode="python", exclude=excluded)
    projection_payload.pop("per_url_delivery_identity_action_id", None)
    projection = ApprovedPacketV3PlanningProjection.model_validate(
        projection_payload,
        strict=True,
    )
    legacy_projection = projection.model_dump(mode="json")
    legacy_projection.pop("per_url_delivery_identity_action_id", None)
    context_digest = planning_generation_intent_v3_context_digest(legacy_projection)
    intent_digest = planning_generation_intent_v3_digest(context_digest)
    payload = snapshot.model_dump(mode="python") | {
        "context_digest": context_digest,
        "intent_digest": intent_digest,
    }
    payload.pop("per_url_delivery_identity_action_id", None)
    return PlanningGenerationIntentV3Snapshot.model_validate(payload, strict=True)


def test_v3_default_dispatch_readers_receive_exact_identity_action_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    current = _preview()
    identity_action_id = current.per_url_delivery_identity_action_id
    assert identity_action_id is not None
    pack = _pack()
    reader_calls: list[tuple[str, str | None]] = []
    pack_module = importlib.import_module("apps.api.wilq_api.routers.content_source_pack_v3")
    packet_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )

    def read_pack(
        _work_item_id: str,
        *,
        per_url_delivery_identity_action_id: str | None = None,
    ):
        reader_calls.append(("pack", per_url_delivery_identity_action_id))
        return pack

    def read_packet(
        _work_item_id: str,
        *,
        per_url_delivery_identity_action_id: str | None = None,
    ):
        reader_calls.append(("packet", per_url_delivery_identity_action_id))
        return current

    monkeypatch.setattr(pack_module, "read_current_source_pack_v3_preview", read_pack)
    monkeypatch.setattr(packet_module, "read_current_research_packet_v3_preview", read_packet)
    dispatch_module = importlib.import_module("wilq.content.planning.generation_intent_v3_dispatch")
    assert (
        "identity_action_id"
        in inspect.signature(dispatch_module._load_current_projection).parameters
    )
    monkeypatch.setattr(
        dispatch_module,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(planning_input=object(), blockers=()),
    )
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(item=SimpleNamespace(id="wi_exact", evidence_ids=())),
        service_profile_context=SimpleNamespace(service_card_id=None),
    )
    result = dispatch_module._load_current_projection(
        work_item_id="wi_exact",
        packet_id=current.preview_id,
        digest=current.preview_hash,
        identity_action_id=identity_action_id,
        workflow_store=ContentWorkflowStore(tmp_path / "workflow.sqlite3"),
        snapshot_loader=lambda _work_item_id: snapshot,
        source_pack_loader=None,
        current_packet_loader=None,
        source_facts_loader=lambda: (),
    )

    assert isinstance(result, ResearchPacketV3Blocker)
    assert result.code == "research_packet_v3_approval_missing"
    assert reader_calls == [("pack", identity_action_id), ("packet", identity_action_id)]


def test_v3_identity_guard_blocks_queue_insert_and_holds_the_admission_write_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _source_pack, seed = _ready_inputs()
    planning_input = _planning_input_with_caller_context(seed).model_copy(
        update={"service_label": "Usługi środowiskowe"}
    )
    request = ContentPlanningProposalRequest(
        content_kind=planning_input.content_kind,
        service_card_id=planning_input.confirmed_service_card_id,
        expected_planning_input_digest=planning_input.planning_input_digest,
        requested_by="synthetic-reviewer",
    )
    store = ContentPlanningProposalStore(tmp_path / "planning.sqlite3")
    queue_module = importlib.import_module("wilq.content.planning.planning_generation_queue")
    assert "queue_admission_guard" in inspect.signature(enqueue_planning_generation).parameters
    scheduled: list[dict[str, object]] = []
    monkeypatch.setattr(
        queue_module,
        "schedule_queued_planning_generation",
        lambda **kwargs: scheduled.append(kwargs) or kwargs["result"],
    )
    blocker = ResearchPacketV3Blocker(
        code="per_url_delivery_identity_mismatch",
        owner="WILQ content workflow",
        evidence_ids=(),
        safe_next_step="Przygotuj intent dla aktualnej tożsamości strony.",
    )
    blocked_response = _proposal_blocked(planning_input.work_item_id, request, blocker)
    guard_calls = 0
    writer_started = Event()
    writer_acquired = Event()
    writer_thread: Thread | None = None
    writer_was_blocked: bool | None = None

    def concurrent_writer() -> None:
        connection = sqlite3.connect(store.path, timeout=2)
        try:
            writer_started.set()
            connection.execute("BEGIN IMMEDIATE")
            writer_acquired.set()
            connection.rollback()
        finally:
            connection.close()

    def queue_admission_guard(connection: sqlite3.Connection):
        nonlocal guard_calls, writer_thread, writer_was_blocked
        guard_calls += 1
        assert connection.in_transaction
        writer_thread = Thread(target=concurrent_writer, daemon=True)
        writer_thread.start()
        assert writer_started.wait(1)
        writer_was_blocked = not writer_acquired.wait(0.05)
        return blocked_response

    outcome = enqueue_planning_generation(
        planning_input=planning_input,
        work_item_id=planning_input.work_item_id,
        request=request,
        snapshot_loader=lambda _work_item_id: None,  # type: ignore[arg-type]
        store=store,
        generation_guard=lambda: None,
        queue_admission_guard=queue_admission_guard,
    )
    if writer_thread is not None:
        writer_thread.join(timeout=2)

    subject = ContentPlanningSubject(
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
    )
    assert outcome.status == "blocked"
    assert guard_calls == 1
    assert writer_was_blocked is True
    assert writer_acquired.is_set()
    assert (
        store.queued_subject_response(
            planning_input.work_item_id,
            subject,
            request.expected_planning_input_digest,
        )
        is None
    )
    assert scheduled == []


def _queue_admission_fixture(tmp_path: Path):
    current = _preview()
    client, workflow_store = _client(tmp_path, current)
    packet_receipt = _approve_exact_packet(workflow_store, current)
    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": packet_receipt.packet_id, "packet_digest": packet_receipt.packet_digest},
    )
    assert response.status_code == 200, response.text
    proposal = workflow_store.load_planning_generation_intent_v3_proposal(
        response.json()["action_id"]
    )
    assert proposal is not None
    identity = _pack().per_url_identity
    assert identity is not None
    assert getattr(proposal.snapshot, "per_url_delivery_identity_action_id", None) == (
        identity.action_id
    )
    _source_pack, seed = _ready_inputs()
    planning_input = _planning_input_with_caller_context(seed).model_copy(
        update={"service_label": "Usługi środowiskowe"}
    )
    request = ContentPlanningProposalRequest(
        content_kind=planning_input.content_kind,
        service_card_id=planning_input.confirmed_service_card_id,
        expected_planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=packet_receipt.packet_id,
        expected_research_packet_digest=packet_receipt.packet_digest,
        requested_by="synthetic-reviewer",
    )
    return workflow_store, proposal, identity, planning_input, request


def test_v3_queue_admission_blocks_semantic_drift_after_initial_currentness_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workflow_store, proposal, identity, planning_input, request = _queue_admission_fixture(tmp_path)
    observed_blockers: list[ResearchPacketV3Blocker] = []
    build_admission_guard = getattr(
        importlib.import_module("wilq.content.planning.generation_intent_v3_dispatch"),
        "_build_queue_admission_guard",
        None,
    )
    assert callable(build_admission_guard)
    admission_guard = build_admission_guard(proposal, request, observed_blockers)
    with workflow_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO content_per_url_delivery_identity_bindings "
            "(binding_id, action_id, canonical_path, current_work_item_id, "
            "semantic_row_digest, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                identity.binding_id,
                identity.action_id,
                identity.canonical_path,
                identity.current_work_item_id,
                identity.semantic_row_digest,
                "{}",
            ),
        )
        connection.execute(
            "INSERT INTO content_per_url_decision_observations "
            "(observation_id, canonical_path, current_work_item_id, semantic_row_digest, "
            "evidence_digest, observed_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "observation_before_queue_check",
                identity.canonical_path,
                identity.current_work_item_id,
                identity.semantic_row_digest,
                "1" * 64,
                "2026-09-25T00:00:00Z",
                "{}",
            ),
        )
    with workflow_store._connect() as connection:
        assert admission_guard(connection) is None
    with workflow_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO content_per_url_decision_observations "
            "(observation_id, canonical_path, current_work_item_id, semantic_row_digest, "
            "evidence_digest, observed_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "observation_after_queue_check",
                identity.canonical_path,
                identity.current_work_item_id,
                "f" * 64,
                "2" * 64,
                "2026-09-25T00:00:01Z",
                "{}",
            ),
        )
    queue_module = importlib.import_module("wilq.content.planning.planning_generation_queue")
    scheduled: list[dict[str, object]] = []
    monkeypatch.setattr(
        queue_module,
        "schedule_queued_planning_generation",
        lambda **kwargs: scheduled.append(kwargs) or kwargs["result"],
    )
    queue_store = ContentPlanningProposalStore(workflow_store.path)
    outcome = enqueue_planning_generation(
        planning_input=planning_input,
        work_item_id=planning_input.work_item_id,
        request=request,
        snapshot_loader=lambda _work_item_id: None,  # type: ignore[arg-type]
        store=queue_store,
        generation_guard=lambda: None,
        queue_admission_guard=admission_guard,
    )
    subject = ContentPlanningSubject(
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
    )

    assert outcome.status == "blocked"
    assert observed_blockers[-1].code == "per_url_delivery_identity_mismatch"
    assert (
        queue_store.queued_subject_response(
            planning_input.work_item_id,
            subject,
            request.expected_planning_input_digest,
        )
        is None
    )
    assert scheduled == []


def test_v3_queue_admission_blocks_work_item_scope_drift_with_matching_digest(
    tmp_path: Path,
) -> None:
    workflow_store, proposal, identity, _planning_input, request = _queue_admission_fixture(
        tmp_path
    )
    observed_blockers: list[ResearchPacketV3Blocker] = []
    build_admission_guard = getattr(
        importlib.import_module("wilq.content.planning.generation_intent_v3_dispatch"),
        "_build_queue_admission_guard",
        None,
    )
    assert callable(build_admission_guard)
    admission_guard = build_admission_guard(proposal, request, observed_blockers)
    with workflow_store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO content_per_url_delivery_identity_bindings "
            "(binding_id, action_id, canonical_path, current_work_item_id, "
            "semantic_row_digest, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                identity.binding_id,
                identity.action_id,
                identity.canonical_path,
                identity.current_work_item_id,
                identity.semantic_row_digest,
                "{}",
            ),
        )
        connection.execute(
            "INSERT INTO content_per_url_decision_observations "
            "(observation_id, canonical_path, current_work_item_id, semantic_row_digest, "
            "evidence_digest, observed_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "observation_prior_exact_work_item_scope",
                identity.canonical_path,
                identity.current_work_item_id,
                identity.semantic_row_digest,
                "2" * 64,
                "2026-09-25T00:00:01Z",
                "{}",
            ),
        )
        connection.execute(
            "INSERT INTO content_per_url_decision_observations "
            "(observation_id, canonical_path, current_work_item_id, semantic_row_digest, "
            "evidence_digest, observed_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "observation_latest_wrong_work_item",
                identity.canonical_path,
                "wi_other",
                identity.semantic_row_digest,
                "3" * 64,
                "2026-09-25T00:00:02Z",
                "{}",
            ),
        )
    with workflow_store._connect() as connection:
        result = admission_guard(connection)

    assert result is not None
    assert result.status == "blocked"
    assert observed_blockers[-1].code == "per_url_delivery_identity_mismatch"


def test_v3_legacy_intent_without_identity_blocks_before_dispatch_reads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    current = _preview()
    client, packet_store = _client(tmp_path, current)
    packet_receipt = _approve_exact_packet(packet_store, current)
    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": packet_receipt.packet_id, "packet_digest": packet_receipt.packet_digest},
    )
    assert response.status_code == 200, response.text
    current_proposal = packet_store.load_planning_generation_intent_v3_proposal(
        response.json()["action_id"]
    )
    assert current_proposal is not None
    legacy_snapshot = _legacy_snapshot_without_identity(current_proposal.snapshot)
    legacy_action_id = planning_generation_intent_v3_action_id(legacy_snapshot.intent_digest)
    legacy_proposal = PlanningGenerationIntentV3Proposal(
        action_id=legacy_action_id,
        snapshot=legacy_snapshot,
    )
    legacy_store = ContentWorkflowStore(tmp_path / "legacy.sqlite3")
    assert legacy_store.record_planning_generation_intent_v3_proposal(legacy_proposal) == "created"
    receipt_reads: list[str] = []
    load_receipt = legacy_store.load_planning_generation_intent_v3_receipt

    def track_receipt_read(action_id: str):
        receipt_reads.append(action_id)
        return load_receipt(action_id)

    monkeypatch.setattr(
        legacy_store,
        "load_planning_generation_intent_v3_receipt",
        track_receipt_read,
    )
    projection_calls: list[tuple[str, ...]] = []
    queue_calls: list[dict[str, object]] = []

    def load_projection(
        _work_item_id: str,
        _packet_id: str,
        _packet_digest: str,
        _identity_action_id: str | None = None,
    ) -> ResearchPacketV3Blocker:
        projection_calls.append(())
        return ResearchPacketV3Blocker(
            code="unexpected_projection_read",
            owner="WILQ content workflow",
            evidence_ids=(),
            safe_next_step="Nie uruchamiaj dispatch dla legacy intentu.",
        )

    def enqueue(**kwargs: object) -> PlanningGenerationIntentV3DispatchOutcome:
        queue_calls.append(kwargs)
        raise AssertionError("Legacy intent reached the generation queue.")

    outcome = dispatch_applied_planning_intent_v3(
        legacy_action_id,
        workflow_store=legacy_store,
        audit_store=LocalStateStore(tmp_path / "audit.sqlite3"),
        proposal_store=ContentPlanningProposalStore(tmp_path / "proposals.sqlite3"),
        snapshot_loader=lambda _work_item_id: None,  # type: ignore[arg-type]
        projection_loader=load_projection,
        enqueue=enqueue,
    )

    assert outcome.status == "blocked"
    assert outcome.blocker is not None
    assert outcome.blocker.code == "per_url_delivery_identity_required"
    assert receipt_reads == []
    assert projection_calls == []
    assert queue_calls == []
