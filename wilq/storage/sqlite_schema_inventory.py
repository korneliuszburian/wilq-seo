from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.storage.model_json import model_json
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION

SQLITE_SCHEMA_INVENTORY_CONTRACT: Literal["wilq_sqlite_schema_inventory_v1"] = (
    "wilq_sqlite_schema_inventory_v1"
)
SQLITE_SCHEMA_CATALOG_CONTRACT: Literal["wilq_sqlite_schema_catalog_v1"] = (
    "wilq_sqlite_schema_catalog_v1"
)
SQLITE_SCHEMA_IDENTITY_CONTRACT: Literal["wilq_sqlite_schema_identity_v1"] = (
    "wilq_sqlite_schema_identity_v1"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SQLITE_SIDECAR_SUFFIXES = ("-journal", "-shm", "-wal")
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", strict=True)]
NonNegativeInteger = Annotated[int, Field(ge=0, strict=True)]


class SqliteSchemaInventoryError(RuntimeError):
    """The explicitly supplied SQLite source cannot produce a safe inventory."""


class _FrozenContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SqliteTableColumn(_FrozenContractModel):
    position: int
    name: str
    declared_type: str
    not_null: bool
    default_sql: str | None
    primary_key_position: int
    hidden: int


class SqliteIndexColumn(_FrozenContractModel):
    position: int
    column_id: int
    name: str | None
    descending: bool
    collation: str | None
    is_key: bool


class SqliteTableInventory(_FrozenContractModel):
    name: str
    sql: str | None
    sql_sha256: Sha256Digest | None
    columns: tuple[SqliteTableColumn, ...]


class SqliteIndexInventory(_FrozenContractModel):
    name: str
    table_name: str
    sql: str | None
    sql_sha256: Sha256Digest | None
    columns: tuple[SqliteIndexColumn, ...]


class SqliteTriggerInventory(_FrozenContractModel):
    name: str
    table_name: str
    sql: str | None
    sql_sha256: Sha256Digest | None


class UnsupportedSqliteSchemaObject(_FrozenContractModel):
    object_type: str
    name: str
    table_name: str
    sql: str | None
    sql_sha256: Sha256Digest | None


class SqliteSchemaCatalog(_FrozenContractModel):
    contract_version: Literal["wilq_sqlite_schema_catalog_v1"] = SQLITE_SCHEMA_CATALOG_CONTRACT
    tables: tuple[SqliteTableInventory, ...]
    indexes: tuple[SqliteIndexInventory, ...]
    triggers: tuple[SqliteTriggerInventory, ...]
    unsupported_objects: tuple[UnsupportedSqliteSchemaObject, ...]


class SqliteSchemaIdentity(_FrozenContractModel):
    contract_version: Literal["wilq_sqlite_schema_identity_v1"] = SQLITE_SCHEMA_IDENTITY_CONTRACT
    sqlite_user_version: int
    sqlite_application_id: int
    catalog_sha256: Sha256Digest
    application_sha256: Sha256Digest | None
    seed_sha256: Sha256Digest | None
    identity_sha256: Sha256Digest


SqliteSchemaCompatibilityStatus = Literal[
    "exact_post_s5",
    "unverified_post_s5",
    "unsupported_schema_identity",
]
SqliteSchemaCompatibilityReason = Literal[
    "application_sha256_missing",
    "seed_sha256_missing",
    "expected_identity_missing",
    "identity_sha256_mismatch",
    "unsupported_object_type",
    "unsupported_user_version",
]


class SqliteSchemaCompatibility(_FrozenContractModel):
    status: SqliteSchemaCompatibilityStatus
    expected_identity_sha256: Sha256Digest | None
    reasons: tuple[SqliteSchemaCompatibilityReason, ...]


class SqliteSourceByteProof(_FrozenContractModel):
    size_bytes: NonNegativeInteger
    sha256: Sha256Digest
    preserved: Literal[True] = True


class SqliteSchemaInventory(_FrozenContractModel):
    contract_version: Literal["wilq_sqlite_schema_inventory_v1"] = SQLITE_SCHEMA_INVENTORY_CONTRACT
    identity: SqliteSchemaIdentity
    compatibility: SqliteSchemaCompatibility
    catalog: SqliteSchemaCatalog
    source_bytes: SqliteSourceByteProof


def inspect_sqlite_schema(
    path: Path,
    *,
    application_sha256: str | None = None,
    seed_sha256: str | None = None,
    expected_identity_sha256: str | None = None,
) -> SqliteSchemaInventory:
    """Inventory one isolated SQLite file without initializing or mutating it."""

    application_sha256 = _validated_sha256(application_sha256, "application_sha256")
    seed_sha256 = _validated_sha256(seed_sha256, "seed_sha256")
    expected_identity_sha256 = _validated_sha256(
        expected_identity_sha256,
        "expected_identity_sha256",
    )
    source = _resolve_isolated_source(path)
    before = _source_byte_proof(source)
    try:
        with closing(_connect_read_only(source)) as connection:
            connection.execute("BEGIN")
            sqlite_user_version = _pragma_integer(connection, "user_version")
            sqlite_application_id = _pragma_integer(connection, "application_id")
            catalog = _catalog(connection)
    except (OSError, sqlite3.Error, UnicodeError, ValueError) as exc:
        raise SqliteSchemaInventoryError(
            "SQLite source schema cannot be inspected read-only"
        ) from exc
    _require_no_sidecars(source)
    after = _source_byte_proof(source)
    if before != after:
        raise SqliteSchemaInventoryError("SQLite source bytes changed during inspection")

    catalog_sha256 = _canonical_sha256(catalog)
    identity_payload: dict[str, object] = {
        "application_sha256": application_sha256,
        "catalog_sha256": catalog_sha256,
        "contract_version": SQLITE_SCHEMA_IDENTITY_CONTRACT,
        "seed_sha256": seed_sha256,
        "sqlite_application_id": sqlite_application_id,
        "sqlite_user_version": sqlite_user_version,
    }
    identity_sha256 = _canonical_sha256(identity_payload)
    compatibility = _compatibility(
        sqlite_user_version=sqlite_user_version,
        unsupported_objects=catalog.unsupported_objects,
        identity_sha256=identity_sha256,
        application_sha256=application_sha256,
        seed_sha256=seed_sha256,
        expected_identity_sha256=expected_identity_sha256,
    )
    return SqliteSchemaInventory(
        identity=SqliteSchemaIdentity(
            sqlite_user_version=sqlite_user_version,
            sqlite_application_id=sqlite_application_id,
            catalog_sha256=catalog_sha256,
            application_sha256=application_sha256,
            seed_sha256=seed_sha256,
            identity_sha256=identity_sha256,
        ),
        compatibility=compatibility,
        catalog=catalog,
        source_bytes=SqliteSourceByteProof(
            size_bytes=before[0],
            sha256=before[1],
        ),
    )


def canonical_sqlite_schema_inventory_json(inventory: SqliteSchemaInventory) -> str:
    return model_json(inventory)


def _resolve_isolated_source(path: Path) -> Path:
    try:
        source = path.resolve(strict=True)
    except OSError as exc:
        raise SqliteSchemaInventoryError("SQLite source file is required") from exc
    if not source.is_file():
        raise SqliteSchemaInventoryError("SQLite source must be a regular file")
    _require_no_sidecars(source)
    return source


def _require_no_sidecars(path: Path) -> None:
    if any(Path(f"{path}{suffix}").exists() for suffix in _SQLITE_SIDECAR_SUFFIXES):
        raise SqliteSchemaInventoryError(
            "SQLite source must be an isolated file without journal, shm, or wal sidecars"
        )


def _source_byte_proof(path: Path) -> tuple[int, str]:
    try:
        digest = sha256()
        size_bytes = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                size_bytes += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise SqliteSchemaInventoryError("SQLite source bytes cannot be read") from exc
    return size_bytes, digest.hexdigest()


def _connect_read_only(path: Path) -> sqlite3.Connection:
    uri = f"{path.as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _pragma_integer(connection: sqlite3.Connection, pragma_name: str) -> int:
    if pragma_name not in {"application_id", "user_version"}:
        raise ValueError("Unsupported SQLite identity pragma")
    row = connection.execute(f"PRAGMA {pragma_name}").fetchone()  # nosec B608
    if row is None:
        raise ValueError(f"SQLite {pragma_name} is unavailable")
    return int(row[0])


def _catalog(connection: sqlite3.Connection) -> SqliteSchemaCatalog:
    tables: list[SqliteTableInventory] = []
    indexes: list[SqliteIndexInventory] = []
    triggers: list[SqliteTriggerInventory] = []
    unsupported_objects: list[UnsupportedSqliteSchemaObject] = []
    rows = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_schema
        ORDER BY type, name, tbl_name
        """
    ).fetchall()
    for row in rows:
        object_type = cast(str, row["type"])
        name = cast(str, row["name"])
        if name.startswith("sqlite_"):
            continue
        table_name = cast(str, row["tbl_name"])
        sql = cast(str | None, row["sql"])
        sql_sha256 = sha256(sql.encode("utf-8")).hexdigest() if sql is not None else None
        if object_type == "table":
            tables.append(
                SqliteTableInventory(
                    name=name,
                    sql=sql,
                    sql_sha256=sql_sha256,
                    columns=_table_columns(connection, name),
                )
            )
        elif object_type == "index":
            indexes.append(
                SqliteIndexInventory(
                    name=name,
                    table_name=table_name,
                    sql=sql,
                    sql_sha256=sql_sha256,
                    columns=_index_columns(connection, name),
                )
            )
        elif object_type == "trigger":
            triggers.append(
                SqliteTriggerInventory(
                    name=name,
                    table_name=table_name,
                    sql=sql,
                    sql_sha256=sql_sha256,
                )
            )
        else:
            unsupported_objects.append(
                UnsupportedSqliteSchemaObject(
                    object_type=object_type,
                    name=name,
                    table_name=table_name,
                    sql=sql,
                    sql_sha256=sql_sha256,
                )
            )
    return SqliteSchemaCatalog(
        tables=tuple(sorted(tables, key=lambda item: item.name)),
        indexes=tuple(sorted(indexes, key=lambda item: item.name)),
        triggers=tuple(sorted(triggers, key=lambda item: item.name)),
        unsupported_objects=tuple(
            sorted(
                unsupported_objects,
                key=lambda item: (item.object_type, item.name, item.table_name),
            )
        ),
    )


def _table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> tuple[SqliteTableColumn, ...]:
    rows = connection.execute(
        """
        SELECT cid, name, type, "notnull", dflt_value, pk, hidden
        FROM pragma_table_xinfo(?)
        ORDER BY cid
        """,
        (table_name,),
    ).fetchall()
    return tuple(
        SqliteTableColumn(
            position=int(row["cid"]),
            name=cast(str, row["name"]),
            declared_type=cast(str, row["type"]),
            not_null=bool(row["notnull"]),
            default_sql=cast(str | None, row["dflt_value"]),
            primary_key_position=int(row["pk"]),
            hidden=int(row["hidden"]),
        )
        for row in rows
    )


def _index_columns(
    connection: sqlite3.Connection,
    index_name: str,
) -> tuple[SqliteIndexColumn, ...]:
    rows = connection.execute(
        """
        SELECT seqno, cid, name, "desc", coll, "key"
        FROM pragma_index_xinfo(?)
        ORDER BY seqno
        """,
        (index_name,),
    ).fetchall()
    return tuple(
        SqliteIndexColumn(
            position=int(row["seqno"]),
            column_id=int(row["cid"]),
            name=cast(str | None, row["name"]),
            descending=bool(row["desc"]),
            collation=cast(str | None, row["coll"]),
            is_key=bool(row["key"]),
        )
        for row in rows
    )


def _compatibility(
    *,
    sqlite_user_version: int,
    unsupported_objects: tuple[UnsupportedSqliteSchemaObject, ...],
    identity_sha256: str,
    application_sha256: str | None,
    seed_sha256: str | None,
    expected_identity_sha256: str | None,
) -> SqliteSchemaCompatibility:
    reasons: list[SqliteSchemaCompatibilityReason] = []
    if sqlite_user_version != SQLITE_SCHEMA_VERSION:
        reasons.append("unsupported_user_version")
    if unsupported_objects:
        reasons.append("unsupported_object_type")
    if expected_identity_sha256 is not None and identity_sha256 != expected_identity_sha256:
        reasons.append("identity_sha256_mismatch")
    if reasons:
        status: SqliteSchemaCompatibilityStatus = "unsupported_schema_identity"
    else:
        if application_sha256 is None:
            reasons.append("application_sha256_missing")
        if seed_sha256 is None:
            reasons.append("seed_sha256_missing")
        if expected_identity_sha256 is None:
            reasons.append("expected_identity_missing")
        status = "unverified_post_s5" if reasons else "exact_post_s5"
    return SqliteSchemaCompatibility(
        status=status,
        expected_identity_sha256=expected_identity_sha256,
        reasons=tuple(reasons),
    )


def _validated_sha256(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _canonical_sha256(value: BaseModel | dict[str, object]) -> str:
    return sha256(model_json(value).encode("utf-8")).hexdigest()
