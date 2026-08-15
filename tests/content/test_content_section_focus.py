from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from wilq.content.workflow.contracts.section_focus import (
    ContentSectionFocusRecord,
    ContentSectionFocusResponse,
    content_section_focus_status,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


@pytest.mark.parametrize(
    ("record", "current_planning_digest", "section_ids_in_plan", "expected"),
    [
        (None, "a" * 64, {"section_1"}, "missing"),
        (
            ContentSectionFocusRecord(
                work_item_id="work_1",
                section_id="section_1",
                planning_digest="a" * 64,
                updated_by="wilku",
                updated_at=datetime(2026, 8, 15, tzinfo=UTC),
            ),
            "a" * 64,
            {"section_1"},
            "current",
        ),
        (
            ContentSectionFocusRecord(
                work_item_id="work_1",
                section_id="section_1",
                planning_digest="a" * 64,
                updated_by="wilku",
                updated_at=datetime(2026, 8, 15, tzinfo=UTC),
            ),
            "b" * 64,
            {"section_1"},
            "stale",
        ),
        (
            ContentSectionFocusRecord(
                work_item_id="work_1",
                section_id="section_1",
                planning_digest="a" * 64,
                updated_by="wilku",
                updated_at=datetime(2026, 8, 15, tzinfo=UTC),
            ),
            "a" * 64,
            {"section_2"},
            "stale",
        ),
    ],
)
def test_content_section_focus_status_tracks_exact_current_plan(
    record: ContentSectionFocusRecord | None,
    current_planning_digest: str,
    section_ids_in_plan: set[str],
    expected: str,
) -> None:
    assert (
        content_section_focus_status(
            record,
            current_planning_digest,
            section_ids_in_plan,
        )
        == expected
    )


def test_content_section_focus_response_exposes_record_only_when_current() -> None:
    record = ContentSectionFocusRecord(
        work_item_id="work_1",
        section_id="section_1",
        planning_digest="a" * 64,
        updated_by="wilku",
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
    )

    response = ContentSectionFocusResponse(
        status="current",
        record=record,
        safe_next_step="Kontynuuj pracę nad wybraną sekcją.",
    )

    assert response.record == record


def test_stale_content_section_focus_response_cannot_expose_old_record() -> None:
    record = ContentSectionFocusRecord(
        work_item_id="work_1",
        section_id="section_1",
        planning_digest="a" * 64,
        updated_by="wilku",
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="only when current"):
        ContentSectionFocusResponse(
            status="stale",
            record=record,
            safe_next_step="Wybierz sekcję ponownie.",
        )


@pytest.mark.parametrize(
    ("section_id", "planning_digest"),
    [
        ("   ", "a" * 64),
        ("section_1", "not-a-sha256"),
    ],
)
def test_content_section_focus_record_rejects_invalid_identity(
    section_id: str,
    planning_digest: str,
) -> None:
    with pytest.raises(ValueError):
        ContentSectionFocusRecord(
            work_item_id="work_1",
            section_id=section_id,
            planning_digest=planning_digest,
            updated_at=datetime(2026, 8, 15, tzinfo=UTC),
        )


def test_content_section_focus_survives_store_reload_and_can_be_cleared(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.sqlite3"
    record = ContentSectionFocusRecord(
        work_item_id="work_1",
        section_id="section_1",
        planning_digest="a" * 64,
        updated_by="wilku",
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
    )
    replacement = record.model_copy(
        update={
            "section_id": "section_2",
            "planning_digest": "b" * 64,
            "updated_by": "marketer",
            "updated_at": datetime(2026, 8, 15, 1, tzinfo=UTC),
        }
    )

    saved = LocalStateStore(path).save_content_section_focus(record)
    replaced = LocalStateStore(path).save_content_section_focus(replacement)
    loaded = LocalStateStore(path).get_content_section_focus("work_1")
    LocalStateStore(path).clear_content_section_focus("work_1")

    assert saved == record
    assert replaced == replacement
    assert loaded == replacement
    assert LocalStateStore(path).get_content_section_focus("work_1") is None


def test_existing_v3_store_gains_additive_section_focus_schema(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO codex_runs VALUES ('legacy_run', '2026-08-14', '{}')"
        )
        connection.execute("PRAGMA user_version = 3")

    store = LocalStateStore(path)
    assert store.get_content_section_focus("work_1") is None
    assert store.get_content_section_focus("work_1") is None

    with sqlite3.connect(path) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(content_section_focus)")
        ]
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        legacy_run_count = connection.execute(
            "SELECT COUNT(*) FROM codex_runs WHERE id = 'legacy_run'"
        ).fetchone()[0]

    assert SQLITE_SCHEMA_VERSION == 4
    assert schema_version == SQLITE_SCHEMA_VERSION
    assert columns == [
        "work_item_id",
        "section_id",
        "planning_digest",
        "updated_by",
        "updated_at",
        "payload_json",
    ]
    assert legacy_run_count == 1


def test_unrelated_store_cannot_claim_v4_before_focus_table_exists(
    tmp_path: Path,
) -> None:
    path = tmp_path / "shared.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 3")

    assert ContentWorkflowStore(path).list_draft_revisions("work_1") == []
    with sqlite3.connect(path) as connection:
        version_before_focus_migration = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
        focus_table_before_migration = connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = 'content_section_focus'
            """
        ).fetchone()[0]

    assert version_before_focus_migration == 3
    assert focus_table_before_migration == 0

    assert LocalStateStore(path).get_content_section_focus("work_1") is None
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = 'content_section_focus'
            """
        ).fetchone()[0] == 1
