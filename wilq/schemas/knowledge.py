from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    blocked_claim_label,
    blocked_claim_summary_label,
    evidence_count_label,
    knowledge_reference_count_label,
    mapped_action_type_count_label,
    missing_contract_count_label,
    missing_contract_detail_label,
    required_evidence_count_label,
    source_connector_summary_label,
    source_lineage_count_label,
)

from .core import ActionRisk, KnowledgeTaxonomyType, utc_now


class WorkspaceDossierEntry(BaseModel):
    id: str
    title: str
    summary: str
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    status: Literal["reviewed", "review_required", "open", "known_trap"] = "reviewed"


class WorkspaceDossier(BaseModel):
    id: str
    workspace_id: str
    display_name: str
    business_brief: str
    exclusions: list[str] = Field(default_factory=list)
    source_packs: list[WorkspaceDossierEntry] = Field(default_factory=list)
    previous_checks: list[WorkspaceDossierEntry] = Field(default_factory=list)
    reports: list[WorkspaceDossierEntry] = Field(default_factory=list)
    recommendation_history: list[WorkspaceDossierEntry] = Field(default_factory=list)
    client_truths: list[WorkspaceDossierEntry] = Field(default_factory=list)
    known_false_positives: list[WorkspaceDossierEntry] = Field(default_factory=list)
    open_blockers: list[WorkspaceDossierEntry] = Field(default_factory=list)


class SourceDocument(BaseModel):
    id: str
    title: str
    source_type: str
    source_url_or_path: str
    last_checked: str
    summary: str


KNOWLEDGE_DISPLAY_TITLE_LABELS = {
    "card_goal_001_rules": "Zakaz wymyślania metryk",
    "google_ads_search_playbook": "Diagnostyka wyszukiwanych haseł Google Ads",
    "google_ads_budget_review_playbook": "Przegląd budżetów Google Ads",
    "google_ads_demand_gen_playbook": "Gotowość Demand Gen",
    "google_ads_pmax_playbook": "Gotowość PMax i sprzedaży produktowej",
    "google_ads_negative_keywords_playbook": "Przegląd wykluczeń Google Ads",
    "google_ads_custom_segments_playbook": "Segmenty niestandardowe z wyszukiwanych haseł",
    "gsc_seo_content_playbook": "Okazje SEO i content z GSC",
    "ahrefs_content_gap_playbook": "Luki contentowe i konkurencja z Ahrefs",
    "localo_local_seo_playbook": "Widoczność lokalna Localo",
    "ga4_behavior_diagnostics_playbook": "Diagnostyka zachowania GA4",
    "merchant_feed_optimization_playbook": "Diagnostyka pliku produktowego Merchant",
    "linkedin_content_playbook": "Publikacje LinkedIn",
    "facebook_content_playbook": "Publikacje Facebook",
    "wordpress_content_refresh_playbook": "Odświeżanie treści WordPress",
}

KNOWLEDGE_CARD_TYPE_LABELS = {
    "ads_pattern_card": "wzorzec Ads",
    "campaign_card": "kampanie",
    "competitor_card": "konkurencja",
    "content_card": "treści",
    "keyword_cluster_card": "klastry słów",
    "local_visibility_card": "widoczność lokalna",
    "negative_keyword_pattern_card": "wykluczenia",
    "service_card": "plik produktowy i usługi",
    "social_pattern_card": "social",
    "voice_rule": "reguła głosu",
}

KNOWLEDGE_SOURCE_TYPE_LABELS = {
    "marketing_playbook": "zasada pracy",
    "repo_goal": "reguła projektu",
}

KNOWLEDGE_STATUS_LABELS = {
    "ready": "gotowe",
    "blocked": "zablokowane",
    "planned": "planowane",
}

KNOWLEDGE_ROUTE_LABELS = {
    "/command-center": "Plan dnia",
    "/merchant": "Merchant",
    "/content-workflow": "Treści",
    "/ads-doctor": "Ads",
    "/ads-doctor/demand-gen": "Demand Gen",
    "/ahrefs": "Ahrefs",
    "/ga4": "GA4",
    "/localo": "Localo",
    "/social-publisher": "Social",
}

KNOWLEDGE_RISK_LABELS = {
    "low": "niskie ryzyko",
    "medium": "średnie ryzyko",
    "high": "wysokie ryzyko",
    "critical": "krytyczne ryzyko",
}

KNOWLEDGE_TAXONOMY_TYPE_LABELS = {
    KnowledgeTaxonomyType.client_truth: "prawda o kliencie",
    KnowledgeTaxonomyType.expert_operating: "wiedza operacyjna eksperta",
    KnowledgeTaxonomyType.platform_trap: "pułapka platformy/API",
    KnowledgeTaxonomyType.workspace_memory: "pamięć workspace",
    KnowledgeTaxonomyType.observed_outcome: "zaobserwowany wynik",
}


def _knowledge_card_type_label(value: str) -> str:
    return KNOWLEDGE_CARD_TYPE_LABELS.get(value, "typ wiedzy do sprawdzenia")


def _knowledge_source_type_label(value: str) -> str:
    return KNOWLEDGE_SOURCE_TYPE_LABELS.get(value, "źródło wiedzy do sprawdzenia")


def _knowledge_route_label(value: str) -> str:
    return KNOWLEDGE_ROUTE_LABELS.get(value, "widok do sprawdzenia")


def _knowledge_status_label(value: str) -> str:
    return KNOWLEDGE_STATUS_LABELS.get(value, "status wiedzy do sprawdzenia")


def _knowledge_risk_label(value: str) -> str:
    return KNOWLEDGE_RISK_LABELS.get(value, "ryzyko do sprawdzenia")


def _knowledge_blocked_binding_count_label(count: int) -> str:
    if count == 0:
        return "brak zablokowanych decyzji"
    if count == 1:
        return "1 zablokowana decyzja"
    if 2 <= count <= 4:
        return f"{count} zablokowane decyzje"
    return f"{count} zablokowanych decyzji"


class KnowledgeCard(BaseModel):
    id: str
    card_type: str
    card_type_label: str = ""
    title: str
    display_title: str = ""
    summary: str
    source_type: str
    source_type_label: str = ""
    source_id: str
    source_url_or_path: str
    extracted_at: datetime = Field(default_factory=utc_now)
    confidence: float = Field(ge=0, le=1)
    last_seen_at: datetime = Field(default_factory=utc_now)
    source_lineage: list[str] = Field(default_factory=list)
    source_lineage_summary_label: str = ""

    @model_validator(mode="after")
    def fill_operator_labels(self) -> KnowledgeCard:
        if not self.display_title:
            self.display_title = (
                KNOWLEDGE_DISPLAY_TITLE_LABELS.get(self.source_id)
                or KNOWLEDGE_DISPLAY_TITLE_LABELS.get(self.id)
                or self.title
            )
        if not self.card_type_label:
            self.card_type_label = _knowledge_card_type_label(self.card_type)
        if not self.source_type_label:
            self.source_type_label = _knowledge_source_type_label(self.source_type)
        if not self.source_lineage_summary_label:
            self.source_lineage_summary_label = source_lineage_count_label(self.source_lineage)
        return self


class KnowledgeTaxonomyEntry(BaseModel):
    id: KnowledgeTaxonomyType
    label: str = ""
    definition: str
    owned_by: Literal[
        "source_fact_compiler",
        "expert_rule_compiler",
        "platform_rule_pack",
        "workspace_dossier",
        "measurement_loop",
    ]
    allowed_usage: list[str] = Field(default_factory=list)
    forbidden_usage: list[str] = Field(default_factory=list)
    example_records: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_operator_labels(self) -> KnowledgeTaxonomyEntry:
        expected_owner_by_type = {
            KnowledgeTaxonomyType.client_truth: "source_fact_compiler",
            KnowledgeTaxonomyType.expert_operating: "expert_rule_compiler",
            KnowledgeTaxonomyType.platform_trap: "platform_rule_pack",
            KnowledgeTaxonomyType.workspace_memory: "workspace_dossier",
            KnowledgeTaxonomyType.observed_outcome: "measurement_loop",
        }
        expected_owner = expected_owner_by_type[self.id]
        if self.owned_by != expected_owner:
            raise ValueError(f"{self.id} knowledge must be owned by {expected_owner}.")
        if not self.label:
            self.label = KNOWLEDGE_TAXONOMY_TYPE_LABELS[self.id]
        return self


class MarketingPlaybook(BaseModel):
    id: str
    family: str
    title: str
    display_title: str = ""
    card_type: str
    card_type_label: str = ""
    source_type_label: str = "zasada pracy"
    source_anchors: list[str] = Field(min_length=1)
    required_evidence: list[str] = Field(min_length=1)
    maps_to_opportunity_types: list[str] = Field(min_length=1)
    maps_to_action_types: list[str] = Field(min_length=1)
    expert_rule_ids: list[str] = Field(default_factory=list)
    compact_playbook: str = Field(min_length=1)
    refusal_rules: list[str] = Field(default_factory=list)
    output_contract: str = Field(min_length=1)
    source_path: str
    required_evidence_summary_label: str = ""
    mapped_action_type_summary_label: str = ""

    @model_validator(mode="after")
    def fill_operator_labels(self) -> MarketingPlaybook:
        if not self.display_title:
            self.display_title = KNOWLEDGE_DISPLAY_TITLE_LABELS.get(self.id, self.title)
        if not self.card_type_label:
            self.card_type_label = _knowledge_card_type_label(self.card_type)
        if not self.source_type_label:
            self.source_type_label = "zasada pracy"
        if not self.required_evidence_summary_label:
            self.required_evidence_summary_label = required_evidence_count_label(
                self.required_evidence
            )
        if not self.mapped_action_type_summary_label:
            self.mapped_action_type_summary_label = mapped_action_type_count_label(
                self.maps_to_action_types
            )
        return self


class KnowledgeCompilerResult(BaseModel):
    status: Literal["completed", "failed"]
    generated_at: datetime = Field(default_factory=utc_now)
    card_count: int
    cards: list[KnowledgeCard]


class KnowledgeDecisionBinding(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "planned"]
    status_label: str = ""
    route: str
    route_label: str = ""
    skill_id: str | None = None
    summary: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    source_connector_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    playbook_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    knowledge_summary_label: str = ""
    required_evidence: list[str] = Field(default_factory=list)
    required_evidence_summary_label: str = ""
    missing_contracts: list[str] = Field(default_factory=list)
    missing_contract_labels: list[str] = Field(default_factory=list)
    missing_contract_summary_label: str = ""
    missing_contract_detail_label: str = ""
    has_missing_contracts: bool = False
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    blocked_claim_count_summary_label: str = ""
    has_blocked_claims: bool = False
    source_lineage: list[str] = Field(default_factory=list)
    source_lineage_summary_label: str = ""
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""

    @model_validator(mode="after")
    def fill_operator_labels(self) -> KnowledgeDecisionBinding:
        if not self.status_label:
            self.status_label = _knowledge_status_label(self.status)
        if not self.route_label:
            self.route_label = _knowledge_route_label(self.route)
        if not self.risk_label:
            risk_value = self.risk.value if isinstance(self.risk, ActionRisk) else self.risk
            self.risk_label = _knowledge_risk_label(str(risk_value))
        if not self.source_connector_summary_label:
            self.source_connector_summary_label = source_connector_summary_label(
                self.source_connectors
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.knowledge_summary_label:
            self.knowledge_summary_label = knowledge_reference_count_label(
                knowledge_card_ids=self.knowledge_card_ids,
                playbook_ids=self.playbook_ids,
                expert_rule_ids=self.expert_rule_ids,
            )
        if not self.required_evidence_summary_label:
            self.required_evidence_summary_label = required_evidence_count_label(
                self.required_evidence
            )
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        self.has_missing_contracts = bool(self.missing_contract_labels or self.missing_contracts)
        if not self.missing_contract_summary_label:
            self.missing_contract_summary_label = missing_contract_count_label(
                self.missing_contracts
            )
        if not self.missing_contract_detail_label:
            self.missing_contract_detail_label = missing_contract_detail_label(
                self.missing_contract_labels or self.missing_contracts
            )
        self.has_blocked_claims = bool(self.blocked_claim_labels or self.blocked_claims)
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_summary_label(self.blocked_claims)
        if not self.blocked_claim_count_summary_label:
            self.blocked_claim_count_summary_label = blocked_claim_count_label(self.blocked_claims)
        if not self.source_lineage_summary_label:
            self.source_lineage_summary_label = source_lineage_count_label(self.source_lineage)
        return self


class KnowledgeOperatingMapResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    source_card_count: int
    playbook_count: int
    expert_rule_count: int
    binding_count: int
    blocked_binding_summary_label: str = ""
    missing_contract_summary_label: str = ""
    blocked_claim_count_summary_label: str = ""
    bindings: list[KnowledgeDecisionBinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_operator_summary_labels(self) -> KnowledgeOperatingMapResponse:
        if not self.blocked_binding_summary_label:
            blocked_count = sum(1 for binding in self.bindings if binding.status == "blocked")
            self.blocked_binding_summary_label = _knowledge_blocked_binding_count_label(
                blocked_count
            )
        if not self.missing_contract_summary_label:
            self.missing_contract_summary_label = missing_contract_count_label(
                contract for binding in self.bindings for contract in binding.missing_contracts
            )
        if not self.blocked_claim_count_summary_label:
            self.blocked_claim_count_summary_label = blocked_claim_count_label(
                claim for binding in self.bindings for claim in binding.blocked_claims
            )
        return self


class PlatformTrapContract(BaseModel):
    """Typed platform constraint pack used to block unsafe conclusions."""

    platform: Literal["google_ads", "ga4", "merchant_center", "search_console", "wordpress"]
    constraints: list[str] = Field(min_length=1)
    blocked_claims: list[str] = Field(default_factory=list)
    safe_next_steps: list[str] = Field(min_length=1)


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
    source_ids: list[str] = Field(default_factory=list)
    requires_evidence: bool = True
    condition: str | None = None
    required_connectors: list[str] = Field(default_factory=list)
    required_metrics: list[str] = Field(default_factory=list)
    minimum_window: str | None = None
    segmentation: list[str] = Field(default_factory=list)
    false_positive_checks: list[str] = Field(default_factory=list)
    blocked_states: list[str] = Field(default_factory=list)
    recommendation_template: str | None = None
    forbidden_conclusions: list[str] = Field(default_factory=list)
    safety_level: Literal["low", "medium", "high"] = "medium"
    eval_case_ids: list[str] = Field(default_factory=list)
    platform_trap: PlatformTrapContract | None = None


class ExpertRuleSummary(BaseModel):
    id: str
    name: str
    domain: str
    source_anchor: str
    required_inputs: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    output_contract: str
    requires_evidence: bool = True
    condition: str | None = None
    required_connectors: list[str] = Field(default_factory=list)
    required_metrics: list[str] = Field(default_factory=list)
    minimum_window: str | None = None
    segmentation: list[str] = Field(default_factory=list)
    false_positive_checks: list[str] = Field(default_factory=list)
    blocked_states: list[str] = Field(default_factory=list)
    recommendation_template: str | None = None
    forbidden_conclusions: list[str] = Field(default_factory=list)
    safety_level: Literal["low", "medium", "high"] = "medium"
    eval_case_ids: list[str] = Field(default_factory=list)
    platform_trap: PlatformTrapContract | None = None


class ExpertKnowledgeSource(BaseModel):
    id: str
    domain: str
    knowledge_type: KnowledgeTaxonomyType
    source_type: Literal[
        "official_platform_doc",
        "repo_structured_rule",
        "reviewed_internal_sop",
        "public_site",
        "measurement_evidence",
        "workspace_memory",
    ]
    license_status: Literal["commit_safe", "review_required", "private_reference_only"]
    source_reference: str
    freshness_date: date
    reviewer: str | None = None
    trust_level: Literal["low", "medium", "high"] = "medium"
    allowed_usage: list[str] = Field(min_length=1)
    forbidden_usage: list[str] = Field(min_length=1)
    linked_rule_ids: list[str] = Field(min_length=1)


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
