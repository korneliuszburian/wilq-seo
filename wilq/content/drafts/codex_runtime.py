from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContentCodexRuntimeTrace(BaseModel):
    """Auditable trace of one bounded, server-side Codex turn."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["not_started", "completed", "blocked", "failed"]
    run_id: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    event_methods: list[str] = Field(default_factory=list)
    item_types: list[str] = Field(default_factory=list)
    external_call_attempted: bool = False


__all__ = ["ContentCodexRuntimeTrace"]
