from __future__ import annotations

import sqlite3

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_rows import (
    job_is_stale,
    response_from_job_row,
    table_exists,
)
from wilq.content.planning.subject import ContentPlanningSubject


class PlanningSubjectReadMixin:
    def _read_connection(self) -> sqlite3.Connection | None:
        raise NotImplementedError

    def active_subject_generation_response(
        self,
        work_item_id: str,
        subject: ContentPlanningSubject,
        *,
        excluding_digest: str | None = None,
    ) -> ContentPlanningProposalResponse | None:
        connection = self._read_connection()
        if connection is None or not table_exists(connection, "content_planning_generation_jobs"):
            return None
        try:
            with connection:
                rows = connection.execute(
                    """
                    SELECT planning_input_digest, payload_json, updated_at, work_item_id,
                           service_card_id, content_kind, subject_key
                    FROM content_planning_generation_jobs
                    WHERE work_item_id = ? AND content_kind = ? AND subject_key = ?
                      AND status = 'queued'
                    ORDER BY updated_at DESC
                    """,
                    (work_item_id, subject.content_kind, subject.subject_key),
                ).fetchall()
        finally:
            connection.close()
        for row in rows:
            if excluding_digest and row["planning_input_digest"] == excluding_digest:
                continue
            if job_is_stale(row["updated_at"]):
                continue
            return response_from_job_row(row)
        return None


__all__ = ["PlanningSubjectReadMixin"]
