from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContentNewPageDraftBinding(BaseModel):
    """Exact new-page identity authorized for one future dev-draft attempt.

    This intentionally does not reuse ``ContentDraftRevisionBinding``: a new
    page has no public canonical URL or legacy handoff/package identity.
    """

    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    foundation_id: str = Field(min_length=1)
    service_card_id: str = Field(min_length=1)
    service_card_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authoring_profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: Literal["page", "post"]

