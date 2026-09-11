from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from wilq.content.workflow.target.target_discovery import (
    ContentTargetAuthoringLayout,
    ContentTargetAuthoringSurface,
    ContentTargetContract,
    ContentTargetObservationEvidence,
)
from wilq.content.workflow.target.target_mapping import (
    ContentTargetMappingComponent,
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingFieldBinding,
    ContentTargetMappingPreview,
    ContentTargetMappingRevision,
    ContentTargetMappingSelection,
    ContentTargetMappingSourceField,
    ContentTargetMappingTarget,
    new_content_target_mapping_confirmation,
)
from wilq.content.workflow.target.target_mapping_persistence import (
    build_content_target_mapping_persisted_record,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/verify_content_status_214.py"
_SPEC = importlib.util.spec_from_file_location("verify_content_status_214", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
status = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = status
_SPEC.loader.exec_module(status)

_EXPORT_SCRIPT = _ROOT / "scripts/export_content_status_csv.py"
_EXPORT_SPEC = importlib.util.spec_from_file_location(
    "export_content_status_csv", _EXPORT_SCRIPT
)
assert _EXPORT_SPEC is not None and _EXPORT_SPEC.loader is not None
exporter = importlib.util.module_from_spec(_EXPORT_SPEC)
_EXPORT_SPEC.loader.exec_module(exporter)


def test_canonical_status_csv_satisfies_the_current_state_contract() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")

    assert status.validate_rows(columns, rows) == []
    assert status.validate_csv(_ROOT / "docs/content-status-214.csv") == []
    assert sum(row["revision_scope"] == "current" for row in rows) == 18
    assert sum(row["semantic_review_status"] == "zero_findings" for row in rows) == 17
    assert sum(row["delivery_status"] == "dev_draft_verified" for row in rows) == 7
    ippc = next(
        row
        for row in rows
        if row["path"].startswith(
            "/obowiazki-pomiarowe-instalacji-wymagajacej-pozwolenia-zintegrowanego"
        )
    )
    assert ippc["target_mapping_status"] == "blocked_target_unavailable"
    assert ippc["delivery_status"] == "blocked_target_unavailable"


def test_status_contract_rejects_an_unsupported_schema_version() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    changed_rows[0]["schema_version"] = "content_status_214_v2"

    errors = status.validate_rows(columns, changed_rows)

    assert "CSV uses an unsupported schema version" in errors


def test_legacy_exporter_cannot_overwrite_the_canonical_journal() -> None:
    args = Namespace(
        journal=Path("not-read.json"),
        sitemap=Path("not-read.json"),
        acf_inventory=Path("not-read.json"),
        state_db=Path("not-read.sqlite3"),
        output=_ROOT / "docs/content-status-214.csv",
    )

    with pytest.raises(ValueError, match="legacy exporter schema"):
        exporter.export(args)


def test_legacy_exporter_cannot_overwrite_a_hardlink_to_the_journal(
    tmp_path: Path,
) -> None:
    alias = _ROOT / "docs" / f".{tmp_path.name}-journal-alias.csv"
    try:
        os.link(_ROOT / "docs/content-status-214.csv", alias)
        args = Namespace(
            journal=Path("not-read.json"),
            sitemap=Path("not-read.json"),
            acf_inventory=Path("not-read.json"),
            state_db=Path("not-read.sqlite3"),
            output=alias,
        )

        with pytest.raises(ValueError, match="legacy exporter schema"):
            exporter.export(args)
    finally:
        alias.unlink(missing_ok=True)


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


def test_status_contract_rejects_drifted_disposition_counts_and_robot_gate() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    changed_rows[0]["final_disposition"] = "noindex"
    changed_rows[0]["robot_ready"] = "true"

    errors = status.validate_rows(columns, changed_rows)

    assert "expected final disposition counts 57/87/46/24" in errors
    assert "robot-ready rows are not allowed before the final delivery gate" in errors


def test_status_contract_rejects_malformed_url_authority() -> None:
    columns, rows = status.load_rows(_ROOT / "docs/content-status-214.csv")
    changed_rows = [dict(row) for row in rows]
    changed_rows[0]["url"] = "https://[::1"

    errors = status.validate_rows(columns, changed_rows)

    assert any("URL has an invalid port" in error for error in errors)


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

    verified_without_mapping = [dict(row) for row in rows]
    verified = next(
        row
        for row in verified_without_mapping
        if row["delivery_status"] == "dev_draft_verified"
    )
    verified["target_mapping_status"] = ""
    errors = status.validate_rows(columns, verified_without_mapping)

    assert any("incompatible target mapping and delivery status" in error for error in errors)

    unapproved_verified = [dict(row) for row in rows]
    verified = next(
        row
        for row in unapproved_verified
        if row["delivery_status"] == "dev_draft_verified"
    )
    verified.update(
        {
            "content_state": "not_written",
            "revision_review_decision": "",
            "semantic_review_status": "not_generated",
        }
    )
    errors = status.validate_rows(columns, unapproved_verified)

    assert any(
        "verified dev draft requires exact current execution receipt" in error
        for error in errors
    )

    mapping_without_revision = [dict(row) for row in rows]
    mapped = next(
        row
        for row in mapping_without_revision
        if row["target_mapping_status"] == "confirmed_the_content"
    )
    mapped.update(
        {
            "revision_id": "",
            "revision_digest": "",
            "revision_scope": "none",
            "content_state": "not_written",
            "revision_review_decision": "",
            "semantic_review_status": "not_generated",
        }
    )
    errors = status.validate_rows(columns, mapping_without_revision)

    assert any("target mapping status requires a bound revision" in error for error in errors)


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

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_draft_revision_reviews SET work_item_id = ?",
            ("other_work_item",),
        )
    row["revision_review_decision"] = "approved"
    assert status.validate_state_db([row], database) == [
        "/current: revision approval does not match state DB"
    ]

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_draft_revision_reviews SET work_item_id = ?",
            ("work_item_current",),
        )
        connection.execute(
            "UPDATE content_semantic_reviews SET payload_json = ?",
            (json.dumps({"status": "reviewable", "findings": [{"severity": "low"}]}),),
        )
    row["revision_review_decision"] = "approved"
    assert status.validate_state_db([row], database) == [
        "/current: semantic zero-findings status does not match state DB"
    ]

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_semantic_reviews SET work_item_id = ?, payload_json = ?",
            ("other_work_item", json.dumps({"status": "reviewable", "findings": []})),
        )
    assert status.validate_state_db([row], database) == [
        "/current: semantic zero-findings status does not match state DB"
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

    row["wordpress_type"] = "uslugi"
    assert status.validate_state_db([row], database) == [
        "/current: dev execution is not an exact verified draft creation"
    ]
    row["wordpress_type"] = "post"

    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM content_wordpress_draft_execution_history"
            ).fetchone()[0]
        )
        payload["boundary"]["live_write_enabled"] = False
        connection.execute(
            "UPDATE content_wordpress_draft_execution_history SET payload_json = ?",
            (json.dumps(payload),),
        )
    assert status.validate_state_db([row], database) == [
        "/current: dev execution is not an exact verified draft creation"
    ]

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_wordpress_draft_execution_history SET payload_json = ?",
            (
                json.dumps(
                    {
                        "status": "blocked",
                        "mode": "live",
                        "external_write_attempted": True,
                        "wordpress_post_id": "1991",
                        "expected_content_digest": digest,
                        "observed_content_digest": digest,
                    }
                ),
            ),
        )
    assert status.validate_state_db([row], database) == [
        "/current: dev execution is not an exact verified draft creation"
    ]

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


def test_state_db_requires_exact_confirmed_target_mapping(tmp_path: Path) -> None:
    revision_id = f"content_revision_{'f' * 32}"
    digest = "a" * 64
    row = _current_row(revision_id, digest)
    row["target_mapping_status"] = "confirmed_the_content"
    database = tmp_path / "mapping.sqlite3"
    _write_state_db(database, revision_id, digest)

    assert status.validate_state_db([row], database) == [
        "/current: confirmed content mapping does not match state DB"
    ]

    surface = ContentTargetAuthoringSurface(
        kind="wordpress_post_content",
        root_field="content",
        layouts=[
            ContentTargetAuthoringLayout(
                name="wordpress_post_content",
                fields=["title", "content_html"],
            )
        ],
    )
    contract = ContentTargetContract(
        environment="staging",
        object_id="1",
        url="https://ekologus.dev.proudsite.pl/current",
        post_type="post",
        rest_endpoint="posts",
        post_status="publish",
        modified="2026-09-11T00:00:00Z",
        authoring_surface=surface,
    )
    contract_digest = status._canonical_digest(contract.model_dump(mode="json"))
    target = ContentTargetMappingTarget(
        target_contract=contract,
        target_contract_digest=contract_digest,
        observation_evidence=ContentTargetObservationEvidence(
            evidence_id="ev_mapping_test",
            connector_id="wordpress_ekologus",
            object_id="1",
            post_type="post",
            url=contract.url,
            post_status="publish",
            modified=contract.modified,
            observed_at="2026-09-11T00:00:00Z",
        ),
    )
    components = [
        ContentTargetMappingComponent(
            component_id="document-title",
            kind="document_title",
            label="Tytuł",
            status="human_only",
            reason="Mapowanie wymaga potwierdzenia.",
            target_root_field="content",
            available_layouts=["wordpress_post_content"],
            source_fields=[ContentTargetMappingSourceField(key="wordpress_title", label="Tytuł")],
        ),
        ContentTargetMappingComponent(
            component_id="document-content",
            kind="document_content",
            label="Treść",
            status="human_only",
            reason="Mapowanie wymaga potwierdzenia.",
            target_root_field="content",
            available_layouts=["wordpress_post_content"],
            source_fields=[ContentTargetMappingSourceField(key="document_html", label="Treść")],
        ),
    ]
    revision = ContentTargetMappingRevision(revision_id=revision_id, content_digest=digest)
    binding_digest = status._canonical_digest(
        {
            "revision": revision.model_dump(mode="json"),
            "target_contract_digest": contract_digest,
            "components": [component.model_dump(mode="json") for component in components],
        }
    )
    preview = ContentTargetMappingPreview(
        work_item_id="work_item_current",
        revision=revision,
        status="ready_for_human_mapping",
        target=target,
        binding_digest=binding_digest,
        components=components,
    )
    command = ContentTargetMappingConfirmationCommand(
        expected_revision_digest=digest,
        expected_target_contract_digest=contract_digest,
        expected_binding_digest=binding_digest,
        confirmed_by="test",
        selections=[
            ContentTargetMappingSelection(
                component_id="document-title",
                layout_name="wordpress_post_content",
                field_bindings=[
                    ContentTargetMappingFieldBinding(
                        source_field="wordpress_title", target_field="title"
                    )
                ],
            ),
            ContentTargetMappingSelection(
                component_id="document-content",
                layout_name="wordpress_post_content",
                field_bindings=[
                    ContentTargetMappingFieldBinding(
                        source_field="document_html", target_field="content_html"
                    )
                ],
            ),
        ],
    )
    confirmation = new_content_target_mapping_confirmation(
        work_item_id="work_item_current",
        preview=preview,
        command=command,
        confirmation_number=1,
        created_at="2026-09-11T00:00:00+00:00",
    )
    payload = build_content_target_mapping_persisted_record(
        preview=preview,
        confirmation=confirmation,
    ).model_dump(mode="json")
    confirmation_id = payload["confirmation"]["confirmation_id"]
    confirmation_digest = payload["confirmation"]["confirmation_digest"]
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE content_target_mapping_confirmations "
            "(confirmation_id TEXT, work_item_id TEXT, revision_id TEXT, revision_digest TEXT, "
            "target_contract_digest TEXT, binding_digest TEXT, confirmation_number INTEGER, "
            "confirmation_digest TEXT, created_at TEXT, payload_json TEXT)"
        )
        connection.execute(
            "INSERT INTO content_target_mapping_confirmations VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                confirmation_id,
                "work_item_current",
                revision_id,
                digest,
                contract_digest,
                binding_digest,
                1,
                confirmation_digest,
                payload["confirmation"]["created_at"],
                json.dumps(payload),
            ),
        )

    assert status.validate_state_db([row], database) == []

    mutated_command = command.model_copy(update={"selections": command.selections[:1]})
    with pytest.raises(ValueError, match="pełnego dokumentu"):
        new_content_target_mapping_confirmation(
            work_item_id="work_item_current",
            preview=preview,
            command=mutated_command,
            confirmation_number=confirmation.confirmation_number,
            created_at=confirmation.created_at,
        )
    payload["confirmation"]["selections"] = payload["confirmation"]["selections"][:1]
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_target_mapping_confirmations SET payload_json = ?",
            (json.dumps(payload),),
        )
    assert status.validate_state_db([row], database) == [
        "/current: confirmed content mapping does not match state DB"
    ]

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_target_mapping_confirmations SET payload_json = ?",
            ("{",),
        )
    assert status.validate_state_db([row], database) == [
        "/current: confirmed content mapping does not match state DB"
    ]

    payload["version"] = 2
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE content_target_mapping_confirmations SET payload_json = ?",
            (json.dumps(payload),),
        )
    assert status.validate_state_db([row], database) == [
        "/current: confirmed content mapping does not match state DB"
    ]


def test_state_db_uri_escapes_path_query_characters(tmp_path: Path) -> None:
    revision_id = f"content_revision_{'0' * 32}"
    digest = "1" * 64
    database = tmp_path / "state?mode=memory.sqlite3"
    _write_state_db(database, revision_id, digest)

    assert status.validate_state_db([_current_row(revision_id, digest)], database) == []


def test_state_db_rejects_duplicate_execution_handoff(tmp_path: Path) -> None:
    revision_id = f"content_revision_{'7' * 32}"
    digest = "8" * 64
    handoff_id = "wordpress_draft_handoff_work_item_current_revision"
    database = tmp_path / "duplicate-execution.sqlite3"
    _write_state_db(database, revision_id, digest, handoff_id=handoff_id)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO content_wordpress_draft_execution_history VALUES (?, ?, ?, ?, ?)",
            ("work_item_current", handoff_id, "content_revision_other", "9" * 64, "{}"),
        )
    row = _current_row(revision_id, digest)
    row.update(
        {
            "delivery_status": "dev_draft_verified",
            "dev_execution_handoff_id": handoff_id,
            "dev_draft_post_id": "1991",
        }
    )

    assert status.validate_state_db([row], database) == [
        "/current: dev execution receipt does not match state DB"
    ]


def test_state_db_malformed_payloads_fail_closed(tmp_path: Path) -> None:
    revision_id = f"content_revision_{'1' * 32}"
    digest = "2" * 64

    revision_db = tmp_path / "malformed-revision.sqlite3"
    _write_state_db(revision_db, revision_id, digest)
    with sqlite3.connect(revision_db) as connection:
        connection.execute(
            "UPDATE content_draft_revisions SET payload_json = ?", ("{",)
        )
    assert status.validate_state_db([_current_row(revision_id, digest)], revision_db) == [
        "/current: revision payload does not match state DB",
        "/current: revision URL path does not match state DB",
    ]

    review_db = tmp_path / "malformed-review.sqlite3"
    _write_state_db(review_db, revision_id, digest)
    with sqlite3.connect(review_db) as connection:
        connection.execute(
            "UPDATE content_draft_revision_reviews SET payload_json = ?", ("{",)
        )
    assert status.validate_state_db([_current_row(revision_id, digest)], review_db) == [
        "/current: revision approval does not match state DB"
    ]

    semantic_db = tmp_path / "malformed-semantic.sqlite3"
    _write_state_db(semantic_db, revision_id, digest)
    with sqlite3.connect(semantic_db) as connection:
        connection.execute(
            "UPDATE content_semantic_reviews SET payload_json = ?", ("{",)
        )
    assert status.validate_state_db([_current_row(revision_id, digest)], semantic_db) == [
        "/current: semantic zero-findings status does not match state DB"
    ]

    execution_db = tmp_path / "malformed-execution.sqlite3"
    handoff_id = "wordpress_draft_handoff_work_item_current_revision"
    _write_state_db(execution_db, revision_id, digest, handoff_id=handoff_id)
    execution_row = _current_row(revision_id, digest)
    execution_row.update(
        {
            "delivery_status": "dev_draft_verified",
            "dev_execution_handoff_id": handoff_id,
            "dev_draft_post_id": "1991",
        }
    )
    with sqlite3.connect(execution_db) as connection:
        connection.execute(
            "UPDATE content_wordpress_draft_execution_history SET payload_json = ?", ("{",)
        )
    assert status.validate_state_db([execution_row], execution_db) == [
        "/current: dev execution receipt does not match state DB"
    ]


def test_state_db_shadowed_newer_records_fail_closed(tmp_path: Path) -> None:
    revision_id = f"content_revision_{'3' * 32}"
    digest = "4" * 64
    database = tmp_path / "shadowed.sqlite3"
    _write_state_db(database, revision_id, digest)
    newer_revision_id = f"content_revision_{'5' * 32}"
    newer_digest = "6" * 64
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO content_draft_revisions VALUES (?, ?, ?, ?, ?)",
            (newer_revision_id, "work_item_current", 2, newer_digest, "{"),
        )
        connection.execute(
            "INSERT INTO content_draft_revision_reviews VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision_newer",
                "work_item_current",
                revision_id,
                digest,
                2,
                "approved",
                "{",
            ),
        )
        connection.execute(
            "INSERT INTO content_semantic_reviews VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                revision_id,
                "work_item_current",
                digest,
                "wilq_semantic_content_review_v1",
                "2026-09-12T00:00:00+00:00",
                "semantic_review_newer",
                "{",
            ),
        )

    row = _current_row(revision_id, digest)
    errors = status.validate_state_db([row], database)

    assert "/current: current revision is not latest in state DB" in errors
    assert "/current: revision approval does not match state DB" in errors
    assert "/current: semantic zero-findings status does not match state DB" in errors


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
        "target_mapping_status": "",
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
              decision_id TEXT, work_item_id TEXT, revision_id TEXT,
              revision_digest TEXT, decision_number INTEGER, decision TEXT,
              payload_json TEXT
            );
            CREATE TABLE content_semantic_reviews (
              revision_id TEXT, work_item_id TEXT, revision_digest TEXT,
              criteria_version TEXT, created_at TEXT, review_id TEXT, payload_json TEXT
            );
            CREATE TABLE content_wordpress_draft_execution_history (
              work_item_id TEXT, handoff_id TEXT, revision_id TEXT,
              revision_digest TEXT, payload_json TEXT
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
                json.dumps(
                    {
                        "schema_version": "wilq_content_draft_revision_v1",
                        "revision_id": revision_id,
                        "work_item_id": "work_item_current",
                        "revision_number": 1,
                        "content_digest": digest,
                        "draft_package_id": "draft_package_current",
                        "draft_package_digest": "2" * 64,
                        "planning_digest": "3" * 64,
                        "final_canonical_url": "https://example.test/current",
                        "publish_ready": False,
                    }
                ),
            ),
        )
        connection.execute(
            "INSERT INTO content_draft_revision_reviews VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision_current",
                "work_item_current",
                revision_id,
                digest,
                1,
                "approved",
                json.dumps(
                    {
                        "decision_id": "decision_current",
                        "work_item_id": "work_item_current",
                        "revision_id": revision_id,
                        "revision_digest": digest,
                        "decision_number": 1,
                        "decision": "approved",
                    }
                ),
            ),
        )
        connection.execute(
            "INSERT INTO content_semantic_reviews VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                revision_id,
                "work_item_current",
                digest,
                "wilq_semantic_content_review_v1",
                "2026-09-11T00:00:00+00:00",
                "semantic_review_current",
                json.dumps(
                    {
                        "work_item_id": "work_item_current",
                        "revision_id": revision_id,
                        "revision_digest": digest,
                        "criteria_version": "wilq_semantic_content_review_v1",
                        "status": "reviewable",
                        "findings": [],
                    }
                ),
            ),
        )
        if handoff_id is not None:
            connection.execute(
                "INSERT INTO content_wordpress_draft_execution_history VALUES (?, ?, ?, ?, ?)",
                (
                    "work_item_current",
                    handoff_id,
                    revision_id,
                    digest,
                    json.dumps(
                        {
                            "status": "created",
                            "mode": "live",
                            "external_write_attempted": True,
                            "wordpress_post_id": "1991",
                            "endpoint": "posts",
                            "revision_binding": {
                                "work_item_id": "work_item_current",
                                "revision_id": revision_id,
                                "content_digest": digest,
                                "handoff_id": handoff_id,
                                "draft_package_id": "draft_package_current",
                                "draft_package_digest": "2" * 64,
                                "planning_digest": "3" * 64,
                                "approval_decision_id": "decision_current",
                                "final_canonical_url": "https://example.test/current",
                            },
                            "boundary": {
                                "live_write_enabled": True,
                                "live_adapter_configured": True,
                                "publish_allowed": False,
                                "destructive_update_allowed": False,
                            },
                            "expected_content_digest": digest,
                            "observed_content_digest": digest,
                            "expected_title_digest": "e" * 64,
                            "observed_title_digest": "e" * 64,
                        }
                    ),
                ),
            )
