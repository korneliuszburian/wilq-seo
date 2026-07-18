from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.operator_labels import blocker_count_label, impact_comparison_summary_label

from .core import ActionMode, ActionRisk, ActionStatus, MetricFact, OpportunityDomain, utc_now


class AuditEvent(BaseModel):
    id: str
    action_id: str | None = None
    event_type: str
    event_type_label: str = ""
    actor: str
    principal_id: str | None = None
    workspace_id: str | None = None
    trust_level: Literal["local_unverified"] | None = None
    submitted_actor_label: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    redacted: bool = True


class ActionWordPressDraftApplyBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class ActionMutationAuditRecord(BaseModel):
    id: str
    action_id: str
    connector: str
    action_type: str | None = None
    status: Literal["blocked", "applied", "failed"]
    status_label: str = ""
    adapter_reached: bool = False
    external_write_attempted: bool = False
    mutation_attempted: bool = False
    mutation_adapter: str | None = None
    actor: str
    principal_id: str | None = None
    workspace_id: str | None = None
    trust_level: Literal["local_unverified"] | None = None
    submitted_actor_label: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    audit_event_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    wordpress_draft_binding: ContentDraftRevisionBinding | None = None
    wordpress_revision_blockers: list[ActionWordPressDraftApplyBlocker] = Field(
        default_factory=list
    )
    summary: str
    redacted: bool = True


class ActionMutationReadinessRequirement(BaseModel):
    code: str
    label: str
    satisfied: bool = False
    evidence: str | None = None


class ActionMutationReadinessBlocker(BaseModel):
    code: str
    label: str
    reason: str
    next_step: str


class ActionMutationApplyContract(BaseModel):
    contract: Literal["action_apply_contract_v1"] = "action_apply_contract_v1"
    action_id: str
    action_type: str
    connector: str
    allowed_operation: str
    required_mode: Literal["apply"] = "apply"
    draft_only: bool = True
    publication_allowed: bool = False
    destructive_allowed: bool = False
    adapter_status: Literal["not_implemented", "implemented"] = "not_implemented"
    required_env_flags: list[str] = Field(default_factory=list)
    required_input_contracts: list[str] = Field(default_factory=list)
    required_audit_events: list[str] = Field(default_factory=list)
    blocked_outputs: list[str] = Field(default_factory=list)
    operator_summary: str


class ActionMutationReadinessResponse(BaseModel):
    response_type: Literal["action_mutation_readiness"] = "action_mutation_readiness"
    contract: Literal["action_mutation_readiness_v1"] = "action_mutation_readiness_v1"
    action_id: str
    title: str
    connector: str
    connector_label: str = ""
    mode: ActionMode
    mode_label: str = ""
    risk: ActionRisk
    risk_label: str = ""
    validation_status: Literal["not_validated", "valid", "invalid"]
    review_gate_status: str = ""
    ready_to_request_apply: bool = False
    vendor_write_possible: bool = False
    would_attempt_vendor_write: bool = False
    mutation_adapter: str | None = None
    apply_contract: ActionMutationApplyContract | None = None
    target_candidate_id: str | None = None
    target_label: str | None = None
    target_url: str | None = None
    write_authorization_status: (
        Literal[
            "missing_audit_trace",
            "audit_actor_mismatch",
            "available",
            "blocked_outside_action_apply",
        ]
        | None
    ) = None
    missing_audit_event_types: list[str] = Field(default_factory=list)
    requirements: list[ActionMutationReadinessRequirement] = Field(default_factory=list)
    blockers: list[ActionMutationReadinessBlocker] = Field(default_factory=list)
    operator_next_step: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    latest_mutation_audit_id: str | None = None
    latest_mutation_audit_status: Literal["blocked", "applied", "failed"] | None = None


class ActionMutationReadinessSummaryResponse(BaseModel):
    response_type: Literal["action_mutation_readiness_summary"] = (
        "action_mutation_readiness_summary"
    )
    contract: Literal["action_mutation_readiness_summary_v1"] = (
        "action_mutation_readiness_summary_v1"
    )
    action_count: int = 0
    ready_to_request_apply_count: int = 0
    vendor_write_possible_count: int = 0
    would_attempt_vendor_write_count: int = 0
    prepare_only_count: int = 0
    missing_adapter_count: int = 0
    high_risk_blocked_count: int = 0
    top_blockers: list[str] = Field(default_factory=list)
    first_write_candidate: ActionMutationReadinessResponse | None = None
    first_write_candidate_reason: str = ""
    activation_plan_steps: list[str] = Field(default_factory=list)
    activation_next_step: str = ""
    operator_next_step: str
    items: list[ActionMutationReadinessResponse] = Field(default_factory=list)


ActionReviewOutcome = Literal[
    "approved_for_prepare",
    "needs_changes",
    "rejected",
    "deferred",
]


class ActionReviewRequest(BaseModel):
    outcome: ActionReviewOutcome
    reviewed_by: str = Field(min_length=1)
    notes: str = Field(min_length=1, max_length=2000)
    checked_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    wordpress_draft: ContentDraftRevisionBinding | None = None

    @field_validator("checked_items", "blockers")
    @classmethod
    def no_blank_review_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("review items must not be blank")
        return value


class ActionReviewGate(BaseModel):
    status: Literal[
        "pending_validation",
        "validated_prepare_only",
        "ready_to_apply",
        "blocked_apply",
    ] = "pending_validation"
    status_label: str = ""
    summary: str = "Wymaga walidacji akcji przed kolejnym krokiem."
    required_checks: list[str] = Field(default_factory=list)
    required_check_labels: list[str] = Field(default_factory=list)
    operator_checklist: list[str] = Field(default_factory=list)
    operator_checklist_labels: list[str] = Field(default_factory=list)
    apply_blockers: list[str] = Field(default_factory=list)
    apply_blocker_labels: list[str] = Field(default_factory=list)
    apply_blocker_summary_label: str = ""
    confirmation_required: bool = True
    apply_allowed: bool = False
    last_review_outcome: ActionReviewOutcome | None = None
    last_review_outcome_label: str | None = None
    last_reviewed_by: str | None = None
    last_reviewed_at: datetime | None = None
    last_review_summary: str | None = None
    last_confirmation_by: str | None = None
    last_confirmation_at: datetime | None = None
    last_confirmation_summary: str | None = None
    last_impact_check_status: Literal["checked", "blocked"] | None = None
    last_impact_check_status_label: str | None = None
    last_impact_checked_by: str | None = None
    last_impact_checked_at: datetime | None = None
    last_impact_check_summary: str | None = None
    last_mutation_audit_id: str | None = None
    last_mutation_audit_status: Literal["blocked", "applied", "failed"] | None = None
    last_mutation_audit_status_label: str | None = None
    last_mutation_audit_actor: str | None = None
    last_mutation_audit_at: datetime | None = None
    last_mutation_audit_summary: str | None = None
    last_mutation_adapter_reached: bool | None = None
    last_mutation_adapter_reached_label: str | None = None
    last_external_write_attempted: bool | None = None
    last_external_write_attempted_label: str | None = None
    last_mutation_attempted: bool | None = None
    last_mutation_attempted_label: str | None = None
    last_mutation_adapter: str | None = None
    last_mutation_adapter_label: str | None = None
    last_mutation_audit_event_id: str | None = None
    last_mutation_audit_trace_label: str | None = None
    last_mutation_blockers: list[str] = Field(default_factory=list)
    last_mutation_blocker_labels: list[str] = Field(default_factory=list)
    last_mutation_blocker_summary_label: str = ""

    @model_validator(mode="after")
    def hydrate_summary_labels(self) -> ActionReviewGate:
        if not self.apply_blocker_summary_label:
            self.apply_blocker_summary_label = blocker_count_label(
                self.apply_blocker_labels or self.apply_blockers
            )
        if not self.last_mutation_blocker_summary_label:
            self.last_mutation_blocker_summary_label = blocker_count_label(
                self.last_mutation_blocker_labels or self.last_mutation_blockers
            )
        self.last_impact_check_summary = impact_comparison_summary_label(
            self.last_impact_check_summary
        )
        return self


class ActionPreviewRowViewModel(BaseModel):
    label: str
    value: str


class ActionPreviewCardViewModel(BaseModel):
    id: str
    kind: str
    title_label: str
    subtitle_label: str = ""
    status_label: str = ""
    rows: list[ActionPreviewRowViewModel] = Field(default_factory=list)
    apply_state_label: str = ""
    system_readiness_label: str = ""


class ActionPreviewItemViewModel(BaseModel):
    id: str
    preview_contract: str | None = None
    candidate_id: str | None = None
    title_label: str
    status_label: str = ""
    rows: list[ActionPreviewRowViewModel] = Field(default_factory=list)


class ActionObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    domain: OpportunityDomain
    connector: str
    connector_label: str = ""
    mode: ActionMode
    mode_label: str = ""
    risk: ActionRisk
    risk_label: str = ""
    status: ActionStatus
    status_label: str = ""
    evidence_ids: list[str] = Field(min_length=1)
    evidence_summary_label: str = ""
    metrics: list[MetricFact] = Field(default_factory=list)
    human_diagnosis: str = Field(min_length=1)
    recommended_reason: str
    payload: dict[str, Any]
    validation_status: Literal["not_validated", "valid", "invalid"]
    validation_status_label: str = ""
    review_gate: ActionReviewGate = Field(default_factory=ActionReviewGate)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    audit_events: list[AuditEvent] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("Identyfikatory dowodów akcji nie mogą być puste")
        return value


class ActionValidationResult(BaseModel):
    action_id: str
    valid: bool
    status: Literal["valid", "invalid"]
    status_label: str = ""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=utc_now)


class ActionApplyResult(BaseModel):
    action_id: str
    applied: bool
    status: Literal["applied", "blocked", "failed"]
    status_label: str = ""
    audit_event: AuditEvent
    mutation_audit: ActionMutationAuditRecord
    errors: list[str] = Field(default_factory=list)
    wordpress_revision_blockers: list[ActionWordPressDraftApplyBlocker] = Field(
        default_factory=list
    )
    adapter_result: dict[str, Any] | None = None


class ActionPreviewRequest(BaseModel):
    requested_by: str | None = None
    max_items: int = Field(default=8, ge=1, le=50)
    wordpress_draft: ContentDraftRevisionBinding | None = None


class ActionPreviewResult(BaseModel):
    action_id: str
    status: Literal["preview_ready", "blocked"]
    status_label: str = ""
    dry_run: bool = True
    mutation_allowed: bool = False
    preview_contract: str | None = None
    preview_items: list[ActionPreviewItemViewModel] = Field(default_factory=list)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
    preview_items_total: int = 0
    omitted_items: int = 0
    blockers: list[str] = Field(default_factory=list)
    blocker_labels: list[str] = Field(default_factory=list)
    audit_event: AuditEvent
    review_gate: ActionReviewGate


class ActionReviewResult(BaseModel):
    action_id: str
    status: Literal["recorded"]
    status_label: str = ""
    audit_event: AuditEvent
    review_gate: ActionReviewGate


class AdsExternalExecutionAcknowledgementRequest(BaseModel):
    """Human report that an Ads recommendation was executed outside WILQ."""

    model_config = ConfigDict(extra="forbid")

    measurement_plan_id: str = Field(min_length=1)
    execution_status: Literal["executed", "not_executed", "unknown"]
    acknowledged_by: str = Field(min_length=1, max_length=200)
    executed_at: datetime | None = None
    notes: str = Field(min_length=1, max_length=2000)


class ActionConfirmRequest(BaseModel):
    confirmed_by: str = Field(min_length=1)
    notes: str = Field(min_length=1, max_length=2000)
    preview_acknowledged: bool = False
    target_roas: float | None = Field(default=None, gt=0)
    target_cpa_micros: int | None = Field(default=None, gt=0)
    wordpress_draft: ContentDraftRevisionBinding | None = None


class ActionConfirmResult(BaseModel):
    action_id: str
    confirmed: bool
    status: Literal["confirmed", "blocked"]
    status_label: str = ""
    blockers: list[str] = Field(default_factory=list)
    blocker_labels: list[str] = Field(default_factory=list)
    audit_event: AuditEvent
    review_gate: ActionReviewGate


class AdsTargetGuardrailConfirmation(BaseModel):
    id: str
    connector_id: Literal["google_ads"] = "google_ads"
    action_id: str
    target_roas: float | None = Field(default=None, gt=0)
    target_cpa_micros: int | None = Field(default=None, gt=0)
    confirmed_by: str = Field(min_length=1)
    notes: str = Field(min_length=1, max_length=2000)
    audit_event_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def exactly_one_target(self) -> AdsTargetGuardrailConfirmation:
        target_count = int(self.target_roas is not None) + int(self.target_cpa_micros is not None)
        if target_count != 1:
            raise ValueError("exactly one Ads target guardrail must be confirmed")
        return self


class AdsStrategyReviewRecord(BaseModel):
    id: str
    connector_id: Literal["google_ads"] = "google_ads"
    action_id: str
    outcome: ActionReviewOutcome
    reviewed_by: str = Field(min_length=1)
    notes: str = Field(min_length=1, max_length=2000)
    checked_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    audit_event_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ActionImpactCheckRequest(BaseModel):
    checked_by: str = Field(min_length=1)
    notes: str = Field(min_length=1, max_length=2000)
    pre_window_days: int = Field(default=7, ge=1, le=90)
    post_window_days: int = Field(default=7, ge=1, le=90)
    wordpress_draft: ContentDraftRevisionBinding | None = None


class ActionImpactCheckResult(BaseModel):
    action_id: str
    status: Literal["checked", "blocked"]
    status_label: str = ""
    pre_window_days: int
    post_window_days: int
    metric_fact_count: int = 0
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    blockers: list[str] = Field(default_factory=list)
    blocker_labels: list[str] = Field(default_factory=list)
    audit_event: AuditEvent
    review_gate: ActionReviewGate


ActionWordPressDraftApplyInput = ContentDraftRevisionBinding


class ActionApplyRequest(BaseModel):
    confirm: bool = False
    confirmed_by: str | None = None
    wordpress_draft: ActionWordPressDraftApplyInput | None = None


class CodexRun(BaseModel):
    id: str
    skill: str | None = None
    hook: str | None = None
    source: str | None = None
    status: Literal["started", "completed", "failed", "blocked"]
    used_endpoints: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    error: str | None = None
