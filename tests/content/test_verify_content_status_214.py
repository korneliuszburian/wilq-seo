from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/verify_content_status_214.py"
_SPEC = importlib.util.spec_from_file_location("verify_content_status_214", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
status = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = status
_SPEC.loader.exec_module(status)


def test_canonical_status_csv_satisfies_the_current_state_contract() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")

    assert status.validate_rows(columns, rows) == []
    assert status.validate_csv(_ROOT / "docs/content-status-214.csv") == []
    assert sum(row["revision_scope"] == "current" for row in rows) == 18
    assert sum(row["semantic_review_status"] == "zero_findings" for row in rows) == 17
    assert sum(row["delivery_status"] == "dev_draft_verified" for row in rows) == 8


def test_historical_journal_sidecar_requires_supersession_markers(tmp_path: Path) -> None:
    sidecar = tmp_path / status.HISTORICAL_JOURNAL_SIDECAR
    sidecar.write_text(status.HISTORICAL_JOURNAL_MARKERS[0], encoding="utf-8")

    errors = status.validate_historical_journal_sidecar(sidecar)

    assert errors == [
        "historical journal sidecar is missing required marker",
        "historical journal sidecar is missing required marker",
        "historical journal sidecar is missing required marker",
    ]


def test_status_contract_rejects_unregistered_or_unsorted_blockers() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    changed_rows[0]["blocker_codes"] = "z_unregistered;a_unregistered"

    errors = status.validate_rows(columns, changed_rows)

    assert any("blocker codes are not sorted" in error for error in errors)
    assert any("unregistered blocker code" in error for error in errors)


def test_status_contract_rejects_duplicate_paths_and_noncanonical_urls() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    changed_rows[1]["path"] = changed_rows[0]["path"]
    changed_rows[2]["url"] = "https://user@ekologus.dev.proudsite.pl/other?query#fragment"

    errors = status.validate_rows(columns, changed_rows)

    assert "paths must be unique" in errors
    assert any("canonical dev origin" in error for error in errors)


def test_status_contract_rejects_unknown_or_incompatible_vocabularies() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    changed_rows[0]["wordpress_type"] = "article"
    changed_rows[1]["wordpress_type"] = "post"
    changed_rows[1]["content_kind"] = "service"
    changed_rows[2]["target_mapping_status"] = "confirmed_the_content"
    changed_rows[2]["delivery_status"] = "candidate_blocked"

    errors = status.validate_rows(columns, changed_rows)

    assert any("invalid wordpress type" in error for error in errors)
    assert any("incompatible wordpress type and content kind" in error for error in errors)
    assert any("incompatible target mapping and delivery status" in error for error in errors)


def test_blank_wordpress_type_is_limited_to_taxonomy_or_nonkeep_service_rows() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    assert status.validate_rows(columns, rows) == []
    changed_rows = [dict(row) for row in rows]
    taxonomy = next(
        row
        for row in changed_rows
        if row["wordpress_type"] == "" and row["content_kind"] == "taxonomy_or_system"
    )
    oferta = next(row for row in changed_rows if row["path"] == "/oferta")
    taxonomy["content_kind"] = "editorial"
    oferta["final_disposition"] = "keep"

    errors = status.validate_rows(columns, changed_rows)

    assert sum("incompatible wordpress type and content kind" in error for error in errors) == 2


def test_status_contract_requires_historical_reason_blockers() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    historical_keep = next(row for row in changed_rows if row["path"] == "/oferta/bhp-i-p-poz")
    historical_nonkeep = next(
        row
        for row in changed_rows
        if row["path"] == "/co-powinien-wiedziec-kierownik-skladowiska-odpadow"
    )
    historical_keep["blocker_codes"] = "owner_review_required"
    historical_nonkeep["blocker_codes"] = "non_survivor_redirect"

    errors = status.validate_rows(columns, changed_rows)

    assert any("historical keep row lacks" in error for error in errors)
    assert any("historical non-keep row lacks" in error for error in errors)


def test_malformed_csv_skips_state_db_validation(tmp_path: Path, monkeypatch) -> None:
    malformed = tmp_path / "malformed.csv"
    malformed.write_text("path\n/current\n", encoding="utf-8")
    (tmp_path / status.HISTORICAL_JOURNAL_SIDECAR).write_text(
        "\n".join(status.HISTORICAL_JOURNAL_MARKERS),
        encoding="utf-8",
    )
    observed: list[Path] = []
    monkeypatch.setattr(
        status,
        "validate_state_db",
        lambda _rows, state_db: observed.append(state_db) or [],
    )

    errors = status.validate_csv(malformed, tmp_path / "state.sqlite3")

    assert errors == ["CSV columns do not match contract"]
    assert observed == []


def test_state_db_validation_checks_exact_current_revision_and_semantic_status(
    tmp_path: Path,
) -> None:
    revision_id = f"content_revision_{'a' * 32}"
    digest = "b" * 64
    row = _current_row(revision_id, digest)
    database = tmp_path / "status.sqlite3"
    _write_state_db(database, revision_id, digest)

    assert status.validate_state_db([row], database) == []

    row["semantic_review_status"] = "unavailable"
    assert status.validate_state_db([row], database) == [
        "/current: unavailable semantic review exists in state DB"
    ]

    row["semantic_review_status"] = "zero_findings"
    row["revision_review_decision"] = "needs_changes"
    assert status.validate_state_db([row], database) == [
        "/current: revision approval does not match state DB"
    ]


def test_state_db_validation_checks_exact_dev_execution_receipt(tmp_path: Path) -> None:
    revision_id = f"content_revision_{'c' * 32}"
    digest = "d" * 64
    handoff_id = "wordpress_draft_handoff_work_item_current_revision"
    row = _current_row(revision_id, digest)
    row.update(
        {
            "delivery_status": "dev_draft_verified",
            "dev_execution_handoff_id": handoff_id,
            "dev_draft_post_id": "1991",
        }
    )
    database = tmp_path / "execution.sqlite3"
    _write_state_db(database, revision_id, digest, handoff_id=handoff_id)

    assert status.validate_state_db([row], database) == []

    row["dev_draft_post_id"] = "other"
    assert status.validate_state_db([row], database) == [
        "/current: dev execution receipt does not match state DB"
    ]


def test_state_db_allows_historical_revision_that_is_latest_in_its_old_work_item(
    tmp_path: Path,
) -> None:
    revision_id = f"content_revision_{'e' * 32}"
    digest = "f" * 64
    row = _current_row(revision_id, digest)
    row.update(
        {
            "content_state": "not_written",
            "revision_scope": "historical",
            "revision_review_decision": "",
            "semantic_review_status": "not_generated",
            "blocker_codes": "historical_revision_not_reusable",
        }
    )
    database = tmp_path / "historical.sqlite3"
    _write_state_db(database, revision_id, digest)

    assert status.validate_state_db([row], database) == []


def _current_row(revision_id: str, digest: str) -> dict[str, str]:
    return {
        "path": "/current",
        "url": "https://example.test/current",
        "final_disposition": "keep",
        "content_state": "written_approved",
        "revision_scope": "current",
        "revision_id": revision_id,
        "revision_digest": digest,
        "revision_review_decision": "approved",
        "semantic_review_status": "zero_findings",
        "delivery_status": "candidate_blocked",
        "dev_execution_handoff_id": "",
        "dev_draft_post_id": "",
    }


def _write_state_db(
    database: Path,
    revision_id: str,
    digest: str,
    *,
    handoff_id: str | None = None,
) -> None:
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE content_draft_revisions (
              revision_id TEXT, work_item_id TEXT, revision_number INTEGER,
              content_digest TEXT, payload_json TEXT
            );
            CREATE TABLE content_draft_revision_reviews (
              revision_id TEXT, decision TEXT, decision_number INTEGER
            );
            CREATE TABLE content_semantic_reviews (revision_id TEXT, payload_json TEXT);
            CREATE TABLE content_wordpress_draft_execution_history (
              handoff_id TEXT, revision_id TEXT, revision_digest TEXT, payload_json TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO content_draft_revisions VALUES (?, ?, ?, ?, ?)",
            (
                revision_id,
                "work_item_current",
                1,
                digest,
                json.dumps({"final_canonical_url": "https://example.test/current"}),
            ),
        )
        connection.execute(
            "INSERT INTO content_draft_revision_reviews VALUES (?, ?, ?)",
            (revision_id, "approved", 1),
        )
        connection.execute(
            "INSERT INTO content_semantic_reviews VALUES (?, ?)",
            (revision_id, json.dumps({"status": "reviewable", "findings": []})),
        )
        if handoff_id is not None:
            connection.execute(
                "INSERT INTO content_wordpress_draft_execution_history VALUES (?, ?, ?, ?)",
                (handoff_id, revision_id, digest, json.dumps({"wordpress_post_id": "1991"})),
            )
