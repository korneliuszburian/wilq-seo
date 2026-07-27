from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import cast

from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPageBriefInput,
    ContentNewPagePlanningFoundation,
    build_new_page_brief,
)
from wilq.content.workflow.store_schema import ensure_content_workflow_schema
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path


def new_page_brief_store() -> NewPageBriefStore:
    return NewPageBriefStore(state_db_path())


class NewPageBriefStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        ensure_content_workflow_schema(connection)
        return connection

    def create_new_page_brief(self, input: ContentNewPageBriefInput) -> ContentNewPageBrief:
        redacted_input = ContentNewPageBriefInput.model_validate(
            redact_mapping(input.model_dump(mode="json"))
        )
        brief = build_new_page_brief(redacted_input)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_new_page_briefs (brief_id, created_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (brief.brief_id, brief.created_at.isoformat(), brief.model_dump_json()),
            )
        return brief

    def load_new_page_brief(self, brief_id: str) -> ContentNewPageBrief | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_new_page_briefs WHERE brief_id = ?",
                (brief_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentNewPageBrief.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_new_page_foundation(
        self,
        foundation: ContentNewPagePlanningFoundation,
    ) -> tuple[str, ContentNewPagePlanningFoundation]:
        stored = ContentNewPagePlanningFoundation.model_validate(
            redact_mapping(foundation.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM content_new_page_foundations WHERE brief_id = ?",
                (stored.brief_id,),
            ).fetchone()
            if existing is not None:
                existing_foundation = ContentNewPagePlanningFoundation.model_validate(
                    json.loads(cast(str, existing["payload_json"]))
                )
                if (
                    existing_foundation.brief_digest != stored.brief_digest
                    or existing_foundation.overlap_digest != stored.overlap_digest
                    or existing_foundation.service_card_id != stored.service_card_id
                    or existing_foundation.service_card_digest != stored.service_card_digest
                ):
                    raise ValueError(
                        "Dla tego briefu istnieje już podstawa planowania "
                        "z innym dokładnym wiązaniem."
                    )
                return (
                    "idempotent",
                    existing_foundation,
                )
            connection.execute(
                """
                INSERT INTO content_new_page_foundations
                  (foundation_id, brief_id, work_item_id, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    stored.foundation_id,
                    stored.brief_id,
                    stored.work_item_id,
                    stored.created_at.isoformat(),
                    stored.model_dump_json(),
                ),
            )
        return "created", stored

    def load_new_page_foundation(
        self,
        brief_id: str,
    ) -> ContentNewPagePlanningFoundation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_new_page_foundations WHERE brief_id = ?",
                (brief_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentNewPagePlanningFoundation.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )
