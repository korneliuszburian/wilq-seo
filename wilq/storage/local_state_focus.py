from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.contracts.section_focus import ContentSectionFocusRecord
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state_runs import _model_from_json, _model_json


class _SectionFocusStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_content_section_focus(
        self,
        record: ContentSectionFocusRecord,
    ) -> ContentSectionFocusRecord:
        redacted = ContentSectionFocusRecord.model_validate(
            redact_mapping(record.model_dump(mode="json"))
        )
        payload_json = _model_json(redacted)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_section_focus (
                  work_item_id, section_id, planning_digest, updated_by, updated_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  section_id = excluded.section_id,
                  planning_digest = excluded.planning_digest,
                  updated_by = excluded.updated_by,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.work_item_id,
                    redacted.section_id,
                    redacted.planning_digest,
                    redacted.updated_by,
                    redacted.updated_at.isoformat(),
                    payload_json,
                ),
            )
        return redacted

    def get_content_section_focus(
        self,
        work_item_id: str,
    ) -> ContentSectionFocusRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_section_focus WHERE work_item_id = ?",
                (work_item_id,),
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(ContentSectionFocusRecord, cast(str, row["payload_json"]))

    def clear_content_section_focus(self, work_item_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM content_section_focus WHERE work_item_id = ?",
                (work_item_id,),
            )


__all__ = ["_SectionFocusStoreMixin"]
