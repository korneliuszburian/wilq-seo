from __future__ import annotations

from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64DecodeError
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from wilq.schemas import CodexRun, CodexRunHistorySummary

CODEX_RUN_HISTORY_DEFAULT_LIMIT = 50
CODEX_RUN_HISTORY_MAX_LIMIT = 100


class InvalidCodexRunHistoryCursor(ValueError):
    pass


class CodexRunHistoryCursor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1] = 1
    started_at: datetime
    run_id: str = Field(min_length=1)

    @field_validator("started_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("cursor timestamp must include a timezone")
        return value


def encode_codex_run_history_cursor(*, started_at: datetime, run_id: str) -> str:
    payload = CodexRunHistoryCursor(started_at=started_at, run_id=run_id)
    return urlsafe_b64encode(payload.model_dump_json().encode("utf-8")).decode("ascii").rstrip("=")


def decode_codex_run_history_cursor(cursor: str) -> CodexRunHistoryCursor:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = b64decode(f"{cursor}{padding}", altchars=b"-_", validate=True)
        return CodexRunHistoryCursor.model_validate_json(payload)
    except (Base64DecodeError, UnicodeDecodeError, ValidationError, ValueError) as error:
        raise InvalidCodexRunHistoryCursor("invalid Codex run history cursor") from error


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
