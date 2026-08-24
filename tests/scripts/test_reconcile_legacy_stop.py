from __future__ import annotations

import json
import sqlite3
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.reconcile_legacy_stop import main
from wilq.codex.stop_reconciliation import STOP_RECONCILIATION_EXPECTED_COUNT, read_manifest
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore
from wilq.storage.model_json import model_json

GENERATED_AT = "2026-08-24T12:00:00+00:00"
BATCH_ID = "run_s5_batch_cli"


def _seed(path: Path) -> tuple[LocalStateStore, list[str]]:
    store = LocalStateStore(path)
    run_ids = [f"codex_cli_stop_{index:02d}" for index in range(STOP_RECONCILIATION_EXPECTED_COUNT)]
    for index, run_id in enumerate(run_ids):
        store.save_codex_run(
            CodexRun(
                id=run_id,
                hook="Stop",
                status="started",
                started_at=datetime(2026, 8, 20, tzinfo=UTC) + timedelta(minutes=index),
            )
        )
    return store, run_ids


def _seed_v6(path: Path) -> list[str]:
    run_ids = [
        f"codex_cli_v6_stop_{index:02d}" for index in range(STOP_RECONCILIATION_EXPECTED_COUNT)
    ]
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
        for index, run_id in enumerate(run_ids):
            started_at = datetime(2026, 8, 20, tzinfo=UTC) + timedelta(minutes=index)
            payload = CodexRun(
                id=run_id,
                hook="Stop",
                status="started",
                started_at=started_at,
            ).model_dump(mode="json")
            payload["legacy_marker"] = f"v6-{index}"
            connection.execute(
                "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
                (run_id, started_at.isoformat(), model_json(payload)),
            )
        connection.execute("PRAGMA user_version = 6")
    return run_ids


def _seed_complete_v6(path: Path) -> list[str]:
    _, run_ids = _seed(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE codex_stop_events_legacy")
        connection.execute("DROP TABLE codex_stop_reconciliation_batches")
        connection.execute("PRAGMA user_version = 6")
    return run_ids


def _backup(path: Path, destination: Path) -> None:
    with sqlite3.connect(path) as source, sqlite3.connect(destination) as target:
        source.backup(target)


def _manifest_argv(state_path: Path, manifest_path: Path, run_ids: list[str]) -> list[str]:
    argv = [
        "manifest",
        "--state-db",
        str(state_path),
        "--output",
        str(manifest_path),
        "--source-fixed-point",
        "ca3a7304",
        "--generated-at",
        GENERATED_AT,
    ]
    for run_id in run_ids:
        argv.extend(("--run-id", run_id))
    return argv


def _apply_argv(
    state_path: Path,
    manifest_path: Path,
    backup_path: Path,
    *,
    authorize: bool = False,
) -> list[str]:
    manifest = read_manifest(manifest_path)
    argv = [
        "apply",
        "--state-db",
        str(state_path),
        "--manifest",
        str(manifest_path),
        "--manifest-sha256",
        manifest.manifest_sha256,
        "--expected-count",
        "20",
        "--backup",
        str(backup_path),
        "--batch-id",
        BATCH_ID,
    ]
    if authorize:
        argv.append("--authorize-mutation")
    return argv


def _snapshot(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(path) as connection:
        return {
            "runs": connection.execute("SELECT * FROM codex_runs ORDER BY id").fetchall(),
            "batches": connection.execute(
                "SELECT * FROM codex_stop_reconciliation_batches ORDER BY batch_id"
            ).fetchall(),
            "legacy": connection.execute(
                "SELECT * FROM codex_stop_events_legacy ORDER BY source_id"
            ).fetchall(),
            "audits": connection.execute("SELECT * FROM audit_events ORDER BY id").fetchall(),
        }


def test_manifest_cli_is_strictly_read_only_for_v6_source(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "cli-v6-state.sqlite3"
    run_ids = _seed_v6(state_path)
    manifest_path = tmp_path / "manifest.json"
    before_bytes = state_path.read_bytes()
    before_mode = stat.S_IMODE(state_path.stat().st_mode)

    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "manifest_created"
    assert read_manifest(manifest_path).expected_count == 20
    assert state_path.read_bytes() == before_bytes
    assert stat.S_IMODE(state_path.stat().st_mode) == before_mode
    with sqlite3.connect(f"{state_path.resolve().as_uri()}?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
        assert (
            connection.execute(
                """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'codex_stop_events_legacy'
            """
            ).fetchone()
            is None
        )


def test_apply_cli_defaults_to_dry_run_and_leaves_state_unchanged(
    tmp_path: Path,
    capsys,
) -> None:
    state_path = tmp_path / "cli-dry-run.sqlite3"
    backup_path = tmp_path / "cli-dry-run-backup.sqlite3"
    _, run_ids = _seed(state_path)
    _backup(state_path, backup_path)
    manifest_path = tmp_path / "dry-run-manifest.json"
    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0
    capsys.readouterr()
    before = _snapshot(state_path)

    assert main(_apply_argv(state_path, manifest_path, backup_path)) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "dry_run_ready"
    assert output["dry_run"] is True
    assert output["mutation_authorized"] is False
    assert output["would_copy_count"] == 20
    assert _snapshot(state_path) == before


def test_valid_default_dry_run_is_byte_exact_on_complete_v6_store(
    tmp_path: Path,
    capsys,
) -> None:
    state_path = tmp_path / "cli-valid-v6-dry-run.sqlite3"
    backup_path = tmp_path / "cli-valid-v6-dry-run-backup.sqlite3"
    run_ids = _seed_complete_v6(state_path)
    _backup(state_path, backup_path)
    manifest_path = tmp_path / "valid-v6-dry-run-manifest.json"
    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0
    capsys.readouterr()
    before_bytes = state_path.read_bytes()
    before_mode = stat.S_IMODE(state_path.stat().st_mode)

    assert main(_apply_argv(state_path, manifest_path, backup_path)) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "dry_run_ready"
    assert output["would_copy_count"] == 20
    assert state_path.read_bytes() == before_bytes
    assert stat.S_IMODE(state_path.stat().st_mode) == before_mode
    with sqlite3.connect(f"{state_path.resolve().as_uri()}?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
        assert (
            connection.execute(
                """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name IN (?, ?)
            """,
                ("codex_stop_reconciliation_batches", "codex_stop_events_legacy"),
            ).fetchall()
            == []
        )


def test_apply_cli_blocks_mismatched_gate_without_mutation(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "cli-blocked-v6.sqlite3"
    backup_path = tmp_path / "cli-blocked-v6-backup.sqlite3"
    run_ids = _seed_v6(state_path)
    _backup(state_path, backup_path)
    manifest_path = tmp_path / "blocked-manifest.json"
    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0
    capsys.readouterr()
    argv = _apply_argv(state_path, manifest_path, backup_path)
    argv[argv.index("--expected-count") + 1] = "19"
    before = state_path.read_bytes()

    assert main(argv) == 2

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["rollback_result"] == "not_started"
    assert state_path.read_bytes() == before

    digest_argv = _apply_argv(state_path, manifest_path, backup_path)
    digest_argv[digest_argv.index("--manifest-sha256") + 1] = "0" * 64
    assert main(digest_argv) == 2
    digest_output = json.loads(capsys.readouterr().out)
    assert digest_output["status"] == "blocked"
    assert digest_output["rollback_result"] == "not_started"
    assert state_path.read_bytes() == before


def test_authorized_apply_cli_returns_exact_success_receipt(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "cli-apply.sqlite3"
    backup_path = tmp_path / "cli-apply-backup.sqlite3"
    _, run_ids = _seed(state_path)
    _backup(state_path, backup_path)
    manifest_path = tmp_path / "apply-manifest.json"
    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0
    capsys.readouterr()

    assert main(_apply_argv(state_path, manifest_path, backup_path, authorize=True)) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "applied"
    assert output["copied_count"] == 20
    assert output["reconciled_count"] == 20
    assert output["cas_lost_count"] == 0
    assert output["rollback_result"] == "not_required"


def test_apply_cli_reports_cas_loss_as_typed_partial_result(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "cli-partial.sqlite3"
    backup_path = tmp_path / "cli-partial-backup.sqlite3"
    store, run_ids = _seed(state_path)
    _backup(state_path, backup_path)
    manifest_path = tmp_path / "partial-manifest.json"
    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0
    capsys.readouterr()
    losing = store.get_codex_run(run_ids[0])
    assert losing is not None
    store.save_codex_run(losing.model_copy(update={"status": "completed"}))

    assert main(_apply_argv(state_path, manifest_path, backup_path, authorize=True)) == 3

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "partial"
    assert output["cas_lost_count"] == 1
    assert output["cas_lost_run_ids"] == [run_ids[0]]


def test_apply_cli_reports_rolled_back_storage_failure_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    state_path = tmp_path / "cli-rollback.sqlite3"
    backup_path = tmp_path / "cli-rollback-backup.sqlite3"
    _, run_ids = _seed(state_path)
    _backup(state_path, backup_path)
    manifest_path = tmp_path / "rollback-manifest.json"
    assert main(_manifest_argv(state_path, manifest_path, run_ids)) == 0
    capsys.readouterr()
    rejected_run_id = run_ids[10]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            f"""
            CREATE TRIGGER reject_cli_s5_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.payload_json LIKE '%{rejected_run_id}%'
            BEGIN
              SELECT RAISE(FAIL, 'forced cli audit failure');
            END
            """  # nosec B608 -- fixed synthetic test identifier.
        )
    before = _snapshot(state_path)

    assert main(_apply_argv(state_path, manifest_path, backup_path, authorize=True)) == 4

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "failed"
    assert output["rollback_result"] == "rolled_back"
    assert _snapshot(state_path) == before
