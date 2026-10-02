"""Append-only full-text receipts and one-shot dispatch, checked at append."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from wilq.content.drafts.full_draft_generation_v3_contracts import (
    FullDraftGenerationV3Binding,
    FullDraftGenerationV3Receipt,
    FullDraftGenerationV3Snapshot,
    FullDraftGenerationV3WorkerStart,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.store.refresh_preparation_atomic import RefreshPreparationAtomicityError
from wilq.schemas import ActionMutationAuditRecord, AuditEvent, CodexRun
from wilq.schemas.core import utc_now

if TYPE_CHECKING:
    from wilq.content.workflow.documents.revisions import ContentDraftRevisionAppendCommand

_TableKind = Literal["snapshots", "receipts", "dispatches", "worker_starts"]

_SCHEMA_STATEMENTS = (
    "CREATE TABLE IF NOT EXISTS content_full_draft_generation_v3_snapshots "
    "(action_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_snapshots_no_update "
    "BEFORE UPDATE ON content_full_draft_generation_v3_snapshots "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_snapshots_no_delete "
    "BEFORE DELETE ON content_full_draft_generation_v3_snapshots "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_snapshots_no_replace "
    "BEFORE INSERT ON content_full_draft_generation_v3_snapshots "
    "WHEN EXISTS (SELECT 1 FROM content_full_draft_generation_v3_snapshots "
    "WHERE action_id = NEW.action_id) "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TABLE IF NOT EXISTS content_full_draft_generation_v3_receipts "
    "(action_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_receipts_no_update "
    "BEFORE UPDATE ON content_full_draft_generation_v3_receipts "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_receipts_no_delete "
    "BEFORE DELETE ON content_full_draft_generation_v3_receipts "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_receipts_no_replace "
    "BEFORE INSERT ON content_full_draft_generation_v3_receipts "
    "WHEN EXISTS (SELECT 1 FROM content_full_draft_generation_v3_receipts "
    "WHERE action_id = NEW.action_id) "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TABLE IF NOT EXISTS content_full_draft_generation_v3_dispatches "
    "(action_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_dispatches_no_update "
    "BEFORE UPDATE ON content_full_draft_generation_v3_dispatches "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_dispatches_no_delete "
    "BEFORE DELETE ON content_full_draft_generation_v3_dispatches "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_dispatches_no_replace "
    "BEFORE INSERT ON content_full_draft_generation_v3_dispatches "
    "WHEN EXISTS (SELECT 1 FROM content_full_draft_generation_v3_dispatches "
    "WHERE action_id = NEW.action_id) "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TABLE IF NOT EXISTS content_full_draft_generation_v3_worker_starts "
    "(action_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_worker_starts_no_update "
    "BEFORE UPDATE ON content_full_draft_generation_v3_worker_starts "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_worker_starts_no_delete "
    "BEFORE DELETE ON content_full_draft_generation_v3_worker_starts "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS content_full_draft_generation_v3_worker_starts_no_replace "
    "BEFORE INSERT ON content_full_draft_generation_v3_worker_starts "
    "WHEN EXISTS (SELECT 1 FROM content_full_draft_generation_v3_worker_starts "
    "WHERE action_id = NEW.action_id) "
    "BEGIN SELECT RAISE(ABORT, 'full draft v3 authority is append-only'); END",
)

_LOAD_STATEMENTS: dict[_TableKind, str] = {
    "snapshots": (
        "SELECT payload_json FROM content_full_draft_generation_v3_snapshots WHERE action_id = ?"
    ),
    "receipts": (
        "SELECT payload_json FROM content_full_draft_generation_v3_receipts WHERE action_id = ?"
    ),
    "dispatches": (
        "SELECT payload_json FROM content_full_draft_generation_v3_dispatches WHERE action_id = ?"
    ),
    "worker_starts": (
        "SELECT payload_json FROM content_full_draft_generation_v3_worker_starts "
        "WHERE action_id = ?"
    ),
}

_RECORD_STATEMENTS: dict[_TableKind, str] = {
    "snapshots": (
        "INSERT INTO content_full_draft_generation_v3_snapshots "
        "(action_id, payload_json) VALUES (?, ?)"
    ),
    "receipts": (
        "INSERT INTO content_full_draft_generation_v3_receipts "
        "(action_id, payload_json) VALUES (?, ?)"
    ),
    "dispatches": (
        "INSERT INTO content_full_draft_generation_v3_dispatches "
        "(action_id, payload_json) VALUES (?, ?)"
    ),
    "worker_starts": (
        "INSERT INTO content_full_draft_generation_v3_worker_starts "
        "(action_id, payload_json) VALUES (?, ?)"
    ),
}


def ensure_full_draft_generation_v3_schema(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA_STATEMENTS:
        connection.execute(statement)


def _load[T: BaseModel](
    connection: sqlite3.Connection, kind: _TableKind, action_id: str, model: type[T]
) -> T | None:
    row = connection.execute(_LOAD_STATEMENTS[kind], (action_id,)).fetchone()
    if row is None:
        return None
    parsed = model.model_validate_json(row["payload_json"])
    if isinstance(parsed, FullDraftGenerationV3Receipt):
        actual = parsed.snapshot.action_id
    elif isinstance(
        parsed,
        (
            FullDraftGenerationV3Snapshot,
            FullDraftGenerationV3Binding,
            FullDraftGenerationV3WorkerStart,
        ),
    ):
        actual = parsed.action_id
    else:
        raise ValueError("full_draft_v3_stored_contract_mismatch")
    if actual != action_id:
        raise ValueError("full_draft_v3_stored_identity_mismatch")
    return parsed


def _record(
    connection: sqlite3.Connection, kind: _TableKind, action_id: str, value: BaseModel
) -> str:
    old = _load(connection, kind, action_id, type(value))
    if old is not None:
        return "idempotent" if old == value else "conflict"
    connection.execute(_RECORD_STATEMENTS[kind], (action_id, value.model_dump_json()))
    return "created"


class FullDraftGenerationV3StoreMixin:
    path: Path

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_full_draft_generation_v3_snapshot(
        self, snapshot: FullDraftGenerationV3Snapshot
    ) -> str:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return _record(connection, "snapshots", snapshot.action_id, snapshot)

    def load_full_draft_generation_v3_snapshot(
        self, action_id: str
    ) -> FullDraftGenerationV3Snapshot | None:
        with self._connect() as connection:
            return _load(connection, "snapshots", action_id, FullDraftGenerationV3Snapshot)

    def record_full_draft_generation_v3_receipt(self, receipt: FullDraftGenerationV3Receipt) -> str:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            snapshot = _load(
                connection, "snapshots", receipt.snapshot.action_id, FullDraftGenerationV3Snapshot
            )
            if snapshot != receipt.snapshot:
                raise ValueError("full_draft_v3_action_changed")
            return _record(connection, "receipts", receipt.snapshot.action_id, receipt)

    def load_full_draft_generation_v3_receipt(
        self, action_id: str
    ) -> FullDraftGenerationV3Receipt | None:
        with self._connect() as connection:
            return _load(connection, "receipts", action_id, FullDraftGenerationV3Receipt)

    def load_full_draft_generation_v3_dispatch(
        self, action_id: str
    ) -> FullDraftGenerationV3Binding | None:
        with self._connect() as connection:
            return _load(connection, "dispatches", action_id, FullDraftGenerationV3Binding)

    def latest_full_draft_generation_v3_receipt(
        self, work_item_id: str
    ) -> FullDraftGenerationV3Receipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT action_id FROM content_full_draft_generation_v3_receipts "
                "WHERE json_extract(payload_json, '$.snapshot.work_item_id') = ? "
                "ORDER BY rowid DESC LIMIT 1",
                (work_item_id,),
            ).fetchone()
            return (
                None
                if row is None
                else _load(connection, "receipts", row["action_id"], FullDraftGenerationV3Receipt)
            )

    def load_full_draft_generation_v3_worker_start(
        self, action_id: str
    ) -> FullDraftGenerationV3WorkerStart | None:
        with self._connect() as connection:
            return _load(connection, "worker_starts", action_id, FullDraftGenerationV3WorkerStart)

    def start_full_draft_generation_v3_worker(
        self,
        receipt: FullDraftGenerationV3Receipt,
        binding: FullDraftGenerationV3Binding,
        current_guard: Callable[[], None],
    ) -> bool:
        from wilq.content.drafts.initial_draft_run import effective_initial_draft_deadline

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            claimed = _load(
                connection, "dispatches", binding.action_id, FullDraftGenerationV3Binding
            )
            if claimed != binding:
                raise ValueError("full_draft_v3_dispatch_mismatch")
            old = _load(
                connection, "worker_starts", binding.action_id, FullDraftGenerationV3WorkerStart
            )
            if old is not None:
                if old.binding != binding:
                    raise ValueError("full_draft_v3_worker_mismatch")
                return False
            assert_full_draft_v3_authority(connection, receipt, self.path)
            current_guard()
            run = _load_run(connection, binding.run_id)
            if run is None or run.status != "started":
                raise ValueError("full_draft_v3_run_terminal")
            if utc_now() >= effective_initial_draft_deadline(run):
                raise ValueError("full_draft_v3_run_expired")
            _record(
                connection,
                "worker_starts",
                binding.action_id,
                FullDraftGenerationV3WorkerStart(binding=binding, started_at=utc_now()),
            )
            return True

    def claim_full_draft_generation_v3(
        self,
        receipt: FullDraftGenerationV3Receipt,
        run_factory: Callable[[], CodexRun],
        current_guard: Callable[[], None],
    ) -> tuple[FullDraftGenerationV3Binding, bool]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            old = _load(
                connection, "dispatches", receipt.snapshot.action_id, FullDraftGenerationV3Binding
            )
            assert_full_draft_v3_authority(connection, receipt, self.path)
            current_guard()
            if old is not None:
                return old, False
            if (
                connection.execute(
                    "SELECT 1 FROM content_draft_revisions WHERE work_item_id = ? LIMIT 1",
                    (receipt.snapshot.work_item_id,),
                ).fetchone()
                is not None
            ):
                raise ValueError("full_draft_v3_base_revision_changed")
            run = run_factory()
            run = run.model_copy(update={"action_ids": [receipt.snapshot.action_id]})
            binding = FullDraftGenerationV3Binding.from_receipt(receipt).model_copy(
                update={"run_id": run.id}
            )
            _record(connection, "dispatches", binding.action_id, binding)
            connection.execute(
                "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
                (run.id, run.started_at.isoformat(), run.model_dump_json()),
            )
            return binding, True


def assert_full_draft_v3_authority(
    connection: sqlite3.Connection, receipt: FullDraftGenerationV3Receipt, path: Path
) -> None:
    from wilq.content.drafts.full_draft_generation_v3 import (
        FULL_DRAFT_GENERATION_V3_ADAPTER,
        full_draft_generation_v3_chain,
        full_draft_generation_v3_snapshot,
    )
    from wilq.content.workflow.store.store import ContentWorkflowStore

    snapshot = receipt.snapshot
    stored = _load(connection, "receipts", snapshot.action_id, FullDraftGenerationV3Receipt)
    recorded = _load(connection, "snapshots", snapshot.action_id, FullDraftGenerationV3Snapshot)
    if stored != receipt or recorded != snapshot:
        raise ValueError("full_draft_v3_receipt_mismatch")
    rows = connection.execute(
        "SELECT payload_json FROM content_planning_proposals WHERE work_item_id = ? "
        "AND content_kind = ? AND subject_key = ? ORDER BY proposal_version DESC LIMIT 1",
        (snapshot.work_item_id, snapshot.content_kind, snapshot.subject_key),
    ).fetchall()
    proposal = (
        None if not rows else ContentPlanningProposal.model_validate_json(rows[0]["payload_json"])
    )
    if (
        proposal is None
        or full_draft_generation_v3_snapshot(proposal, store=ContentWorkflowStore(path)) != snapshot
    ):
        raise ValueError("full_draft_v3_plan_changed")
    events = [
        AuditEvent.model_validate_json(row["payload_json"])
        for row in connection.execute(
            "SELECT payload_json FROM audit_events WHERE action_id = ?", (snapshot.action_id,)
        )
    ]
    chain = full_draft_generation_v3_chain(snapshot, events, receipt.confirmed_by)
    if tuple(event.id for event in chain) != (
        receipt.preview_audit_id,
        receipt.review_audit_id,
        receipt.confirmation_audit_id,
        receipt.impact_audit_id,
    ):
        raise ValueError("full_draft_v3_audit_changed")
    if (receipt.reviewed_by, receipt.created_at, receipt.confirmed_by) != (
        chain[1].actor,
        chain[1].created_at,
        chain[2].actor,
    ):
        raise ValueError("full_draft_v3_audit_provenance_mismatch")
    applies = sorted(
        (event for event in events if event.event_type.startswith("apply_")),
        key=lambda event: (event.created_at, event.id),
        reverse=True,
    )
    applied = None if not applies else applies[0]
    if (
        applied is None
        or applied.event_type != "apply_succeeded"
        or (applied.details.get("context_digest"), applied.details.get("payload_digest"))
        != (snapshot.context_digest, receipt.action_payload_digest)
    ):
        raise ValueError("full_draft_v3_apply_audit_missing")
    mutations = [
        ActionMutationAuditRecord.model_validate_json(row["payload_json"])
        for row in connection.execute(
            "SELECT payload_json FROM action_mutation_audits WHERE action_id = ?",
            (snapshot.action_id,),
        )
    ]
    mutation = next((item for item in mutations if item.audit_event_id == applied.id), None)
    if (
        mutation is None
        or mutation.status != "applied"
        or mutation.mutation_adapter != FULL_DRAFT_GENERATION_V3_ADAPTER
        or mutation.external_write_attempted
    ):
        raise ValueError("full_draft_v3_mutation_audit_missing")


def assert_full_draft_v3_revision_current(
    connection: sqlite3.Connection,
    command: ContentDraftRevisionAppendCommand,
    completed_run: CodexRun | None,
    path: Path,
) -> None:
    try:
        binding = command.generation_authorization
        if binding is None:
            raise ValueError("full_draft_v3_authorization_missing")
        receipt = _load(connection, "receipts", binding.action_id, FullDraftGenerationV3Receipt)
        claimed = _load(connection, "dispatches", binding.action_id, FullDraftGenerationV3Binding)
        if (
            receipt is None
            or claimed != binding
            or binding
            != FullDraftGenerationV3Binding.from_receipt(receipt).model_copy(
                update={"run_id": binding.run_id}
            )
        ):
            raise ValueError("full_draft_v3_dispatch_mismatch")
        assert_full_draft_v3_authority(connection, receipt, path)
        snapshot = receipt.snapshot
        if (
            command.work_item_id,
            command.content_kind,
            command.service_card_id,
            command.planning_digest,
            command.planning_input_digest,
            command.research_packet_id,
            command.research_packet_digest,
            command.final_canonical_url,
            command.base_revision_id,
            command.created_by,
        ) != (
            snapshot.work_item_id,
            snapshot.content_kind,
            snapshot.service_card_id,
            snapshot.planning_digest,
            snapshot.planning_input_digest,
            snapshot.packet_id,
            snapshot.packet_digest,
            snapshot.page_url,
            None,
            receipt.confirmed_by,
        ) or command.refresh_preparation_binding is not None:
            raise ValueError("full_draft_v3_revision_mismatch")
        run = _load_run(connection, binding.run_id)
        worker = _load(
            connection, "worker_starts", binding.action_id, FullDraftGenerationV3WorkerStart
        )
        if (
            run is None
            or completed_run is None
            or completed_run.id != binding.run_id
            or completed_run.status != "completed"
            or completed_run.completed_at is None
            or completed_run.error is not None
            or command.proposal_metadata is None
            or command.proposal_metadata.codex_run_id != binding.run_id
            or worker is None
            or worker.binding != binding
            or run.status != "started"
            or run.action_ids != [binding.action_id]
            or run.hook != "content_initial_full_draft"
            or run.source != "wilq_api"
            or completed_run.model_copy(
                update={"status": "started", "completed_at": None, "error": None}
            )
            != run
            or (run.proposal_id, run.planning_digest, run.planning_input_digest)
            != (snapshot.proposal_id, snapshot.planning_digest, snapshot.planning_input_digest)
        ):
            raise ValueError("full_draft_v3_run_mismatch")
    except (ValueError, sqlite3.Error) as error:
        raise RefreshPreparationAtomicityError("stale_initial_draft_context") from error


def _load_run(connection: sqlite3.Connection, run_id: str) -> CodexRun | None:
    row = connection.execute(
        "SELECT payload_json FROM codex_runs WHERE id = ?", (run_id,)
    ).fetchone()
    return None if row is None else CodexRun.model_validate_json(row["payload_json"])


def assert_draft_revision_authority(
    connection: sqlite3.Connection,
    command: ContentDraftRevisionAppendCommand,
    completed_run: CodexRun | None,
    path: Path,
) -> None:
    from wilq.content.workflow.store.refresh_preparation_atomic import (
        assert_refresh_preparation_revision_current,
    )

    if command.generation_authorization is not None:
        assert_full_draft_v3_revision_current(connection, command, completed_run, path)
        return
    assert_refresh_preparation_revision_current(connection, command)
    if command.base_revision_id is not None:
        return
    packet_id = command.research_packet_id
    if packet_id is not None and packet_id.startswith("content_research_packet_v3_"):
        raise RefreshPreparationAtomicityError("full_draft_v3_authorization_missing")
    planning_schema = connection.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'table' AND name = 'content_planning_proposals'"
    ).fetchone()
    if planning_schema is None:
        return
    row = connection.execute(
        "SELECT payload_json FROM content_planning_proposals WHERE work_item_id = ? "
        "AND json_extract(payload_json, '$.planning_digest') = ? "
        "ORDER BY proposal_version DESC LIMIT 1",
        (command.work_item_id, command.planning_digest),
    ).fetchone()
    proposal = (
        None if row is None else ContentPlanningProposal.model_validate_json(row["payload_json"])
    )
    packet_id = None if proposal is None else proposal.research_packet_id
    if packet_id is not None and packet_id.startswith("content_research_packet_v3_"):
        raise RefreshPreparationAtomicityError("full_draft_v3_authorization_missing")
