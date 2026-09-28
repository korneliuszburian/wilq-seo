"""Local, single-use confirmation authority for sensitive ActionObjects.

Issuance is intentionally a TTY-only operation.  The signed token is a
short-lived transport value; only its digest and the resulting principal
receipt are persisted.  This module contains the cryptographic and atomic
storage boundary so callers cannot accidentally persist the token itself.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import string
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.audit.identity import LocalAuditTrustLevel
from wilq.storage.local_state import state_db_path
from wilq.storage.private_paths import prepare_private_store_path

TRUSTED_LOCAL_CONFIRMATION_CONTRACT = "trusted_local_confirmation_grant_v1"
TRUSTED_LOCAL_CONFIRMATION_PHRASE = "POTWIERDZAM DOKŁADNĄ AKCJĘ"
TRUSTED_LOCAL_TRUST_LEVEL: LocalAuditTrustLevel = "local_confirmed"
MAX_TRUSTED_LOCAL_CONFIRMATION_TTL_SECONDS = 300
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_TOKEN_VERSION = 1


class TrustedLocalConfirmationError(ValueError):
    """Typed failure from trusted local confirmation authority or storage."""

    def __init__(self, message: str, *, code: str = "trusted_local_confirmation_error") -> None:
        super().__init__(message)
        self.code = code


class TrustedLocalConfirmationBlocked(TrustedLocalConfirmationError):
    """A grant was not issued or consumed at the trusted local boundary."""

class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TrustedLocalConfirmationClaims(_FrozenModel):
    contract: str = TRUSTED_LOCAL_CONFIRMATION_CONTRACT
    version: int = _TOKEN_VERSION
    principal_id: str = Field(min_length=1, max_length=240)
    os_uid: int = Field(ge=0)
    workspace_id: str = Field(min_length=1, max_length=240)
    action_id: str = Field(min_length=1, max_length=240)
    payload_digest: str = Field(pattern=_DIGEST_PATTERN)
    snapshot_digest: str = Field(pattern=_DIGEST_PATTERN)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=32, max_length=256)

    @model_validator(mode="after")
    def validate_claims(self) -> TrustedLocalConfirmationClaims:
        if self.contract != TRUSTED_LOCAL_CONFIRMATION_CONTRACT or self.version != _TOKEN_VERSION:
            raise ValueError("Unsupported trusted local confirmation contract.")
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("Trusted local confirmation timestamps must be timezone-aware.")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("Trusted local confirmation timestamps must be timezone-aware.")
        lifetime = (self.expires_at - self.issued_at).total_seconds()
        if lifetime <= 0 or lifetime > MAX_TRUSTED_LOCAL_CONFIRMATION_TTL_SECONDS:
            raise ValueError("Trusted local confirmation TTL exceeds five minutes.")
        return self


# Public vocabulary aliases: the signed claims are the grant carried by the
# short-lived token, while the persisted model below is its receipt.
TrustedLocalConfirmationGrant = TrustedLocalConfirmationClaims


class TrustedLocalPrincipalReceipt(_FrozenModel):
    """Persisted, non-secret readback of one consumed local grant."""

    contract: str = TRUSTED_LOCAL_CONFIRMATION_CONTRACT
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_DIGEST_PATTERN)
    grant_digest: str = Field(pattern=_DIGEST_PATTERN)
    nonce_digest: str = Field(pattern=_DIGEST_PATTERN)
    principal_id: str = Field(min_length=1, max_length=240)
    os_uid: int = Field(ge=0)
    workspace_id: str = Field(min_length=1, max_length=240)
    action_id: str = Field(min_length=1, max_length=240)
    payload_digest: str = Field(pattern=_DIGEST_PATTERN)
    snapshot_digest: str = Field(pattern=_DIGEST_PATTERN)
    issued_at: datetime
    expires_at: datetime
    consumed_at: datetime
    trust_level: LocalAuditTrustLevel = TRUSTED_LOCAL_TRUST_LEVEL

    @model_validator(mode="after")
    def validate_receipt_identity(self) -> TrustedLocalPrincipalReceipt:
        if self.contract != TRUSTED_LOCAL_CONFIRMATION_CONTRACT:
            raise ValueError("Unsupported trusted local principal receipt contract.")
        if self.trust_level != TRUSTED_LOCAL_TRUST_LEVEL:
            raise ValueError("Principal receipt is not trusted local confirmation.")
        for value in (self.issued_at, self.expires_at, self.consumed_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    "Trusted local principal receipt timestamps must be timezone-aware."
                )
        payload = self.model_dump(mode="json")
        receipt_id = payload.pop("receipt_id")
        receipt_digest = payload.pop("receipt_digest")
        expected_digest = _canonical_digest(payload)
        if receipt_digest != expected_digest or receipt_id != (
            f"trusted_local_principal_receipt_{expected_digest[:24]}"
        ):
            raise ValueError("Trusted local principal receipt identity is invalid.")
        return self


TrustedLocalConfirmationReceipt = TrustedLocalPrincipalReceipt


def trusted_local_confirmation_store_path() -> Path:
    """Return the private receipt DB path alongside the configured state DB."""

    state_path = state_db_path()
    return state_path.with_suffix(state_path.suffix + ".trusted-local-confirmation.sqlite3")


def trusted_local_confirmation_key_path() -> Path:
    """Return the canonical private runtime signing-key path."""

    state_path = state_db_path()
    return state_path.with_suffix(state_path.suffix + ".trusted-local-confirmation.key")


class TrustedLocalConfirmationStore:
    """SQLite store whose only durable grant material is digest plus receipt."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(self.path, normalize_existing_parent=False)
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS trusted_local_principal_receipts (
              grant_digest TEXT PRIMARY KEY,
              nonce_digest TEXT NOT NULL UNIQUE,
              action_id TEXT NOT NULL,
              payload_digest TEXT NOT NULL,
              snapshot_digest TEXT NOT NULL,
              principal_id TEXT NOT NULL,
              workspace_id TEXT NOT NULL,
              os_uid INTEGER NOT NULL,
              consumed_at TEXT NOT NULL,
              receipt_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trusted_local_receipts_binding
            ON trusted_local_principal_receipts (
              principal_id, workspace_id, action_id, payload_digest, snapshot_digest
            );
            """
        )
        self.path.chmod(0o600)
        return connection

    def consume(self, receipt: TrustedLocalPrincipalReceipt) -> TrustedLocalPrincipalReceipt:
        payload_json = _model_json(receipt)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    """
                    SELECT 1 FROM trusted_local_principal_receipts
                    WHERE grant_digest = ? OR nonce_digest = ?
                    """,
                    (receipt.grant_digest, receipt.nonce_digest),
                ).fetchone()
                if existing is not None:
                    raise TrustedLocalConfirmationBlocked(
                        "Trusted local confirmation grant replay detected (single-use).",
                        code="trusted_local_confirmation_replay",
                    )
                connection.execute(
                    """
                    INSERT INTO trusted_local_principal_receipts (
                      grant_digest, nonce_digest, action_id, payload_digest, snapshot_digest,
                      principal_id, workspace_id, os_uid, consumed_at, receipt_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.grant_digest,
                        receipt.nonce_digest,
                        receipt.action_id,
                        receipt.payload_digest,
                        receipt.snapshot_digest,
                        receipt.principal_id,
                        receipt.workspace_id,
                        receipt.os_uid,
                        receipt.consumed_at.isoformat(),
                        payload_json,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation grant replay detected (single-use).",
                code="trusted_local_confirmation_replay",
            ) from error
        return receipt

    def find(
        self,
        *,
        principal_id: str,
        workspace_id: str,
        action_id: str,
        payload_digest: str,
        snapshot_digest: str,
        os_uid: int | None = None,
    ) -> TrustedLocalPrincipalReceipt | None:
        query = """
            SELECT receipt_json FROM trusted_local_principal_receipts
            WHERE principal_id = ? AND workspace_id = ? AND action_id = ?
              AND payload_digest = ? AND snapshot_digest = ?
        """
        parameters: list[object] = [
            principal_id,
            workspace_id,
            action_id,
            payload_digest,
            snapshot_digest,
        ]
        if os_uid is not None:
            query += " AND os_uid = ?"
            parameters.append(os_uid)
        query += " ORDER BY consumed_at DESC LIMIT 1"
        with self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        if row is None:
            return None
        try:
            return TrustedLocalPrincipalReceipt.model_validate_json(
                cast(str, row["receipt_json"]), strict=True
            )
        except Exception as error:
            raise TrustedLocalConfirmationBlocked(
                "Persisted trusted local principal receipt is invalid.",
                code="trusted_local_confirmation_receipt_invalid",
            ) from error

    def list_receipts(self) -> list[TrustedLocalPrincipalReceipt]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT receipt_json FROM trusted_local_principal_receipts "
                "ORDER BY consumed_at, grant_digest"
            ).fetchall()
        receipts: list[TrustedLocalPrincipalReceipt] = []
        for row in rows:
            try:
                receipts.append(
                    TrustedLocalPrincipalReceipt.model_validate_json(
                        cast(str, row["receipt_json"]), strict=True
                    )
                )
            except Exception:
                continue
        return receipts


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _os_uid() -> int:
    if not hasattr(os, "getuid"):
        raise RuntimeError("OS UID is unavailable")
    return os.getuid()


class TrustedLocalConfirmationAuthority:
    """Issue and consume signed local grants with injectable test seams."""

    def __init__(
        self,
        *,
        store: TrustedLocalConfirmationStore | None = None,
        signing_key: bytes | None = None,
        key_path: Path | None = None,
        clock: Callable[[], datetime] = _utc_now,
        uid_reader: Callable[[], int] = _os_uid,
        random_bytes: Callable[[int], bytes] = secrets.token_bytes,
    ) -> None:
        self.store = store or TrustedLocalConfirmationStore(trusted_local_confirmation_store_path())
        self.signing_key = signing_key
        self.key_path = key_path
        self.clock = clock
        self.uid_reader = uid_reader
        self.random_bytes = random_bytes

    def current_uid(self) -> int:
        """Read and validate the current OS UID at the authority boundary."""

        try:
            uid = self.uid_reader()
        except Exception as error:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation requires a local OS UID.",
                code="trusted_local_confirmation_uid_missing",
            ) from error
        if not isinstance(uid, int) or uid < 0:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation requires a local OS UID.",
                code="trusted_local_confirmation_uid_missing",
            )
        return uid

    def issue(
        self,
        *,
        principal_id: str,
        workspace_id: str,
        action_id: str,
        payload_digest: str,
        snapshot_digest: str,
        is_tty: bool,
        confirmation_phrase: str,
        ttl_seconds: int = MAX_TRUSTED_LOCAL_CONFIRMATION_TTL_SECONDS,
    ) -> str:
        if not is_tty:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation requires an interactive TTY.",
                code="trusted_local_confirmation_tty_required",
            )
        if confirmation_phrase != TRUSTED_LOCAL_CONFIRMATION_PHRASE:
            raise TrustedLocalConfirmationBlocked(
                "Exact confirmation phrase does not match.",
                code="trusted_local_confirmation_phrase_required",
            )
        if not 1 <= ttl_seconds <= MAX_TRUSTED_LOCAL_CONFIRMATION_TTL_SECONDS:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation TTL must be between one second and five minutes.",
                code="trusted_local_confirmation_ttl_invalid",
            )
        uid = self.current_uid()
        issued_at = _aware_datetime(self.clock(), field="issued_at")
        nonce_bytes = self.random_bytes(32)
        if not isinstance(nonce_bytes, bytes) or len(nonce_bytes) < 16:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation nonce generation failed.",
                code="trusted_local_confirmation_nonce_invalid",
            )
        try:
            claims = TrustedLocalConfirmationClaims(
                principal_id=principal_id,
                os_uid=uid,
                workspace_id=workspace_id,
                action_id=action_id,
                payload_digest=payload_digest,
                snapshot_digest=snapshot_digest,
                issued_at=issued_at,
                expires_at=issued_at + timedelta(seconds=ttl_seconds),
                nonce=_b64url_encode(nonce_bytes),
            )
        except Exception as error:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation grant binding is invalid.",
                code="trusted_local_confirmation_binding_invalid",
            ) from error
        body = _b64url_encode(_model_json(claims).encode("utf-8"))
        signature = hmac.new(self._key(), body.encode("ascii"), hashlib.sha256).digest()
        return f"{body}.{_b64url_encode(signature)}"

    def consume(
        self,
        token: str,
        *,
        action_id: str,
        payload_digest: str,
        snapshot_digest: str,
        workspace_id: str,
        principal_id: str | None = None,
        os_uid: int | None = None,
    ) -> TrustedLocalPrincipalReceipt:
        claims = self._decode_and_verify(token)
        now = _aware_datetime(self.clock(), field="consumed_at")
        actual_uid = self.current_uid()
        expected_uid = actual_uid if os_uid is None else os_uid
        if expected_uid != actual_uid or claims.os_uid != expected_uid:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation OS UID does not match.",
                code="trusted_local_confirmation_uid_mismatch",
            )
        if now >= claims.expires_at:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation grant has expired.",
                code="trusted_local_confirmation_expired",
            )
        expected_values = {
            "action_id": action_id,
            "payload_digest": payload_digest,
            "snapshot_digest": snapshot_digest,
            "workspace_id": workspace_id,
        }
        for field, expected in expected_values.items():
            if getattr(claims, field) != expected:
                raise TrustedLocalConfirmationBlocked(
                    f"Trusted local confirmation {field} does not match.",
                    code=f"trusted_local_confirmation_{field}_mismatch",
                )
        if principal_id is not None and claims.principal_id != principal_id:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation principal does not match.",
                code="trusted_local_confirmation_principal_mismatch",
            )
        grant_digest = _sha256_text(token)
        nonce_digest = _sha256_text(claims.nonce)
        receipt_payload: dict[str, Any] = {
            "contract": TRUSTED_LOCAL_CONFIRMATION_CONTRACT,
            "grant_digest": grant_digest,
            "nonce_digest": nonce_digest,
            "principal_id": claims.principal_id,
            "os_uid": claims.os_uid,
            "workspace_id": claims.workspace_id,
            "action_id": claims.action_id,
            "payload_digest": claims.payload_digest,
            "snapshot_digest": claims.snapshot_digest,
            "issued_at": claims.issued_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "expires_at": claims.expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "consumed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "trust_level": TRUSTED_LOCAL_TRUST_LEVEL,
        }
        receipt_digest = _canonical_digest(receipt_payload)
        receipt = TrustedLocalPrincipalReceipt(
            receipt_id=f"trusted_local_principal_receipt_{receipt_digest[:24]}",
            receipt_digest=receipt_digest,
            **receipt_payload,
        )
        return self.store.consume(receipt)

    def receipt_for(
        self,
        *,
        principal_id: str,
        workspace_id: str,
        action_id: str,
        payload_digest: str,
        snapshot_digest: str,
        os_uid: int | None = None,
    ) -> TrustedLocalPrincipalReceipt | None:
        actual_uid = self.current_uid()
        if os_uid is not None and os_uid != actual_uid:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation OS UID does not match.",
                code="trusted_local_confirmation_uid_mismatch",
            )
        receipt = self.store.find(
            principal_id=principal_id,
            workspace_id=workspace_id,
            action_id=action_id,
            payload_digest=payload_digest,
            snapshot_digest=snapshot_digest,
            os_uid=None,
        )
        if receipt is None:
            return None
        if receipt.os_uid != actual_uid:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation persisted receipt OS UID does not match.",
                code="trusted_local_confirmation_uid_mismatch",
            )
        now = _aware_datetime(self.clock(), field="checked_at")
        if now >= receipt.expires_at:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation principal receipt has expired.",
                code="trusted_local_confirmation_expired",
            )
        return receipt

    def _key(self) -> bytes:
        if self.signing_key is not None:
            if len(self.signing_key) < 32:
                raise TrustedLocalConfirmationBlocked(
                    "Trusted local confirmation signing key is too short.",
                    code="trusted_local_confirmation_key_invalid",
                )
            return self.signing_key
        path = self.key_path or trusted_local_confirmation_key_path()
        try:
            self._reject_key_symlinks(path)
            prepare_private_store_path(path, normalize_existing_parent=False)
            self._reject_key_symlinks(path)
            if path.exists():
                return self._read_key_file(path)
            key = secrets.token_bytes(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(path, flags, 0o600)
            except FileExistsError:
                self._reject_key_symlinks(path)
                return self._read_key_file(path)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(key)
            finally:
                path.chmod(0o600)
            return key
        except TrustedLocalConfirmationError:
            raise
        except Exception as error:
            raise TrustedLocalConfirmationError(
                "Trusted local confirmation signing key is unavailable.",
                code="trusted_local_confirmation_key_unavailable",
            ) from error

    @staticmethod
    def _reject_key_symlinks(path: Path) -> None:
        if path.is_symlink() or path.parent.is_symlink():
            raise TrustedLocalConfirmationError(
                "Trusted local confirmation signing key symlink is not allowed.",
                code="trusted_local_confirmation_key_symlink",
            )

    @staticmethod
    def _read_key_file(path: Path) -> bytes:
        if path.is_symlink() or not path.is_file():
            raise TrustedLocalConfirmationError(
                "Trusted local confirmation signing key path is not a regular file.",
                code="trusted_local_confirmation_key_invalid",
            )
        path.chmod(0o600)
        key = path.read_bytes()
        if len(key) < 32:
            raise TrustedLocalConfirmationError(
                "Trusted local confirmation signing key is invalid.",
                code="trusted_local_confirmation_key_invalid",
            )
        return key

    def _decode_and_verify(self, token: str) -> TrustedLocalConfirmationClaims:
        if not isinstance(token, str):
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation token is invalid.",
                code="trusted_local_confirmation_token_invalid",
            )
        parts = token.split(".")
        if len(parts) != 2:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation token is invalid.",
                code="trusted_local_confirmation_token_invalid",
            )
        body, encoded_signature = parts
        try:
            supplied_signature = _b64url_decode(encoded_signature)
            claims_json = _b64url_decode(body).decode("utf-8")
            claims = TrustedLocalConfirmationClaims.model_validate_json(
                claims_json, strict=True
            )
        except Exception as error:
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation token is invalid.",
                code="trusted_local_confirmation_token_invalid",
            ) from error
        expected_signature = hmac.new(
            self._key(), body.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise TrustedLocalConfirmationBlocked(
                "Trusted local confirmation signature is invalid.",
                code="trusted_local_confirmation_signature_invalid",
            )
        return claims


def trusted_local_confirmation_authority() -> TrustedLocalConfirmationAuthority:
    return TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(trusted_local_confirmation_store_path())
    )


def _model_json(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    # The base64url alphabet is a public constant, not a credential.
    alphabet = (
        string.ascii_uppercase
        + string.ascii_lowercase
        + string.digits
        + "-_"
    )
    if not value or any(character not in alphabet for character in value):
        raise ValueError("Invalid base64url value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _aware_datetime(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise TrustedLocalConfirmationBlocked(
            f"Trusted local confirmation {field} must be timezone-aware.",
            code="trusted_local_confirmation_time_invalid",
        )
    return value.astimezone(UTC)


__all__ = [
    "MAX_TRUSTED_LOCAL_CONFIRMATION_TTL_SECONDS",
    "TRUSTED_LOCAL_CONFIRMATION_CONTRACT",
    "TRUSTED_LOCAL_CONFIRMATION_PHRASE",
    "TRUSTED_LOCAL_TRUST_LEVEL",
    "TrustedLocalConfirmationAuthority",
    "TrustedLocalConfirmationBlocked",
    "TrustedLocalConfirmationError",
    "TrustedLocalConfirmationClaims",
    "TrustedLocalConfirmationGrant",
    "TrustedLocalConfirmationReceipt",
    "TrustedLocalConfirmationStore",
    "TrustedLocalPrincipalReceipt",
    "trusted_local_confirmation_authority",
    "trusted_local_confirmation_key_path",
    "trusted_local_confirmation_store_path",
]
