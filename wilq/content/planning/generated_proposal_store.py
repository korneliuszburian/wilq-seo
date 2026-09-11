from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, cast

from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_queries import (
    PROPOSAL_INPUT_SELECTS as _PROPOSAL_INPUT_SELECTS,
)
from wilq.content.planning.generated_proposal_queries import (
    PROPOSAL_LATEST_SELECTS as _PROPOSAL_LATEST_SELECTS,
)
from wilq.content.planning.generated_proposal_queries import (
    PROPOSAL_PLANNING_DIGEST_SELECTS as _PROPOSAL_PLANNING_DIGEST_SELECTS,
)
from wilq.content.planning.generated_proposal_rows import (
    job_is_stale as _job_is_stale,
)
from wilq.content.planning.generated_proposal_rows import (
    proposal_from_row as _proposal_from_row,
)
from wilq.content.planning.generated_proposal_rows import (
    proposal_insert_values as _proposal_insert_values,
)
from wilq.content.planning.generated_proposal_rows import (
    response_from_job_row as _response_from_job_row,
)
from wilq.content.planning.generated_proposal_rows import (
    table_exists as _table_exists,
)
from wilq.content.planning.generated_proposal_rows import (
    validate_generated_proposal as _validate_generated_proposal,
)
from wilq.content.planning.generated_proposal_schema import ensure_generated_proposal_schema
from wilq.content.planning.generated_proposal_subject_read import PlanningSubjectReadMixin
from wilq.content.planning.generation_claim_store import (
    refresh_preparation_binding_columns_present,
)
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.content.workflow.store.refresh_preparation_atomic import (
    assert_refresh_preparation_proposal_current,
)
from wilq.schemas import CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.model_json import model_json
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

PlanningEnqueueOutcome = Literal["queued", "existing", "in_flight", "finished"]
GeneratedProposalSaveOutcome = Literal["created", "idempotent", "replaced"]
PlanningTerminalSaveOutcome = Literal["saved", "claim_stale", "ignored"]


def content_planning_proposal_store() -> ContentPlanningProposalStore:
    return ContentPlanningProposalStore(state_db_path())


def _open_read_connection(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    reject_newer_sqlite_schema(connection)
    if any(
        _table_exists(connection, table)
        for table in (
            "content_planning_proposals",
            "content_planning_proposal_repairs",
            "content_planning_generation_jobs",
        )
    ):
        ensure_generated_proposal_schema(connection)
        ensure_sqlite_schema_version(connection)
        connection.commit()
    return connection


class _ContentPlanningProposalConvenienceMixin:
    def for_input(
        self,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
    ) -> ContentPlanningProposal | None:
        raise NotImplementedError

    def latest(
        self,
        work_item_id: str,
        service_card_id: str | None = None,
    ) -> ContentPlanningProposal | None:
        raise NotImplementedError

    def read_latest_or_none_for_input(
        self,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
    ) -> ContentPlanningProposal | None:
        """Read the latest proposal only when it matches the exact input."""

        return self.for_input(work_item_id, service_card_id, planning_input_digest)

    def latest_for_service(
        self,
        work_item_id: str,
        service_card_id: str,
    ) -> ContentPlanningProposal | None:
        """Read the newest persisted proposal for one service card."""

        return self.latest(work_item_id, service_card_id)


class ContentPlanningProposalStore(
    _ContentPlanningProposalConvenienceMixin,
    PlanningSubjectReadMixin,
):
    def __init__(self, path: Path) -> None:
        self.path = path

    def latest(
        self,
        work_item_id: str,
        service_card_id: str | None = None,
    ) -> ContentPlanningProposal | None:
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                row = _latest_proposal_row(connection, work_item_id, service_card_id)
        finally:
            connection.close()
        return _proposal_from_row(row)

    def for_input(
        self,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
    ) -> ContentPlanningProposal | None:
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                row = _proposal_row_for_subject_input(
                    connection,
                    work_item_id,
                    ContentPlanningSubject(service_card_id=service_card_id),
                    planning_input_digest,
                )
        finally:
            connection.close()
        return _proposal_from_row(row)

    def for_subject_input(
        self,
        work_item_id: str,
        subject: ContentPlanningSubject,
        planning_input_digest: str,
    ) -> ContentPlanningProposal | None:
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                row = _proposal_row_for_subject_input(
                    connection, work_item_id, subject, planning_input_digest
                )
        finally:
            connection.close()
        return _proposal_from_row(row)

    def latest_for_planning_digest(
        self,
        work_item_id: str,
        planning_digest: str,
    ) -> ContentPlanningProposal | None:
        """Read the newest proposal bound to an approved planning workspace."""
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                row = _proposal_row_for_planning_digest(connection, work_item_id, planning_digest)
        finally:
            connection.close()
        return _proposal_from_row(row)

    def queued_response(
        self,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
        *,
        include_stale: bool = False,
    ) -> ContentPlanningProposalResponse | None:
        """Return the durable in-flight/failed response for an exact input."""
        return self.queued_subject_response(
            work_item_id,
            ContentPlanningSubject(service_card_id=service_card_id),
            planning_input_digest,
            include_stale=include_stale,
        )

    def queued_subject_response(
        self,
        work_item_id: str,
        subject: ContentPlanningSubject,
        planning_input_digest: str,
        *,
        include_stale: bool = False,
    ) -> ContentPlanningProposalResponse | None:
        connection = self._read_connection()
        if connection is None or not _table_exists(connection, "content_planning_generation_jobs"):
            return None
        try:
            with connection:
                row = connection.execute(
                    """
                    SELECT payload_json, status, updated_at, work_item_id,
                           service_card_id, content_kind, subject_key, planning_input_digest
                    FROM content_planning_generation_jobs
                    WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
                      AND planning_input_digest = ?
                    LIMIT 1
                    """,
                    (
                        work_item_id,
                        subject.content_kind,
                        subject.subject_key,
                        planning_input_digest,
                    ),
                ).fetchone()
        finally:
            connection.close()
        if row is None or row["status"] not in {"queued", "blocked", "failed", "stale"}:
            return None
        response = _response_from_job_row(row)
        if not include_stale and row["status"] == "queued" and _job_is_stale(row["updated_at"]):
            return None
        return response

    def latest_generation_response(
        self,
        work_item_id: str,
        service_card_id: str | None = None,
    ) -> ContentPlanningProposalResponse | None:
        connection = self._read_connection()
        if connection is None or not _table_exists(connection, "content_planning_generation_jobs"):
            return None
        try:
            with connection:
                query = """
                    SELECT payload_json, status, updated_at, work_item_id,
                           service_card_id, content_kind, subject_key, planning_input_digest
                    FROM content_planning_generation_jobs
                    WHERE work_item_id = ?
                      AND status IN ('queued', 'blocked', 'failed', 'stale')
                """
                parameters: list[str] = [work_item_id]
                if service_card_id is not None:
                    query += " AND service_card_id = ?"
                    parameters.append(service_card_id)
                query += " ORDER BY updated_at DESC LIMIT 1"
                row = connection.execute(query, parameters).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        response = _response_from_job_row(row)
        if row["status"] == "queued" and _job_is_stale(row["updated_at"]):
            return None
        return response

    def active_generation_response(
        self,
        work_item_id: str,
        service_card_id: str,
        *,
        excluding_digest: str | None = None,
    ) -> ContentPlanningProposalResponse | None:
        """Read the current sibling job without accepting a stale worker."""
        return self.active_subject_generation_response(
            work_item_id,
            ContentPlanningSubject(service_card_id=service_card_id),
            excluding_digest=excluding_digest,
        )

    def enqueue(
        self,
        response: ContentPlanningProposalResponse,
    ) -> PlanningEnqueueOutcome:
        return _enqueue(self, response)

    def enqueue_pending(
        self,
        *,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
        response: ContentPlanningProposalResponse,
        allow_finished_reset: bool = False,
    ) -> PlanningEnqueueOutcome:
        """Persist a request before the expensive snapshot is built."""
        return _enqueue_subject_pending(
            self,
            work_item_id=work_item_id,
            subject=ContentPlanningSubject(service_card_id=service_card_id),
            planning_input_digest=planning_input_digest,
            response=response,
            allow_finished_reset=allow_finished_reset,
        )

    def enqueue_subject_pending(
        self,
        *,
        work_item_id: str,
        subject: ContentPlanningSubject,
        planning_input_digest: str,
        response: ContentPlanningProposalResponse,
        allow_finished_reset: bool = False,
    ) -> PlanningEnqueueOutcome:
        return _enqueue_subject_pending(
            self,
            work_item_id=work_item_id,
            subject=subject,
            planning_input_digest=planning_input_digest,
            response=response,
            allow_finished_reset=allow_finished_reset,
        )

    def save_terminal_response(
        self,
        response: ContentPlanningProposalResponse,
        *,
        job_planning_input_digest: str,
        claim_version: int | None = None,
        refresh_preparation_binding: ContentRefreshPreparationBinding | None = None,
    ) -> PlanningTerminalSaveOutcome:
        return _save_terminal_response(
            self,
            response,
            job_planning_input_digest=job_planning_input_digest,
            claim_version=claim_version,
            refresh_preparation_binding=refresh_preparation_binding,
        )

    def save_generated(
        self,
        proposal: ContentPlanningProposal,
        completed_run: CodexRun,
        *,
        replace_existing_exact_input: bool = False,
    ) -> tuple[GeneratedProposalSaveOutcome, ContentPlanningProposal]:
        return _save_generated(
            self,
            proposal,
            completed_run,
            replace_existing_exact_input=replace_existing_exact_input,
        )

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        ensure_generated_proposal_schema(connection)
        ensure_sqlite_schema_version(connection)
        connection.commit()
        return connection

    @contextmanager
    def run_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as connection:
            yield connection

    def _read_connection(self) -> sqlite3.Connection | None:
        return _open_read_connection(self.path)


def _enqueue(
    store: ContentPlanningProposalStore,
    response: ContentPlanningProposalResponse,
) -> PlanningEnqueueOutcome:
    if response.planning_input_digest is None:
        raise ValueError("Queued planning requires an exact input digest.")
    subject = ContentPlanningSubject(
        content_kind=response.content_kind,
        service_card_id=response.service_card_id,
    )
    return _enqueue_subject_pending(
        store,
        work_item_id=response.work_item_id,
        subject=subject,
        planning_input_digest=response.planning_input_digest,
        response=response,
    )


def _enqueue_pending(
    store: ContentPlanningProposalStore,
    *,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
    response: ContentPlanningProposalResponse,
    allow_finished_reset: bool = False,
) -> PlanningEnqueueOutcome:
    return _enqueue_subject_pending(
        store,
        work_item_id=work_item_id,
        subject=ContentPlanningSubject(service_card_id=service_card_id),
        planning_input_digest=planning_input_digest,
        response=response,
        allow_finished_reset=allow_finished_reset,
    )


def _enqueue_subject_pending(
    store: ContentPlanningProposalStore,
    *,
    work_item_id: str,
    subject: ContentPlanningSubject,
    planning_input_digest: str,
    response: ContentPlanningProposalResponse,
    allow_finished_reset: bool = False,
) -> PlanningEnqueueOutcome:
    payload = redact_mapping(response.model_dump(mode="json"))
    with store.run_transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
                SELECT status, updated_at FROM content_planning_generation_jobs
                WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
                  AND planning_input_digest = ?
                LIMIT 1
                """,
            (work_item_id, subject.content_kind, subject.subject_key, planning_input_digest),
        ).fetchone()
        if row is not None and row["status"] == "finished" and not allow_finished_reset:
            return "finished"
        if row is not None and row["status"] == "queued" and not _job_is_stale(row["updated_at"]):
            return "existing"
        sibling = connection.execute(
            """
                SELECT planning_input_digest, updated_at
                FROM content_planning_generation_jobs
                WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
                  AND status = 'queued' AND planning_input_digest != ?
                ORDER BY updated_at DESC LIMIT 1
                """,
            (work_item_id, subject.content_kind, subject.subject_key, planning_input_digest),
        ).fetchone()
        if sibling is not None and not _job_is_stale(sibling["updated_at"]):
            return "in_flight"
        connection.execute(
            """
            UPDATE content_planning_generation_jobs
            SET status = 'stale'
            WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
              AND planning_input_digest = ?
              AND status IN ('failed', 'blocked')
            """,
            (work_item_id, subject.content_kind, subject.subject_key, planning_input_digest),
        )
        if allow_finished_reset:
            upsert_status_fence = """
                INSERT INTO content_planning_generation_jobs (
                  work_item_id, service_card_id, content_kind, subject_key,
                  planning_input_digest, status,
                  payload_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(work_item_id, content_kind, subject_key, planning_input_digest)
                DO UPDATE SET status = 'queued', payload_json = excluded.payload_json,
                              updated_at = excluded.updated_at
                WHERE content_planning_generation_jobs.status IN ('queued', 'stale', 'finished')
                """
        else:
            upsert_status_fence = """
                INSERT INTO content_planning_generation_jobs (
                  work_item_id, service_card_id, content_kind, subject_key,
                  planning_input_digest, status,
                  payload_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(work_item_id, content_kind, subject_key, planning_input_digest)
                DO UPDATE SET status = 'queued', payload_json = excluded.payload_json,
                              updated_at = excluded.updated_at
                WHERE content_planning_generation_jobs.status IN ('queued', 'stale')
                """
        connection.execute(
            upsert_status_fence,
            (
                work_item_id,
                subject.service_card_id,
                subject.content_kind,
                subject.subject_key,
                planning_input_digest,
                model_json(payload),
            ),
        )
    return "queued"


def _save_terminal_response(
    store: ContentPlanningProposalStore,
    response: ContentPlanningProposalResponse,
    *,
    job_planning_input_digest: str,
    claim_version: int | None = None,
    refresh_preparation_binding: ContentRefreshPreparationBinding | None = None,
) -> PlanningTerminalSaveOutcome:
    subject = ContentPlanningSubject(
        content_kind=response.content_kind,
        service_card_id=response.service_card_id,
    )
    payload = redact_mapping(response.model_dump(mode="json"))
    status = response.status if response.status in {"blocked", "failed", "stale"} else "finished"
    exact_job_digest = job_planning_input_digest
    expected_binding = (
        _response_refresh_preparation_binding(response)
        if refresh_preparation_binding is None
        else refresh_preparation_binding
    )
    with store.run_transaction() as connection:
        if claim_version is not None:
            if not _table_exists(connection, "content_planning_generation_claims"):
                return "claim_stale"
            if not refresh_preparation_binding_columns_present(connection):
                return "claim_stale"
            if not _terminal_response_matches_durable_binding(
                connection,
                response=response,
                expected_binding=expected_binding,
                work_item_id=response.work_item_id,
                subject=subject,
                planning_input_digest=exact_job_digest,
            ):
                return "claim_stale"
            authorization_id, authorization_digest = _binding_identity(expected_binding)
            updated = connection.execute(
                """
                    UPDATE content_planning_generation_jobs
                    SET status = ?, payload_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
                      AND planning_input_digest = ?
                      AND EXISTS (
                        SELECT 1
                        FROM content_planning_generation_claims AS claim
                        WHERE claim.work_item_id = ?
                          AND claim.content_kind = ? AND claim.subject_key = ?
                          AND claim.planning_input_digest = ?
                          AND claim.claim_version = ?
                          AND claim.status = 'claimed'
                          AND claim.refresh_preparation_authorization_id IS ?
                          AND claim.refresh_preparation_authorization_digest IS ?
                      )
                    """,
                (
                    status,
                    model_json(payload),
                    response.work_item_id,
                    subject.content_kind,
                    subject.subject_key,
                    exact_job_digest,
                    response.work_item_id,
                    subject.content_kind,
                    subject.subject_key,
                    exact_job_digest,
                    claim_version,
                    authorization_id,
                    authorization_digest,
                ),
            )
            return "saved" if updated.rowcount == 1 else "claim_stale"
        updated = connection.execute(
            """
                UPDATE content_planning_generation_jobs
                SET status = ?, payload_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
                  AND planning_input_digest = ?
                """,
            (
                status,
                model_json(payload),
                response.work_item_id,
                subject.content_kind,
                subject.subject_key,
                exact_job_digest,
            ),
        )
    return "saved" if updated.rowcount > 0 else "ignored"


def _terminal_response_matches_durable_binding(
    connection: sqlite3.Connection,
    *,
    response: ContentPlanningProposalResponse,
    expected_binding: ContentRefreshPreparationBinding | None,
    work_item_id: str,
    subject: ContentPlanningSubject,
    planning_input_digest: str,
) -> bool:
    row = connection.execute(
        """
        SELECT payload_json, status, updated_at, work_item_id, service_card_id,
               content_kind, subject_key, planning_input_digest
        FROM content_planning_generation_jobs
        WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
          AND planning_input_digest = ?
        LIMIT 1
        """,
        (work_item_id, subject.content_kind, subject.subject_key, planning_input_digest),
    ).fetchone()
    if row is None:
        return False
    try:
        stored = _response_from_job_row(row)
    except ValueError:
        return False
    return (
        _response_refresh_preparation_binding(response) == expected_binding
        and _response_refresh_preparation_binding(stored) == expected_binding
    )


def _response_refresh_preparation_binding(
    response: ContentPlanningProposalResponse,
) -> ContentRefreshPreparationBinding | None:
    if response.refresh_preparation_binding is not None:
        return response.refresh_preparation_binding
    return None if response.proposal is None else response.proposal.refresh_preparation_binding


def _binding_identity(
    binding: ContentRefreshPreparationBinding | None,
) -> tuple[str | None, str | None]:
    if binding is None:
        return None, None
    return binding.authorization_id, binding.authorization_digest


def _save_generated(
    store: ContentPlanningProposalStore,
    proposal: ContentPlanningProposal,
    completed_run: CodexRun,
    *,
    replace_existing_exact_input: bool = False,
) -> tuple[GeneratedProposalSaveOutcome, ContentPlanningProposal]:
    _validate_generated_proposal(proposal, completed_run)
    with store.run_transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert_refresh_preparation_proposal_current(connection, proposal)
        subject = ContentPlanningSubject(
            content_kind=proposal.content_kind,
            service_card_id=proposal.service_card_id,
        )
        existing_row = _proposal_row_for_subject_input(
            connection,
            proposal.work_item_id,
            subject,
            str(proposal.planning_input_digest),
        )
        if existing_row is not None:
            existing = _proposal_from_row(existing_row)
            if existing is None:
                raise RuntimeError("Planning proposal row disappeared during save.")
            if not replace_existing_exact_input:
                return "idempotent", existing
        else:
            existing = None
        row = connection.execute(
            """
                SELECT COALESCE(MAX(proposal_version), 0) AS latest_version
                FROM (
                  SELECT proposal_version FROM content_planning_proposals WHERE work_item_id = ?
                  UNION ALL
                  SELECT proposal_version
                  FROM content_planning_proposal_repairs
                  WHERE work_item_id = ?
                )
                """,
            (proposal.work_item_id, proposal.work_item_id),
        ).fetchone()
        version = 1 if row is None else int(row["latest_version"]) + 1
        versioned = proposal.model_copy(update={"proposal_version": version})
        safe_proposal = ContentPlanningProposal.model_validate(
            redact_mapping(versioned.model_dump(mode="json"))
        )
        safe_run = CodexRun.model_validate(redact_mapping(completed_run.model_dump(mode="json")))
        created_at = safe_proposal.created_at or safe_run.completed_at
        if created_at is None:
            raise RuntimeError("Generated planning proposal is missing created_at.")
        connection.execute(
            """
                INSERT INTO codex_runs (id, started_at, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  started_at = excluded.started_at,
                  payload_json = excluded.payload_json
                """,
            (
                safe_run.id,
                safe_run.started_at.isoformat(),
                safe_run.model_dump_json(),
            ),
        )
        if existing is None:
            connection.execute(
                """
                    INSERT INTO content_planning_proposals (
                      proposal_id, work_item_id, proposal_version, service_card_id,
                      content_kind, subject_key,
                      planning_input_digest, created_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                _proposal_insert_values(safe_proposal, created_at),
            )
            outcome: GeneratedProposalSaveOutcome = "created"
        else:
            values = _proposal_insert_values(safe_proposal, created_at)
            connection.execute(
                """
                    INSERT INTO content_planning_proposal_repairs (
                      proposal_id, work_item_id, proposal_version, service_card_id,
                      content_kind, subject_key,
                      planning_input_digest, supersedes_proposal_id, created_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                (*values[:7], existing.proposal_id, *values[7:]),
            )
            outcome = "replaced"
    return outcome, safe_proposal


def _proposal_row_for_subject_input(
    connection: sqlite3.Connection,
    work_item_id: str,
    subject: ContentPlanningSubject,
    planning_input_digest: str,
) -> sqlite3.Row | None:
    tables = _proposal_tables(connection)
    query = " UNION ALL ".join(_PROPOSAL_INPUT_SELECTS[table] for table in tables)
    # Table fragments are fixed above; every caller value remains a bound parameter.
    row = connection.execute(
        "SELECT * FROM (" + query + ") ORDER BY proposal_version DESC LIMIT 1",  # nosec B608
        (
            work_item_id,
            subject.content_kind,
            subject.subject_key,
            planning_input_digest,
        )
        * len(tables),
    ).fetchone()
    return cast(sqlite3.Row | None, row)


def _latest_proposal_row(
    connection: sqlite3.Connection,
    work_item_id: str,
    service_card_id: str | None,
) -> sqlite3.Row | None:
    tables = _proposal_tables(connection)
    where = (
        "work_item_id = ?"
        if service_card_id is None
        else "work_item_id = ? AND service_card_id = ?"
    )
    query = " UNION ALL ".join(_PROPOSAL_LATEST_SELECTS[table] + where for table in tables)
    base_params = (work_item_id,) if service_card_id is None else (work_item_id, service_card_id)
    params = base_params * len(tables)
    # Table fragments are fixed above; every caller value remains a bound parameter.
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM ("  # nosec B608
            + query
            + ") ORDER BY proposal_version DESC LIMIT 1",
            params,
        ).fetchone(),
    )


def _proposal_row_for_planning_digest(
    connection: sqlite3.Connection,
    work_item_id: str,
    planning_digest: str,
) -> sqlite3.Row | None:
    tables = _proposal_tables(connection)
    query = " UNION ALL ".join(_PROPOSAL_PLANNING_DIGEST_SELECTS[table] for table in tables)
    # Table fragments are fixed above; every caller value remains a bound parameter.
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM ("  # nosec B608
            + query
            + ") ORDER BY proposal_version DESC LIMIT 1",
            (work_item_id, planning_digest) * len(tables),
        ).fetchone(),
    )


def _proposal_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    tables = ["content_planning_proposals"]
    if _table_exists(connection, "content_planning_proposal_repairs"):
        tables.append("content_planning_proposal_repairs")
    return tuple(tables)


__all__ = [
    "ContentPlanningProposalStore",
    "PlanningTerminalSaveOutcome",
    "PlanningEnqueueOutcome",
    "content_planning_proposal_store",
]
