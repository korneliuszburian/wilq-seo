from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ConnectorStatusValue(StrEnum):
    configured = "configured"
    missing_credentials = "missing_credentials"
    missing_dependency = "missing_dependency"
    unreachable = "unreachable"
    auth_error = "auth_error"
    rate_limited = "rate_limited"
    error = "error"
    disabled = "disabled"


class ConnectorRefreshMode(StrEnum):
    status_probe = "status_probe"
    vendor_read = "vendor_read"


class ConnectorRefreshStatus(StrEnum):
    completed = "completed"
    blocked = "blocked"
    failed = "failed"


class ActionMode(StrEnum):
    suggest = "suggest"
    prepare = "prepare"
    apply = "apply"


class ActionRisk(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ActionStatus(StrEnum):
    new = "new"
    ready = "ready"
    needs_validation = "needs_validation"
    validation_failed = "validation_failed"
    ready_to_apply = "ready_to_apply"
    applying = "applying"
    applied = "applied"
    failed = "failed"
    dismissed = "dismissed"
    blocked = "blocked"


class OpportunityDomain(StrEnum):
    google_ads = "google_ads"
    gsc_seo = "gsc_seo"
    ahrefs = "ahrefs"
    localo = "localo"
    wordpress = "wordpress"
    social = "social"
    knowledge = "knowledge"
    content = "content"
    codex = "codex"
    ga4 = "ga4"
    merchant = "merchant"
    google_sheets = "google_sheets"


class FreshnessState(BaseModel):
    state: Literal["fresh", "stale", "unknown", "missing"]
    last_success_at: datetime | None = None
    checked_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class ConnectorCapability(BaseModel):
    read: bool = True
    write: bool = False
    operations: list[str] = Field(default_factory=list)


class ConnectorStatus(BaseModel):
    id: str
    label: str
    status: ConnectorStatusValue
    configured: bool
    missing_credentials: list[str] = Field(default_factory=list)
    available_credential_sources: list[str] = Field(default_factory=list)
    error: str | None = None
    last_success_at: datetime | None = None
    freshness: FreshnessState
    capabilities: ConnectorCapability
    required_env: list[str] = Field(default_factory=list)
    supported_actions: list[str] = Field(default_factory=list)
    rate_limit_notes: str | None = None
    cost_notes: str | None = None
    risk_notes: str | None = None
    health_check: str


class Evidence(BaseModel):
    id: str
    source_connector: str
    source_type: str
    source_id: str
    collected_at: datetime = Field(default_factory=utc_now)
    freshness: FreshnessState
    summary: str
    raw_ref: str | None = None


class ConnectorRefreshRequest(BaseModel):
    mode: ConnectorRefreshMode = ConnectorRefreshMode.status_probe
    reason: str | None = None


class ConnectorRefreshRun(BaseModel):
    id: str
    connector_id: str
    mode: ConnectorRefreshMode
    status: ConnectorRefreshStatus
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    missing_credentials: list[str] = Field(default_factory=list)
    checked_credentials: list[str] = Field(default_factory=list)
    external_call_attempted: bool = False
    vendor_data_collected: bool = False
    metric_summary: dict[str, float | int | str] = Field(default_factory=dict)
    summary: str
    errors: list[str] = Field(default_factory=list)
    redacted: bool = True


class MetricFact(BaseModel):
    name: str
    value: float | int | str
    period: str
    source_connector: str
    evidence_id: str
    dimensions: dict[str, str] = Field(default_factory=dict)
    unit: str | None = None
    collected_at: datetime | None = None
    previous_value: float | int | str | None = None
    delta: float | int | None = None
    delta_percent: float | None = None
    trend: Literal["up", "down", "flat", "unknown"] = "unknown"
    freshness_state: Literal["fresh", "stale", "unknown"] = "unknown"
    freshness_label: str | None = None


class Opportunity(BaseModel):
    id: str
    type: str
    title: str
    domain: OpportunityDomain
    source_connectors: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    metrics: list[MetricFact] = Field(default_factory=list)
    human_diagnosis: str = Field(min_length=1)
    recommended_action: str
    risk: ActionRisk = ActionRisk.low
    action_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    playbook_ids: list[str] = Field(default_factory=list)
    is_fixture: bool = False

    @field_validator("source_connectors", "evidence_ids")
    @classmethod
    def no_blank_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("items must not be blank")
        return value


class AuditEvent(BaseModel):
    id: str
    action_id: str | None = None
    event_type: str
    actor: str
    created_at: datetime = Field(default_factory=utc_now)
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    redacted: bool = True


class ActionMutationAuditRecord(BaseModel):
    id: str
    action_id: str
    connector: str
    action_type: str | None = None
    status: Literal["blocked", "applied", "failed"]
    mutation_attempted: bool = False
    mutation_adapter: str | None = None
    actor: str
    created_at: datetime = Field(default_factory=utc_now)
    audit_event_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    summary: str
    redacted: bool = True


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
    summary: str = "Wymaga walidacji ActionObject przed kolejnym krokiem."
    required_checks: list[str] = Field(default_factory=list)
    operator_checklist: list[str] = Field(default_factory=list)
    apply_blockers: list[str] = Field(default_factory=list)
    confirmation_required: bool = True
    apply_allowed: bool = False
    last_review_outcome: ActionReviewOutcome | None = None
    last_reviewed_by: str | None = None
    last_reviewed_at: datetime | None = None
    last_review_summary: str | None = None
    last_confirmation_by: str | None = None
    last_confirmation_at: datetime | None = None
    last_confirmation_summary: str | None = None
    last_impact_check_status: Literal["checked", "blocked"] | None = None
    last_impact_checked_by: str | None = None
    last_impact_checked_at: datetime | None = None
    last_impact_check_summary: str | None = None
    last_mutation_audit_id: str | None = None
    last_mutation_audit_status: Literal["blocked", "applied", "failed"] | None = None
    last_mutation_audit_actor: str | None = None
    last_mutation_audit_at: datetime | None = None
    last_mutation_audit_summary: str | None = None
    last_mutation_attempted: bool | None = None
    last_mutation_adapter: str | None = None
    last_mutation_audit_event_id: str | None = None
    last_mutation_blockers: list[str] = Field(default_factory=list)


class ActionObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    domain: OpportunityDomain
    connector: str
    mode: ActionMode
    risk: ActionRisk
    status: ActionStatus
    evidence_ids: list[str] = Field(min_length=1)
    metrics: list[MetricFact] = Field(default_factory=list)
    human_diagnosis: str = Field(min_length=1)
    recommended_reason: str
    payload: dict[str, Any]
    validation_status: Literal["not_validated", "valid", "invalid"]
    review_gate: ActionReviewGate = Field(default_factory=ActionReviewGate)
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    audit_events: list[AuditEvent] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("ActionObject evidence IDs must not be blank")
        return value


class ActionValidationResult(BaseModel):
    action_id: str
    valid: bool
    status: Literal["valid", "invalid"]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=utc_now)


class ActionApplyResult(BaseModel):
    action_id: str
    applied: bool
    status: Literal["applied", "blocked", "failed"]
    audit_event: AuditEvent
    mutation_audit: ActionMutationAuditRecord
    errors: list[str] = Field(default_factory=list)


class ActionPreviewRequest(BaseModel):
    requested_by: str | None = None
    max_items: int = Field(default=8, ge=1, le=50)


class ActionPreviewResult(BaseModel):
    action_id: str
    status: Literal["preview_ready", "blocked"]
    dry_run: bool = True
    mutation_allowed: bool = False
    preview_contract: str | None = None
    preview_items: list[dict[str, Any]] = Field(default_factory=list)
    preview_items_total: int = 0
    omitted_items: int = 0
    blockers: list[str] = Field(default_factory=list)
    audit_event: AuditEvent
    review_gate: ActionReviewGate


class ActionReviewResult(BaseModel):
    action_id: str
    status: Literal["recorded"]
    audit_event: AuditEvent
    review_gate: ActionReviewGate


class ActionConfirmRequest(BaseModel):
    confirmed_by: str = Field(min_length=1)
    notes: str = Field(min_length=1, max_length=2000)
    preview_acknowledged: bool = False
    target_roas: float | None = Field(default=None, gt=0)
    target_cpa_micros: int | None = Field(default=None, gt=0)


class ActionConfirmResult(BaseModel):
    action_id: str
    confirmed: bool
    status: Literal["confirmed", "blocked"]
    blockers: list[str] = Field(default_factory=list)
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
        target_count = int(self.target_roas is not None) + int(
            self.target_cpa_micros is not None
        )
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


class ActionImpactCheckResult(BaseModel):
    action_id: str
    status: Literal["checked", "blocked"]
    pre_window_days: int
    post_window_days: int
    metric_fact_count: int = 0
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    audit_event: AuditEvent
    review_gate: ActionReviewGate


class ActionApplyRequest(BaseModel):
    confirm: bool = False
    confirmed_by: str | None = None


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


class SourceDocument(BaseModel):
    id: str
    title: str
    source_type: str
    source_url_or_path: str
    last_checked: str
    summary: str


class KnowledgeCard(BaseModel):
    id: str
    card_type: str
    title: str
    summary: str
    source_type: str
    source_id: str
    source_url_or_path: str
    extracted_at: datetime = Field(default_factory=utc_now)
    confidence: float = Field(ge=0, le=1)
    last_seen_at: datetime = Field(default_factory=utc_now)
    source_lineage: list[str] = Field(default_factory=list)


class MarketingPlaybook(BaseModel):
    id: str
    family: str
    title: str
    card_type: str
    source_anchors: list[str] = Field(min_length=1)
    required_evidence: list[str] = Field(min_length=1)
    maps_to_opportunity_types: list[str] = Field(min_length=1)
    maps_to_action_types: list[str] = Field(min_length=1)
    expert_rule_ids: list[str] = Field(default_factory=list)
    compact_playbook: str = Field(min_length=1)
    refusal_rules: list[str] = Field(default_factory=list)
    output_contract: str = Field(min_length=1)
    source_path: str


class KnowledgeCompilerResult(BaseModel):
    status: Literal["completed", "failed"]
    generated_at: datetime = Field(default_factory=utc_now)
    card_count: int
    cards: list[KnowledgeCard]


class KnowledgeDecisionBinding(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "planned"]
    route: str
    skill_id: str | None = None
    summary: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    playbook_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    missing_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_lineage: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class KnowledgeOperatingMapResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    source_card_count: int
    playbook_count: int
    expert_rule_count: int
    binding_count: int
    bindings: list[KnowledgeDecisionBinding] = Field(default_factory=list)


class ExpertRule(BaseModel):
    id: str
    name: str
    domain: str
    version: int
    source_anchor: str
    source_path: str
    when_to_use: str | None = None
    required_inputs: list[str] = Field(default_factory=list)
    diagnostic_logic: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    risk_notes: str | None = None
    output_contract: str
    capabilities: list[str] = Field(default_factory=list)
    required_mapping: list[str] = Field(default_factory=list)
    requires_evidence: bool = True


class ExpertRuleSummary(BaseModel):
    id: str
    name: str
    domain: str
    source_anchor: str
    required_inputs: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    output_contract: str
    requires_evidence: bool = True


class ExpertCapability(BaseModel):
    id: str
    domain: str
    source_rule_id: str
    required_mapping: list[str] = Field(default_factory=list)
    output_contract: str
    requires_evidence: bool = True


class ServiceCard(KnowledgeCard):
    card_type: Literal["service_card"] = "service_card"


class ContentCard(KnowledgeCard):
    card_type: Literal["content_card"] = "content_card"


class KeywordClusterCard(KnowledgeCard):
    card_type: Literal["keyword_cluster_card"] = "keyword_cluster_card"


class CampaignCard(KnowledgeCard):
    card_type: Literal["campaign_card"] = "campaign_card"


class VoiceRule(KnowledgeCard):
    card_type: Literal["voice_rule"] = "voice_rule"


class ConnectorSummary(BaseModel):
    total: int
    configured: int
    missing_credentials: int


class MarketingBriefItem(BaseModel):
    id: str
    title: str
    kind: Literal["metric", "blocker", "action", "recommendation"]
    priority: int = Field(ge=1, le=100)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    summary: str
    next_step: str
    risk: ActionRisk = ActionRisk.low
    blocker_reason: str | None = None


class MarketingBriefSection(BaseModel):
    id: str
    title: str
    description: str
    items: list[MarketingBriefItem] = Field(default_factory=list)


class MarketingBrief(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector_summary: ConnectorSummary
    sections: list[MarketingBriefSection]
    top_metric_facts: list[MetricFact] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0
    recommendation_count: int = 0


class TacticalQueueItem(BaseModel):
    id: str
    title: str
    domain: OpportunityDomain
    intent: Literal[
        "content_refresh",
        "content_create",
        "content_merge",
        "content_block",
        "landing_page_quality",
        "tracking_gap",
        "merchant_feed_triage",
        "traffic_quality_review",
    ]
    priority: int = Field(ge=1, le=100)
    risk: ActionRisk = ActionRisk.low
    source_connectors: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    dimensions: dict[str, str] = Field(default_factory=dict)
    diagnosis: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)

    @field_validator("source_connectors", "evidence_ids")
    @classmethod
    def require_nonblank_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("Tactical queue trace IDs must not be blank")
        return value


class TacticalQueueResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    items: list[TacticalQueueItem] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)


class AdsDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class AdsBlockedHandoff(BaseModel):
    id: str = "ads_oauth_blocked_handoff"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    marketer_message: str
    repair_steps: list[str] = Field(default_factory=list)
    allowed_demo_claims: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)


class AdsCampaignMetricRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak targetu"
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = (
        "niski sygnał"
    )
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str = ""
    human_review_gates: list[str] = Field(default_factory=list)


class AdsCampaignReadContract(BaseModel):
    id: str = "ads_campaign_activity_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    next_step: str


class AdsAccountCurrencyReadContract(BaseModel):
    id: str = "ads_account_currency_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    currency_code: str | None = None
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsBusinessTargetInterpretation(BaseModel):
    id: str = "ads_business_target_interpretation"
    interpretation_contract: Literal["ads_business_target_interpretation_v1"] = (
        "ads_business_target_interpretation_v1"
    )
    status: Literal["ready", "preliminary", "blocked"]
    summary: str
    allowed_uses: list[str] = Field(default_factory=list)
    blocked_uses: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    apply_allowed: bool = False
    destructive: bool = False


class AdsBusinessContextReadContract(BaseModel):
    id: str = "ads_business_context_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    profit_margin: float | None = None
    business_goal: str | None = None
    budget_goal: str | None = None
    target_roas: float | None = None
    target_cpa_micros: int | None = None
    strategy_review_status: Literal[
        "missing",
        "approved_for_prepare",
        "needs_changes",
        "rejected",
        "deferred",
    ] = "missing"
    strategy_reviewed_by: str | None = None
    strategy_reviewed_at: datetime | None = None
    strategy_review_summary: str | None = None
    configured_sources: list[str] = Field(default_factory=list)
    business_policy_ids: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    target_interpretation: AdsBusinessTargetInterpretation
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    next_step: str


class AdsDerivedKpiRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    ctr: float | None = None
    average_cpc_micros: float | None = None
    conversion_rate: float | None = None
    cost_per_conversion_micros: float | None = None
    roas: float | None = None
    value_per_conversion: float | None = None
    target_roas: float | None = None
    roas_vs_target: float | None = None
    target_cpa_micros: int | None = None
    cpa_vs_target_micros: float | None = None
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak targetu"
    target_review_priority: int = 90
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsDerivedKpiReadContract(BaseModel):
    id: str = "ads_derived_kpi_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    kpi_rows: list[AdsDerivedKpiRow] = Field(default_factory=list)
    next_step: str


class AdsBudgetApplySafetyReview(BaseModel):
    id: str
    budget_preview_id: str
    safety_contract: Literal["campaign_budget_apply_safety_v1"] = (
        "campaign_budget_apply_safety_v1"
    )
    status: Literal["blocked"] = "blocked"
    reason: str
    max_allowed_delta_percent: float = 0.3
    current_budget_amount_micros: int | None = None
    proposed_budget_amount_micros: int | None = None
    proposed_delta_percent: float | None = None
    missing_requirements: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsBudgetApplyPreview(BaseModel):
    id: str
    campaign_id: str | None = None
    campaign_name: str
    campaign_budget_id: str | None = None
    campaign_budget_name: str | None = None
    operation_type: Literal["CampaignBudgetOperation"] = "CampaignBudgetOperation"
    current_budget_amount_micros: int | None = None
    proposed_budget_amount_micros: int | None = None
    proposed_budget_delta_micros: int | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    safety_review: AdsBudgetApplySafetyReview
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsBudgetPacingRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    budget_id: str | None = None
    budget_name: str | None = None
    budget_period: str | None = None
    budget_status: str | None = None
    budget_amount_micros: int | None = None
    cost_micros_7d: int | None = None
    seven_day_budget_micros: int | None = None
    spend_to_budget_ratio_7d: float | None = None
    has_recommended_budget: bool | None = None
    recommended_budget_amount_micros: int | None = None
    recommended_budget_delta_micros: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    payload_preview: AdsBudgetApplyPreview | None = None
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsSharedBudgetCampaignShare(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    cost_micros_7d: int | None = None
    spend_share_7d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class AdsSharedBudgetDistributionRow(BaseModel):
    budget_id: str
    budget_name: str | None = None
    campaign_count: int
    budget_amount_micros: int | None = None
    seven_day_budget_micros: int | None = None
    total_cost_micros_7d: int | None = None
    spend_to_budget_ratio_7d: float | None = None
    campaign_shares: list[AdsSharedBudgetCampaignShare] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsBudgetPacingReadContract(BaseModel):
    id: str = "ads_budget_pacing_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    budget_rows: list[AdsBudgetPacingRow] = Field(default_factory=list)
    shared_budget_distribution_rows: list[AdsSharedBudgetDistributionRow] = Field(
        default_factory=list
    )
    payload_preview: list[AdsBudgetApplyPreview] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsRecommendationApplyPreview(BaseModel):
    id: str
    recommendation_id: str | None = None
    recommendation_resource_name: str | None = None
    recommendation_type: str
    campaign_id: str | None = None
    campaign_budget_id: str | None = None
    operation_type: Literal["ApplyRecommendationOperation"] = "ApplyRecommendationOperation"
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsRecommendationRow(BaseModel):
    recommendation_id: str | None = None
    recommendation_resource_name: str | None = None
    recommendation_type: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = (
        "normalne"
    )
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    dismissed: bool = False
    campaign_id: str | None = None
    campaign_budget_id: str | None = None
    campaign_count: int | None = None
    impact_available: bool = False
    base_clicks: int | None = None
    potential_clicks: int | None = None
    delta_clicks: int | None = None
    base_impressions: int | None = None
    potential_impressions: int | None = None
    delta_impressions: int | None = None
    base_cost_micros: int | None = None
    potential_cost_micros: int | None = None
    delta_cost_micros: int | None = None
    base_conversions: float | None = None
    potential_conversions: float | None = None
    delta_conversions: float | None = None
    base_conversion_value: float | None = None
    potential_conversion_value: float | None = None
    delta_conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    payload_preview: AdsRecommendationApplyPreview | None = None
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsRecommendationsReadContract(BaseModel):
    id: str = "ads_recommendations_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    recommendation_rows: list[AdsRecommendationRow] = Field(default_factory=list)
    payload_preview: list[AdsRecommendationApplyPreview] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsImpressionShareRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    search_impression_share: float | None = None
    search_budget_lost_impression_share: float | None = None
    search_rank_lost_impression_share: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsImpressionShareReadContract(BaseModel):
    id: str = "ads_impression_share_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    impression_share_rows: list[AdsImpressionShareRow] = Field(default_factory=list)
    next_step: str


class AdsChangeHistoryRow(BaseModel):
    change_event_id: str | None = None
    change_date_time: str | None = None
    change_resource_id: str | None = None
    change_resource_type: str | None = None
    resource_change_operation: str | None = None
    client_type: str | None = None
    campaign_id: str | None = None
    changed_field_count: int | None = None
    changed_fields: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsChangeHistoryReadContract(BaseModel):
    id: str = "ads_change_history_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    change_history_rows: list[AdsChangeHistoryRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsSearchTermMetricRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    search_term_status: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsSearchTermsReadContract(BaseModel):
    id: str = "ads_search_terms_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    next_step: str


class AdsSearchTermNgramRow(BaseModel):
    ngram: str
    ngram_size: int = Field(ge=1, le=3)
    source_search_term_count: int = 0
    sample_search_terms: list[str] = Field(default_factory=list)
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsSearchTermNgramReadContract(BaseModel):
    id: str = "ads_search_term_ngram_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    ngram_rows: list[AdsSearchTermNgramRow] = Field(default_factory=list)
    next_step: str


class AdsSearchTermSafetyRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    search_term_status: str | None = None
    clicks_90d: int | None = None
    impressions_90d: int | None = None
    cost_micros_90d: int | None = None
    conversions_90d: float | None = None
    conversion_value_90d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsSearchTermSafetyReadContract(BaseModel):
    id: str = "ads_search_term_safety_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    safety_rows: list[AdsSearchTermSafetyRow] = Field(default_factory=list)
    next_step: str


class AdsKeywordMatchContextRow(BaseModel):
    keyword_text: str
    match_type: str
    criterion_id: str | None = None
    criterion_status: str | None = None
    negative: bool | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsKeywordMatchContextReadContract(BaseModel):
    id: str = "ads_keyword_match_context_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    context_rows: list[AdsKeywordMatchContextRow] = Field(default_factory=list)
    next_step: str


class AdsCustomSegmentTargetingPreview(BaseModel):
    id: str
    custom_segment_preview_id: str
    target_scope: Literal["campaign_context_review"] = "campaign_context_review"
    campaign_id: str | None = None
    campaign_name: str | None = None
    operation_type: Literal["custom_segment_targeting_review"] = (
        "custom_segment_targeting_review"
    )
    reason: str
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentPayloadPreview(BaseModel):
    id: str
    custom_segment_name: str
    member_type: Literal["KEYWORD"] = "KEYWORD"
    source_terms: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    campaign_name: str | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    targeting_preview: list[AdsCustomSegmentTargetingPreview] = Field(
        default_factory=list
    )
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentAudienceForecastRow(BaseModel):
    id: str
    candidate_id: str
    custom_segment_name: str
    status: Literal["ready", "missing_forecast"] = "missing_forecast"
    forecast_available: bool = False
    audience_size: int | None = None
    source_terms: list[str] = Field(default_factory=list)
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsCustomSegmentAudienceForecastReadContract(BaseModel):
    id: str = "ads_custom_segment_audience_forecast_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    checked_candidate_count: int = 0
    forecast_row_count: int = 0
    forecast_rows: list[AdsCustomSegmentAudienceForecastRow] = Field(
        default_factory=list
    )
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    next_step: str


def default_ads_custom_segment_audience_forecast_contract() -> (
    AdsCustomSegmentAudienceForecastReadContract
):
    return AdsCustomSegmentAudienceForecastReadContract(
        status="blocked",
        title="Forecast i audience size custom segments",
        summary=(
            "Brak kandydatów custom segments do sprawdzenia forecastu albo audience size."
        ),
        missing_read_contracts=["custom_segment_candidates", "forecast_or_audience_size"],
        operator_review_gates=["forecast_or_audience_size", "human_confirm_before_apply"],
        blocked_claims=["audience size", "conversion uplift", "ROAS", "targeting applied"],
        next_step=(
            "Najpierw zbuduj kandydatów custom segments z realnych source terms."
        ),
    )


class AdsKeywordPlannerIdeaRow(BaseModel):
    idea_text: str
    avg_monthly_searches: int | None = None
    competition: str | None = None
    competition_index: int | None = None
    low_top_of_page_bid_micros: int | None = None
    high_top_of_page_bid_micros: int | None = None
    source_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class AdsKeywordPlannerReadContract(BaseModel):
    id: str = "ads_keyword_planner_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    idea_rows: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    next_step: str


class AdsCustomSegmentSourceQuality(BaseModel):
    total_terms: int = 0
    accepted_terms: int = 0
    rejected_terms: int = 0
    missing_metric_terms: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)


class AdsCustomSegmentCandidate(BaseModel):
    id: str
    name: str
    intent: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = (
        "normalne"
    )
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    source_terms: list[str] = Field(default_factory=list)
    rejected_terms: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    source_quality: AdsCustomSegmentSourceQuality = Field(
        default_factory=AdsCustomSegmentSourceQuality
    )
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
    validation_status: Literal["pending_validation", "blocked"] = "pending_validation"
    payload_preview: AdsCustomSegmentPayloadPreview | None = None
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str


class AdsCustomSegmentsReadContract(BaseModel):
    id: str = "ads_custom_segments_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    candidates: list[AdsCustomSegmentCandidate] = Field(default_factory=list)
    payload_preview: list[AdsCustomSegmentPayloadPreview] = Field(default_factory=list)
    audience_forecast_read_contract: AdsCustomSegmentAudienceForecastReadContract = (
        Field(default_factory=default_ads_custom_segment_audience_forecast_contract)
    )
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsNegativeKeywordPayloadPreview(BaseModel):
    id: str
    search_term: str
    negative_keyword_text: str
    match_type: Literal["EXACT"]
    level: Literal["ad_group", "campaign_review_required"]
    campaign_id: str | None = None
    campaign_name: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsNegativeKeywordCandidate(BaseModel):
    id: str
    search_term: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = (
        "normalne"
    )
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    campaign_name: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    clicks_90d: int | None = None
    impressions_90d: int | None = None
    cost_micros_90d: int | None = None
    conversions_90d: float | None = None
    conversion_value_90d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    safety_evidence_ids: list[str] = Field(default_factory=list)
    keyword_context_evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    safety_metric_facts: list[MetricFact] = Field(default_factory=list)
    keyword_context_rows: list[AdsKeywordMatchContextRow] = Field(default_factory=list)
    payload_preview: AdsNegativeKeywordPayloadPreview | None = None
    required_checks: list[str] = Field(default_factory=list)
    safety_status: Literal[
        "needs_90_day_review",
        "read_ready_needs_human_review",
        "blocked",
    ] = "needs_90_day_review"
    validation_status: Literal["pending_validation", "blocked"] = "pending_validation"
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str


class AdsNegativeKeywordsReadContract(BaseModel):
    id: str = "ads_negative_keywords_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    candidates: list[AdsNegativeKeywordCandidate] = Field(default_factory=list)
    payload_preview: list[AdsNegativeKeywordPayloadPreview] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_campaign_activity",
        "review_business_context",
        "review_derived_kpi",
        "review_budget_context",
        "review_recommendations",
        "review_impression_share",
        "review_change_history",
        "review_search_term_safety",
        "review_search_terms",
        "review_search_term_ngrams",
        "review_negative_keyword_safety",
        "prepare_custom_segments",
        "block_write_actions",
        "fix_ads_access",
    ]
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    rationale: str
    next_step: str
    priority: int = Field(default=50, ge=1, le=100)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    derived_kpi_rows: list[AdsDerivedKpiRow] = Field(default_factory=list)
    budget_rows: list[AdsBudgetPacingRow] = Field(default_factory=list)
    shared_budget_distribution_rows: list[AdsSharedBudgetDistributionRow] = Field(
        default_factory=list
    )
    budget_apply_preview: list[AdsBudgetApplyPreview] = Field(default_factory=list)
    recommendation_rows: list[AdsRecommendationRow] = Field(default_factory=list)
    recommendation_apply_preview: list[AdsRecommendationApplyPreview] = Field(
        default_factory=list
    )
    impression_share_rows: list[AdsImpressionShareRow] = Field(default_factory=list)
    change_history_rows: list[AdsChangeHistoryRow] = Field(default_factory=list)
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    search_term_ngram_rows: list[AdsSearchTermNgramRow] = Field(default_factory=list)
    search_term_safety_rows: list[AdsSearchTermSafetyRow] = Field(default_factory=list)
    keyword_match_context_rows: list[AdsKeywordMatchContextRow] = Field(
        default_factory=list
    )
    keyword_planner_idea_rows: list[AdsKeywordPlannerIdeaRow] = Field(
        default_factory=list
    )
    custom_segment_candidates: list[AdsCustomSegmentCandidate] = Field(default_factory=list)
    custom_segment_payload_preview: list[AdsCustomSegmentPayloadPreview] = Field(
        default_factory=list
    )
    custom_segment_audience_forecast_rows: list[
        AdsCustomSegmentAudienceForecastRow
    ] = Field(default_factory=list)
    negative_keyword_candidates: list[AdsNegativeKeywordCandidate] = Field(default_factory=list)
    negative_keyword_payload_preview: list[AdsNegativeKeywordPayloadPreview] = Field(
        default_factory=list
    )
    action_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class AdsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    live_data_available: bool
    campaign_read_contract: AdsCampaignReadContract
    account_currency_read_contract: AdsAccountCurrencyReadContract
    business_context_read_contract: AdsBusinessContextReadContract
    derived_kpi_read_contract: AdsDerivedKpiReadContract
    budget_pacing_read_contract: AdsBudgetPacingReadContract
    recommendations_read_contract: AdsRecommendationsReadContract
    impression_share_read_contract: AdsImpressionShareReadContract
    change_history_read_contract: AdsChangeHistoryReadContract
    search_terms_read_contract: AdsSearchTermsReadContract
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract
    keyword_planner_read_contract: AdsKeywordPlannerReadContract
    custom_segments_read_contract: AdsCustomSegmentsReadContract
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract
    decision_queue: list[AdsDecisionItem] = Field(default_factory=list)
    sections: list[AdsDiagnosticSection] = Field(default_factory=list)
    blocked_handoff: AdsBlockedHandoff | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class DemandGenAdGroupAdRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_id: str | None = None
    ad_type: str | None = None
    ad_status: str | None = None
    final_url_count: int = 0
    asset_reference_count: int = 0
    evidence_ids: list[str] = Field(default_factory=list)


class DemandGenCreativeAssetRow(BaseModel):
    asset_id: str | None = None
    asset_type: str | None = None
    field_type: str | None = None
    impressions: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class DemandGenLandingQualityRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    landing_page: str
    source_medium: str | None = None
    active_users: int | None = None
    sessions: int | None = None
    engagement_rate: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class DemandGenMigrationConstraintRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    advertising_channel_type: str | None = None
    migration_candidate: bool = False
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class MerchantDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class MerchantIssueCluster(BaseModel):
    id: str
    issue_type: str
    severity: str
    resolution: str | None = None
    affected_attribute: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    product_count: int = 0
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_titles: list[str] = Field(default_factory=list)
    sample_unavailable_reason: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    action_id: str | None = None
    risk: ActionRisk = ActionRisk.low
    next_step: str


class MerchantDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_issue_cluster",
        "review_feed_status",
        "block_until_vendor_read",
    ]
    status: Literal["ready", "blocked", "missing"]
    title: str
    summary: str | None = None
    cluster_id: str | None = None
    issue_type: str | None = None
    severity: str | None = None
    resolution: str | None = None
    affected_attribute: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    product_count: int | None = None
    issue_count: int | None = None
    priority: int = Field(ge=1, le=100)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low


class MerchantDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    live_data_available: bool
    product_count: int | None = None
    issue_count: int | None = None
    issue_clusters: list[MerchantIssueCluster] = Field(default_factory=list)
    decision_queue: list[MerchantDecisionItem] = Field(default_factory=list)
    sections: list[MerchantDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class ContentDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class ContentAhrefsCandidateRow(BaseModel):
    id: str
    topic: str
    gap_type: str
    relevance_status: Literal["relevant", "review", "off_topic"]
    relevance_score: int
    business_relevance_reasons: list[str] = Field(default_factory=list)
    gsc_demand: Literal["present", "missing"]
    wordpress_inventory_match: Literal["present", "missing"]
    gsc_overlap_terms: list[str] = Field(default_factory=list)
    wordpress_overlap_urls: list[str] = Field(default_factory=list)
    keyword: str | None = None
    competitor_domain: str | None = None
    source_url: str | None = None
    target_url: str | None = None
    metric_name: str
    metric_value: int | float | str
    evidence_ids: list[str] = Field(default_factory=list)
    next_step: str


class ContentDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "refresh_or_merge",
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
        "block_as_tracking_not_content",
        "review_ahrefs_gap_records",
    ]
    status: Literal["ready", "blocked"] = "ready"
    title: str
    summary: str | None = None
    priority: int = 50
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    page: str | None = None
    normalized_page_path: str | None = None
    queries: list[str] = Field(default_factory=list)
    query_count: int = 0
    primary_query: str | None = None
    total_clicks: int | None = None
    total_impressions: int | None = None
    aggregate_ctr: float | None = None
    best_average_position: float | None = None
    wordpress_match: str | None = None
    wordpress_match_confidence: str | None = None
    wordpress_content_url: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    ahrefs_candidate_rows: list[ContentAhrefsCandidateRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low


class ContentDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connectors: list[ConnectorStatus]
    latest_refreshes: list[ConnectorRefreshRun] = Field(default_factory=list)
    live_data_available: bool
    query_page_count: int = 0
    matched_inventory_count: int = 0
    decision_queue: list[ContentDecisionItem] = Field(default_factory=list)
    sections: list[ContentDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class Ga4TrackingQualityPayloadPreview(BaseModel):
    id: str
    preview_contract: Literal["ga4_tracking_quality_review_v1"]
    operation_type: Literal["tracking_quality_review"]
    landing_page: str | None = None
    source_medium: str | None = None
    campaign_name: str | None = None
    tracking_dimension_gaps: list[
        Literal["landing_page", "source_medium", "campaign_name"]
    ] = Field(default_factory=list)
    metric_snapshot: dict[str, float | int | str] = Field(default_factory=dict)
    reason: str
    required_validation: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class Ga4DiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class Ga4DecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "fix_measurement",
        "review_traffic_quality",
        "review_landing_mapping",
    ]
    title: str
    status: Literal["ready", "blocked"] = "ready"
    priority: int = Field(default=50, ge=1, le=100)
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    landing_page: str | None = None
    source_medium: str | None = None
    campaign_name: str | None = None
    wordpress_match: str | None = None
    wordpress_match_confidence: str | None = None
    wordpress_content_url: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low


class Ga4DiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    live_data_available: bool
    landing_group_count: int = 0
    low_engagement_count: int = 0
    wordpress_match_count: int = 0
    decision_queue: list[Ga4DecisionItem] = Field(default_factory=list)
    sections: list[Ga4DiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class LocaloAccessProbe(BaseModel):
    status: Literal["access_ready", "access_blocked", "unknown"]
    source_run_id: str | None = None
    mcp_initialize_status: int | None = None
    authorization_code_supported: bool | None = None
    pkce_s256_supported: bool | None = None
    access_token_present: bool | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    summary: str


class LocaloDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class LocaloDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "access_ready_wait_for_visibility_facts",
        "fix_access",
        "review_local_visibility",
        "block_visibility_claims",
    ]
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    rationale: str
    next_step: str
    access_status: Literal["access_ready", "access_blocked", "unknown"]
    priority: int = Field(ge=1, le=100)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_evidence: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class LocaloDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    access_probe: LocaloAccessProbe
    live_data_available: bool
    visibility_fact_count: int = 0
    decision_queue: list[LocaloDecisionItem] = Field(default_factory=list)
    sections: list[LocaloDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class AhrefsDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class AhrefsDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_authority_context",
        "review_gap_records",
        "run_authority_read",
        "block_gap_claims",
    ]
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    rationale: str
    next_step: str
    priority: int = Field(ge=1, le=100)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_evidence: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class AhrefsGapRecord(BaseModel):
    id: str
    gap_type: Literal[
        "competitor_page",
        "content_gap",
        "backlink_gap",
        "organic_keyword_gap",
        "top_page_gap",
    ]
    title: str
    summary: str
    source_url: str | None = None
    target_url: str | None = None
    competitor_domain: str | None = None
    keyword: str | None = None
    metric_facts: list[MetricFact] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium


class AhrefsGapReadContract(BaseModel):
    id: Literal["ahrefs_gap_read_contract"] = "ahrefs_gap_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    available_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    allowed_evidence: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    gap_records: list[AhrefsGapRecord] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium


class AhrefsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    live_data_available: bool
    authority_fact_count: int = 0
    gap_fact_count: int = 0
    gap_read_contract: AhrefsGapReadContract
    decision_queue: list[AhrefsDecisionItem] = Field(default_factory=list)
    sections: list[AhrefsDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class CommandCenterBriefItem(BaseModel):
    id: str
    title: str
    route: str
    status: Literal["ready", "blocked", "missing"]
    priority: int = Field(ge=1, le=100)
    summary: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class CommandCenterDemoStep(BaseModel):
    id: str
    label: str
    route: str
    status: Literal["ready", "blocked"]
    what_it_proves: str
    operator_prompt: str
    source_item_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)


class CommandCenterActionPlanItem(BaseModel):
    id: str
    title: str
    route: str
    status: Literal["ready", "blocked"]
    priority: int = Field(ge=1, le=100)
    category: str
    why_it_matters: str
    operator_action: str
    skill_id: str | None = None
    codex_prompt: str | None = None
    codex_context_endpoint: str | None = None
    expected_codex_output: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class DailyDecision(BaseModel):
    id: str
    title: str
    route: str
    status: Literal["ready", "blocked"]
    priority: int = Field(ge=1, le=100)
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    co_widzimy: str
    dlaczego_to_ma_znaczenie: str
    bezpieczny_next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    skill_id: str | None = None
    codex_prompt: str | None = None
    codex_context_endpoint: str | None = None
    expected_codex_output: str | None = None
    risk: ActionRisk = ActionRisk.low


class CommandCenterResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    strict_instruction: str
    primary_next_step: str
    blocker_count: int = 0
    tactical_item_count: int = 0
    daily_decisions: list[DailyDecision] = Field(default_factory=list)
    operator_brief: list[CommandCenterBriefItem] = Field(default_factory=list)
    demo_script: list[CommandCenterDemoStep] = Field(default_factory=list)
    action_plan: list[CommandCenterActionPlanItem] = Field(default_factory=list)
    connector_summary: ConnectorSummary
    sections: dict[str, list[Opportunity]]
    active_actions: list[ActionObject]
    connector_health: list[ConnectorStatus]
    codex_operator_status: dict[str, Any]


class DemandGenReadinessContract(BaseModel):
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    metric_tiles: dict[str, str | int | float] = Field(default_factory=dict)
    available_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    payload_preview: list[dict[str, Any]] = Field(default_factory=list)
    campaign_rows_evaluated: int = 0
    campaign_channel_counts: dict[str, int] = Field(default_factory=dict)
    demand_gen_campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    demand_gen_ad_group_ad_rows: list[DemandGenAdGroupAdRow] = Field(default_factory=list)
    demand_gen_creative_asset_rows: list[DemandGenCreativeAssetRow] = Field(
        default_factory=list
    )
    demand_gen_landing_quality_rows: list[DemandGenLandingQualityRow] = Field(
        default_factory=list
    )
    demand_gen_migration_constraint_rows: list[DemandGenMigrationConstraintRow] = Field(
        default_factory=list
    )
    next_step: str
    risk: ActionRisk = ActionRisk.medium
