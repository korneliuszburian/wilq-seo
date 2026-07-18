from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    validate_no_inline_link,
    validate_plain_internal_link_anchor,
)

ContentInitialDraftStatus = Literal[
    "generating", "created", "blocked", "failed", "conflict"
]
ContentInitialDraftBlockerCode = Literal[
    "planning_not_approved",
    "planning_not_generated",
    "stale_planning_input",
    "proposal_mismatch",
    "revision_already_exists",
    "missing_generation_contract",
    "runtime_blocked",
    "runtime_failed",
    "invalid_structured_output",
    "document_scope_mismatch",
    "generated_claim_blocked",
    "revision_conflict",
    "persistence_failed",
    "generation_in_progress",
]


class ContentInitialDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_proposal_id: str = Field(min_length=1)
    expected_planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_by: str = Field(min_length=1)

    @field_validator("expected_proposal_id", "requested_by")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Initial draft request fields cannot be blank.")
        return stripped


class ContentInitialDraftSectionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)

    @field_validator("heading", "body_markdown")
    @classmethod
    def reject_inline_links(cls, value: str) -> str:
        return validate_no_inline_link(value)


class ContentInitialDraftFaqOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    answer_markdown: str = Field(min_length=1)

    @field_validator("question", "answer_markdown")
    @classmethod
    def reject_inline_links(cls, value: str) -> str:
        return validate_no_inline_link(value)


class ContentInitialDraftCtaOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body_markdown: str = Field(min_length=1)

    @field_validator("body_markdown")
    @classmethod
    def reject_inline_links(cls, value: str) -> str:
        return validate_no_inline_link(value)


class ContentInitialDraftInternalLinkOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_url: str = Field(min_length=1)
    anchor_text: str = Field(min_length=1)

    @field_validator("target_url")
    @classmethod
    def require_safe_public_target(cls, value: str) -> str:
        if not content_is_safe_public_url(value):
            raise ValueError("Initial-draft internal link requires a safe public URL.")
        return value

    @field_validator("anchor_text")
    @classmethod
    def require_plain_anchor_text(cls, value: str) -> str:
        return validate_plain_internal_link_anchor(value)


class ContentInitialDraftModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["pl-PL"] = "pl-PL"
    page_assets: ContentDraftRevisionPageAssets
    sections: list[ContentInitialDraftSectionOutput] = Field(min_length=1)
    faq: list[ContentInitialDraftFaqOutput] = Field(default_factory=list)
    cta_blocks: list[ContentInitialDraftCtaOutput] = Field(default_factory=list)
    internal_links: list[ContentInitialDraftInternalLinkOutput] = Field(default_factory=list)
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_unique_document_targets(self) -> ContentInitialDraftModelOutput:
        section_ids = [item.section_id.strip() for item in self.sections]
        headings = [item.heading.strip() for item in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Initial draft section IDs must be unique.")
        if len(headings) != len(set(headings)):
            raise ValueError("Initial draft headings must be unique.")
        return self


class ContentInitialDraftBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentInitialDraftBlockerCode
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)
    source_codes: list[str] = Field(default_factory=list)


class ContentInitialDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentInitialDraftStatus
    work_item_id: str = Field(min_length=1)
    proposal_id: str | None = None
    run_id: str | None = None
    revision: ContentDraftRevision | None = None
    runtime: ContentCodexRuntimeTrace = Field(
        default_factory=lambda: ContentCodexRuntimeTrace(status="not_started")
    )
    blockers: list[ContentInitialDraftBlocker] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_status_payload(self) -> ContentInitialDraftResponse:
        if self.status == "created":
            if self.revision is None or self.run_id is None or self.blockers:
                raise ValueError("Created initial draft requires one revision and run.")
        elif self.status == "generating":
            if self.revision is not None or not self.blockers:
                raise ValueError("Generating initial draft requires a blocker and no revision.")
        elif self.revision is not None or not self.blockers:
            raise ValueError("Non-created initial draft requires blockers and no revision.")
        return self


__all__ = [
    "ContentInitialDraftBlocker",
    "ContentInitialDraftBlockerCode",
    "ContentInitialDraftCtaOutput",
    "ContentInitialDraftFaqOutput",
    "ContentInitialDraftInternalLinkOutput",
    "ContentInitialDraftModelOutput",
    "ContentInitialDraftRequest",
    "ContentInitialDraftResponse",
    "ContentInitialDraftSectionOutput",
]
