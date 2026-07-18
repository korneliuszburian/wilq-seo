from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace

ContentSemanticCriteriaVersion = Literal["wilq_semantic_content_review_v1"]
ContentSemanticDimension = Literal[
    "answer_directness",
    "completeness",
    "logical_flow",
    "specificity",
    "repetition",
    "search_intent_fit",
    "buyer_fit",
    "credibility",
    "conversion_clarity",
]
CONTENT_SEMANTIC_DIMENSIONS: tuple[ContentSemanticDimension, ...] = (
    "answer_directness",
    "completeness",
    "logical_flow",
    "specificity",
    "repetition",
    "search_intent_fit",
    "buyer_fit",
    "credibility",
    "conversion_clarity",
)
ContentSemanticTarget = str
ContentSemanticStatus = Literal["reviewable", "needs_changes"]
ContentSemanticResponseStatus = Literal[
    "generating",
    "not_generated",
    "created",
    "idempotent",
    "ready",
    "stale",
    "blocked",
    "failed",
    "conflict",
]
ContentSemanticBlockerCode = Literal[
    "missing_revision",
    "stale_revision",
    "legacy_revision",
    "stale_content_context",
    "missing_planning_input",
    "source_material_review_required",
    "storage_activation_required",
    "runtime_blocked",
    "runtime_failed",
    "invalid_structured_output",
    "semantic_scope_mismatch",
    "persistence_failed",
    "review_conflict",
    "generation_in_progress",
]


class ContentSemanticReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_by: str = Field(min_length=1)

    @field_validator("requested_by")
    @classmethod
    def require_requester(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Semantic review requires requester attribution.")
        return stripped


class ContentSemanticDimensionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: ContentSemanticDimension
    status: Literal["strong", "needs_changes"]
    reason: str = Field(min_length=1)
    affected_targets: list[ContentSemanticTarget] = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def require_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Semantic dimension reason cannot be blank.")
        return value


class ContentSemanticFindingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: ContentSemanticDimension
    severity: Literal["high", "medium", "low"]
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    affected_targets: list[ContentSemanticTarget] = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("label", "reason", "instruction")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Semantic finding text cannot be blank.")
        return value


class ContentSemanticReviewModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["pl-PL"] = "pl-PL"
    dimensions: list[ContentSemanticDimensionAssessment] = Field(
        min_length=len(CONTENT_SEMANTIC_DIMENSIONS),
        max_length=len(CONTENT_SEMANTIC_DIMENSIONS),
    )
    findings: list[ContentSemanticFindingOutput] = Field(default_factory=list)
    publish_ready: Literal[False] = False
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def require_every_dimension_once(self) -> ContentSemanticReviewModelOutput:
        dimensions = [item.dimension for item in self.dimensions]
        if tuple(dimensions) != CONTENT_SEMANTIC_DIMENSIONS:
            raise ValueError("Semantic review must assess every dimension in canonical order.")
        return self


class ContentSemanticFinding(ContentSemanticFindingOutput):
    finding_id: str = Field(min_length=1)


class ContentSemanticReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    criteria_version: ContentSemanticCriteriaVersion = "wilq_semantic_content_review_v1"
    codex_run_id: str = Field(min_length=1)
    status: ContentSemanticStatus
    dimensions: list[ContentSemanticDimensionAssessment] = Field(
        min_length=len(CONTENT_SEMANTIC_DIMENSIONS),
        max_length=len(CONTENT_SEMANTIC_DIMENSIONS),
    )
    findings: list[ContentSemanticFinding] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    requested_by: str = Field(min_length=1)
    created_at: datetime
    safe_next_step: str = Field(min_length=1)
    publish_ready: Literal[False] = False
    human_review_required: Literal[True] = True
    action_object_created: Literal[False] = False

    @model_validator(mode="after")
    def require_advisory_status(self) -> ContentSemanticReview:
        finding_ids = [item.finding_id.strip() for item in self.findings]
        if len(finding_ids) != len(set(finding_ids)) or any(not item for item in finding_ids):
            raise ValueError("Semantic finding IDs must be visible and unique.")
        expected = "needs_changes" if self.findings else "reviewable"
        if self.status != expected:
            raise ValueError("Semantic review status must be derived from findings.")
        return self


class ContentSemanticReviewBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentSemanticBlockerCode
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)
    source_codes: list[str] = Field(default_factory=list)


class ContentSemanticReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentSemanticResponseStatus
    work_item_id: str = Field(min_length=1)
    revision_id: str | None = None
    revision_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    review: ContentSemanticReview | None = None
    run_id: str | None = None
    runtime: ContentCodexRuntimeTrace = Field(
        default_factory=lambda: ContentCodexRuntimeTrace(status="not_started")
    )
    blockers: list[ContentSemanticReviewBlocker] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)
    publish_ready: Literal[False] = False
    human_review_required: Literal[True] = True
    action_object_created: Literal[False] = False

    @model_validator(mode="after")
    def require_status_payload(self) -> ContentSemanticReviewResponse:
        if self.status in {"created", "idempotent", "ready", "stale"}:
            if self.review is None or self.blockers:
                raise ValueError("Readable semantic-review status requires one review.")
        elif self.status == "generating":
            if self.review is not None or not self.blockers:
                raise ValueError("Generating semantic review requires blockers and no review.")
        elif self.status == "not_generated":
            if self.review is not None or self.blockers:
                raise ValueError("Not-generated semantic review cannot expose a result or blocker.")
        elif self.review is not None or not self.blockers:
            raise ValueError("Blocked semantic-review status requires blockers and no review.")
        if self.review is not None and (
            self.work_item_id != self.review.work_item_id
            or self.revision_id != self.review.revision_id
            or self.revision_digest != self.review.revision_digest
            or self.run_id != self.review.codex_run_id
        ):
            raise ValueError("Semantic-review response must bind the exact embedded review.")
        return self


__all__ = [
    "CONTENT_SEMANTIC_DIMENSIONS",
    "ContentSemanticBlockerCode",
    "ContentSemanticDimension",
    "ContentSemanticDimensionAssessment",
    "ContentSemanticFinding",
    "ContentSemanticFindingOutput",
    "ContentSemanticReview",
    "ContentSemanticReviewBlocker",
    "ContentSemanticReviewModelOutput",
    "ContentSemanticReviewRequest",
    "ContentSemanticReviewResponse",
]
