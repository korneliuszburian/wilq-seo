from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.quality.review import ContentQualityReview
from wilq.content.workflow.revisions import ContentDraftRevision

ContentCodexSectionProposalStatus = Literal[
    "created",
    "idempotent",
    "blocked",
    "failed",
    "conflict",
]
ContentCodexSectionProposalBlockerCode = Literal[
    "missing_planning_binding",
    "missing_base_revision",
    "stale_base_revision",
    "revision_not_ready_for_proposal",
    "stale_content_context",
    "missing_generation_contract",
    "unknown_selected_section",
    "ambiguous_claim_marker",
    "runtime_blocked",
    "runtime_failed",
    "invalid_structured_output",
    "section_scope_mismatch",
    "proposal_contract_blocked",
    "quality_blocked",
    "revision_conflict",
]


class ContentCodexSectionProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_base_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_section_headings: list[str] = Field(min_length=1)
    requested_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_unambiguous_selection(self) -> ContentCodexSectionProposalRequest:
        headings = [heading.strip() for heading in self.selected_section_headings]
        if any(not heading for heading in headings):
            raise ValueError("Selected section headings cannot be blank.")
        if len(headings) != len(set(headings)):
            raise ValueError("Selected section headings must be unique.")
        if not self.requested_by.strip():
            raise ValueError("Content proposal requires a visible requester attribution.")
        self.selected_section_headings = headings
        self.requested_by = self.requested_by.strip()
        return self


class ContentCodexSectionProposalBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentCodexSectionProposalBlockerCode
    label: str
    reason: str
    next_step: str
    source_codes: list[str] = Field(default_factory=list)


class ContentCodexRuntimeTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["not_started", "completed", "blocked", "failed"]
    thread_id: str | None = None
    turn_id: str | None = None
    event_methods: list[str] = Field(default_factory=list)
    item_types: list[str] = Field(default_factory=list)
    external_call_attempted: bool = False


class ContentCodexSectionProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentCodexSectionProposalStatus
    run_id: str | None = None
    work_item_id: str
    base_revision_id: str
    selected_section_headings: list[str]
    revision: ContentDraftRevision | None = None
    quality_review: ContentQualityReview | None = None
    quality_review_scope: Literal["persisted_selected_sections_and_declared_lineage"] = (
        "persisted_selected_sections_and_declared_lineage"
    )
    semantic_review_required: Literal[True] = True
    runtime: ContentCodexRuntimeTrace
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    blockers: list[ContentCodexSectionProposalBlocker] = Field(default_factory=list)
    safe_next_step: str
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_status_payload(self) -> ContentCodexSectionProposalResponse:
        if self.status in {"created", "idempotent"}:
            if (
                self.run_id is None
                or self.revision is None
                or self.quality_review is None
                or self.quality_review.verdict == "blocked"
                or self.blockers
            ):
                raise ValueError("Created content proposal requires a reviewable revision.")
        elif self.revision is not None or not self.blockers:
            raise ValueError("Non-created content proposal requires blockers and no revision.")
        return self


__all__ = [
    "ContentCodexRuntimeTrace",
    "ContentCodexSectionProposalBlocker",
    "ContentCodexSectionProposalBlockerCode",
    "ContentCodexSectionProposalRequest",
    "ContentCodexSectionProposalResponse",
]
