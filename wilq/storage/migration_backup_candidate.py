from __future__ import annotations

import os
import re
import shutil
import sqlite3
import stat
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from wilq.storage.model_json import model_json
from wilq.storage.sqlite_schema_inventory import (
    SqliteSchemaIdentity,
    SqliteSchemaInventory,
    SqliteSchemaInventoryError,
    canonical_sqlite_schema_inventory_json,
    inspect_sqlite_schema,
)

MIGRATION_BACKUP_MANIFEST_CONTRACT: Literal["wilq_migration_backup_manifest_v1"] = (
    "wilq_migration_backup_manifest_v1"
)
MIGRATION_BACKUP_RECEIPT_CONTRACT: Literal["wilq_migration_backup_receipt_v1"] = (
    "wilq_migration_backup_receipt_v1"
)
MIGRATION_BACKUP_RESTORE_RECEIPT_CONTRACT: Literal["wilq_migration_backup_restore_receipt_v1"] = (
    "wilq_migration_backup_restore_receipt_v1"
)

_BACKUP_FILENAME = "wilq.sqlite3"
_MANIFEST_FILENAME = "manifest.json"
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", strict=True)]
NonNegativeInteger = Annotated[int, Field(ge=0, strict=True)]


class MigrationBackupCandidateError(RuntimeError):
    """A migration backup candidate could not be proven without source mutation."""


class _FrozenContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MigrationBackupFileProof(_FrozenContractModel):
    size_bytes: NonNegativeInteger
    sha256: Sha256Digest


class MigrationBackupReadback(_FrozenContractModel):
    source_bytes: MigrationBackupFileProof
    inventory_sha256: Sha256Digest
    identity: SqliteSchemaIdentity
    integrity_check: Literal["ok"] = "ok"


class MigrationBackupManifest(_FrozenContractModel):
    contract_version: Literal["wilq_migration_backup_manifest_v1"] = (
        MIGRATION_BACKUP_MANIFEST_CONTRACT
    )
    accepted_inventory: SqliteSchemaInventory
    source: MigrationBackupReadback
    backup: MigrationBackupReadback
    restore_readback: MigrationBackupReadback


class MigrationBackupCandidateReceipt(_FrozenContractModel):
    contract_version: Literal["wilq_migration_backup_receipt_v1"] = (
        MIGRATION_BACKUP_RECEIPT_CONTRACT
    )
    status: Literal["generation_valid"] = "generation_valid"
    manifest_file: MigrationBackupFileProof
    manifest: MigrationBackupManifest


class MigrationBackupRestoreReceipt(_FrozenContractModel):
    contract_version: Literal["wilq_migration_backup_restore_receipt_v1"] = (
        MIGRATION_BACKUP_RESTORE_RECEIPT_CONTRACT
    )
    status: Literal["restored"] = "restored"
    manifest_file: MigrationBackupFileProof
    destination: MigrationBackupReadback


@dataclass(frozen=True)
class _SealedFileIdentity:
    device: int
    inode: int
    mode: int
    link_count: int
    size_bytes: int
    modified_at_ns: int
    changed_at_ns: int


def build_migration_backup_candidate(
    *,
    source_path: Path,
    candidate_directory: Path,
    accepted_inventory: SqliteSchemaInventory,
) -> MigrationBackupCandidateReceipt:
    """Build and atomically seal one exact SQLite migration backup candidate."""

    _accepted_identity(accepted_inventory)
    _require_fresh_candidate_path(candidate_directory)
    source = _resolved_source(source_path)
    source_before = _readback(source, accepted_inventory)
    if source_before.source_bytes != _file_proof(source):
        raise MigrationBackupCandidateError("Accepted source byte proof is not current")

    staging_directory: Path | None = None
    try:
        staging_directory = _create_private_staging_directory(candidate_directory.parent)
        backup_path = staging_directory / _BACKUP_FILENAME
        manifest_path = staging_directory / _MANIFEST_FILENAME
        restore_stage = staging_directory / ".restore-readback.sqlite3"

        _copy_exact_file(source, backup_path)
        backup_readback = _readback(backup_path, accepted_inventory)
        _copy_exact_file(backup_path, restore_stage)
        try:
            restore_readback = _readback(restore_stage, accepted_inventory)
        except Exception:
            with suppress(OSError):
                restore_stage.unlink(missing_ok=True)
            raise
        try:
            restore_stage.unlink(missing_ok=True)
        except OSError as exc:
            raise MigrationBackupCandidateError(
                "Migration backup restore readback staging cleanup failed"
            ) from exc

        source_after = _readback(source, accepted_inventory)
        if source_after != source_before:
            raise MigrationBackupCandidateError(
                "SQLite source changed while the migration backup candidate was built"
            )
        manifest = MigrationBackupManifest(
            accepted_inventory=accepted_inventory,
            source=source_before,
            backup=backup_readback,
            restore_readback=restore_readback,
        )
        _write_private_file(manifest_path, model_json(manifest).encode("utf-8"))
        manifest_file = _file_proof(manifest_path)
        _sync_directory(staging_directory)
        receipt = verify_migration_backup_candidate(
            source_path=source,
            candidate_directory=staging_directory,
            expected_manifest_sha256=manifest_file.sha256,
        )
        _publish_candidate_directory(staging_directory, candidate_directory)
        staging_directory = None
    except Exception:
        if staging_directory is not None:
            shutil.rmtree(staging_directory, ignore_errors=True)
        raise
    return receipt


def verify_migration_backup_candidate(
    *,
    source_path: Path,
    candidate_directory: Path,
    expected_manifest_sha256: str,
) -> MigrationBackupCandidateReceipt:
    """Verify the sealed candidate against its external hash and current source generation."""

    source = _resolved_source(source_path)
    manifest, manifest_file, backup_path = _verified_candidate(
        candidate_directory,
        expected_manifest_sha256,
    )
    if _file_proof(source) != manifest.source.source_bytes:
        raise MigrationBackupCandidateError("Migration backup source generation differs")
    source_before = _readback(source, manifest.accepted_inventory)
    source_after = _readback(source, manifest.accepted_inventory)
    if source_before != source_after:
        raise MigrationBackupCandidateError(
            "SQLite source changed while the migration backup candidate was verified"
        )
    if source_before != manifest.source:
        raise MigrationBackupCandidateError("Migration backup source generation differs")
    return MigrationBackupCandidateReceipt(
        manifest_file=manifest_file,
        manifest=manifest,
    )


def restore_migration_backup_candidate(
    *,
    candidate_directory: Path,
    destination_path: Path,
    expected_manifest_sha256: str,
) -> MigrationBackupRestoreReceipt:
    """Restore a sealed candidate to one fresh alternate path after full verification."""

    _require_fresh_destination(destination_path)
    manifest, manifest_file, backup_path = _verified_candidate(
        candidate_directory,
        expected_manifest_sha256,
    )
    _require_private_restore_parent(destination_path.parent)
    descriptor: int | None = None
    staging_path: Path | None = None
    try:
        descriptor, staging_name = tempfile.mkstemp(
            dir=destination_path.parent,
            prefix=f".{destination_path.name}.",
            suffix=".staging",
        )
        staging_path = Path(staging_name)
        os.close(descriptor)
        descriptor = None
        staging_path.unlink()
    except OSError as exc:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)
        if staging_path is not None:
            with suppress(OSError):
                staging_path.unlink(missing_ok=True)
        raise MigrationBackupCandidateError(
            "Migration backup restore staging file cannot be prepared"
        ) from exc
    if staging_path is None:
        raise MigrationBackupCandidateError("Migration backup restore staging path is unavailable")
    published = False
    try:
        _copy_exact_file(backup_path, staging_path)
        destination_readback = _readback(staging_path, manifest.accepted_inventory)
        if destination_readback != manifest.restore_readback:
            raise MigrationBackupCandidateError("Migration backup restore readback differs")
        _verified_candidate(candidate_directory, expected_manifest_sha256)
        try:
            os.link(staging_path, destination_path)
        except FileExistsError as exc:
            raise MigrationBackupCandidateError(
                "Migration backup restore destination must be fresh"
            ) from exc
        published = True
        try:
            staging_path.unlink()
        except OSError as exc:
            raise MigrationBackupCandidateError(
                "Migration backup restore staging cleanup failed"
            ) from exc
        _sync_directory(destination_path.parent)
    except Exception:
        if published:
            with suppress(OSError):
                destination_path.unlink()
        with suppress(OSError):
            staging_path.unlink()
        raise
    return MigrationBackupRestoreReceipt(
        manifest_file=manifest_file,
        destination=destination_readback,
    )


def _verified_candidate(
    candidate_directory: Path,
    expected_manifest_sha256: str,
) -> tuple[MigrationBackupManifest, MigrationBackupFileProof, Path]:
    _require_sha256(expected_manifest_sha256, "expected_manifest_sha256")
    backup_path, manifest_path = _candidate_files(candidate_directory)
    manifest_payload, manifest_identity = _read_sealed_payload(manifest_path)
    manifest_file = _payload_proof(manifest_payload)
    if manifest_file.sha256 != expected_manifest_sha256:
        raise MigrationBackupCandidateError("Migration backup manifest digest differs")
    try:
        manifest = MigrationBackupManifest.model_validate_json(manifest_payload)
    except (ValidationError, ValueError) as exc:
        raise MigrationBackupCandidateError("Migration backup manifest is invalid") from exc
    _accepted_identity(manifest.accepted_inventory)
    if manifest.source != manifest.backup or manifest.backup != manifest.restore_readback:
        raise MigrationBackupCandidateError("Migration backup restore readback differs")
    backup, backup_identity = _readback_sealed_candidate(
        backup_path,
        manifest.accepted_inventory,
    )
    if backup != manifest.backup:
        raise MigrationBackupCandidateError("Migration backup file proof differs")
    _candidate_files(candidate_directory)
    if (
        _sealed_file_identity(backup_path) != backup_identity
        or _sealed_file_identity(manifest_path) != manifest_identity
    ):
        raise MigrationBackupCandidateError("Migration backup candidate files changed")
    return manifest, manifest_file, backup_path


def _accepted_identity(inventory: SqliteSchemaInventory) -> tuple[str, str, str]:
    application_sha256 = inventory.identity.application_sha256
    seed_sha256 = inventory.identity.seed_sha256
    expected_identity_sha256 = inventory.compatibility.expected_identity_sha256
    if (
        inventory.compatibility.status != "exact_post_s5"
        or inventory.compatibility.reasons
        or application_sha256 is None
        or seed_sha256 is None
        or expected_identity_sha256 != inventory.identity.identity_sha256
    ):
        raise MigrationBackupCandidateError(
            "An accepted exact D1 SQLite schema inventory is required"
        )
    return application_sha256, seed_sha256, expected_identity_sha256


def _readback(
    path: Path,
    accepted_inventory: SqliteSchemaInventory,
) -> MigrationBackupReadback:
    application_sha256, seed_sha256, expected_identity_sha256 = _accepted_identity(
        accepted_inventory
    )
    try:
        inventory = inspect_sqlite_schema(
            path,
            application_sha256=application_sha256,
            seed_sha256=seed_sha256,
            expected_identity_sha256=expected_identity_sha256,
        )
        if inventory != accepted_inventory:
            raise MigrationBackupCandidateError(
                "SQLite readback differs from the accepted D1 inventory"
            )
        _require_integrity_check(path)
    except MigrationBackupCandidateError:
        raise
    except (OSError, sqlite3.Error, SqliteSchemaInventoryError, ValueError) as exc:
        raise MigrationBackupCandidateError("SQLite candidate readback failed") from exc
    inventory_sha256 = sha256(
        canonical_sqlite_schema_inventory_json(inventory).encode("utf-8")
    ).hexdigest()
    return MigrationBackupReadback(
        source_bytes=MigrationBackupFileProof(
            size_bytes=inventory.source_bytes.size_bytes,
            sha256=inventory.source_bytes.sha256,
        ),
        inventory_sha256=inventory_sha256,
        identity=inventory.identity,
    )


def _readback_sealed_candidate(
    path: Path,
    accepted_inventory: SqliteSchemaInventory,
) -> tuple[MigrationBackupReadback, _SealedFileIdentity]:
    before = _sealed_file_identity(path)
    readback = _readback(path, accepted_inventory)
    after = _sealed_file_identity(path)
    if after != before:
        raise MigrationBackupCandidateError("Migration backup candidate files changed")
    return readback, before


def _require_integrity_check(path: Path) -> None:
    resolved = path.resolve(strict=True)
    uri = f"{resolved.as_uri()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.execute("PRAGMA query_only = ON")
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    if rows != [("ok",)]:
        raise MigrationBackupCandidateError("SQLite integrity check failed")


def _resolved_source(path: Path) -> Path:
    try:
        source = path.resolve(strict=True)
    except OSError as exc:
        raise MigrationBackupCandidateError("SQLite migration source is required") from exc
    if not source.is_file():
        raise MigrationBackupCandidateError("SQLite migration source must be a regular file")
    return source


def _require_fresh_candidate_path(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise MigrationBackupCandidateError("Migration backup candidate path must be fresh")


def _create_private_staging_directory(parent: Path) -> Path:
    try:
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".wilq-migration-backup-", dir=parent))
    except OSError as exc:
        raise MigrationBackupCandidateError(
            "Migration backup staging directory cannot be created"
        ) from exc
    staging.chmod(0o700)
    return staging


def _publish_candidate_directory(staging: Path, destination: Path) -> None:
    destination_created = False
    try:
        destination.mkdir(mode=0o700)
        destination_created = True
        destination.chmod(0o700)
        staging_backup = staging / _BACKUP_FILENAME
        staging_manifest = staging / _MANIFEST_FILENAME
        os.link(
            staging_backup,
            destination / _BACKUP_FILENAME,
            follow_symlinks=False,
        )
        staging_backup.unlink()
        os.link(
            staging_manifest,
            destination / _MANIFEST_FILENAME,
            follow_symlinks=False,
        )
        staging_manifest.unlink()
        staging.rmdir()
        _sync_directory(destination)
        _sync_directory(destination.parent)
    except (OSError, MigrationBackupCandidateError) as exc:
        if destination_created:
            shutil.rmtree(destination, ignore_errors=True)
        raise MigrationBackupCandidateError(
            "Migration backup candidate cannot be published atomically"
        ) from exc


def _candidate_files(candidate_directory: Path) -> tuple[Path, Path]:
    if candidate_directory.is_symlink() or not candidate_directory.is_dir():
        raise MigrationBackupCandidateError("Migration backup candidate directory is required")
    try:
        directory_mode = stat.S_IMODE(candidate_directory.lstat().st_mode)
    except OSError as exc:
        raise MigrationBackupCandidateError(
            "Migration backup candidate directory cannot be inspected"
        ) from exc
    if directory_mode != 0o700:
        raise MigrationBackupCandidateError("Migration backup candidate directory is not private")
    try:
        entries = {entry.name for entry in candidate_directory.iterdir()}
    except OSError as exc:
        raise MigrationBackupCandidateError(
            "Migration backup candidate directory cannot be inspected"
        ) from exc
    if entries != {_BACKUP_FILENAME, _MANIFEST_FILENAME}:
        raise MigrationBackupCandidateError("Migration backup candidate files are incomplete")
    backup_path = candidate_directory / _BACKUP_FILENAME
    manifest_path = candidate_directory / _MANIFEST_FILENAME
    for candidate_file in (backup_path, manifest_path):
        _sealed_file_identity(candidate_file)
    return backup_path, manifest_path


def _read_sealed_payload(path: Path) -> tuple[bytes, _SealedFileIdentity]:
    path_before = _sealed_file_identity(path)
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        descriptor_before = _sealed_identity_from_stat(os.fstat(descriptor))
        if descriptor_before != path_before:
            raise MigrationBackupCandidateError("Migration backup candidate files changed")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        descriptor_after = _sealed_identity_from_stat(os.fstat(descriptor))
    except MigrationBackupCandidateError:
        raise
    except OSError as exc:
        raise MigrationBackupCandidateError(
            "Migration backup candidate file cannot be read safely"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    path_after = _sealed_file_identity(path)
    if descriptor_after != path_before or path_after != path_before:
        raise MigrationBackupCandidateError("Migration backup candidate files changed")
    return b"".join(chunks), path_before


def _sealed_file_identity(path: Path) -> _SealedFileIdentity:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise MigrationBackupCandidateError(
            "Migration backup candidate file cannot be inspected"
        ) from exc
    return _sealed_identity_from_stat(metadata)


def _sealed_identity_from_stat(metadata: os.stat_result) -> _SealedFileIdentity:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise MigrationBackupCandidateError(
            "Migration backup candidate files must be private independent regular files"
        )
    return _SealedFileIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        link_count=metadata.st_nlink,
        size_bytes=metadata.st_size,
        modified_at_ns=metadata.st_mtime_ns,
        changed_at_ns=metadata.st_ctime_ns,
    )


def _require_fresh_destination(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise MigrationBackupCandidateError("Migration backup restore destination must be fresh")


def _require_private_restore_parent(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata = path.lstat()
    except OSError as exc:
        raise MigrationBackupCandidateError(
            "Migration backup restore destination parent cannot be inspected"
        ) from exc
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise MigrationBackupCandidateError(
            "Migration backup restore destination parent must be private"
        )


def _copy_exact_file(source: Path, destination: Path) -> None:
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        created = True
        os.fchmod(descriptor, 0o600)
        with source.open("rb") as source_file, os.fdopen(descriptor, "wb") as destination_file:
            descriptor = None
            shutil.copyfileobj(source_file, destination_file, length=1024 * 1024)
            destination_file.flush()
            os.fsync(destination_file.fileno())
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            destination.unlink(missing_ok=True)
        raise MigrationBackupCandidateError("SQLite candidate file cannot be copied") from exc


def _write_private_file(path: Path, payload: bytes) -> None:
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        created = True
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as destination:
            descriptor = None
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            path.unlink(missing_ok=True)
        raise MigrationBackupCandidateError("Migration backup manifest cannot be written") from exc


def _file_proof(path: Path) -> MigrationBackupFileProof:
    try:
        digest = sha256()
        size_bytes = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                size_bytes += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise MigrationBackupCandidateError("Migration backup file cannot be hashed") from exc
    return MigrationBackupFileProof(size_bytes=size_bytes, sha256=digest.hexdigest())


def _payload_proof(payload: bytes) -> MigrationBackupFileProof:
    return MigrationBackupFileProof(
        size_bytes=len(payload),
        sha256=sha256(payload).hexdigest(),
    )


def _require_sha256(value: str, label: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise MigrationBackupCandidateError(f"{label} must be a lowercase SHA-256 digest")


def _sync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise MigrationBackupCandidateError("Migration backup directory cannot be synced") from exc


__all__ = [
    "MIGRATION_BACKUP_MANIFEST_CONTRACT",
    "MIGRATION_BACKUP_RECEIPT_CONTRACT",
    "MIGRATION_BACKUP_RESTORE_RECEIPT_CONTRACT",
    "MigrationBackupCandidateError",
    "MigrationBackupCandidateReceipt",
    "MigrationBackupFileProof",
    "MigrationBackupManifest",
    "MigrationBackupReadback",
    "MigrationBackupRestoreReceipt",
    "build_migration_backup_candidate",
    "restore_migration_backup_candidate",
    "verify_migration_backup_candidate",
]
