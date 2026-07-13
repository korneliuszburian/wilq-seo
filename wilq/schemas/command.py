from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import action_count_label, evidence_count_label, source_connector_labels

from .actions import ActionObject, ActionPreviewCardViewModel
from .ads import (
    AdsCampaignMetricRow,
    DemandGenAdGroupAdRow,
    DemandGenCampaignModeReviewRow,
    DemandGenCreativeAssetRow,
    DemandGenLandingQualityRow,
)
from .core import (
    ActionRisk,
    ConnectorStatus,
    DecisionState,
    FreshnessState,
    MetricFact,
    Opportunity,
    _unique_strings,
    utc_now,
)
from .knowledge import WorkspaceDossier
from .marketing import ConnectorSummary, _marketing_risk_label


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
    domain: str = "wilq"
    freshness: FreshnessState = Field(default_factory=lambda: FreshnessState(state="unknown"))
    freshness_label: str = ""
    decision_state: DecisionState = "unknown"
    decision_state_label: str = ""
    route: str
    route_label: str = ""
    cta_label: str = ""
    status: Literal["ready", "blocked"]
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    co_widzimy: str
    dlaczego_to_ma_znaczenie: str
    bezpieczny_next_step: str
    why_it_matters: str
    operator_action: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    skill_id: str | None = None
    skill_label: str | None = None
    codex_prompt: str | None = None
    codex_context_endpoint: str | None = None
    expected_codex_output: str | None = None
    risk: ActionRisk = ActionRisk.low


WorkOrderStatus = Literal["review_required", "blocked", "done"]
WorkOrderOwnerRole = Literal[
    "marketer",
    "ads_analytics",
    "content_seo",
    "product_feed",
    "local_seo",
    "owner_review",
    "developer_audit",
]


class WorkOrder(BaseModel):
    id: str
    title: str
    status: WorkOrderStatus
    status_label: str = ""
    owner_role: WorkOrderOwnerRole
    priority: int = Field(ge=1, le=100)
    domain: str = "wilq"
    route: str
    route_label: str = ""
    summary: str
    why_it_matters: str
    next_safe_step: str
    close_condition: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    freshness: FreshnessState = Field(default_factory=lambda: FreshnessState(state="unknown"))
    freshness_label: str = ""
    risk: ActionRisk = ActionRisk.medium
    decision_id: str | None = None


def work_order_from_daily_decision(decision: DailyDecision) -> WorkOrder:
    return WorkOrder(
        id=decision.id.replace("decision_", "work_order_", 1),
        title=decision.title,
        status=_work_order_status_from_decision(decision),
        status_label=_work_order_status_label(_work_order_status_from_decision(decision)),
        owner_role=_work_order_owner_role(decision.domain),
        priority=decision.priority,
        domain=decision.domain,
        route=decision.route,
        route_label=decision.route_label,
        summary=decision.co_widzimy,
        why_it_matters=decision.dlaczego_to_ma_znaczenie,
        next_safe_step=decision.bezpieczny_next_step,
        close_condition=_work_order_close_condition(decision),
        source_connectors=decision.source_connectors,
        source_connector_labels=decision.source_connector_labels,
        evidence_ids=decision.evidence_ids,
        evidence_summary=decision.evidence_summary,
        action_ids=decision.action_ids,
        action_summary=decision.action_summary,
        blocked_claims=decision.blocked_claims,
        blocked_claim_labels=decision.blocked_claim_labels,
        freshness=decision.freshness,
        freshness_label=decision.freshness_label,
        risk=decision.risk,
        decision_id=decision.id,
    )


def _work_order_status_from_decision(decision: DailyDecision) -> WorkOrderStatus:
    if decision.decision_state == "ready" and decision.status == "ready":
        return "review_required"
    return "blocked"


def _work_order_status_label(status: WorkOrderStatus) -> str:
    return {
        "review_required": "do sprawdzenia",
        "blocked": "zablokowane",
        "done": "zamknięte",
    }[status]


def _work_order_owner_role(domain: str) -> WorkOrderOwnerRole:
    if domain in {"google_ads", "ga4", "ads"}:
        return "ads_analytics"
    if domain in {"merchant", "products"}:
        return "product_feed"
    if domain in {"content", "gsc_seo", "wordpress", "ahrefs", "seo"}:
        return "content_seo"
    if domain in {"localo", "local"}:
        return "local_seo"
    if domain in {"knowledge", "service_profile"}:
        return "owner_review"
    return "marketer"


def _work_order_close_condition(decision: DailyDecision) -> str:
    if decision.decision_state == "blocked":
        return "Zamknięte dopiero po usunięciu blokady i ponownym potwierdzeniu dowodów w WILQ."
    if decision.decision_state in {"stale", "missing", "unknown"}:
        return "Zamknięte po odświeżeniu źródeł i ponownej ocenie decyzji w WILQ."
    if decision.action_ids:
        return (
            "Zamknięte po review wskazanej akcji, zapisaniu decyzji i pozostawieniu audytu w WILQ."
        )
    return "Zamknięte po ręcznym potwierdzeniu decyzji i zapisaniu wyniku pracy."


DailyCheckItemCategory = Literal[
    "anomaly",
    "risk",
    "opportunity",
    "blocked_recommendation",
    "safe_next_action",
    "do_not_touch",
]


class DailyCheckConnectorRef(BaseModel):
    connector_id: str
    status: Literal["checked", "skipped"]
    freshness: FreshnessState = Field(default_factory=lambda: FreshnessState(state="unknown"))
    reason: str = ""


class DailyCheckItem(BaseModel):
    id: str
    category: DailyCheckItemCategory
    title: str
    status: Literal["ready", "review_required", "blocked"]
    priority: int = Field(ge=1, le=100)
    summary: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    freshness: FreshnessState = Field(default_factory=lambda: FreshnessState(state="unknown"))
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    missing_contracts: list[str] = Field(default_factory=list)
    false_positive_guards: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.medium

    @model_validator(mode="after")
    def require_trace_for_operator_items(self) -> DailyCheckItem:
        if self.status != "blocked" and self.category != "blocked_recommendation":
            missing: list[str] = []
            if not self.source_connectors:
                missing.append("source_connectors")
            if not self.evidence_ids:
                missing.append("evidence_ids")
            if not self.expert_rule_ids:
                missing.append("expert_rule_ids")
            if self.freshness.state in {"unknown", "missing"}:
                missing.append("freshness")
            if missing:
                raise ValueError(
                    f"Daily check item {self.id} lacks required trace fields: " + ", ".join(missing)
                )
        return self


class RecommendationLogRecord(BaseModel):
    id: str
    workspace_id: str
    recommendation_id: str
    status: Literal["made", "accepted", "rejected", "deferred"]
    reason: str
    follow_up: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    outcome_summary: str | None = None
    recorded_by: str
    recorded_at: datetime = Field(default_factory=utc_now)
    redacted: bool = True

    @model_validator(mode="after")
    def require_trace_for_recommendation(self) -> RecommendationLogRecord:
        if self.status in {"made", "accepted"} and (
            not self.evidence_ids or not self.source_connectors
        ):
            raise ValueError("Recommendation log requires evidence_ids and source_connectors.")
        return self


class DailyCheckResult(BaseModel):
    workspace_id: str
    date: date
    status: Literal["ready", "review_ready", "blocked", "degraded"]
    checked_connectors: list[DailyCheckConnectorRef] = Field(default_factory=list)
    skipped_connectors: list[DailyCheckConnectorRef] = Field(default_factory=list)
    anomalies: list[DailyCheckItem] = Field(default_factory=list)
    risks: list[DailyCheckItem] = Field(default_factory=list)
    opportunities: list[DailyCheckItem] = Field(default_factory=list)
    blocked_recommendations: list[DailyCheckItem] = Field(default_factory=list)
    safe_next_actions: list[DailyCheckItem] = Field(default_factory=list)
    do_not_touch: list[DailyCheckItem] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    expert_rules_used: list[str] = Field(default_factory=list)
    freshness: FreshnessState = Field(default_factory=lambda: FreshnessState(state="unknown"))
    workspace_dossier: WorkspaceDossier | None = None
    recommendation_history: list[RecommendationLogRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_trace_from_items(self) -> DailyCheckResult:
        items = [
            *self.anomalies,
            *self.risks,
            *self.opportunities,
            *self.blocked_recommendations,
            *self.safe_next_actions,
            *self.do_not_touch,
        ]
        if not self.evidence_ids:
            self.evidence_ids = _unique_strings(
                evidence_id for item in items for evidence_id in item.evidence_ids
            )
        if not self.source_connectors:
            self.source_connectors = _unique_strings(
                connector for item in items for connector in item.source_connectors
            )
        if not self.expert_rules_used:
            self.expert_rules_used = _unique_strings(
                rule_id for item in items for rule_id in item.expert_rule_ids
            )
        return self


class CommandCenterResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    strict_instruction: str
    primary_next_step: str
    blocker_count: int = 0
    tactical_item_count: int = 0
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary: str = ""
    daily_decisions: list[DailyDecision] = Field(default_factory=list)
    work_orders: list[WorkOrder] = Field(default_factory=list)
    operator_brief: list[CommandCenterBriefItem] = Field(default_factory=list)
    demo_script: list[CommandCenterDemoStep] = Field(default_factory=list)
    action_plan: list[CommandCenterActionPlanItem] = Field(default_factory=list)
    connector_summary: ConnectorSummary
    sections: dict[str, list[Opportunity]]
    active_actions: list[ActionObject]
    connector_health: list[ConnectorStatus]
    codex_operator_status: dict[str, Any]

    @model_validator(mode="after")
    def fill_lineage_summaries(self) -> CommandCenterResponse:
        if not self.work_orders:
            self.work_orders = [
                work_order_from_daily_decision(decision) for decision in self.daily_decisions
            ]
        if not self.source_connectors:
            self.source_connectors = _unique_strings(
                connector
                for decision in self.daily_decisions
                for connector in decision.source_connectors
            )
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        if not self.evidence_ids:
            self.evidence_ids = _unique_strings(
                evidence_id
                for decision in self.daily_decisions
                for evidence_id in decision.evidence_ids
            )
        if not self.action_ids:
            self.action_ids = _unique_strings(
                action_id for decision in self.daily_decisions for action_id in decision.action_ids
            )
        if not self.evidence_summary:
            self.evidence_summary = evidence_count_label(self.evidence_ids)
        if not self.action_summary:
            self.action_summary = action_count_label(self.action_ids)
        return self


class DemandGenReadinessContract(BaseModel):
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    metric_tiles: dict[str, str | int | float] = Field(default_factory=dict)
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    payload_preview: list[dict[str, Any]] = Field(default_factory=list)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
    campaign_rows_evaluated: int = 0
    campaign_channel_counts: dict[str, int] = Field(default_factory=dict)
    campaign_channel_labels: dict[str, str] = Field(default_factory=dict)
    demand_gen_campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    demand_gen_ad_group_ad_rows: list[DemandGenAdGroupAdRow] = Field(default_factory=list)
    demand_gen_creative_asset_rows: list[DemandGenCreativeAssetRow] = Field(default_factory=list)
    demand_gen_landing_quality_rows: list[DemandGenLandingQualityRow] = Field(default_factory=list)
    demand_gen_campaign_mode_review_rows: list[DemandGenCampaignModeReviewRow] = Field(
        default_factory=list
    )
    next_step: str
    risk: ActionRisk = ActionRisk.medium
    risk_label: str = ""

    @model_validator(mode="after")
    def fill_operator_labels(self) -> DemandGenReadinessContract:
        if not self.status_label:
            self.status_label = _demand_gen_status_label(self.status)
        if not self.risk_label:
            self.risk_label = _marketing_risk_label(self.risk)
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


def _demand_gen_status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
    }
    return labels.get(status, "status do sprawdzenia")
