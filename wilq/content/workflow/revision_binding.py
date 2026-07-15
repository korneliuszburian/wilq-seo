from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContentDraftRevisionBinding(BaseModel):
    """Exact approved revision authorized for one WordPress draft handoff."""

    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    handoff_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    draft_package_id: str = Field(min_length=1)
    draft_package_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_decision_id: str = Field(min_length=1)
    final_canonical_url: str = Field(min_length=1)
