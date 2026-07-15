from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from wilq.content.workflow.revision_binding import (
    ContentDraftRevisionBinding as ContentDraftRevisionBinding,
)

if TYPE_CHECKING:
    from wilq.content.drafts.package import ContentDraftPackage

ContentDraftRevisionDecision = Literal[
    "approved",
    "needs_changes",
    "rejected",
    "deferred",
]
ContentDraftRevisionStateStatus = Literal[
    "empty",
    "unreviewed",
    "needs_changes",
    "approved",
    "rejected",
    "deferred",
]
ContentDraftRevisionWriteStatus = Literal["created", "idempotent", "conflict"]
ContentDraftRevisionConflictCode = Literal[
    "apply_in_progress",
    "stale_base",
    "revision_not_found",
    "stale_revision",
    "stale_review",
    "digest_mismatch",
]


class ContentDraftRevisionProposalSectionLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class ContentDraftRevisionProposalMetadata(BaseModel):
    """Compact, durable provenance for an API-owned Codex child revision."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["codex_app_server"] = "codex_app_server"
    codex_run_id: str = Field(min_length=1)
    selected_section_headings: list[str] = Field(min_length=1)
    section_lineage: list[ContentDraftRevisionProposalSectionLineage] = Field(min_length=1)
    quality_verdict: Literal[
        "needs_changes",
        "reviewable",
        "ready_for_human_review",
    ]
    quality_finding_codes: list[str] = Field(default_factory=list)
    review_scope: Literal["persisted_selected_sections_and_declared_lineage"] = (
        "persisted_selected_sections_and_declared_lineage"
    )
    semantic_review_required: Literal[True] = True

    @model_validator(mode="after")
    def require_selected_lineage(self) -> ContentDraftRevisionProposalMetadata:
        headings = [heading.strip() for heading in self.selected_section_headings]
        lineage_headings = [lineage.heading.strip() for lineage in self.section_lineage]
        if headings != lineage_headings or len(headings) != len(set(headings)):
            raise ValueError("Proposal lineage must match the unique selected headings.")
        self.selected_section_headings = headings
        return self


class ContentDraftRevisionSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1)
    body_markdown: str
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("heading", "body_markdown")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Draft revision section text cannot be blank.")
        return value


class ContentDraftRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    revision_number: int = Field(ge=1)
    base_revision_id: str | None = None
    content_digest: str = Field(min_length=64, max_length=64)
    draft_package_id: str = Field(min_length=1)
    draft_package_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    planning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    final_canonical_url: str = Field(min_length=1)
    title: str
    sections: list[ContentDraftRevisionSection] = Field(min_length=1)
    proposal_metadata: ContentDraftRevisionProposalMetadata | None = None
    publish_ready: Literal[False] = False
    created_by: str = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def require_draft_content(self) -> ContentDraftRevision:
        _validate_draft_content(
            title=self.title,
            sections=self.sections,
            created_by=self.created_by,
        )
        return self


class ContentDraftRevisionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    decision_number: int = Field(ge=1)
    work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(min_length=64, max_length=64)
    decision: ContentDraftRevisionDecision
    reviewed_by: str = Field(min_length=1)
    notes: str = ""
    checked_items: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime

    @model_validator(mode="after")
    def require_review_evidence(self) -> ContentDraftRevisionReview:
        _validate_review_decision(
            decision=self.decision,
            reviewed_by=self.reviewed_by,
            notes=self.notes,
            checked_items=self.checked_items,
            evidence_ids=self.evidence_ids,
        )
        return self


class ContentDraftRevisionAppendCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    base_revision_id: str | None = None
    draft_package_id: str = Field(min_length=1)
    draft_package_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_canonical_url: str = Field(min_length=1)
    title: str
    sections: list[ContentDraftRevisionSection] = Field(min_length=1)
    proposal_metadata: ContentDraftRevisionProposalMetadata | None = None
    publish_ready: Literal[False] = False
    created_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_draft_content(self) -> ContentDraftRevisionAppendCommand:
        _validate_draft_content(
            title=self.title,
            sections=self.sections,
            created_by=self.created_by,
        )
        return self


class ContentDraftRevisionReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(min_length=64, max_length=64)
    base_decision_id: str | None = None
    decision: ContentDraftRevisionDecision
    reviewed_by: str = Field(min_length=1)
    notes: str = ""
    checked_items: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_review_evidence(self) -> ContentDraftRevisionReviewCommand:
        _validate_review_decision(
            decision=self.decision,
            reviewed_by=self.reviewed_by,
            notes=self.notes,
            checked_items=self.checked_items,
            evidence_ids=self.evidence_ids,
        )
        return self


class ContentDraftRevisionConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentDraftRevisionConflictCode
    current_revision_id: str | None = None
    current_revision_digest: str | None = None


class ContentDraftRevisionWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentDraftRevisionWriteStatus
    revision: ContentDraftRevision | None = None
    conflict: ContentDraftRevisionConflict | None = None

    @model_validator(mode="after")
    def require_discriminated_payload(self) -> ContentDraftRevisionWriteResult:
        if self.status == "conflict":
            if self.conflict is None or self.revision is not None:
                raise ValueError("Conflict result requires only conflict details.")
        elif self.revision is None or self.conflict is not None:
            raise ValueError("Successful revision result requires only a revision.")
        return self


class ContentDraftRevisionReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentDraftRevisionWriteStatus
    review: ContentDraftRevisionReview | None = None
    conflict: ContentDraftRevisionConflict | None = None

    @model_validator(mode="after")
    def require_discriminated_payload(self) -> ContentDraftRevisionReviewResult:
        if self.status == "conflict":
            if self.conflict is None or self.review is not None:
                raise ValueError("Conflict result requires only conflict details.")
        elif self.review is None or self.conflict is not None:
            raise ValueError("Successful review result requires only a review.")
        return self


class ContentDraftRevisionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentDraftRevisionStateStatus
    latest_revision: ContentDraftRevision | None = None
    latest_review: ContentDraftRevisionReview | None = None
    revision_count: int = Field(ge=0)

    @model_validator(mode="after")
    def require_consistent_current_state(self) -> ContentDraftRevisionState:
        if self.status == "empty":
            if self.latest_revision is not None or self.latest_review is not None:
                raise ValueError("Empty revision state cannot contain persisted content.")
            if self.revision_count != 0:
                raise ValueError("Empty revision state requires revision_count=0.")
            return self
        if self.latest_revision is None or self.revision_count < 1:
            raise ValueError("Non-empty revision state requires a latest revision.")
        if self.status == "unreviewed":
            if self.latest_review is not None:
                raise ValueError("Unreviewed state cannot contain a current review.")
            return self
        if self.latest_review is None or self.latest_review.decision != self.status:
            raise ValueError("Reviewed state must match the current revision review.")
        if (
            self.latest_review.revision_id != self.latest_revision.revision_id
            or self.latest_review.revision_digest != self.latest_revision.content_digest
        ):
            raise ValueError("Current review must match the exact latest revision and digest.")
        return self


def content_draft_package_digest(draft_package: ContentDraftPackage) -> str:
    canonical_json = json.dumps(
        draft_package.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def _validate_review_decision(
    *,
    decision: ContentDraftRevisionDecision,
    reviewed_by: str,
    notes: str,
    checked_items: list[str],
    evidence_ids: list[str],
) -> None:
    if not reviewed_by.strip():
        raise ValueError("Revision review requires a visible reviewer identifier.")
    if any(not item.strip() for item in checked_items):
        raise ValueError("Revision review checked_items cannot contain blank values.")
    if any(not evidence_id.strip() for evidence_id in evidence_ids):
        raise ValueError("Revision review evidence_ids cannot contain blank values.")
    if decision == "approved":
        if not any(item.strip() for item in checked_items):
            raise ValueError("Approved revision review requires checked_items.")
        if not any(evidence_id.strip() for evidence_id in evidence_ids):
            raise ValueError("Approved revision review requires evidence_ids.")
        return
    if not notes.strip():
        raise ValueError(f"{decision} revision review requires notes.")


def _validate_draft_content(
    *,
    title: str,
    sections: list[ContentDraftRevisionSection],
    created_by: str,
) -> None:
    if not created_by.strip():
        raise ValueError("Draft revision requires a visible creator identifier.")
    if not title.strip():
        raise ValueError("Draft revision title cannot be blank.")
    normalized_headings = [section.heading.strip() for section in sections]
    if len(normalized_headings) != len(set(normalized_headings)):
        raise ValueError("Draft revision section headings must be unique after stripping.")
