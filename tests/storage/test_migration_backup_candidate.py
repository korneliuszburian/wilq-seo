from __future__ import annotations

import json
import os
import sqlite3
import stat
from hashlib import sha256
from pathlib import Path

import pytest

from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage import migration_backup_candidate
from wilq.storage.local_state import LocalStateStore
from wilq.storage.migration_backup_candidate import (
    MigrationBackupCandidateError,
    build_migration_backup_candidate,
    restore_migration_backup_candidate,
    verify_migration_backup_candidate,
)
from wilq.storage.sqlite_schema_inventory import (
    SqliteSchemaInventory,
    canonical_sqlite_schema_inventory_json,
    inspect_sqlite_schema,
)

APPLICATION_SHA256 = "a" * 64
SEED_SHA256 = "b" * 64


def _accepted_inventory(path: Path) -> SqliteSchemaInventory:
    baseline = inspect_sqlite_schema(
        path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )
    accepted = inspect_sqlite_schema(
        path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
        expected_identity_sha256=baseline.identity.identity_sha256,
    )
    assert accepted.compatibility.status == "exact_post_s5"
    return accepted


def _source(path: Path) -> SqliteSchemaInventory:
    LocalStateStore(path).status()
    ContentWorkflowStore(path).list_draft_revisions("missing")
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO content_draft_revisions (
              revision_id, work_item_id, revision_number, base_revision_id,
              content_digest, created_at, payload_json
            ) VALUES ('revision_d2', 'work_d2', 1, NULL, 'digest', '2026-08-24', '{}')
            """
        )
    return _accepted_inventory(path)


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _metadata_without_atime(path: Path) -> tuple[int, int, int, int, int, int, int]:
    metadata = path.stat()
    return (
        metadata.st_mode,
        metadata.st_mtime_ns,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_ino,
        metadata.st_nlink,
        metadata.st_size,
    )


def test_atomic_candidate_binds_exact_source_backup_manifest_and_restore_readback(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"

    receipt = build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )

    backup_path = candidate_directory / "wilq.sqlite3"
    manifest_path = candidate_directory / "manifest.json"
    assert {path.name for path in candidate_directory.iterdir()} == {
        "manifest.json",
        "wilq.sqlite3",
    }
    assert receipt.status == "generation_valid"
    assert receipt.manifest.accepted_inventory == accepted_inventory
    assert receipt.manifest.source.source_bytes.sha256 == sha256(source_before).hexdigest()
    assert receipt.manifest.backup.source_bytes.sha256 == _file_sha256(backup_path)
    assert receipt.manifest.source == receipt.manifest.backup
    assert receipt.manifest.backup == receipt.manifest.restore_readback
    assert receipt.manifest.source.identity == accepted_inventory.identity
    assert receipt.manifest.source.identity.application_sha256 == APPLICATION_SHA256
    assert receipt.manifest.source.identity.seed_sha256 == SEED_SHA256
    assert (
        receipt.manifest.source.inventory_sha256
        == sha256(
            canonical_sqlite_schema_inventory_json(accepted_inventory).encode("utf-8")
        ).hexdigest()
    )
    assert receipt.manifest.source.integrity_check == "ok"
    assert receipt.manifest_file.sha256 == _file_sha256(manifest_path)
    assert receipt.manifest_file.size_bytes == manifest_path.stat().st_size
    assert (
        verify_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            expected_manifest_sha256=receipt.manifest_file.sha256,
        )
        == receipt
    )
    assert backup_path.read_bytes() == source_before
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before
    assert stat.S_IMODE(candidate_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(manifest_path.stat().st_mode) == 0o600
    serialized_manifest = manifest_path.read_text(encoding="utf-8")
    assert str(source_path) not in serialized_manifest
    assert str(candidate_directory) not in serialized_manifest
    assert not any(
        Path(f"{path}{suffix}").exists()
        for path in (source_path, backup_path)
        for suffix in ("-journal", "-shm", "-wal")
    )


@pytest.mark.parametrize("tampered_name", ["wilq.sqlite3", "manifest.json"])
def test_tampered_candidate_fails_verification_and_restore_without_touching_source(
    tmp_path: Path,
    tampered_name: str,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"
    receipt = build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )
    tampered_path = candidate_directory / tampered_name
    tampered_path.write_bytes(tampered_path.read_bytes() + b"tampered")
    restore_path = tmp_path / "restore" / "wilq.sqlite3"

    with pytest.raises(MigrationBackupCandidateError):
        verify_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            expected_manifest_sha256=receipt.manifest_file.sha256,
        )
    with pytest.raises(MigrationBackupCandidateError):
        restore_migration_backup_candidate(
            candidate_directory=candidate_directory,
            destination_path=restore_path,
            expected_manifest_sha256=receipt.manifest_file.sha256,
        )

    assert not restore_path.exists()
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before
    assert _accepted_inventory(source_path) == accepted_inventory


@pytest.mark.parametrize("tampered_name", ["wilq.sqlite3", "manifest.json"])
@pytest.mark.parametrize("alias_kind", ["symlink", "hardlink"])
def test_candidate_file_alias_is_tampering_even_when_every_byte_matches(
    tmp_path: Path,
    tampered_name: str,
    alias_kind: str,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"
    receipt = build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )
    tampered_path = candidate_directory / tampered_name
    alias_target = tmp_path / "aliases" / tampered_name
    alias_target.parent.mkdir()
    alias_target.write_bytes(tampered_path.read_bytes())
    tampered_path.unlink()
    if alias_kind == "symlink":
        tampered_path.symlink_to(alias_target)
    else:
        os.link(alias_target, tampered_path)
    restore_path = tmp_path / "restore" / "wilq.sqlite3"

    with pytest.raises(MigrationBackupCandidateError):
        verify_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            expected_manifest_sha256=receipt.manifest_file.sha256,
        )
    with pytest.raises(MigrationBackupCandidateError):
        restore_migration_backup_candidate(
            candidate_directory=candidate_directory,
            destination_path=restore_path,
            expected_manifest_sha256=receipt.manifest_file.sha256,
        )

    assert not restore_path.exists()
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before
    assert _accepted_inventory(source_path) == accepted_inventory


def test_restore_publishes_an_exact_private_copy_only_at_a_fresh_alternate_path(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"
    candidate = build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )
    restore_path = tmp_path / "restore" / "wilq.sqlite3"

    restored = restore_migration_backup_candidate(
        candidate_directory=candidate_directory,
        destination_path=restore_path,
        expected_manifest_sha256=candidate.manifest_file.sha256,
    )

    assert restored.status == "restored"
    assert restored.manifest_file == candidate.manifest_file
    assert restored.destination == candidate.manifest.restore_readback
    assert restore_path.read_bytes() == source_before
    assert stat.S_IMODE(restore_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(restore_path.parent.stat().st_mode) == 0o700
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before
    with pytest.raises(MigrationBackupCandidateError, match="fresh"):
        restore_migration_backup_candidate(
            candidate_directory=candidate_directory,
            destination_path=restore_path,
            expected_manifest_sha256=candidate.manifest_file.sha256,
        )
    assert restore_path.read_bytes() == source_before


def test_unverified_or_stale_d1_authority_never_creates_a_candidate(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    unverified_inventory = inspect_sqlite_schema(
        source_path,
        application_sha256=APPLICATION_SHA256,
        seed_sha256=SEED_SHA256,
    )
    candidate_directory = tmp_path / "unverified-candidate"

    with pytest.raises(MigrationBackupCandidateError, match="accepted exact D1"):
        build_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            accepted_inventory=unverified_inventory,
        )
    assert not candidate_directory.exists()

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            """
            INSERT INTO audit_events (id, action_id, created_at, payload_json)
            VALUES ('audit_after_d1', 'action_d2', '2026-08-24', '{}')
            """
        )
    stale_generation = source_path.read_bytes()
    stale_metadata = _metadata_without_atime(source_path)
    stale_candidate_directory = tmp_path / "stale-candidate"

    with pytest.raises(MigrationBackupCandidateError, match="D1 inventory"):
        build_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=stale_candidate_directory,
            accepted_inventory=accepted_inventory,
        )
    assert source_path.read_bytes() == stale_generation
    assert _metadata_without_atime(source_path) == stale_metadata
    assert not stale_candidate_directory.exists()
    assert not list(tmp_path.glob(".wilq-migration-backup-*"))


def test_every_candidate_and_restore_staging_byte_is_private_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    observed_destination_modes: list[int] = []
    original_copy = migration_backup_candidate.shutil.copyfileobj

    def observe_destination_mode(source, destination, length=0) -> None:
        observed_destination_modes.append(stat.S_IMODE(os.fstat(destination.fileno()).st_mode))
        original_copy(source, destination, length)

    monkeypatch.setattr(
        migration_backup_candidate.shutil,
        "copyfileobj",
        observe_destination_mode,
    )
    candidate_directory = tmp_path / "candidate"
    candidate = build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )
    restore_migration_backup_candidate(
        candidate_directory=candidate_directory,
        destination_path=tmp_path / "world-readable-parent" / "wilq.sqlite3",
        expected_manifest_sha256=candidate.manifest_file.sha256,
    )

    assert observed_destination_modes
    assert set(observed_destination_modes) == {0o600}


def test_rehashed_manifest_cannot_rebind_the_restore_readback(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"
    build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )
    manifest_path = candidate_directory / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["restore_readback"]["source_bytes"]["sha256"] = "c" * 64
    tampered_manifest = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    manifest_path.write_bytes(tampered_manifest)
    manifest_path.chmod(0o600)

    with pytest.raises(MigrationBackupCandidateError, match="restore"):
        verify_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            expected_manifest_sha256=sha256(tampered_manifest).hexdigest(),
        )

    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before


def test_publication_failure_after_staging_leaves_no_candidate_or_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"
    original_link = migration_backup_candidate.os.link

    def fail_manifest_commit(
        source: object,
        destination: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        if Path(destination).name == "manifest.json":
            raise OSError("injected manifest commit failure")
        original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(migration_backup_candidate.os, "link", fail_manifest_commit)

    with pytest.raises(MigrationBackupCandidateError, match="publish"):
        build_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            accepted_inventory=accepted_inventory,
        )

    assert not candidate_directory.exists()
    assert not list(tmp_path.glob(".wilq-migration-backup-*"))
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before


def test_schema_readable_source_with_failed_integrity_never_becomes_a_candidate(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    _source(source_path)
    with sqlite3.connect(source_path) as connection:
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        root_page = int(
            connection.execute(
                "SELECT rootpage FROM sqlite_schema WHERE name = 'content_draft_revisions'"
            ).fetchone()[0]
        )
    corrupted = bytearray(source_path.read_bytes())
    corrupted[(root_page - 1) * page_size] = 0
    source_path.write_bytes(corrupted)
    accepted_corrupt_inventory = _accepted_inventory(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"

    with pytest.raises(MigrationBackupCandidateError):
        build_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            accepted_inventory=accepted_corrupt_inventory,
        )

    assert not candidate_directory.exists()
    assert not list(tmp_path.glob(".wilq-migration-backup-*"))
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before


def test_candidate_alias_swap_during_d1_readback_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "source" / "wilq.sqlite3"
    accepted_inventory = _source(source_path)
    source_before = source_path.read_bytes()
    source_metadata_before = _metadata_without_atime(source_path)
    candidate_directory = tmp_path / "candidate"
    candidate = build_migration_backup_candidate(
        source_path=source_path,
        candidate_directory=candidate_directory,
        accepted_inventory=accepted_inventory,
    )
    backup_path = candidate_directory / "wilq.sqlite3"
    alias_target = tmp_path / "alias.sqlite3"
    alias_target.write_bytes(backup_path.read_bytes())
    original_inspect = migration_backup_candidate.inspect_sqlite_schema
    swapped = False

    def swap_before_d1_readback(path, **kwargs):
        nonlocal swapped
        if path == backup_path and not swapped:
            swapped = True
            backup_path.unlink()
            backup_path.symlink_to(alias_target)
        return original_inspect(path, **kwargs)

    monkeypatch.setattr(
        migration_backup_candidate,
        "inspect_sqlite_schema",
        swap_before_d1_readback,
    )

    with pytest.raises(MigrationBackupCandidateError, match="independent|changed"):
        verify_migration_backup_candidate(
            source_path=source_path,
            candidate_directory=candidate_directory,
            expected_manifest_sha256=candidate.manifest_file.sha256,
        )

    assert swapped is True
    assert source_path.read_bytes() == source_before
    assert _metadata_without_atime(source_path) == source_metadata_before
