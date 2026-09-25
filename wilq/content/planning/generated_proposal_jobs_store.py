"""Transactional persistence for pending content planning generation jobs."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_rows import job_is_stale as _job_is_stale
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json

if TYPE_CHECKING:
    from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore

PlanningEnqueueOutcome = Literal["queued", "existing", "in_flight", "finished"]


class _PlanningGenerationAdmissionBlocked(RuntimeError):
    def __init__(self, response: ContentPlanningProposalResponse) -> None:
        super().__init__("Planning generation admission is no longer current.")
        self.response = response


def _per_url_identity_matches_current_observation(
    connection: sqlite3.Connection,
    *,
    action_id: str,
    canonical_path: str,
    current_work_item_id: str,
) -> bool:
    binding = connection.execute(
        "SELECT canonical_path, current_work_item_id, semantic_row_digest "
        "FROM content_per_url_delivery_identity_bindings WHERE action_id = ?",
        (action_id,),
    ).fetchone()
    if (
        binding is None
        or binding["canonical_path"] != canonical_path
        or binding["current_work_item_id"] != current_work_item_id
    ):
        return False
    observation = connection.execute(
        "SELECT canonical_path, current_work_item_id, semantic_row_digest "
        "FROM content_per_url_decision_observations "
        "WHERE canonical_path = ? OR current_work_item_id = ? "
        "ORDER BY sequence DESC LIMIT 1",
        (binding["canonical_path"], binding["current_work_item_id"]),
    ).fetchone()
    return (
        observation is not None
        and observation["canonical_path"] == binding["canonical_path"]
        and observation["current_work_item_id"] == binding["current_work_item_id"]
        and observation["semantic_row_digest"] == binding["semantic_row_digest"]
    )


def _enqueue_subject_pending(
    store: ContentPlanningProposalStore,
    *,
    work_item_id: str,
    subject: ContentPlanningSubject,
    planning_input_digest: str,
    response: ContentPlanningProposalResponse,
    allow_finished_reset: bool = False,
    admission_guard: Callable[[sqlite3.Connection], ContentPlanningProposalResponse | None]
    | None = None,
) -> PlanningEnqueueOutcome:
    """Admit one pending job, checking a supplied guard inside its write transaction."""

    payload = redact_mapping(response.model_dump(mode="json"))
    with store.run_transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if admission_guard is not None:
            blocked = admission_guard(connection)
            if blocked is not None:
                raise _PlanningGenerationAdmissionBlocked(blocked)
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
