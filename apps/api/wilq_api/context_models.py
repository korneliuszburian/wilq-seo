from __future__ import annotations

from pydantic import BaseModel, Field


class ContextPackRequest(BaseModel):
    skill: str | None = None
    skill_id: str | None = None
    focus: str | None = None
    max_opportunities: int = Field(default=5, ge=1, le=25)
    full_context: bool = False
