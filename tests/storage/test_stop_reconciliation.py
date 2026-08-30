from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from wilq.codex.stop_reconciliation import (
    LEGACY_STOP_RECONCILIATION_ERROR,
    STOP_RECONCILIATION_EXPECTED_COUNT,
    StopReconciliationManifestError,
    StopReconciliationStorageError,
    apply_stop_reconciliation,
    create_stop_reconciliation_manifest,
    manifest_sha256,
    plan_stop_reconciliation,
    write_manifest,
)
from wilq.schemas import CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import LocalStateStore
from wilq.storage.local_state_stop_reconciliation import SqliteStopReconciliationSource
from wilq.storage.model_json import model_json
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION

SOURCE_FIXED_POINT = "test-source-fixed-point"
BATCH_ID = "run_s5_batch_20260824"
GENERATED_AT = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
STARTED_AT = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
RUN_IDS = tuple(
    f"codex_legacy_stop_{index:02d}" for index in range(STOP_RECONCILIATION_EXPECTED_COUNT)
)
NON_MANIFEST_ID = "codex_legacy_stop_outside_manifest"


def _seed_runs(path: Path, *, include_non_manifest: bool = True) -> LocalStateStore:
    store = LocalStateStore(path)
    for index, run_id in enumerate(RUN_IDS):
        started_at = STARTED_AT + timedelta(minutes=index)
        store.save_codex_run(
            CodexRun(
                id=run_id,
                hook="Stop",
                source="legacy_stop_route",
                status="started",
                model="gpt-5.6-sol",
                prompt_digest=f"{index + 1:064x}",
                started_at=started_at,
                deadline_at=started_at + timedelta(hours=1),
            )
        )
    if include_non_manifest:
        store.save_codex_run(
            CodexRun(
                id=NON_MANIFEST_ID,
                hook="Stop",
                status="started",
                started_at=STARTED_AT - timedelta(days=1),
            )
        )
    with sqlite3.connect(path) as connection:
        for index, run_id in enumerate(RUN_IDS):
            payload_json = connection.execute(
                "SELECT payload_json FROM codex_runs WHERE id = ?", (run_id,)
            ).fetchone()[0]
            payload = json.loads(payload_json)
            payload["legacy_retry_count"] = index
            payload["legacy_opaque_marker"] = f"opaque-{index:02d}"
            connection.execute(
                "UPDATE codex_runs SET payload_json = ? WHERE id = ?",
                (model_json(payload), run_id),
            )
    return store


def _backup(path: Path, destination: Path) -> None:
    with sqlite3.connect(path) as source, sqlite3.connect(destination) as target:
        source.backup(target)


def _downgrade_reconciliation_schema_to_v6(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE codex_stop_events_legacy")
        connection.execute("DROP TABLE codex_stop_reconciliation_batches")
        connection.execute("PRAGMA user_version = 6")


def _manifest(path: Path):
    return create_stop_reconciliation_manifest(
        SqliteStopReconciliationSource(path),
        run_ids=RUN_IDS,
        source_fixed_point=SOURCE_FIXED_POINT,
        generated_at=GENERATED_AT,
    )


def _apply(
    store: LocalStateStore,
    *,
    manifest: Any,
    backup_path: Path,
    batch_id: str = BATCH_ID,
):
    return apply_stop_reconciliation(
        store,
        manifest=manifest,
        batch_id=batch_id,
        backup_path=backup_path,
        mutation_authorized=True,
        expected_count=STOP_RECONCILIATION_EXPECTED_COUNT,
        expected_manifest_sha256=manifest.manifest_sha256,
    )


def _raw_runs(path: Path) -> dict[str, tuple[str, str]]:
    with sqlite3.connect(path) as connection:
        return {
            run_id: (started_at, payload_json)
            for run_id, started_at, payload_json in connection.execute(
                "SELECT id, started_at, payload_json FROM codex_runs ORDER BY id"
            ).fetchall()
        }


def _mutation_snapshot(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(path) as connection:
        return {
            "runs": connection.execute(
                "SELECT id, started_at, payload_json FROM codex_runs ORDER BY id"
            ).fetchall(),
            "batches": connection.execute(
                "SELECT * FROM codex_stop_reconciliation_batches ORDER BY batch_id"
            ).fetchall(),
            "legacy": connection.execute(
                "SELECT * FROM codex_stop_events_legacy ORDER BY batch_id, source_id"
            ).fetchall(),
            "audits": connection.execute("SELECT * FROM audit_events ORDER BY id").fetchall(),
        }


def _assert_only_status_and_error_changed(before: str, after: str) -> None:
    expected = json.loads(before)
    expected["status"] = "failed"
    expected["error"] = LEGACY_STOP_RECONCILIATION_ERROR
    assert json.loads(after) == expected
    assert json.loads(after)["completed_at"] == json.loads(before)["completed_at"]


def test_manifest_is_deterministic_exact_and_contains_raw_payload_digests_only(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "manifest.sqlite3"
    _seed_runs(state_path)

    first = _manifest(state_path)
    second = _manifest(state_path)

    assert first == second
    assert first.expected_count == STOP_RECONCILIATION_EXPECTED_COUNT == 20
    assert first.run_ids == tuple(sorted(RUN_IDS))
    assert len(first.payload_digests) == 20
    assert first.source_fixed_point == SOURCE_FIXED_POINT
    assert manifest_sha256(first) == first.manifest_sha256
    raw_rows = _raw_runs(state_path)
    for run_id in RUN_IDS:
        assert first.started_at[run_id] == raw_rows[run_id][0]
        assert (
            first.payload_digests[run_id]
            == hashlib.sha256(raw_rows[run_id][1].encode("utf-8")).hexdigest()
        )
    serialized = first.model_dump_json()
    assert "payload_json" not in serialized
    assert "gpt-5.6-sol" not in serialized
    assert "opaque-00" not in serialized

    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest_path, first)
    original = manifest_path.read_bytes()
    with pytest.raises(StopReconciliationManifestError, match="already exists"):
        write_manifest(manifest_path, first)
    assert manifest_path.read_bytes() == original


def test_manifest_rejects_non_exact_or_tampered_identity(tmp_path: Path) -> None:
    state_path = tmp_path / "manifest-validation.sqlite3"
    _seed_runs(state_path)
    source = SqliteStopReconciliationSource(state_path)

    with pytest.raises(StopReconciliationManifestError, match="exactly 20"):
        create_stop_reconciliation_manifest(
            source,
            run_ids=RUN_IDS[:-1],
            source_fixed_point=SOURCE_FIXED_POINT,
            generated_at=GENERATED_AT,
        )

    manifest = _manifest(state_path)
    duplicate = manifest.model_copy(
        update={"run_ids": (*manifest.run_ids[:-1], manifest.run_ids[-2])}
    )
    with pytest.raises(StopReconciliationManifestError, match="unique"):
        manifest_sha256(duplicate)
    tampered = manifest.model_copy(update={"source_fixed_point": "different-fixed-point"})
    with pytest.raises(StopReconciliationManifestError, match="digest"):
        manifest_sha256(tampered)


def test_manifest_rejects_secret_like_run_id_before_source_read() -> None:
    unsafe_run_id = "sk-test-run-id-000000000000"
    run_ids = (*[f"codex_legacy_stop_{index:02d}" for index in range(19)], unsafe_run_id)

    class SourceMustNotBeRead:
        def read_stop_reconciliation_rows(self, run_ids):
            raise AssertionError("unsafe manifest IDs must fail before source I/O")

    with pytest.raises(StopReconciliationManifestError, match="safe"):
        create_stop_reconciliation_manifest(
            SourceMustNotBeRead(),
            run_ids=run_ids,
            source_fixed_point=SOURCE_FIXED_POINT,
            generated_at=GENERATED_AT,
        )


def test_manifest_rejects_secret_like_source_fixed_point_before_source_read() -> None:
    run_ids = tuple(f"codex_legacy_stop_{index:02d}" for index in range(20))

    class SourceMustNotBeRead:
        def read_stop_reconciliation_rows(self, run_ids):
            raise AssertionError("unsafe source fixed points must fail before source I/O")

    with pytest.raises(StopReconciliationManifestError, match="source fixed point is not safe"):
        create_stop_reconciliation_manifest(
            SourceMustNotBeRead(),
            run_ids=run_ids,
            source_fixed_point="sk-test-source-fixed-point",
            generated_at=GENERATED_AT,
        )


@pytest.mark.parametrize("batch_id", ["run_sk-test", "run_" + ("a" * 197)])
def test_apply_rejects_unsafe_batch_id_before_applier(tmp_path: Path, batch_id: str) -> None:
    state_path = tmp_path / "stop-reconciliation-batch-id.sqlite3"
    _seed_runs(state_path)
    manifest = _manifest(state_path)

    class ApplierMustNotBeReached:
        def apply_stop_reconciliation(self, **kwargs):
            raise AssertionError("unsafe batch IDs must fail before the applier")

    with pytest.raises(StopReconciliationManifestError, match="batch ID is not safe"):
        apply_stop_reconciliation(
            ApplierMustNotBeReached(),
            manifest=manifest,
            batch_id=batch_id,
            backup_path=state_path,
            mutation_authorized=True,
            expected_count=STOP_RECONCILIATION_EXPECTED_COUNT,
            expected_manifest_sha256=manifest.manifest_sha256,
        )


def test_manifest_digest_is_safe_audit_lineage_even_when_digit_leading() -> None:
    assert redact_mapping({"manifest_digest": "0" * 64}) == {"manifest_digest": "0" * 64}


def test_apply_copies_exact_raw_rows_and_changes_only_status_and_error(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.sqlite3"
    backup_path = tmp_path / "backup.sqlite3"
    store = _seed_runs(state_path)
    before = _raw_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)

    receipt = _apply(store, manifest=manifest, backup_path=backup_path)

    assert receipt.status == "applied"
    assert receipt.copied_count == 20
    assert receipt.reconciled_count == 20
    assert receipt.already_reconciled_count == 0
    assert receipt.cas_lost_count == 0
    assert receipt.reconciled_run_ids == RUN_IDS
    assert receipt.rollback_result == "not_required"
    with sqlite3.connect(state_path) as connection:
        header = connection.execute(
            """
            SELECT batch_id, manifest_sha256, expected_count
            FROM codex_stop_reconciliation_batches
            """
        ).fetchone()
        copied = connection.execute(
            """
            SELECT batch_id, manifest_sha256, source_id, started_at,
                   payload_json, payload_sha256
            FROM codex_stop_events_legacy
            ORDER BY source_id
            """
        ).fetchall()
        audits = connection.execute(
            "SELECT id, payload_json FROM audit_events ORDER BY id"
        ).fetchall()
    assert header == (BATCH_ID, manifest.manifest_sha256, 20)
    assert len(copied) == 20
    for batch_id, digest, source_id, started_at, payload_json, payload_digest in copied:
        assert batch_id == BATCH_ID
        assert digest == manifest.manifest_sha256
        assert (started_at, payload_json) == before[source_id]
        assert payload_digest == hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    after = _raw_runs(state_path)
    for run_id in RUN_IDS:
        assert after[run_id][0] == before[run_id][0]
        _assert_only_status_and_error_changed(before[run_id][1], after[run_id][1])
    assert after[NON_MANIFEST_ID] == before[NON_MANIFEST_ID]
    assert len(audits) == 20
    assert len({audit_id for audit_id, _ in audits}) == 20
    assert all(audit_id.startswith("audit_codex_stop_reconciled_") for audit_id, _ in audits)
    for _, payload_json in audits:
        audit = json.loads(payload_json)
        assert audit["event_type"] == "codex_stop_reconciled"
        assert audit["details"]["manifest_digest"] == manifest.manifest_sha256


def test_dry_run_is_default_shape_and_does_not_mutate(tmp_path: Path) -> None:
    state_path = tmp_path / "dry-run.sqlite3"
    backup_path = tmp_path / "dry-run-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    before = _mutation_snapshot(state_path)

    receipt = plan_stop_reconciliation(
        store,
        manifest=manifest,
        batch_id=BATCH_ID,
        backup_path=backup_path,
        expected_count=20,
        expected_manifest_sha256=manifest.manifest_sha256,
    )

    assert receipt.status == "dry_run_ready"
    assert receipt.dry_run is True
    assert receipt.mutation_authorized is False
    assert receipt.would_copy_count == 20
    assert receipt.would_reconcile_run_ids == RUN_IDS
    assert receipt.rollback_result == "not_started"
    assert _mutation_snapshot(state_path) == before


def test_dry_run_rejects_unsupported_schema_before_classification(tmp_path: Path) -> None:
    state_path = tmp_path / "dry-run-v5.sqlite3"
    backup_path = tmp_path / "dry-run-v5-backup.sqlite3"
    _seed_runs(state_path)
    _downgrade_reconciliation_schema_to_v6(state_path)
    with sqlite3.connect(state_path) as connection:
        connection.execute("PRAGMA user_version = 5")
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    before = state_path.read_bytes()

    with pytest.raises(StopReconciliationManifestError, match="schema version 6, 7 or 8"):
        plan_stop_reconciliation(
            LocalStateStore(state_path),
            manifest=manifest,
            batch_id=BATCH_ID,
            backup_path=backup_path,
            expected_count=20,
            expected_manifest_sha256=manifest.manifest_sha256,
        )

    assert state_path.read_bytes() == before


def test_apply_rejects_unsupported_schema_before_transaction(tmp_path: Path) -> None:
    state_path = tmp_path / "apply-v5.sqlite3"
    backup_path = tmp_path / "apply-v5-backup.sqlite3"
    _seed_runs(state_path)
    _downgrade_reconciliation_schema_to_v6(state_path)
    with sqlite3.connect(state_path) as connection:
        connection.execute("PRAGMA user_version = 5")
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    before = state_path.read_bytes()

    with pytest.raises(
        StopReconciliationManifestError,
        match="schema version 6, 7 or 8",
    ) as failure:
        _apply(store=LocalStateStore(state_path), manifest=manifest, backup_path=backup_path)

    assert failure.value.rollback_result == "not_started"
    assert state_path.read_bytes() == before


def test_apply_gates_and_distinct_snapshot_fail_before_any_write(tmp_path: Path) -> None:
    state_path = tmp_path / "gates.sqlite3"
    backup_path = tmp_path / "gates-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    before = _mutation_snapshot(state_path)

    with pytest.raises(StopReconciliationManifestError, match="authorization"):
        apply_stop_reconciliation(
            store,
            manifest=manifest,
            batch_id=BATCH_ID,
            backup_path=backup_path,
            mutation_authorized=False,
            expected_count=20,
            expected_manifest_sha256=manifest.manifest_sha256,
        )
    with pytest.raises(StopReconciliationManifestError, match="count"):
        apply_stop_reconciliation(
            store,
            manifest=manifest,
            batch_id=BATCH_ID,
            backup_path=backup_path,
            mutation_authorized=True,
            expected_count=19,
            expected_manifest_sha256=manifest.manifest_sha256,
        )
    with pytest.raises(StopReconciliationManifestError, match="digest"):
        apply_stop_reconciliation(
            store,
            manifest=manifest,
            batch_id=BATCH_ID,
            backup_path=backup_path,
            mutation_authorized=True,
            expected_count=20,
            expected_manifest_sha256="0" * 64,
        )
    with pytest.raises(StopReconciliationManifestError, match="distinct"):
        _apply(store, manifest=manifest, backup_path=state_path)

    symlink_path = tmp_path / "state-alias.sqlite3"
    symlink_path.symlink_to(state_path)
    with pytest.raises(StopReconciliationManifestError, match="distinct"):
        _apply(store, manifest=manifest, backup_path=symlink_path)

    hardlink_path = tmp_path / "state-hardlink.sqlite3"
    os.link(state_path, hardlink_path)
    with pytest.raises(StopReconciliationManifestError, match="distinct"):
        _apply(store, manifest=manifest, backup_path=hardlink_path)
    assert _mutation_snapshot(state_path) == before


def test_missing_or_tampered_backup_is_blocked_without_mutation(tmp_path: Path) -> None:
    state_path = tmp_path / "backup-gates.sqlite3"
    backup_path = tmp_path / "tampered-backup.sqlite3"
    timestamp_backup_path = tmp_path / "timestamp-backup.sqlite3"
    store = _seed_runs(state_path)
    manifest = _manifest(state_path)
    before = _mutation_snapshot(state_path)

    with pytest.raises(StopReconciliationManifestError, match="backup"):
        _apply(store, manifest=manifest, backup_path=tmp_path / "missing.sqlite3")
    _backup(state_path, backup_path)
    with sqlite3.connect(backup_path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM codex_runs WHERE id = ?", (RUN_IDS[0],)
            ).fetchone()[0]
        )
        payload["legacy_opaque_marker"] = "valid-but-digest-tampered"
        connection.execute(
            "UPDATE codex_runs SET payload_json = ? WHERE id = ?",
            (model_json(payload), RUN_IDS[0]),
        )
    with pytest.raises(StopReconciliationManifestError, match="payload digest"):
        _apply(store, manifest=manifest, backup_path=backup_path)
    _backup(state_path, timestamp_backup_path)
    with sqlite3.connect(timestamp_backup_path) as connection:
        persisted = connection.execute(
            "SELECT started_at FROM codex_runs WHERE id = ?", (RUN_IDS[0],)
        ).fetchone()[0]
        connection.execute(
            "UPDATE codex_runs SET started_at = ? WHERE id = ?",
            (persisted.replace("+00:00", "Z"), RUN_IDS[0]),
        )
    with pytest.raises(StopReconciliationManifestError, match="timestamp differs"):
        _apply(store, manifest=manifest, backup_path=timestamp_backup_path)
    assert _mutation_snapshot(state_path) == before


def test_cas_loss_does_not_mutate_or_audit_loser_and_non_manifest_run(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "cas-loss.sqlite3"
    backup_path = tmp_path / "cas-loss-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    with sqlite3.connect(state_path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM codex_runs WHERE id = ?", (RUN_IDS[0],)
            ).fetchone()[0]
        )
        payload["status"] = "completed"
        payload["completed_at"] = (STARTED_AT + timedelta(days=1)).isoformat()
        connection.execute(
            "UPDATE codex_runs SET payload_json = ? WHERE id = ?",
            (model_json(payload), RUN_IDS[0]),
        )
    before_apply = _raw_runs(state_path)

    receipt = _apply(store, manifest=manifest, backup_path=backup_path)

    assert receipt.status == "partial"
    assert receipt.reconciled_count == 19
    assert receipt.cas_lost_run_ids == (RUN_IDS[0],)
    assert receipt.cas_lost_count == 1
    after = _raw_runs(state_path)
    assert after[RUN_IDS[0]] == before_apply[RUN_IDS[0]]
    assert after[NON_MANIFEST_ID] == before_apply[NON_MANIFEST_ID]
    with sqlite3.connect(state_path) as connection:
        audit_payloads = [
            json.loads(payload_json)
            for (payload_json,) in connection.execute("SELECT payload_json FROM audit_events")
        ]
        copied_count = connection.execute(
            "SELECT COUNT(*) FROM codex_stop_events_legacy"
        ).fetchone()[0]
    assert len(audit_payloads) == 19
    assert {audit["details"]["run_id"] for audit in audit_payloads} == set(RUN_IDS[1:])
    assert copied_count == 20


def test_persisted_timestamp_change_alone_loses_cas_without_audit(tmp_path: Path) -> None:
    state_path = tmp_path / "timestamp-cas-loss.sqlite3"
    backup_path = tmp_path / "timestamp-cas-loss-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    with sqlite3.connect(state_path) as connection:
        persisted = connection.execute(
            "SELECT started_at FROM codex_runs WHERE id = ?", (RUN_IDS[0],)
        ).fetchone()[0]
        connection.execute(
            "UPDATE codex_runs SET started_at = ? WHERE id = ?",
            (persisted.replace("+00:00", "Z"), RUN_IDS[0]),
        )
    losing_before = _raw_runs(state_path)[RUN_IDS[0]]

    receipt = _apply(store, manifest=manifest, backup_path=backup_path)

    assert receipt.status == "partial"
    assert receipt.cas_lost_run_ids == (RUN_IDS[0],)
    assert _raw_runs(state_path)[RUN_IDS[0]] == losing_before
    with sqlite3.connect(state_path) as connection:
        audit_payloads = [
            json.loads(payload_json)
            for (payload_json,) in connection.execute("SELECT payload_json FROM audit_events")
        ]
    assert {audit["details"]["run_id"] for audit in audit_payloads} == set(RUN_IDS[1:])


def test_repeated_batch_is_byte_idempotent_without_retry_or_duplicate_audit(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "idempotent.sqlite3"
    backup_path = tmp_path / "idempotent-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)

    first = _apply(store, manifest=manifest, backup_path=backup_path)
    after_first = _mutation_snapshot(state_path)
    second = _apply(store, manifest=manifest, backup_path=backup_path)

    assert first.reconciled_count == 20
    assert second.status == "applied"
    assert second.copied_count == 0
    assert second.already_copied_count == 20
    assert second.reconciled_count == 0
    assert second.already_reconciled_count == 20
    assert second.cas_lost_count == 0
    assert _mutation_snapshot(state_path) == after_first


def test_audit_identity_is_redaction_stable_for_safe_components(tmp_path: Path) -> None:
    state_path = tmp_path / "redaction-stable-audit.sqlite3"
    backup_path = tmp_path / "redaction-stable-audit-backup.sqlite3"
    store = LocalStateStore(state_path)
    run_ids = ("A" * 31, "B" * 31, *[f"codex_collision_{index:02d}" for index in range(18)])
    for index, run_id in enumerate(run_ids):
        store.save_codex_run(
            CodexRun(
                id=run_id,
                hook="Stop",
                status="started",
                started_at=STARTED_AT + timedelta(minutes=index),
            )
        )
    _backup(state_path, backup_path)
    manifest = create_stop_reconciliation_manifest(
        SqliteStopReconciliationSource(state_path),
        run_ids=run_ids,
        source_fixed_point=SOURCE_FIXED_POINT,
        generated_at=GENERATED_AT,
    )

    first = _apply(store, manifest=manifest, backup_path=backup_path, batch_id="run_s5-batch")
    second = _apply(store, manifest=manifest, backup_path=backup_path, batch_id="run_s5-batch")

    assert first.status == "applied"
    assert first.reconciled_count == 20
    assert second.status == "applied"
    assert second.reconciled_count == 0
    assert second.already_reconciled_count == 20
    with sqlite3.connect(state_path) as connection:
        audits = connection.execute("SELECT id, payload_json FROM audit_events").fetchall()
    assert len(audits) == 20
    assert len({audit_id for audit_id, _ in audits}) == 20
    assert {json.loads(payload)["details"]["run_id"] for _, payload in audits} == set(run_ids)


def test_eleventh_audit_failure_rolls_back_batch_copies_runs_and_audits(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "rollback.sqlite3"
    backup_path = tmp_path / "rollback-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    before_runs = _raw_runs(state_path)
    rejected_run_id = RUN_IDS[10]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            f"""
            CREATE TRIGGER reject_eleventh_s5_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.payload_json LIKE '%{rejected_run_id}%'
            BEGIN
              SELECT RAISE(FAIL, 'forced eleventh s5 audit failure');
            END
            """  # nosec B608 -- the audit ID is a fixed synthetic test identifier.
        )

    with pytest.raises(StopReconciliationStorageError, match="storage") as failure:
        _apply(store, manifest=manifest, backup_path=backup_path)

    assert failure.value.rollback_result == "rolled_back"
    assert _raw_runs(state_path) == before_runs
    with sqlite3.connect(state_path) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM codex_stop_reconciliation_batches").fetchone()[
                0
            ]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM codex_stop_events_legacy").fetchone()[0] == 0
        )
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 0


def test_failed_first_apply_rolls_v7_schema_expansion_back_to_v6(tmp_path: Path) -> None:
    state_path = tmp_path / "v6-rollback.sqlite3"
    backup_path = tmp_path / "v6-rollback-backup.sqlite3"
    store = _seed_runs(state_path)
    _downgrade_reconciliation_schema_to_v6(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    before_runs = _raw_runs(state_path)
    rejected_run_id = RUN_IDS[10]
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            f"""
            CREATE TRIGGER reject_v6_s5_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.payload_json LIKE '%{rejected_run_id}%'
            BEGIN
              SELECT RAISE(FAIL, 'forced v6 s5 audit failure');
            END
            """  # nosec B608 -- the audit ID is a fixed synthetic test identifier.
        )

    with pytest.raises(StopReconciliationStorageError) as failure:
        _apply(store, manifest=manifest, backup_path=backup_path)

    assert failure.value.rollback_result == "rolled_back"
    assert _raw_runs(state_path) == before_runs
    with sqlite3.connect(state_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
        reconciliation_tables = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name IN (?, ?)
            """,
            ("codex_stop_reconciliation_batches", "codex_stop_events_legacy"),
        ).fetchall()
        assert reconciliation_tables == []
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 0


def test_first_authorized_apply_atomically_expands_v6_and_reconciles(tmp_path: Path) -> None:
    state_path = tmp_path / "v6-success.sqlite3"
    backup_path = tmp_path / "v6-success-backup.sqlite3"
    store = _seed_runs(state_path)
    _downgrade_reconciliation_schema_to_v6(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)

    receipt = _apply(store, manifest=manifest, backup_path=backup_path)

    assert receipt.status == "applied"
    assert receipt.copied_count == receipt.reconciled_count == 20
    with sqlite3.connect(state_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SQLITE_SCHEMA_VERSION
        assert (
            connection.execute("SELECT COUNT(*) FROM codex_stop_reconciliation_batches").fetchone()[
                0
            ]
            == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM codex_stop_events_legacy").fetchone()[0] == 20
        )
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 20


def test_existing_batch_identity_cannot_be_rebound(tmp_path: Path) -> None:
    state_path = tmp_path / "batch-identity.sqlite3"
    backup_path = tmp_path / "batch-identity-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    _apply(store, manifest=manifest, backup_path=backup_path)
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            """
            UPDATE codex_stop_reconciliation_batches
            SET manifest_sha256 = ? WHERE batch_id = ?
            """,
            ("0" * 64, BATCH_ID),
        )
    before = _mutation_snapshot(state_path)

    with pytest.raises(StopReconciliationManifestError, match="Batch identity") as failure:
        _apply(store, manifest=manifest, backup_path=backup_path)

    assert failure.value.rollback_result == "rolled_back"
    assert _mutation_snapshot(state_path) == before


def test_same_manifest_cannot_be_copied_under_an_alternate_batch_id(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "alternate-batch.sqlite3"
    backup_path = tmp_path / "alternate-batch-backup.sqlite3"
    store = _seed_runs(state_path)
    _backup(state_path, backup_path)
    manifest = _manifest(state_path)
    _apply(store, manifest=manifest, backup_path=backup_path)
    before = _mutation_snapshot(state_path)

    with pytest.raises(StopReconciliationManifestError, match="another") as failure:
        _apply(
            store,
            manifest=manifest,
            backup_path=backup_path,
            batch_id="run_s5_alternate_batch",
        )

    assert failure.value.rollback_result == "rolled_back"
    assert _mutation_snapshot(state_path) == before


def test_existing_v6_store_gains_reconciliation_schema_without_data_loss(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "v6.sqlite3"
    run = CodexRun(
        id="codex_v6_opaque",
        hook="Stop",
        status="started",
        started_at=STARTED_AT,
    )
    payload = run.model_dump(mode="json")
    payload["legacy_opaque_marker"] = "keep-exactly"
    payload_json = model_json(payload)
    with sqlite3.connect(state_path) as connection:
        connection.executescript(
            """
            CREATE TABLE codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            CREATE TABLE codex_stop_events (
              id TEXT PRIMARY KEY,
              received_at TEXT NOT NULL,
              event_type TEXT NOT NULL,
              contract_version INTEGER NOT NULL
            );
            CREATE INDEX idx_codex_stop_events_received_at_id
            ON codex_stop_events (received_at, id);
            CREATE TABLE audit_events (
              id TEXT PRIMARY KEY,
              action_id TEXT,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            PRAGMA user_version = 6;
            """
        )
        connection.execute(
            "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
            (run.id, run.started_at.isoformat(), payload_json),
        )
        connection.execute(
            """
            INSERT INTO codex_stop_events (id, received_at, event_type, contract_version)
            VALUES ('stop_v6', '2026-08-20T12:01:00+00:00', 'stop', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO audit_events (id, created_at, payload_json)
            VALUES ('audit_v6', '2026-08-20T12:02:00+00:00', '{"legacy":true}')
            """
        )
    before = (
        sqlite3.connect(state_path)
        .execute("SELECT id, started_at, payload_json FROM codex_runs")
        .fetchall()
    )

    assert LocalStateStore(state_path).status()["schema_version"] == SQLITE_SCHEMA_VERSION

    with sqlite3.connect(state_path) as connection:
        after = connection.execute("SELECT id, started_at, payload_json FROM codex_runs").fetchall()
        stop_events = connection.execute("SELECT * FROM codex_stop_events").fetchall()
        audits = connection.execute("SELECT * FROM audit_events").fetchall()
        tables = {
            name
            for (name,) in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name LIKE 'codex_stop_%'
                """
            ).fetchall()
        }
        reconciliation_counts = (
            connection.execute("SELECT COUNT(*) FROM codex_stop_reconciliation_batches").fetchone()[
                0
            ],
            connection.execute("SELECT COUNT(*) FROM codex_stop_events_legacy").fetchone()[0],
        )
    assert after == before
    assert stop_events == [("stop_v6", "2026-08-20T12:01:00+00:00", "stop", 1)]
    assert audits == [("audit_v6", None, "2026-08-20T12:02:00+00:00", '{"legacy":true}')]
    assert "codex_stop_reconciliation_batches" in tables
    assert "codex_stop_events_legacy" in tables
    assert reconciliation_counts == (0, 0)
