from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.content.test_current_preparation_readiness import (
    WORK_ITEM_ID,
    _seed_exact_current_receipts,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.content_kind_receipt import (
    ContentKindReceipt,
    build_editorial_content_kind_receipt,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
)
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    ContentSourcePackBindingCommand,
)
from wilq.content.workflow.store.refresh_preparation_atomic import (
    RefreshPreparationAtomicityError,
    assert_refresh_preparation_proposal_current,
    assert_refresh_preparation_revision_current,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


def _editorial_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[
    ContentWorkflowStore,
    ContentProductionClassificationRun,
    ContentProductionClassificationRow,
    ContentKindReceipt,
    ContentRefreshPreparationAuthorization,
]:
    store, run = _seed_exact_current_receipts(monkeypatch, tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    planning_input_digest = "f" * 64
    inventory = ContentKindInventoryBinding(
        work_item_id=WORK_ITEM_ID,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        wordpress_content_type="post",
        content_kind="editorial",
        inventory_evidence_ids=("ev_wp_current_readiness",),
        trusted=True,
    )
    receipt = build_editorial_content_kind_receipt(
        work_item_id=WORK_ITEM_ID,
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        planning_input_digest=planning_input_digest,
        inventory_binding=inventory,
    )
    assert store.record_content_kind_receipt(receipt).status == "created"
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        classification_blocker_codes=[item.code for item in row.blockers],
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=classification,
        planning_input_digest=planning_input_digest,
        service_card_id=None,
        content_kind="editorial",
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=datetime.now(UTC),
    )
    return store, run, row, receipt, authorization


def _proposal(authorization: ContentRefreshPreparationAuthorization) -> ContentPlanningProposal:
    binding = authorization.binding
    return ContentPlanningProposal(
        work_item_id=WORK_ITEM_ID,
        planning_digest="a" * 64,
        proposal_id="content_planning_proposal_editorial_atomic",
        codex_run_id="codex_editorial_planning_atomic",
        generation_status="codex_generated",
        planning_input_digest=binding.planning_input_digest,
        content_kind="editorial",
        final_canonical_url=binding.public_url,
        target_reader="Przedsiębiorca",
        buyer_problem="Brak jasnego zakresu obowiązków.",
        buyer_trigger="Zmiana zakresu działalności.",
        search_intent="Informacyjny.",
        cta_direction="Skonsultuj sytuację.",
        sections=[ContentPlanningSection(heading="Zakres", purpose="Porządkuje zakres.")],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak dokładnych danych popytu.",
        ),
        refresh_preparation_binding=binding,
        created_at=datetime.now(UTC),
    )


def _revision(
    authorization: ContentRefreshPreparationAuthorization,
) -> ContentDraftRevisionAppendCommand:
    binding = authorization.binding
    metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_editorial_atomic",
        selected_section_headings=["Zakres"],
        section_lineage=[
            ContentDraftRevisionProposalSectionLineage(
                heading="Zakres",
                evidence_ids=["ev_wp_current_readiness"],
            )
        ],
        quality_verdict="needs_changes",
        quality_finding_codes=["semantic_review_required"],
        refresh_preparation_binding=binding,
    )
    return ContentDraftRevisionAppendCommand(
        work_item_id=WORK_ITEM_ID,
        draft_package_id="draft_package_editorial_atomic",
        draft_package_digest="b" * 64,
        planning_digest="a" * 64,
        planning_input_digest=binding.planning_input_digest,
        content_kind="editorial",
        inventory_digest="c" * 64,
        final_canonical_url=binding.public_url,
        title="Informacje dla przedsiębiorcy",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Opis zakresu do review.",
                evidence_ids=["ev_wp_current_readiness"],
            )
        ],
        proposal_metadata=metadata,
        refresh_preparation_binding=binding,
        created_by="wilku",
    )


def _classification_payload(store: ContentWorkflowStore) -> str:
    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT payload_json FROM content_production_classifications "
            "ORDER BY recorded_at DESC, rowid DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    return str(row[0])


def _append_newer_blocked_pack(store: ContentWorkflowStore) -> ContentSourcePackBinding:
    current = store.list_content_source_pack_bindings(current_work_item_id=WORK_ITEM_ID)[-1]
    command = ContentSourcePackBindingCommand(
        source_pack_id=current.source_pack_id,
        source_pack_sha256=current.source_pack_sha256,
        identity_binding_id=current.identity_binding_id,
        identity_binding_digest=current.identity_binding_digest,
        current_work_item_id=current.current_work_item_id,
        source_fact_ids=current.source_fact_ids,
        evidence_ids=current.evidence_ids,
        fresh_context_digest=current.fresh_context_digest,
        source_fact_registry_receipt=current.source_fact_registry_receipt.model_copy(
            update={"registry_digest": "e" * 64}
        ),
        fresh_context_attestation=current.fresh_context_attestation,
        source_fact_authority_receipt_id=current.source_fact_authority_receipt_id,
        source_fact_authority_receipt_digest=current.source_fact_authority_receipt_digest,
        source_fact_authority_snapshot_digest=current.source_fact_authority_snapshot_digest,
        recorded_by="readiness_test",
        recorded_at=datetime.now(UTC),
    )
    result = store.record_content_source_pack_binding(command)
    assert result.binding.status == "blocked"
    assert result.binding.recorded_at >= current.recorded_at
    assert result.binding.binding_id != current.binding_id
    return result.binding


def _completed_planning_run(proposal: ContentPlanningProposal) -> CodexRun:
    started_at = utc_now()
    return CodexRun(
        id=proposal.codex_run_id or "codex_editorial_planning_atomic",
        skill="wilq-content-operator",
        hook="content_planning_proposal",
        source="wilq_api",
        status="completed",
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
        started_at=started_at,
        completed_at=started_at,
    )


def _revision_runs(command: ContentDraftRevisionAppendCommand) -> tuple[CodexRun, CodexRun]:
    started_at = utc_now()
    started = CodexRun(
        id=command.proposal_metadata.codex_run_id
        if command.proposal_metadata is not None
        else "codex_editorial_revision_atomic",
        skill="wilq-content-operator",
        hook="content_revision_proposal",
        source="wilq_api",
        status="started",
        planning_digest=command.planning_digest,
        planning_input_digest=command.planning_input_digest,
        started_at=started_at,
    )
    return started, started.model_copy(update={"status": "completed", "completed_at": utc_now()})


def _write_real_plan_and_revision(
    store: ContentWorkflowStore,
    authorization: ContentRefreshPreparationAuthorization,
) -> tuple[
    ContentPlanningProposalStore,
    ContentPlanningProposal,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevision,
]:
    proposal_store = ContentPlanningProposalStore(store.path)
    proposal = _proposal(authorization)
    plan_outcome, stored_proposal = proposal_store.save_generated(
        proposal,
        _completed_planning_run(proposal),
    )
    assert plan_outcome == "created"
    readback = proposal_store.latest(WORK_ITEM_ID)
    assert readback == stored_proposal

    revision_command = _revision(authorization)
    started, completed = _revision_runs(revision_command)
    LocalStateStore(store.path).save_codex_run(started)
    revision_result = store.append_draft_revision(
        revision_command,
        completed_codex_run=completed,
    )
    assert revision_result.status == "created"
    assert revision_result.revision is not None
    revision_readback = store.load_draft_revision_state(WORK_ITEM_ID).latest_revision
    assert revision_readback == revision_result.revision
    return proposal_store, stored_proposal, revision_command, revision_result.revision


def test_editorial_receipt_persistence_accepts_ready_blocked_classification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_exact_current_receipts(monkeypatch, tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    inventory = ContentKindInventoryBinding(
        work_item_id=WORK_ITEM_ID,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        wordpress_content_type="post",
        content_kind="editorial",
        inventory_evidence_ids=("ev_wp_current_readiness",),
        trusted=True,
    )
    receipt = build_editorial_content_kind_receipt(
        work_item_id=WORK_ITEM_ID,
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        planning_input_digest="f" * 64,
        inventory_binding=inventory,
    )

    result = store.record_content_kind_receipt(receipt)

    assert result.status == "created"
    assert result.receipt == receipt
    assert row.decision == "blocked"


def test_editorial_authorization_persistence_accepts_same_ready_blocked_row(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run = _seed_exact_current_receipts(monkeypatch, tmp_path)
    row = next(item for item in run.rows if item.current_work_item_id == WORK_ITEM_ID)
    planning_input_digest = "f" * 64
    inventory = ContentKindInventoryBinding(
        work_item_id=WORK_ITEM_ID,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        wordpress_content_type="post",
        content_kind="editorial",
        inventory_evidence_ids=("ev_wp_current_readiness",),
        trusted=True,
    )
    receipt = build_editorial_content_kind_receipt(
        work_item_id=WORK_ITEM_ID,
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        planning_input_digest=planning_input_digest,
        inventory_binding=inventory,
    )
    assert store.record_content_kind_receipt(receipt).status == "created"
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        classification_blocker_codes=[item.code for item in row.blockers],
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=classification,
        planning_input_digest=planning_input_digest,
        service_card_id=None,
        content_kind="editorial",
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=datetime.now(UTC),
    )

    result = store.record_refresh_preparation_authorization(authorization)

    assert result.status == "created"
    assert result.authorization == authorization


def test_plan_and_draft_guards_accept_ready_blocked_row_in_one_outer_transaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run, row, _receipt, authorization = _editorial_context(monkeypatch, tmp_path)
    assert store.record_refresh_preparation_authorization(authorization).status == "created"
    proposal = _proposal(authorization)
    revision = _revision(authorization)
    before_payload = _classification_payload(store)

    with sqlite3.connect(store.path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        assert_refresh_preparation_proposal_current(connection, proposal)
        assert_refresh_preparation_revision_current(connection, revision)
        assert connection.in_transaction
        connection.rollback()

    after = store.load_latest_production_classification()
    assert after is not None
    after_row = after.for_work_item(WORK_ITEM_ID)
    assert after_row is not None
    assert row.decision == "blocked"
    assert after_row.model_dump(mode="json") == row.model_dump(mode="json")
    assert after.run_digest == run.run_digest
    assert _classification_payload(store) == before_payload


def test_newer_blocked_pack_before_authorization_rejects_without_authorization_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run, row, _receipt, authorization = _editorial_context(monkeypatch, tmp_path)
    before_payload = _classification_payload(store)
    blocked_pack = _append_newer_blocked_pack(store)

    with pytest.raises(ValueError, match="current classified row"):
        store.record_refresh_preparation_authorization(authorization)

    with sqlite3.connect(store.path) as connection:
        authorization_count = connection.execute(
            "SELECT COUNT(*) FROM content_refresh_preparation_authorizations"
        ).fetchone()[0]
    assert authorization_count == 0
    assert blocked_pack.status == "blocked"
    assert row.decision == "blocked"
    assert _classification_payload(store) == before_payload
    current = store.load_latest_production_classification()
    assert current is not None
    assert current.run_digest == run.run_digest


def test_newer_blocked_pack_after_authorization_rejects_plan_and_draft_guards(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, run, row, _receipt, authorization = _editorial_context(monkeypatch, tmp_path)
    assert store.record_refresh_preparation_authorization(authorization).status == "created"
    _append_newer_blocked_pack(store)
    proposal = _proposal(authorization)
    revision = _revision(authorization)
    before_payload = _classification_payload(store)

    with sqlite3.connect(store.path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(
            RefreshPreparationAtomicityError,
            match="refresh_preparation_proposal_binding_mismatch",
        ):
            assert_refresh_preparation_proposal_current(connection, proposal)
        with pytest.raises(
            RefreshPreparationAtomicityError,
            match="refresh_preparation_proposal_binding_mismatch",
        ):
            assert_refresh_preparation_revision_current(connection, revision)
        assert connection.in_transaction
        connection.rollback()

    with sqlite3.connect(store.path) as connection:
        authorization_count = connection.execute(
            "SELECT COUNT(*) FROM content_refresh_preparation_authorizations"
        ).fetchone()[0]
        revision_count = connection.execute(
            "SELECT COUNT(*) FROM content_draft_revisions"
        ).fetchone()[0]
    assert authorization_count == 1
    assert revision_count == 0
    assert row.decision == "blocked"
    current = store.load_latest_production_classification()
    assert current is not None
    assert current.run_digest == run.run_digest
    assert _classification_payload(store) == before_payload


def test_real_plan_and_revision_writers_accept_ready_blocked_row_with_readback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, _run, _row, _receipt, authorization = _editorial_context(monkeypatch, tmp_path)
    assert store.record_refresh_preparation_authorization(authorization).status == "created"

    proposal_store, proposal, _revision_command, revision = _write_real_plan_and_revision(
        store, authorization
    )

    assert proposal_store.latest(WORK_ITEM_ID) == proposal
    assert store.load_draft_revision_state(WORK_ITEM_ID).latest_revision == revision


def test_real_writers_reject_distinct_attempts_after_newer_blocked_pack(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, _run, _row, _receipt, authorization = _editorial_context(monkeypatch, tmp_path)
    assert store.record_refresh_preparation_authorization(authorization).status == "created"
    proposal_store, proposal, revision_command, revision = _write_real_plan_and_revision(
        store, authorization
    )
    before_proposal_count = _count_rows(store.path, "content_planning_proposals")
    before_repair_count = _count_rows(store.path, "content_planning_proposal_repairs")
    before_revision_count = _count_rows(store.path, "content_draft_revisions")
    _append_newer_blocked_pack(store)

    next_proposal = proposal.model_copy(
        update={
            "proposal_id": "content_planning_proposal_editorial_atomic_next",
            "codex_run_id": "codex_editorial_planning_atomic_next",
            "planning_digest": "d" * 64,
            "created_at": datetime.now(UTC),
        }
    )
    with pytest.raises(
        RefreshPreparationAtomicityError,
        match="refresh_preparation_proposal_binding_mismatch",
    ):
        proposal_store.save_generated(
            next_proposal,
            _completed_planning_run(next_proposal),
            replace_existing_exact_input=True,
        )

    next_metadata = revision.proposal_metadata
    assert next_metadata is not None
    next_metadata = next_metadata.model_copy(
        update={"codex_run_id": "codex_editorial_revision_atomic_next"}
    )
    next_revision = revision_command.model_copy(
        update={
            "draft_package_id": "draft_package_editorial_atomic_next",
            "draft_package_digest": "e" * 64,
            "planning_digest": "d" * 64,
            "proposal_metadata": next_metadata,
        }
    )
    _started, next_completed = _revision_runs(next_revision)
    with pytest.raises(
        RefreshPreparationAtomicityError,
        match="refresh_preparation_proposal_binding_mismatch",
    ):
        store.append_draft_revision(next_revision, completed_codex_run=next_completed)

    assert _count_rows(store.path, "content_planning_proposals") == before_proposal_count
    assert _count_rows(store.path, "content_planning_proposal_repairs") == before_repair_count
    assert _count_rows(store.path, "content_draft_revisions") == before_revision_count
    assert proposal_store.latest(WORK_ITEM_ID) == proposal
    assert store.load_draft_revision_state(WORK_ITEM_ID).latest_revision == revision


def _count_rows(path: Path, table: str) -> int:
    with sqlite3.connect(path) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
    assert row is not None
    return int(row[0])
