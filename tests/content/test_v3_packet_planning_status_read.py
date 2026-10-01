"""The planning status read verifies an exact current v3 research packet."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.content.test_planning_generation_intent_v3 import _approve_exact_packet
from tests.content.test_planning_generation_intent_v3_generation import (
    _approved_fact,
    _packet,
    _raw_input,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning import proposal_read as proposal_read_module
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    ContentPlanningInputSummary,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal import read_content_planning_proposal
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_claim_store import (
    ContentPlanningGenerationClaimStore,
)
from wilq.content.planning.packet_model_projection_v3 import (
    project_planning_input_for_packet_v3,
)
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningCtaBlock,
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Preview
from wilq.content.workflow.research_packet_v3_receipt import ResearchPacketV3PreviewRecord
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import CodexRun


def _proposal(
    *,
    packet: ResearchPacketV3Preview,
    planning_input_digest: str,
) -> ContentPlanningProposal:
    assert packet.preview_hash is not None
    return ContentPlanningProposal(
        work_item_id=packet.work_item_id,
        planning_digest="c" * 64,
        proposal_id="proposal-v3-status-read",
        codex_run_id="run-v3-status-read",
        generation_status="codex_generated",
        created_at=datetime.now(UTC),
        planning_input_digest=planning_input_digest,
        research_packet_id=f"content_research_packet_v3_{packet.preview_hash[:24]}",
        research_packet_digest=packet.preview_hash,
        content_kind="editorial",
        final_canonical_url=packet.page_url,
        service_card_id=None,
        target_reader="Operator środowiskowy",
        buyer_problem="Brak pewności co do obowiązku.",
        buyer_trigger="Zmiana wymagań.",
        search_intent="sprawdzenie obowiązku",
        cta_direction="Skonsultuj sytuację.",
        sections=[
            ContentPlanningSection(
                heading="Zakres",
                purpose="Wyjaśnia zakres.",
                regulatory_requirement_ids=["requirement_exact"],
                evidence_ids=["ev_official_fact"],
            )
        ],
        cta_blocks=[
            ContentPlanningCtaBlock(
                placement="Zakres",
                purpose="Zaproponuj sprawdzenie sytuacji firmy.",
                copy_direction="Zaproponuj kontakt z doradcą Ekologus.",
            )
        ],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak dokładnych danych.",
        ),
    )


def _snapshot() -> SimpleNamespace:
    return SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(id="wi_exact", content_kind="editorial")
        ),
        service_profile_context=SimpleNamespace(service_card_id=None),
    )


def _patch_registry_fact(monkeypatch: pytest.MonkeyPatch, fact: object) -> None:
    from wilq.content.knowledge import source_facts as source_facts_module

    monkeypatch.setattr(
        source_facts_module, "ekologus_source_facts", lambda: (fact,)
    )


def _patch_read_input(
    monkeypatch: pytest.MonkeyPatch,
    planning_input: object,
) -> None:
    monkeypatch.setattr(
        proposal_read_module,
        "build_content_planning_input",
        lambda _snapshot, service_card_id=None: (
            ContentPlanningInputBuildResult.model_construct(
                planning_input=planning_input,
                blockers=[],
            )
        ),
    )


def _save_completed_generation(
    *,
    proposal_store: ContentPlanningProposalStore,
    packet: ResearchPacketV3Preview,
    planning_input: ContentPlanningInput,
    claim_store: ContentPlanningGenerationClaimStore,
    claim_owner: str,
    claim_version: int,
) -> None:
    completed_at = datetime.now(UTC)
    planning_input_digest = planning_input.planning_input_digest
    completed_run = CodexRun(
        id="run-v3-status-read",
        skill="wilq-content-operator",
        hook="content_planning_proposal",
        source="wilq_api",
        status="completed",
        used_endpoints=[
            f"/api/content/work-items/{packet.work_item_id}/planning-proposals"
        ],
        evidence_ids=list(planning_input.evidence_ids),
        planning_input_digest=planning_input_digest,
        started_at=completed_at,
        completed_at=completed_at,
    )
    outcome, _stored = proposal_store.save_generated(
        _proposal(packet=packet, planning_input_digest=planning_input_digest),
        completed_run,
        planning_input=planning_input,
    )
    assert outcome == "created"
    stored = proposal_store.for_subject_input(
        packet.work_item_id,
        ContentPlanningSubject(content_kind="editorial", service_card_id=None),
        planning_input_digest,
    )
    assert stored is not None
    terminal = ContentPlanningProposalResponse(
        status="created",
        work_item_id=packet.work_item_id,
        content_kind="editorial",
        service_card_id=None,
        planning_input_digest=planning_input_digest,
        research_packet_id=stored.research_packet_id,
        research_packet_digest=stored.research_packet_digest,
        input_summary=content_planning_input_summary(planning_input),
        proposal=stored,
        runtime=ContentCodexRuntimeTrace(status="completed", run_id=completed_run.id),
        safe_next_step="Sprawdź plan.",
    )
    assert proposal_store.save_terminal_response(
        terminal,
        job_planning_input_digest=planning_input_digest,
        claim_version=claim_version,
    ) == "saved"
    assert claim_store.finish(
        work_item_id=packet.work_item_id,
        service_card_id=None,
        content_kind="editorial",
        planning_input_digest=planning_input_digest,
        claim_owner=claim_owner,
        claim_version=claim_version,
        status="finished",
    )


def _approved_packet_with_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ContentPlanningProposalStore, ResearchPacketV3Preview, object, object, str]:
    fact = _approved_fact()
    source_pack, packet = _packet(fact)
    assert packet.preview_hash is not None
    raw_input = _raw_input(packet).model_copy(
        update={"planning_input_digest": packet.planning_input_digest}
    )
    projected = project_planning_input_for_packet_v3(
        raw_input,
        packet=packet,
        source_pack=source_pack,
        source_facts=(fact,),
    )
    planning_input_digest = projected.planning_input.planning_input_digest

    state_path = tmp_path / "state.sqlite3"
    workflow_store = ContentWorkflowStore(state_path)
    monkeypatch.setenv("WILQ_STATE_DB", str(workflow_store.path))
    assert workflow_store.record_research_packet_v3_preview(
        ResearchPacketV3PreviewRecord.from_preview(packet)
    ) in {"created", "idempotent"}
    _approve_exact_packet(workflow_store, packet)

    proposal_store = ContentPlanningProposalStore(state_path)
    queued_run_id = "planning_generation_queue_attempt"
    assert proposal_store.enqueue(
        ContentPlanningProposalResponse(
            status="generating",
            work_item_id=packet.work_item_id,
            content_kind="editorial",
            service_card_id=None,
            planning_input_digest=planning_input_digest,
            research_packet_id=f"content_research_packet_v3_{packet.preview_hash[:24]}",
            research_packet_digest=packet.preview_hash,
            runtime=ContentCodexRuntimeTrace(status="not_started", run_id=queued_run_id),
            safe_next_step="Plan jest przygotowywany.",
        )
    ) == "queued"
    claim_store = ContentPlanningGenerationClaimStore(state_path)
    claim = claim_store.claim(
        work_item_id=packet.work_item_id,
        service_card_id=None,
        content_kind="editorial",
        planning_input_digest=planning_input_digest,
        claim_owner=queued_run_id,
    )
    assert claim.outcome == "acquired"
    _save_completed_generation(
        proposal_store=proposal_store,
        packet=packet,
        planning_input=projected.planning_input,
        claim_store=claim_store,
        claim_owner=queued_run_id,
        claim_version=claim.claim_version,
    )

    _patch_read_input(monkeypatch, raw_input)
    _patch_registry_fact(monkeypatch, fact)
    return proposal_store, packet, source_pack, fact, planning_input_digest


def test_current_exact_v3_packet_reads_as_ready_plan_without_packet_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet, _source_pack, _fact, planning_input_digest = (
        _approved_packet_with_read(tmp_path, monkeypatch)
    )

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "ready", (
        response.blockers,
        response.safe_next_step,
    )
    assert response.planning_input_digest == planning_input_digest
    assert response.research_packet_id == (
        f"content_research_packet_v3_{packet.preview_hash[:24]}"
    )
    assert response.research_packet_digest == packet.preview_hash
    assert response.proposal is not None


@pytest.mark.parametrize(
    "fault",
    ["missing_cta", "missing_regulatory_lineage", "unresolved_inventory_mapping"],
)
def test_exact_v3_packet_runs_existing_proposal_readiness_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    proposal_store, packet, _source_pack, _fact, _digest = _approved_packet_with_read(
        tmp_path, monkeypatch
    )
    assert packet.preview_hash is not None
    with sqlite3.connect(proposal_store.path) as connection:
        payload = json.loads(connection.execute(
            "SELECT payload_json FROM content_planning_proposals WHERE work_item_id = ?",
            (packet.work_item_id,),
        ).fetchone()[0])
        if fault == "missing_cta":
            payload["cta_blocks"] = []
        elif fault == "missing_regulatory_lineage":
            payload["sections"][0].update(regulatory_requirement_ids=[], evidence_ids=[])
        else:
            payload["inventory_mapping"] = [
                dict(
                    inventory_section_id="inventory-unmapped-test",
                    inventory_heading="Sekcja bez mapowania testowego",
                    status="unmapped", mapped_section_id=None,
                    mapped_section_heading=None, disposition=None,
                    reason="", evidence_ids=[],
                )
            ]
        connection.execute(
            "UPDATE content_planning_proposals SET payload_json = ? WHERE work_item_id = ?",
            (json.dumps(payload), packet.work_item_id),
        )

    response = read_content_planning_proposal(snapshot=_snapshot(), store=proposal_store)

    expected = {
        "missing_cta": ("blocked", "quality_gate_failed"),
        "missing_regulatory_lineage": ("blocked", "lineage_mismatch"),
        "unresolved_inventory_mapping": ("stale", "stale_input"),
    }
    assert (response.status, response.blockers[0].code) == expected[fault]
    if fault == "missing_cta":
        assert "missing_cta" in (response.blockers[0].source_codes or [])
    if fault == "unresolved_inventory_mapping":
        assert response.proposal is not None
        packet_id = response.research_packet_id
        assert packet_id is not None and packet_id.endswith(packet.preview_hash[:24])
        assert response.research_packet_digest == packet.preview_hash


@pytest.mark.parametrize("load_state", ["missing", "unavailable"])
def test_v3_packet_unavailable_frozen_input_is_a_typed_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    load_state: str,
) -> None:
    proposal_store, _packet_fixture, _source_pack, _fact, _digest = (
        _approved_packet_with_read(tmp_path, monkeypatch)
    )

    def unavailable_frozen_input(*_args: object) -> None:
        if load_state == "unavailable":
            raise OSError("synthetic frozen input store unavailable")

    monkeypatch.setattr(proposal_store, "frozen_planning_input", unavailable_frozen_input)

    response = read_content_planning_proposal(snapshot=_snapshot(), store=proposal_store)

    assert (response.status, response.blockers[0].code) == ("blocked", "research_packet_blocked")
    assert response.proposal is None
    assert (response.blockers[0].source_codes or []) == [
        "research_packet_v3_frozen_input_unavailable"
    ]


def test_v3_packet_registry_drift_blocks_without_guessing_currentness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, _packet_fixture, _source_pack, fact, _digest = _approved_packet_with_read(
        tmp_path, monkeypatch
    )
    changed_fact = fact.model_copy(update={"extracted_fact": "Inny fakt po review."})
    _patch_registry_fact(monkeypatch, changed_fact)

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "blocked", response.status
    assert response.blockers[0].code == "research_packet_blocked"
    assert response.blockers[0].source_codes[0] == "research_packet_v3_registry_drift"
    assert response.proposal is None


def test_v3_packet_input_drift_blocks_instead_of_showing_a_stale_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet_fixture, _source_pack, _fact, _digest = (
        _approved_packet_with_read(tmp_path, monkeypatch)
    )
    drifted = _raw_input(packet_fixture).model_copy(
        update={"planning_input_digest": "9" * 64}
    )
    _patch_read_input(monkeypatch, drifted)

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "blocked", response.status
    assert response.blockers[0].code == "research_packet_blocked"
    assert response.blockers[0].source_codes[0] == "research_packet_v3_input_drift"


def test_forged_plan_digest_cannot_be_reported_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet, _source_pack, _fact, _digest = _approved_packet_with_read(
        tmp_path, monkeypatch
    )
    connection = sqlite3.connect(proposal_store.path)
    try:
        row = connection.execute(
            "SELECT payload_json FROM content_planning_proposals WHERE work_item_id = ?",
            (packet.work_item_id,),
        ).fetchone()
        payload = json.loads(row[0])
        payload["planning_input_digest"] = "f" * 64
        connection.execute(
            "UPDATE content_planning_proposals SET planning_input_digest = ?, payload_json = ? "
            "WHERE work_item_id = ?",
            ("f" * 64, json.dumps(payload), packet.work_item_id),
        )
        connection.commit()
    finally:
        connection.close()

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "blocked", response.status
    assert response.blockers[0].source_codes[0] == (
        "research_packet_v3_generation_linkage_missing"
    )


def test_v3_packet_without_generation_job_stays_a_typed_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet, _source_pack, _fact, _digest = _approved_packet_with_read(
        tmp_path, monkeypatch
    )
    connection = sqlite3.connect(proposal_store.path)
    try:
        connection.execute("DELETE FROM content_planning_generation_jobs")
        connection.commit()
    finally:
        connection.close()

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "blocked", response.status
    assert response.blockers[0].code == "research_packet_conflict"
    assert response.blockers[0].source_codes[0] == (
        "research_packet_v3_generation_linkage_missing"
    )


def test_registry_loader_failure_is_a_typed_blocker_not_an_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, _packet_fixture, _source_pack, _fact, _digest = _approved_packet_with_read(
        tmp_path, monkeypatch
    )

    def _broken_registry():
        raise RuntimeError("registry read failed")

    from wilq.content.knowledge import source_facts as source_facts_module

    monkeypatch.setattr(source_facts_module, "ekologus_source_facts", _broken_registry)

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "blocked", response.status
    assert response.blockers[0].code == "research_packet_blocked"
    assert response.blockers[0].source_codes[0] == (
        "research_packet_v3_registry_unavailable"
    )


def test_v3_packet_without_exact_receipt_stays_a_typed_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_store, packet, _source_pack, _fact, _digest = _approved_packet_with_read(
        tmp_path, monkeypatch
    )
    assert packet.preview_hash is not None
    missing_packet_id = f"content_research_packet_v3_missing_{packet.preview_hash[:16]}"
    connection = sqlite3.connect(proposal_store.path)
    try:
        row = connection.execute(
            "SELECT payload_json FROM content_planning_proposals WHERE work_item_id = ?",
            (packet.work_item_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        payload["research_packet_id"] = missing_packet_id
        connection.execute(
            "UPDATE content_planning_proposals SET payload_json = ? WHERE work_item_id = ?",
            (json.dumps(payload), packet.work_item_id),
        )
        connection.commit()
    finally:
        connection.close()

    response = read_content_planning_proposal(
        snapshot=_snapshot(),
        store=proposal_store,
    )

    assert response.status == "blocked", response.status
    assert response.blockers[0].code == "research_packet_conflict"
    assert response.blockers[0].source_codes[0] == "research_packet_v3_approval_missing"


def _job_row(
    store: ContentPlanningProposalStore,
    packet: ResearchPacketV3Preview,
    planning_input_digest: str,
) -> sqlite3.Row:
    connection = sqlite3.connect(store.path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM content_planning_generation_jobs "
            "WHERE work_item_id = ? AND content_kind = 'editorial' "
            "AND subject_key = 'editorial' AND planning_input_digest = ?",
            (packet.work_item_id, planning_input_digest),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return row


def _replace_job_payload(
    store: ContentPlanningProposalStore,
    packet: ResearchPacketV3Preview,
    planning_input_digest: str,
    payload: object,
    *,
    status: str | None = None,
) -> None:
    row = _job_row(store, packet, planning_input_digest)
    connection = sqlite3.connect(store.path)
    try:
        connection.execute(
            "UPDATE content_planning_generation_jobs SET payload_json = ?, "
            "status = COALESCE(?, status) WHERE work_item_id = ? "
            "AND content_kind = 'editorial' AND subject_key = 'editorial' "
            "AND planning_input_digest = ?",
            (json.dumps(payload), status, row["work_item_id"], planning_input_digest),
        )
        connection.commit()
    finally:
        connection.close()


def _retry_job_payload(
    packet: ResearchPacketV3Preview,
    planning_input_digest: str,
    *,
    failed: bool,
    input_summary: ContentPlanningInputSummary,
) -> dict[str, object]:
    assert packet.preview_hash is not None
    response = ContentPlanningProposalResponse(
        status="failed" if failed else "generating",
        work_item_id=packet.work_item_id,
        content_kind="editorial",
        service_card_id=None,
        planning_input_digest=planning_input_digest,
        research_packet_id=f"content_research_packet_v3_{packet.preview_hash[:24]}",
        research_packet_digest=packet.preview_hash,
        input_summary=input_summary,
        runtime=ContentCodexRuntimeTrace(
            status="failed" if failed else "not_started",
            run_id="planning_generation_retry",
        ),
        blockers=(
            [
                ContentPlanningProposalBlocker(
                    code="runtime_failed",
                    label="Generowanie planu nie powiodło się",
                    reason="Syntetyczna próba retry nie została ukończona.",
                    next_step="Ponów próbę.",
                )
            ]
            if failed
            else []
        ),
        safe_next_step="Ponów odczyt.",
    )
    return response.model_dump(mode="json")


@pytest.mark.parametrize("failed", [False, True], ids=["queued-retry", "failed-retry"])
def test_completed_exact_plan_remains_readable_while_exact_retry_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed: bool,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    terminal = ContentPlanningProposalResponse.model_validate_json(
        _job_row(store, packet, digest)["payload_json"]
    )
    _replace_job_payload(
        store,
        packet,
        digest,
        _retry_job_payload(
            packet,
            digest,
            failed=failed,
            input_summary=terminal.input_summary,
        ),
        status="failed" if failed else "queued",
    )

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "ready", response.blockers
    assert response.proposal is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("work_item_id", "wi_foreign"),
        ("content_kind", "service"),
        ("service_card_id", "service_foreign"),
    ],
)
def test_foreign_job_identity_cannot_link_current_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    payload = json.loads(_job_row(store, packet, digest)["payload_json"])
    payload[field] = value
    _replace_job_payload(store, packet, digest, payload)

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


@pytest.mark.parametrize(
    ("proposal_field", "value"),
    [("proposal_id", "proposal-foreign"), ("codex_run_id", "run-foreign")],
)
def test_foreign_terminal_proposal_or_run_cannot_link_current_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    proposal_field: str,
    value: str,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    payload = json.loads(_job_row(store, packet, digest)["payload_json"])
    payload["proposal"][proposal_field] = value
    _replace_job_payload(store, packet, digest, payload)

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


def test_terminal_job_status_must_match_its_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    payload = json.loads(_job_row(store, packet, digest)["payload_json"])
    _replace_job_payload(store, packet, digest, payload, status="failed")

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


def test_malformed_job_json_shape_is_a_typed_blocker_not_a_server_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    _replace_job_payload(store, packet, digest, ["not", "a", "response"])

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


def test_job_payload_digest_must_match_its_persisted_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    payload = json.loads(_job_row(store, packet, digest)["payload_json"])
    payload["planning_input_digest"] = "e" * 64
    _replace_job_payload(store, packet, digest, payload)

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


@pytest.mark.parametrize("run_status", ["failed", "started"])
def test_job_without_exact_persisted_completed_run_cannot_report_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_status: str,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    connection = sqlite3.connect(store.path)
    try:
        row = connection.execute(
            "SELECT payload_json FROM codex_runs WHERE id = 'run-v3-status-read'"
        ).fetchone()
        assert row is not None
        run = json.loads(row[0])
        run["status"] = run_status
        connection.execute(
            "UPDATE codex_runs SET payload_json = ? WHERE id = 'run-v3-status-read'",
            (json.dumps(run),),
        )
        connection.commit()
    finally:
        connection.close()

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


@pytest.mark.parametrize("failed", [False, True], ids=["queued", "failed"])
def test_queued_or_failed_job_without_completed_run_cannot_report_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed: bool,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    terminal = ContentPlanningProposalResponse.model_validate_json(
        _job_row(store, packet, digest)["payload_json"]
    )
    _replace_job_payload(
        store,
        packet,
        digest,
        _retry_job_payload(
            packet,
            digest,
            failed=failed,
            input_summary=terminal.input_summary,
        ),
        status="failed" if failed else "queued",
    )
    connection = sqlite3.connect(store.path)
    try:
        connection.execute("DELETE FROM codex_runs WHERE id = 'run-v3-status-read'")
        connection.commit()
    finally:
        connection.close()

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


def test_exact_packet_read_does_not_drop_link_after_unrelated_jobs_exceed_25(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    exact_job = ContentPlanningProposalResponse.model_validate_json(
        _job_row(store, packet, digest)["payload_json"]
    )
    connection = sqlite3.connect(store.path)
    try:
        for index in range(30):
            service_card_id = f"service_unrelated_{index}"
            unrelated_digest = f"{index + 1:064x}"
            response = ContentPlanningProposalResponse(
                status="failed",
                work_item_id=packet.work_item_id,
                content_kind="service",
                service_card_id=service_card_id,
                planning_input_digest=unrelated_digest,
                input_summary=exact_job.input_summary,
                blockers=[
                    ContentPlanningProposalBlocker(
                        code="runtime_failed",
                        label="Retry syntetyczny",
                        reason="Nie ma połączenia z pakietem badanego planu.",
                        next_step="Pomiń.",
                    )
                ],
                safe_next_step="Pomiń.",
            )
            connection.execute(
                "INSERT INTO content_planning_generation_jobs "
                "(work_item_id, service_card_id, content_kind, subject_key, "
                "planning_input_digest, status, payload_json, updated_at) "
                "VALUES (?, ?, 'service', ?, ?, 'failed', ?, ?)",
                (
                    packet.work_item_id,
                    service_card_id,
                    service_card_id,
                    unrelated_digest,
                    response.model_dump_json(),
                    f"2099-01-{(index % 28) + 1:02d}T00:00:00+00:00",
                ),
            )
        connection.commit()
    finally:
        connection.close()

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "ready", response.blockers
    assert response.proposal is not None


def test_plan_subject_must_match_current_editorial_or_service_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, packet, _pack, _fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    service_input = _raw_input(packet).model_copy(
        update={
            "content_kind": "service",
            "confirmed_service_card_id": "service_current",
            "service_label": "Usługa środowiskowa",
            "planning_input_digest": digest,
        }
    )
    _patch_read_input(monkeypatch, service_input)
    service_snapshot = SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(id=packet.work_item_id, content_kind="service")
        ),
        service_profile_context=SimpleNamespace(service_card_id="service_current"),
    )
    from wilq.content.planning import generated_proposal as generated_proposal_module

    monkeypatch.setattr(
        generated_proposal_module,
        "with_explicit_content_service_selection",
        lambda snapshot, _service_card_id: snapshot,
    )

    response = read_content_planning_proposal(snapshot=service_snapshot, store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


def test_workflow_receipt_store_unavailable_is_typed_not_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _packet, _pack, _fact, _digest = _approved_packet_with_read(tmp_path, monkeypatch)
    from wilq.content.planning import proposal_v3_packet_read as v3_packet_read_module

    def unavailable_store():
        raise OSError("synthetic store unavailable")

    monkeypatch.setattr(v3_packet_read_module, "content_workflow_store", unavailable_store)

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None


def test_generation_linkage_store_unavailable_is_typed_not_500(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _packet, _pack, _fact, _digest = _approved_packet_with_read(tmp_path, monkeypatch)

    def unavailable_linkage(*_args: object, **_kwargs: object) -> str | None:
        raise OSError("synthetic linkage unavailable")

    monkeypatch.setattr(
        store,
        "v3_plan_generation_linkage_exact",
        unavailable_linkage,
    )

    response = read_content_planning_proposal(snapshot=_snapshot(), store=store)

    assert response.status == "blocked", response.status
    assert response.proposal is None
