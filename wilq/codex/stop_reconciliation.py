from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from wilq.security.redaction import redact_value

STOP_RECONCILIATION_CONTRACT = "codex_stop_reconciliation_manifest_v1"
STOP_RECONCILIATION_EXPECTED_COUNT = 20
LEGACY_STOP_RECONCILIATION_ERROR = "reconciled_interrupted_before_terminal_commit"
_BATCH_ID_RE = re.compile(r"^run_[A-Za-z0-9_-]+$")
_SOURCE_FIXED_POINT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

RunId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
]
BatchId = Annotated[
    str,
    StringConstraints(min_length=5, max_length=200, pattern=r"^run_[A-Za-z0-9_-]+$"),
]
SourceFixedPoint = Annotated[
    str,
    StringConstraints(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
RawPayloadSha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PersistedTimestamp = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class StopReconciliationManifestError(ValueError):
    """Raised before apply, or after rolling back a manifest-bound transaction."""

    def __init__(
        self,
        message: str,
        *,
        rollback_result: Literal["not_started", "rolled_back"] = "not_started",
    ) -> None:
        super().__init__(message)
        self.rollback_result = rollback_result


class StopReconciliationStorageError(RuntimeError):
    """Raised when a storage failure prevents the manifest operation from committing."""

    def __init__(
        self,
        message: str,
        *,
        rollback_result: Literal["not_started", "rolled_back"],
    ) -> None:
        super().__init__(message)
        self.rollback_result = rollback_result


class StopReconciliationSourceRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: RunId
    started_at: PersistedTimestamp
    status: Literal["started", "completed", "failed", "blocked"]
    payload_json: str = Field(min_length=1)
    payload_sha256: RawPayloadSha256


class StopReconciliationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: Literal["codex_stop_reconciliation_manifest_v1"] = (
        "codex_stop_reconciliation_manifest_v1"
    )
    source_fixed_point: SourceFixedPoint
    generated_at: AwareDatetime
    expected_count: Literal[20] = 20
    run_ids: tuple[RunId, ...] = Field(
        min_length=STOP_RECONCILIATION_EXPECTED_COUNT,
        max_length=STOP_RECONCILIATION_EXPECTED_COUNT,
    )
    started_at: dict[RunId, PersistedTimestamp]
    payload_digests: dict[RunId, RawPayloadSha256]
    manifest_sha256: RawPayloadSha256

    @model_validator(mode="after")
    def validate_exact_shape(self) -> StopReconciliationManifest:
        _validate_manifest_shape(self)
        return self


class StopReconciliationDryRunReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: Literal["codex_stop_reconciliation_dry_run_v1"] = (
        "codex_stop_reconciliation_dry_run_v1"
    )
    status: Literal["dry_run_ready", "dry_run_partial"]
    dry_run: Literal[True] = True
    mutation_authorized: Literal[False] = False
    batch_id: BatchId
    manifest_sha256: RawPayloadSha256
    expected_count: Literal[20] = 20
    would_copy_count: int = Field(ge=0)
    already_copied_count: int = Field(ge=0)
    would_reconcile_count: int = Field(ge=0)
    already_reconciled_count: int = Field(ge=0)
    cas_lost_count: int = Field(ge=0)
    would_reconcile_run_ids: tuple[RunId, ...]
    already_reconciled_run_ids: tuple[RunId, ...]
    cas_lost_run_ids: tuple[RunId, ...]
    backup_verified: Literal[True] = True
    rollback_result: Literal["not_started"] = "not_started"


class StopReconciliationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: Literal["codex_stop_reconciliation_receipt_v1"] = (
        "codex_stop_reconciliation_receipt_v1"
    )
    status: Literal["applied", "partial"]
    dry_run: Literal[False] = False
    mutation_authorized: Literal[True] = True
    batch_id: BatchId
    manifest_sha256: RawPayloadSha256
    expected_count: Literal[20] = 20
    copied_count: int = Field(ge=0)
    already_copied_count: int = Field(ge=0)
    reconciled_count: int = Field(ge=0)
    already_reconciled_count: int = Field(ge=0)
    cas_lost_count: int = Field(ge=0)
    reconciled_run_ids: tuple[RunId, ...]
    already_reconciled_run_ids: tuple[RunId, ...]
    cas_lost_run_ids: tuple[RunId, ...]
    rollback_result: Literal["not_required"] = "not_required"


class StopReconciliationFailureReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: Literal["codex_stop_reconciliation_failure_v1"] = (
        "codex_stop_reconciliation_failure_v1"
    )
    status: Literal["blocked", "failed"]
    error: str
    rollback_result: Literal["not_started", "rolled_back"]


class StopReconciliationSource(Protocol):
    def read_stop_reconciliation_rows(
        self,
        run_ids: Sequence[str],
    ) -> list[StopReconciliationSourceRow]: ...


class StopReconciliationApplier(Protocol):
    def plan_stop_reconciliation(
        self,
        *,
        manifest: StopReconciliationManifest,
        batch_id: BatchId,
        backup_path: Path,
        expected_count: int,
        expected_manifest_sha256: str,
    ) -> StopReconciliationDryRunReceipt: ...

    def apply_stop_reconciliation(
        self,
        *,
        manifest: StopReconciliationManifest,
        batch_id: BatchId,
        backup_path: Path,
        mutation_authorized: bool,
        expected_count: int,
        expected_manifest_sha256: str,
    ) -> StopReconciliationReceipt: ...


def create_stop_reconciliation_manifest(
    source: StopReconciliationSource,
    *,
    run_ids: Sequence[str],
    source_fixed_point: SourceFixedPoint,
    generated_at: datetime,
) -> StopReconciliationManifest:
    normalized_ids = tuple(sorted(run_ids))
    if (
        len(normalized_ids) != STOP_RECONCILIATION_EXPECTED_COUNT
        or len(set(normalized_ids)) != STOP_RECONCILIATION_EXPECTED_COUNT
    ):
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest must contain exactly 20 unique run IDs"
        )
    _validate_safe_source_fixed_point(source_fixed_point)
    for run_id in normalized_ids:
        _validate_safe_run_id(run_id)
    rows = source.read_stop_reconciliation_rows(normalized_ids)
    rows_by_id = {row.run_id: row for row in rows}
    if len(rows_by_id) != len(rows) or set(rows_by_id) != set(normalized_ids):
        raise StopReconciliationManifestError(
            "Stop reconciliation source rows do not match the exact manifest IDs"
        )
    if any(row.status != "started" for row in rows):
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest requires every run to be started"
        )
    for row in rows:
        digest = hashlib.sha256(row.payload_json.encode("utf-8")).hexdigest()
        if digest != row.payload_sha256:
            raise StopReconciliationManifestError(
                "Stop reconciliation source payload digest is invalid"
            )
    try:
        unsigned = StopReconciliationManifest(
            source_fixed_point=source_fixed_point,
            generated_at=generated_at,
            run_ids=normalized_ids,
            started_at={run_id: rows_by_id[run_id].started_at for run_id in normalized_ids},
            payload_digests={
                run_id: rows_by_id[run_id].payload_sha256 for run_id in normalized_ids
            },
            manifest_sha256="0" * 64,
        )
    except StopReconciliationManifestError:
        raise
    except ValueError as exc:
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest input is invalid"
        ) from exc
    return unsigned.model_copy(update={"manifest_sha256": _calculate_manifest_sha256(unsigned)})


def plan_stop_reconciliation(
    applier: StopReconciliationApplier,
    *,
    manifest: StopReconciliationManifest,
    batch_id: BatchId,
    backup_path: Path,
    expected_count: int,
    expected_manifest_sha256: str,
) -> StopReconciliationDryRunReceipt:
    validate_stop_reconciliation_apply_identity(
        manifest,
        batch_id=batch_id,
        expected_count=expected_count,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    return applier.plan_stop_reconciliation(
        manifest=manifest,
        batch_id=batch_id,
        backup_path=backup_path,
        expected_count=expected_count,
        expected_manifest_sha256=expected_manifest_sha256,
    )


def apply_stop_reconciliation(
    applier: StopReconciliationApplier,
    *,
    manifest: StopReconciliationManifest,
    batch_id: BatchId,
    backup_path: Path,
    mutation_authorized: bool,
    expected_count: int,
    expected_manifest_sha256: str,
) -> StopReconciliationReceipt:
    validate_stop_reconciliation_apply_identity(
        manifest,
        batch_id=batch_id,
        expected_count=expected_count,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if mutation_authorized is not True:
        raise StopReconciliationManifestError(
            "Stop reconciliation requires explicit mutation authorization"
        )
    return applier.apply_stop_reconciliation(
        manifest=manifest,
        batch_id=batch_id,
        backup_path=backup_path,
        mutation_authorized=mutation_authorized,
        expected_count=expected_count,
        expected_manifest_sha256=expected_manifest_sha256,
    )


def manifest_sha256(manifest: StopReconciliationManifest) -> str:
    _validate_manifest_shape(manifest)
    calculated = _calculate_manifest_sha256(manifest)
    if calculated != manifest.manifest_sha256:
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest digest does not match its content"
        )
    return calculated


def write_manifest(path: Path, manifest: StopReconciliationManifest) -> str:
    digest = manifest_sha256(manifest)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(_manifest_json(manifest))
    except FileExistsError as exc:
        raise StopReconciliationManifestError("Manifest destination already exists") from exc
    except OSError as exc:
        raise StopReconciliationManifestError("Manifest destination cannot be written") from exc
    return digest


def read_manifest(path: Path) -> StopReconciliationManifest:
    try:
        manifest = StopReconciliationManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StopReconciliationManifestError("Stop reconciliation manifest is invalid") from exc
    manifest_sha256(manifest)
    return manifest


def validate_stop_reconciliation_apply_identity(
    manifest: StopReconciliationManifest,
    *,
    batch_id: BatchId,
    expected_count: int,
    expected_manifest_sha256: str,
) -> str:
    digest = manifest_sha256(manifest)
    _validate_safe_batch_id(batch_id)
    if expected_count != STOP_RECONCILIATION_EXPECTED_COUNT or (
        expected_count != manifest.expected_count
    ):
        raise StopReconciliationManifestError("Expected count does not match manifest")
    if not _SHA256_RE.fullmatch(expected_manifest_sha256) or (expected_manifest_sha256 != digest):
        raise StopReconciliationManifestError("Expected manifest digest does not match")
    return digest


def _validate_manifest_shape(manifest: StopReconciliationManifest) -> None:
    if manifest.expected_count != STOP_RECONCILIATION_EXPECTED_COUNT:
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest expected count is not 20"
        )
    _validate_safe_source_fixed_point(manifest.source_fixed_point)
    if manifest.run_ids != tuple(sorted(manifest.run_ids)):
        raise StopReconciliationManifestError("Stop reconciliation manifest IDs are not sorted")
    if (
        len(manifest.run_ids) != STOP_RECONCILIATION_EXPECTED_COUNT
        or len(set(manifest.run_ids)) != STOP_RECONCILIATION_EXPECTED_COUNT
    ):
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest must contain exactly 20 unique IDs"
        )
    for run_id in manifest.run_ids:
        _validate_safe_run_id(run_id)
    if set(manifest.started_at) != set(manifest.run_ids) or set(manifest.payload_digests) != set(
        manifest.run_ids
    ):
        raise StopReconciliationManifestError(
            "Stop reconciliation manifest mappings do not match IDs"
        )
    for value in manifest.started_at.values():
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise StopReconciliationManifestError(
                "Stop reconciliation timestamp is invalid"
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise StopReconciliationManifestError(
                "Stop reconciliation timestamp must include a timezone"
            )


def _validate_safe_run_id(run_id: str) -> None:
    if redact_value(run_id) != run_id:
        raise StopReconciliationManifestError("Stop reconciliation run ID is not safe for manifest")


def _validate_safe_batch_id(batch_id: str) -> None:
    if (
        not 5 <= len(batch_id) <= 200
        or not _BATCH_ID_RE.fullmatch(batch_id)
        or redact_value(batch_id) != batch_id
    ):
        raise StopReconciliationManifestError("Stop reconciliation batch ID is not safe")


def _validate_safe_source_fixed_point(source_fixed_point: str) -> None:
    if (
        not 1 <= len(source_fixed_point) <= 200
        or not _SOURCE_FIXED_POINT_RE.fullmatch(source_fixed_point)
        or redact_value(source_fixed_point) != source_fixed_point
    ):
        raise StopReconciliationManifestError(
            "Stop reconciliation source fixed point is not safe"
        )


def _calculate_manifest_sha256(manifest: StopReconciliationManifest) -> str:
    payload = manifest.model_dump(mode="json")
    payload.pop("manifest_sha256", None)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _manifest_json(manifest: StopReconciliationManifest) -> str:
    return (
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


__all__ = [
    "LEGACY_STOP_RECONCILIATION_ERROR",
    "STOP_RECONCILIATION_CONTRACT",
    "STOP_RECONCILIATION_EXPECTED_COUNT",
    "BatchId",
    "SourceFixedPoint",
    "StopReconciliationApplier",
    "StopReconciliationDryRunReceipt",
    "StopReconciliationFailureReceipt",
    "StopReconciliationManifest",
    "StopReconciliationManifestError",
    "StopReconciliationReceipt",
    "StopReconciliationSource",
    "StopReconciliationSourceRow",
    "StopReconciliationStorageError",
    "apply_stop_reconciliation",
    "create_stop_reconciliation_manifest",
    "manifest_sha256",
    "validate_stop_reconciliation_apply_identity",
    "plan_stop_reconciliation",
    "read_manifest",
    "write_manifest",
]
