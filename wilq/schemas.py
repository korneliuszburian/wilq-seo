from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    errors: list[str] = Field(default_factory=list)


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


class AdsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    live_data_available: bool
    sections: list[AdsDiagnosticSection] = Field(default_factory=list)
    blocked_handoff: AdsBlockedHandoff | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


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


class MerchantDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    latest_refresh: ConnectorRefreshRun | None = None
    live_data_available: bool
    product_count: int | None = None
    issue_count: int | None = None
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


class ContentDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "refresh_or_merge",
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
        "block_as_tracking_not_content",
    ]
    title: str
    page: str | None = None
    queries: list[str] = Field(default_factory=list)
    query_count: int = 0
    wordpress_match: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
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
    sections: list[Ga4DiagnosticSection] = Field(default_factory=list)
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


class CommandCenterResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    strict_instruction: str
    primary_next_step: str
    blocker_count: int = 0
    tactical_item_count: int = 0
    operator_brief: list[CommandCenterBriefItem] = Field(default_factory=list)
    demo_script: list[CommandCenterDemoStep] = Field(default_factory=list)
    action_plan: list[CommandCenterActionPlanItem] = Field(default_factory=list)
    connector_summary: ConnectorSummary
    sections: dict[str, list[Opportunity]]
    active_actions: list[ActionObject]
    connector_health: list[ConnectorStatus]
    codex_operator_status: dict[str, Any]
