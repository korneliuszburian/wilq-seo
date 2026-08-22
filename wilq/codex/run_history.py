from __future__ import annotations

import hmac
import os
import secrets
from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64DecodeError
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from wilq.schemas import CodexRun, CodexRunHistorySummary

CODEX_RUN_HISTORY_DEFAULT_LIMIT = 50
CODEX_RUN_HISTORY_MAX_LIMIT = 100
CODEX_RUN_HISTORY_CURSOR_SECRET_ENV = "WILQ_CODEX_RUN_HISTORY_CURSOR_SECRET"  # nosec B105  # pragma: allowlist secret
_PROCESS_CURSOR_SIGNING_KEY = secrets.token_bytes(32)


class InvalidCodexRunHistoryCursor(ValueError):
    pass


class CodexRunHistoryCursor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    started_at: datetime
    run_id: str = Field(min_length=1)

    @field_validator("started_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("cursor timestamp must include a timezone")
        return value


def encode_codex_run_history_cursor(*, started_at: datetime, run_id: str) -> str:
    payload = CodexRunHistoryCursor(version=1, started_at=started_at, run_id=run_id)
    payload_bytes = payload.model_dump_json().encode("utf-8")
    signature = hmac.new(_cursor_signing_key(), payload_bytes, sha256).digest()
    return f"{_encode_segment(payload_bytes)}.{_encode_segment(signature)}"


def decode_codex_run_history_cursor(cursor: str) -> CodexRunHistoryCursor:
    try:
        payload_segment, signature_segment = cursor.split(".", maxsplit=1)
        payload = _decode_segment(payload_segment)
        signature = _decode_segment(signature_segment)
        expected_signature = hmac.new(_cursor_signing_key(), payload, sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise InvalidCodexRunHistoryCursor("invalid Codex run history cursor")
        return CodexRunHistoryCursor.model_validate_json(payload)
    except (
        Base64DecodeError,
        InvalidCodexRunHistoryCursor,
        UnicodeDecodeError,
        ValidationError,
        ValueError,
    ) as error:
        raise InvalidCodexRunHistoryCursor("invalid Codex run history cursor") from error


def _cursor_signing_key() -> bytes:
    configured = os.getenv(CODEX_RUN_HISTORY_CURSOR_SECRET_ENV, "").strip()
    return configured.encode("utf-8") if configured else _PROCESS_CURSOR_SIGNING_KEY


def _encode_segment(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_segment(value: str) -> bytes:
    if not value:
        raise InvalidCodexRunHistoryCursor("invalid Codex run history cursor")
    padding = "=" * (-len(value) % 4)
    return b64decode(f"{value}{padding}", altchars=b"-_", validate=True)


def summarize_codex_run(run: CodexRun) -> CodexRunHistorySummary:
    return CodexRunHistorySummary(
        id=run.id,
        skill=run.skill,
        status=run.status,
        model=run.model,
        prompt_template_id=run.prompt_template_id,
        cost_estimate_pln=run.cost_estimate_pln,
        source_material_count=len(run.source_material_ids),
        started_at=run.started_at,
    )
