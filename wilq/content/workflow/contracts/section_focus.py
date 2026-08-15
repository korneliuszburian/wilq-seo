from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ContentSectionFocusStatus = Literal["current", "stale", "missing"]


class ContentSectionFocusRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    planning_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    updated_by: str | None = None
    updated_at: datetime

    @field_validator("section_id")
    @classmethod
    def require_nonblank_section_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("section_id must be non-blank")
        return value

    def is_current_for(self, planning_digest: str | None) -> bool:
        return planning_digest is not None and self.planning_digest == planning_digest


class ContentSectionFocusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentSectionFocusStatus
    record: ContentSectionFocusRecord | None = None
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_record_only_when_current(self) -> ContentSectionFocusResponse:
        if self.status == "current" and self.record is None:
            raise ValueError("Current focus requires its persisted record")
        if self.status != "current" and self.record is not None:
            raise ValueError("Focus record is exposed only when current")
        return self


class ContentSectionFocusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    updated_by: str | None = None

    @field_validator("section_id")
    @classmethod
    def require_nonblank_section_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("section_id must be non-blank")
        return value


def content_section_focus_status(
    record: ContentSectionFocusRecord | None,
    current_planning_digest: str | None,
    section_ids_in_plan: Collection[str],
) -> ContentSectionFocusStatus:
    if record is None:
        return "missing"
    if not record.is_current_for(current_planning_digest):
        return "stale"
    if record.section_id not in section_ids_in_plan:
        return "stale"
    return "current"


__all__ = [
    "ContentSectionFocusRecord",
    "ContentSectionFocusResponse",
    "ContentSectionFocusStatus",
    "ContentSectionFocusUpdateRequest",
    "content_section_focus_status",
]
