"""Typed, advisory-only independent review runs for one exact revision."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ContentIndependentReviewRole = Literal["content_ux", "seo", "factual_regulatory"]
ContentIndependentReviewStatus = Literal["completed"]
ContentIndependentFindingSeverity = Literal["critical", "major", "minor", "info"]
ContentIndependentFindingDisposition = Literal[
    "accept_and_fix",
    "reject_with_evidence",
    "deferred",
    "human_decision",
]
ContentIndependentReviewWriteStatus = Literal["created", "idempotent", "conflict"]
ContentIndependentDispositionStatus = Literal[
    "recorded",
    "idempotent",
    "conflict",
    "child_revision_required",
]

INDEPENDENT_REVIEW_ROLES: tuple[ContentIndependentReviewRole, ...] = (
    "content_ux",
    "seo",
    "factual_regulatory",
)
ROLE_CRITERIA_VERSIONS: dict[ContentIndependentReviewRole, str] = {
    "content_ux": "wilq_independent_content_ux_review_v1",
    "seo": "wilq_independent_seo_review_v1",
    "factual_regulatory": "wilq_independent_factual_regulatory_review_v1",
}


class ContentIndependentReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    code: str = Field(min_length=1, max_length=120)
    severity: ContentIndependentFindingSeverity
    label: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1, max_length=1600)
    instruction: str = Field(min_length=1, max_length=800)
    affected_targets: list[str] = Field(min_length=1, max_length=32)
    evidence_ids: list[str] = Field(min_length=1, max_length=64)
    disposition: ContentIndependentFindingDisposition | None = None
    disposition_reason: str | None = Field(default=None, max_length=1200)
    disposition_evidence_ids: list[str] = Field(default_factory=list, max_length=64)
    disposed_by: str | None = Field(default=None, max_length=160)
    disposed_at: datetime | None = None

    @field_validator("finding_id", "code", "label", "reason", "instruction")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Independent review text cannot be blank.")
        return value

    @field_validator("affected_targets", "evidence_ids", "disposition_evidence_ids")
    @classmethod
    def require_nonblank_list_values(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Independent review list values cannot be blank.")
        return [value.strip() for value in values]

    @field_validator("disposition_reason", "disposed_by")
    @classmethod
    def require_visible_optional_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Independent review disposition metadata cannot be blank.")
        return value

    @model_validator(mode="after")
    def require_disposition_metadata(self) -> ContentIndependentReviewFinding:
        has_disposition = self.disposition is not None
        metadata = (
            self.disposition_reason,
            self.disposed_by,
            self.disposed_at,
        )
        if has_disposition and any(value is None for value in metadata):
            raise ValueError("Finding disposition requires reason, actor and timestamp.")
        if not has_disposition and (
            any(value is not None for value in metadata) or self.disposition_evidence_ids
        ):
            raise ValueError("Undisposed finding cannot carry disposition metadata.")
        if has_disposition and not self.disposition_evidence_ids:
            raise ValueError("Finding disposition requires evidence IDs.")
        return self


class ContentIndependentReviewRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["wilq_independent_review_run_v1"] = "wilq_independent_review_run_v1"
    run_id: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    work_item_id: str = Field(min_length=1, max_length=240)
    revision_id: str = Field(min_length=1, max_length=240)
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: ContentIndependentReviewRole
    model_provider: Literal["opencode-go"]
    model_id: Literal["deepseek-v4.1-flash"]
    model_variant: Literal["max"]
    criteria_version: str = Field(min_length=1, max_length=120)
    status: ContentIndependentReviewStatus = "completed"
    findings: list[ContentIndependentReviewFinding] = Field(default_factory=list, max_length=128)
    evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    source_connectors: list[str] = Field(default_factory=list, max_length=64)
    requested_by: str = Field(min_length=1, max_length=160)
    created_at: datetime
    deterministic_gate_status: Literal["passed"] = "passed"
    advisory_only: Literal[True] = True
    human_review_required: Literal[True] = True
    publish_ready: Literal[False] = False
    action_object_created: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_role_contract(self) -> ContentIndependentReviewRun:
        if ROLE_CRITERIA_VERSIONS[self.role] != self.criteria_version:
            raise ValueError("Independent review criteria must match its exact role.")
        if not self.evidence_ids or not self.source_connectors:
            raise ValueError("Independent review run requires exact evidence and connectors.")
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("Independent review finding IDs must be unique per run.")
        evidence = set(self.evidence_ids)
        for finding in self.findings:
            if not set(finding.evidence_ids).issubset(evidence):
                raise ValueError("Finding evidence must be included in run evidence_ids.")
            if not set(finding.disposition_evidence_ids).issubset(evidence):
                raise ValueError("Disposition evidence must be included in run evidence_ids.")
        return self

    @field_validator("criteria_version", "requested_by")
    @classmethod
    def require_visible_attribution(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Independent review attribution cannot be blank.")
        return value

    @field_validator("evidence_ids", "source_connectors")
    @classmethod
    def require_visible_run_lineage(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Independent review lineage values cannot be blank.")
        return [value.strip() for value in values]


class ContentIndependentReviewRunSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    run: ContentIndependentReviewRun

    @model_validator(mode="after")
    def require_undisposed_findings(self) -> ContentIndependentReviewRunSubmission:
        if any(finding.disposition is not None for finding in self.run.findings):
            raise ValueError("Human dispositions must be recorded through the disposition route.")
        return self


class ContentIndependentFindingDispositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: ContentIndependentFindingDisposition
    reason: str = Field(min_length=1, max_length=1200)
    disposed_by: str = Field(min_length=1, max_length=160)
    evidence_ids: list[str] = Field(default_factory=list, max_length=64)

    @field_validator("reason", "disposed_by")
    @classmethod
    def require_visible_disposition_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Finding disposition text cannot be blank.")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def require_visible_evidence_ids(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Disposition evidence IDs cannot be blank.")
        return [value.strip() for value in values]

    @model_validator(mode="after")
    def require_rejection_evidence(self) -> ContentIndependentFindingDispositionRequest:
        if not self.evidence_ids:
            raise ValueError("Finding disposition requires evidence IDs.")
        return self


class ContentIndependentReviewRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentIndependentReviewWriteStatus
    work_item_id: str
    revision_id: str
    revision_digest: str
    run: ContentIndependentReviewRun | None = None
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_run_for_success(self) -> ContentIndependentReviewRunResponse:
        if self.status in {"created", "idempotent"} and self.run is None:
            raise ValueError("Independent review success requires the persisted run.")
        if self.status == "conflict" and self.run is not None:
            raise ValueError("Independent review conflict cannot carry a run.")
        return self


class ContentIndependentReviewRunCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    revision_id: str
    revision_digest: str
    runs: list[ContentIndependentReviewRun] = Field(default_factory=list)
    storage_status: Literal["ready", "activation_required"] = "ready"
    safe_next_step: str = Field(min_length=1, max_length=600)


class ContentIndependentFindingDispositionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentIndependentDispositionStatus
    work_item_id: str
    revision_id: str
    revision_digest: str
    run: ContentIndependentReviewRun | None = None
    finding_id: str
    requires_child_revision: bool = False
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_run_for_disposition(self) -> ContentIndependentFindingDispositionResponse:
        if self.status != "conflict" and self.run is None:
            raise ValueError("Disposition result requires the current run.")
        if self.status == "child_revision_required" and not self.requires_child_revision:
            raise ValueError("Child-revision status requires its explicit flag.")
        return self


__all__ = [
    "ContentIndependentFindingDisposition",
    "ContentIndependentFindingSeverity",
    "ContentIndependentReviewFinding",
    "ContentIndependentReviewRole",
    "ContentIndependentReviewRun",
    "ContentIndependentReviewRunResponse",
    "ContentIndependentReviewRunCollection",
    "ContentIndependentReviewRunSubmission",
    "ContentIndependentReviewStatus",
    "ContentIndependentReviewWriteStatus",
    "ContentIndependentFindingDispositionRequest",
    "ContentIndependentFindingDispositionResponse",
    "ContentIndependentDispositionStatus",
    "INDEPENDENT_REVIEW_ROLES",
    "ROLE_CRITERIA_VERSIONS",
]
