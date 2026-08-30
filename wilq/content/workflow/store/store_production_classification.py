from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    ContentProductionClassificationRecordResult,
    ContentProductionClassificationRun,
    project_content_production_classification,
)
from wilq.storage.model_json import model_json


class ProductionClassificationStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_production_classification(
        self,
        run: ContentProductionClassificationRun,
    ) -> ContentProductionClassificationRecordResult:
        accepted = ContentProductionClassificationRun.model_validate_json(
            run.model_dump_json(),
            strict=True,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute(
                """
                SELECT * FROM content_production_classifications
                WHERE input_digest = ? OR run_id = ?
                ORDER BY CASE WHEN input_digest = ? THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (accepted.input_digest, accepted.run_id, accepted.input_digest),
            ).fetchone()
            if existing_row is not None:
                existing = _classification_from_row(existing_row)
                if (
                    existing.input_digest == accepted.input_digest
                    and existing.run_digest == accepted.run_digest
                ):
                    return ContentProductionClassificationRecordResult(
                        status="idempotent",
                        run=existing,
                    )
                return ContentProductionClassificationRecordResult(
                    status="conflict",
                    run=existing,
                )
            connection.execute(
                """
                INSERT INTO content_production_classifications (
                  input_digest, run_id, run_digest, policy_id, policy_digest,
                  packet_sha256, judge_sha256, recorded_by, reviewed_by,
                  recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.input_digest,
                    accepted.run_id,
                    accepted.run_digest,
                    accepted.input.policy_id,
                    accepted.input.policy_digest,
                    accepted.input.packet_sha256,
                    accepted.input.judge_sha256,
                    accepted.audit.recorded_by,
                    accepted.audit.reviewed_by,
                    accepted.audit.recorded_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentProductionClassificationRecordResult(status="created", run=accepted)

    def load_latest_production_classification(
        self,
    ) -> ContentProductionClassificationRun | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM content_production_classifications
                ORDER BY recorded_at DESC, rowid DESC
                LIMIT 1
                """
            ).fetchone()
        return None if row is None else _classification_from_row(row)

    def load_production_classification_for_work_item(
        self,
        work_item_id: str,
    ) -> ContentProductionClassificationProjection | None:
        run = self.load_latest_production_classification()
        if run is None:
            return None
        row = run.for_work_item(work_item_id)
        return None if row is None else project_content_production_classification(run, row)


def _classification_from_row(row: sqlite3.Row) -> ContentProductionClassificationRun:
    run = ContentProductionClassificationRun.model_validate_json(
        cast(str, row["payload_json"]),
        strict=True,
    )
    expected_scalars = (
        run.input_digest,
        run.run_id,
        run.run_digest,
        run.input.policy_id,
        run.input.policy_digest,
        run.input.packet_sha256,
        run.input.judge_sha256,
        run.audit.recorded_by,
        run.audit.reviewed_by,
        run.audit.recorded_at.isoformat(),
    )
    stored_scalars = tuple(
        cast(str, row[name])
        for name in (
            "input_digest",
            "run_id",
            "run_digest",
            "policy_id",
            "policy_digest",
            "packet_sha256",
            "judge_sha256",
            "recorded_by",
            "reviewed_by",
            "recorded_at",
        )
    )
    if stored_scalars != expected_scalars:
        raise ValueError("Stored production classification scalars do not match the aggregate.")
    return run


__all__ = ["ProductionClassificationStoreMixin"]
