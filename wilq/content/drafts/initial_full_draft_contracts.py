from __future__ import annotations

import re
from typing import Annotated, Literal, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import ContentPlanningInputBlockerCode
from wilq.content.workflow.decisions.production import ClassificationLookupBasis
from wilq.content.workflow.decisions.production_reuse import ProductionReuseBlockCode
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionReview,
    validate_no_inline_link,
    validate_plain_internal_link_anchor,
)

_NonBlankWireString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, strict=True),
]

ContentInitialDraftStatus = Literal[
    "generating",
    "created",
    "reused",
    "blocked",
    "failed",
    "conflict",
]
ContentInitialDraftBlockerCode = Literal[
    ContentPlanningInputBlockerCode,
    ProductionReuseBlockCode,
    "planning_not_ready",
    "draft_not_started",
    "planning_not_generated",
    "stale_planning_input",
    "proposal_mismatch",
    "revision_already_exists",
    "missing_generation_contract",
    "regulatory_preflight_failed",
    "runtime_blocked",
    "runtime_failed",
    "invalid_structured_output",
    "document_scope_mismatch",
    "generated_claim_blocked",
    "draft_assurance_failed",
    "draft_assurance_runtime_failed",
    "draft_assurance_invalid_output",
    "readability_gate_failed",
    "readability_repair_failed",
    "revision_conflict",
    "persistence_failed",
    "generation_in_progress",
    "initial_draft_queue_full",
    "stale_initial_draft_context",
    "production_classification_missing",
    "production_classification_item_missing",
    "production_classification_digest_required",
    "stale_production_classification",
    "production_generation_disabled",
]
CONTENT_INITIAL_DRAFT_BLOCKER_CODES = frozenset(
    str(code) for code in get_args(ContentInitialDraftBlockerCode)
)
_CONTENT_INITIAL_DRAFT_BLOCKER_CODE_ADAPTER: TypeAdapter[ContentInitialDraftBlockerCode] = (
    TypeAdapter(ContentInitialDraftBlockerCode)
)


def parse_content_initial_draft_blocker_code(
    value: str,
) -> ContentInitialDraftBlockerCode | None:
    """Validate persisted blocker identity against the public contract."""

    try:
        return _CONTENT_INITIAL_DRAFT_BLOCKER_CODE_ADAPTER.validate_python(value)
    except ValidationError:
        return None


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


class ContentInitialDraftReuseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_production_classification_run_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_by: str = Field(min_length=1)

    @field_validator("requested_by")
    @classmethod
    def require_visible_requester(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Initial draft requester cannot be blank.")
        return stripped


ContentWorkItemInitialDraftRequest = ContentInitialDraftRequest | ContentInitialDraftReuseRequest


class ContentInitialDraftSectionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)

    @field_validator("heading", "body_markdown")
    @classmethod
    def require_visible_text_without_inline_links(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Initial-draft section fields cannot be blank.")
        return validate_no_inline_link(value)


class ContentInitialDraftFaqOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    answer_markdown: str = Field(min_length=1)

    @field_validator("question", "answer_markdown")
    @classmethod
    def require_visible_text_without_inline_links(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Initial-draft FAQ fields cannot be blank.")
        return validate_no_inline_link(value)


class ContentInitialDraftCtaOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body_markdown: str = Field(min_length=1)

    @field_validator("body_markdown")
    @classmethod
    def require_visible_text_without_inline_links(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Initial-draft CTA body cannot be blank.")
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

    @field_validator("page_assets", mode="after")
    @classmethod
    def clear_generation_byline(
        cls, value: ContentDraftRevisionPageAssets
    ) -> ContentDraftRevisionPageAssets:
        if value.byline is not None:
            return value.model_copy(update={"byline": None})
        return value

    @model_validator(mode="after")
    def require_unique_document_targets(self) -> ContentInitialDraftModelOutput:
        section_ids = [item.section_id.strip() for item in self.sections]
        headings = [item.heading.strip() for item in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Initial draft section IDs must be unique.")
        if len(headings) != len(set(headings)):
            raise ValueError("Initial draft headings must be unique.")
        for section_id in section_ids:
            if re.match(r"^(?:(?:faq|cta):\d+$|(?:page_assets|link):)", section_id):
                raise ValueError(
                    f"Initial draft section ID must not collide with gate target: {section_id}"
                )
        return self


class ContentInitialDraftBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentInitialDraftBlockerCode
    label: _NonBlankWireString
    reason: _NonBlankWireString
    next_step: _NonBlankWireString
    source_codes: list[str] = Field(default_factory=list)
    retry_after_seconds: int | None = Field(default=None, ge=1)


class ContentInitialDraftApprovedReview(ContentDraftRevisionReview):
    model_config = ConfigDict(extra="forbid")

    decision_id: _NonBlankWireString
    decision: Literal["approved"]
    reviewed_by: _NonBlankWireString
    principal_id: Literal["local_operator"]
    workspace_id: Literal["ekologus_local_pilot"]
    trust_level: Literal["local_unverified"]
    notes: str


class ContentInitialDraftReuseBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification_run_id: _NonBlankWireString
    classification_run_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_set_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_work_item_id: _NonBlankWireString
    lookup_basis: ClassificationLookupBasis
    current_work_item_id: _NonBlankWireString
    retained_work_item_id: _NonBlankWireString | None
    revision_work_item_id: _NonBlankWireString
    identity_reconciliation_status: Literal["fork", "retained_missing"]
    revision_id: _NonBlankWireString
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_review: ContentInitialDraftApprovedReview
    must_not_regenerate: Literal[True]

    @field_validator("must_not_regenerate", mode="before")
    @classmethod
    def require_literal_true(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Reuse binding must forbid regeneration.")
        return value

    @model_validator(mode="after")
    def require_exact_identity_and_review(self) -> ContentInitialDraftReuseBinding:
        if self.identity_reconciliation_status == "fork":
            if (
                self.retained_work_item_id is None
                or self.revision_work_item_id != self.retained_work_item_id
                or self.retained_work_item_id == self.current_work_item_id
            ):
                raise ValueError("Fork reuse requires the exact retained revision owner.")
        elif (
            self.retained_work_item_id is not None
            or self.revision_work_item_id == self.current_work_item_id
        ):
            raise ValueError("Retained-missing reuse requires one distinct historical owner.")
        expected_requested_id = {
            "current": self.current_work_item_id,
            "retained": self.retained_work_item_id,
            "historical_action_owner": self.revision_work_item_id,
        }[self.lookup_basis]
        if (
            expected_requested_id is None
            or self.requested_work_item_id != expected_requested_id
            or (
                self.lookup_basis == "historical_action_owner"
                and self.identity_reconciliation_status != "retained_missing"
            )
        ):
            raise ValueError("Reuse lookup basis does not match the requested identity.")
        review = self.approved_review
        if (
            review.decision != "approved"
            or review.work_item_id != self.revision_work_item_id
            or review.revision_id != self.revision_id
            or review.revision_digest != self.revision_digest
        ):
            raise ValueError("Reuse binding requires the exact approved revision review.")
        return self


class ContentInitialDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentInitialDraftStatus
    work_item_id: _NonBlankWireString
    proposal_id: str | None = None
    run_id: str | None = None
    revision: ContentDraftRevision | None = None
    reuse_binding: ContentInitialDraftReuseBinding | None = None
    runtime: ContentCodexRuntimeTrace = Field(
        default_factory=lambda: ContentCodexRuntimeTrace(status="not_started")
    )
    blockers: list[ContentInitialDraftBlocker] = Field(default_factory=list)
    safe_next_step: _NonBlankWireString
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_status_payload(self) -> ContentInitialDraftResponse:
        if self.status == "reused":
            binding = self.reuse_binding
            if (
                self.revision is None
                or binding is None
                or self.proposal_id is not None
                or self.run_id is not None
                or self.blockers
                or self.runtime.model_dump()
                != ContentCodexRuntimeTrace(status="not_started").model_dump()
                or self.work_item_id != binding.current_work_item_id
                or self.revision.work_item_id != binding.revision_work_item_id
                or self.revision.revision_id != binding.revision_id
                or self.revision.content_digest != binding.revision_digest
            ):
                raise ValueError("Reused initial draft requires one exact retained authority.")
        elif self.reuse_binding is not None:
            raise ValueError("Only a reused initial draft may expose a reuse binding.")
        elif self.status == "created":
            if self.revision is None or self.run_id is None or self.blockers:
                raise ValueError("Created initial draft requires one revision and run.")
        elif self.status == "generating":
            if self.revision is not None or not self.blockers:
                raise ValueError("Generating initial draft requires a blocker and no revision.")
        elif self.revision is not None or not self.blockers:
            raise ValueError("Non-created initial draft requires blockers and no revision.")
        return self


class ContentInitialDraftWireRuntime(ContentCodexRuntimeTrace):
    run_id: str | None = None
    thread_id: str | None
    turn_id: str | None
    event_methods: list[str] = Field(default_factory=list)
    item_types: list[str] = Field(default_factory=list)
    external_call_attempted: bool

    @field_validator("external_call_attempted", mode="before")
    @classmethod
    def require_boolean(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("External-call state must be a boolean.")
        return value


class _ContentInitialDraftWireResponse(ContentInitialDraftResponse):
    work_item_id: _NonBlankWireString
    proposal_id: str | None
    run_id: str | None
    revision: ContentDraftRevision | None
    reuse_binding: ContentInitialDraftReuseBinding | None
    runtime: ContentInitialDraftWireRuntime
    blockers: list[ContentInitialDraftBlocker]
    safe_next_step: _NonBlankWireString
    publish_ready: Literal[False]

    @field_validator("publish_ready", mode="before")
    @classmethod
    def require_literal_false(cls, value: object) -> object:
        if value is not False:
            raise ValueError("Initial draft responses are never publish-ready.")
        return value


class ContentInitialDraftCreatedResponse(_ContentInitialDraftWireResponse):
    status: Literal["created"]
    run_id: _NonBlankWireString
    revision: ContentDraftRevision
    reuse_binding: None
    blockers: list[ContentInitialDraftBlocker] = Field(max_length=0)


class _ContentInitialDraftNoRevisionResponse(_ContentInitialDraftWireResponse):
    revision: None
    reuse_binding: None
    blockers: list[ContentInitialDraftBlocker] = Field(min_length=1)


class ContentInitialDraftGeneratingResponse(_ContentInitialDraftNoRevisionResponse):
    status: Literal["generating"]


class ContentInitialDraftBlockedResponse(_ContentInitialDraftNoRevisionResponse):
    status: Literal["blocked"]


class ContentInitialDraftFailedResponse(_ContentInitialDraftNoRevisionResponse):
    status: Literal["failed"]


class ContentInitialDraftConflictResponse(_ContentInitialDraftNoRevisionResponse):
    status: Literal["conflict"]


class ContentInitialDraftReusedRuntime(ContentInitialDraftWireRuntime):
    status: Literal["not_started"]
    run_id: None
    thread_id: None
    turn_id: None
    event_methods: list[str] = Field(max_length=0)
    item_types: list[str] = Field(max_length=0)
    external_call_attempted: Literal[False]

    @field_validator("external_call_attempted", mode="before")
    @classmethod
    def require_literal_false(cls, value: object) -> object:
        if value is not False:
            raise ValueError("Reused content cannot attempt an external call.")
        return value


class ContentInitialDraftReusedResponse(_ContentInitialDraftWireResponse):
    status: Literal["reused"]
    proposal_id: None
    run_id: None
    revision: ContentDraftRevision
    reuse_binding: ContentInitialDraftReuseBinding
    runtime: ContentInitialDraftReusedRuntime
    blockers: list[ContentInitialDraftBlocker] = Field(max_length=0)


ContentInitialDraftGenerationResponse = Annotated[
    ContentInitialDraftCreatedResponse
    | ContentInitialDraftGeneratingResponse
    | ContentInitialDraftBlockedResponse
    | ContentInitialDraftFailedResponse
    | ContentInitialDraftConflictResponse,
    Field(discriminator="status"),
]


ContentWorkItemInitialDraftResponse = Annotated[
    ContentInitialDraftCreatedResponse
    | ContentInitialDraftGeneratingResponse
    | ContentInitialDraftReusedResponse
    | ContentInitialDraftBlockedResponse
    | ContentInitialDraftFailedResponse,
    Field(discriminator="status"),
]


__all__ = [
    "CONTENT_INITIAL_DRAFT_BLOCKER_CODES",
    "ContentInitialDraftApprovedReview",
    "ContentInitialDraftBlocker",
    "ContentInitialDraftBlockerCode",
    "ContentInitialDraftBlockedResponse",
    "ContentInitialDraftConflictResponse",
    "ContentInitialDraftCreatedResponse",
    "ContentInitialDraftCtaOutput",
    "ContentInitialDraftFailedResponse",
    "ContentInitialDraftFaqOutput",
    "ContentInitialDraftGenerationResponse",
    "ContentInitialDraftGeneratingResponse",
    "ContentInitialDraftInternalLinkOutput",
    "ContentInitialDraftModelOutput",
    "ContentInitialDraftRequest",
    "ContentInitialDraftReusedResponse",
    "ContentInitialDraftReusedRuntime",
    "ContentInitialDraftReuseBinding",
    "ContentInitialDraftReuseRequest",
    "ContentInitialDraftResponse",
    "ContentInitialDraftSectionOutput",
    "ContentInitialDraftWireRuntime",
    "ContentWorkItemInitialDraftRequest",
    "ContentWorkItemInitialDraftResponse",
    "parse_content_initial_draft_blocker_code",
]
