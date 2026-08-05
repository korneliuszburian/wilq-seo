from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContentTargetDraftPreviewField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_field: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    value: str = Field(min_length=1)
    value_kind: Literal["plain_text", "html", "url"]


class ContentTargetDraftPreviewBlocker(BaseModel):
    """A typed reason why an exact target draft payload is unavailable."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["mapping_not_confirmed", "mapping_stale"]
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)
