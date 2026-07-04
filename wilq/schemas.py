from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.operator_labels import (
    action_count_label,
    ads_campaign_status_label,
    ads_channel_type_label,
    blocked_claim_count_label,
    blocked_claim_label,
    blocked_claim_summary_label,
    blocker_count_label,
    connector_refresh_status_label,
    credential_field_count_label,
    credential_source_count_label,
    evidence_count_label,
    impact_comparison_summary_label,
    knowledge_reference_count_label,
    mapped_action_type_count_label,
    metric_fact_label,
    missing_contract_count_label,
    missing_contract_detail_label,
    policy_count_label,
    reported_issue_occurrence_count_label,
    required_evidence_count_label,
    required_validation_count_label,
    source_connector_label,
    source_connector_labels,
    source_connector_summary_label,
    source_contract_count_label,
    source_lineage_count_label,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _unique_strings(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


class ConnectorStatusValue(StrEnum):
    configured = "configured"
    missing_credentials = "missing_credentials"
    missing_dependency = "missing_dependency"
    unreachable = "unreachable"
    auth_error = "auth_error"
    rate_limited = "rate_limited"
    error = "error"
    disabled = "disabled"


class ConnectorProductScope(StrEnum):
    production = "production"
    optional_disabled = "optional_disabled"
    experimental = "experimental"
    runtime = "runtime"


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


DecisionState = Literal["ready", "stale", "blocked", "missing", "unknown"]


class ConnectorCapability(BaseModel):
    read: bool = True
    write: bool = False
    operations: list[str] = Field(default_factory=list)


class ConnectorStatus(BaseModel):
    id: str
    label: str
    status: ConnectorStatusValue
    status_label: str = ""
    product_scope: ConnectorProductScope = ConnectorProductScope.production
    product_scope_label: str = ""
    active_for_daily_work: bool = True
    configured: bool
    missing_credentials: list[str] = Field(default_factory=list)
    missing_credentials_summary_label: str = ""
    available_credential_sources: list[str] = Field(default_factory=list)
    credential_source_summary_label: str = ""
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

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ConnectorStatus:
        if not self.status_label:
            self.status_label = connector_status_label(self.status)
        if not self.product_scope_label:
            labels = {
                ConnectorProductScope.production: "aktywny zakres WILQ",
                ConnectorProductScope.optional_disabled: "opcjonalne, wyłączone w tym zakresie",
                ConnectorProductScope.experimental: "eksperymentalny workflow review",
                ConnectorProductScope.runtime: "runtime operatora, nie źródło marketingowe",
            }
            self.product_scope_label = labels[self.product_scope]
        if not self.missing_credentials_summary_label:
            self.missing_credentials_summary_label = credential_field_count_label(
                self.missing_credentials
            )
        if not self.credential_source_summary_label:
            self.credential_source_summary_label = credential_source_count_label(
                self.available_credential_sources
            )
        return self


def connector_status_label(status: ConnectorStatusValue | str) -> str:
    labels = {
        ConnectorStatusValue.configured: "dostęp skonfigurowany",
        ConnectorStatusValue.missing_credentials: "brak dostępu",
        ConnectorStatusValue.missing_dependency: "brak zależności",
        ConnectorStatusValue.unreachable: "źródło niedostępne",
        ConnectorStatusValue.auth_error: "błąd autoryzacji",
        ConnectorStatusValue.rate_limited: "limit odczytu",
        ConnectorStatusValue.error: "błąd źródła danych",
        ConnectorStatusValue.disabled: "wyłączone w tym zakresie",
    }
    try:
        normalized = ConnectorStatusValue(str(status))
    except ValueError:
        return "status źródła do sprawdzenia"
    return labels.get(normalized, "status źródła do sprawdzenia")


class Evidence(BaseModel):
    id: str
    title_label: str = ""
    source_connector: str
    source_connector_label: str = ""
    source_type: str
    source_type_label: str = ""
    source_id: str
    collected_at: datetime = Field(default_factory=utc_now)
    freshness: FreshnessState
    freshness_label: str = ""
    summary: str
    trace_summary_label: str = ""
    raw_ref: str | None = None


class ConnectorRefreshRequest(BaseModel):
    mode: ConnectorRefreshMode = ConnectorRefreshMode.status_probe
    reason: str | None = None


class ConnectorRefreshRun(BaseModel):
    id: str
    connector_id: str
    connector_label: str = ""
    mode: ConnectorRefreshMode
    status: ConnectorRefreshStatus
    status_label: str = ""
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    missing_credentials: list[str] = Field(default_factory=list)
    checked_credentials: list[str] = Field(default_factory=list)
    external_call_attempted: bool = False
    vendor_data_collected: bool = False
    metrics_persisted: bool = True
    metric_summary: dict[str, float | int | str] = Field(default_factory=dict)
    summary: str
    errors: list[str] = Field(default_factory=list)
    redacted: bool = True

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ConnectorRefreshRun:
        if not self.connector_label:
            self.connector_label = source_connector_label(self.connector_id)
        if not self.status_label:
            self.status_label = connector_refresh_run_status_label(self)
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


def connector_refresh_run_status_label(run: ConnectorRefreshRun) -> str:
    if run.status == ConnectorRefreshStatus.completed and not run.metrics_persisted:
        return "odczyt niepełny - metryki nieutrwalone"
    return connector_refresh_status_label(run.status)


def connector_refresh_has_live_data(run: ConnectorRefreshRun | None) -> bool:
    return (
        run is not None
        and run.status == ConnectorRefreshStatus.completed
        and run.vendor_data_collected
        and run.metrics_persisted
    )


class MetricFact(BaseModel):
    name: str
    metric_label: str = ""
    value: float | int | str
    period: str
    source_connector: str
    evidence_id: str
    dimensions: dict[str, str] = Field(default_factory=dict)
    dimension_labels: dict[str, str] = Field(default_factory=dict)
    dimension_value_labels: dict[str, str] = Field(default_factory=dict)
    unit: str | None = None
    collected_at: datetime | None = None
    previous_value: float | int | str | None = None
    previous_evidence_id: str | None = None
    previous_collected_at: datetime | None = None
    delta: float | int | None = None
    delta_percent: float | None = None
    trend: Literal["up", "down", "flat", "unknown"] = "unknown"
    freshness_state: Literal["fresh", "stale", "unknown"] = "unknown"
    freshness_label: str | None = None

    @model_validator(mode="after")
    def fill_dimension_labels(self) -> MetricFact:
        if not self.metric_label:
            self.metric_label = metric_fact_label(self.name, self.source_connector)
        if not self.dimension_labels:
            self.dimension_labels = {key: _metric_dimension_label(key) for key in self.dimensions}
        if not self.dimension_value_labels:
            self.dimension_value_labels = {
                key: _metric_dimension_value_label(key, value)
                for key, value in self.dimensions.items()
            }
        return self


def _metric_dimension_label(value: str) -> str:
    labels = {
        "affected_attribute": "atrybut",
        "ad_group_id": "identyfikator grupy reklam",
        "ad_group_name": "grupa reklam",
        "advertising_channel_type": "typ kampanii",
        "best_position": "najlepsza pozycja",
        "best_position_url": "adres z najlepszą pozycją",
        "budget_id": "identyfikator budżetu",
        "budget_name": "budżet",
        "budget_period": "okres budżetu",
        "budget_status": "status budżetu",
        "campaign_budget_id": "identyfikator budżetu kampanii",
        "campaign_id": "identyfikator kampanii",
        "campaign_name": "kampania",
        "campaign_status": "status kampanii",
        "changed_field": "zmienione pole",
        "changed_resource": "zmieniony zasób",
        "connector_id": "źródło danych",
        "content_type": "typ treści",
        "content_url": "adres treści",
        "competitor_domain": "konkurent",
        "competitor_target_mode": "tryb porównania konkurencji",
        "contract": "obszar",
        "country": "kraj",
        "cpc": "koszt kliknięcia",
        "criterion_id": "identyfikator kryterium",
        "criterion_status": "status kryterium",
        "gap_type": "typ luki",
        "gsc_page_query_count": "liczba zapytań GSC",
        "inventory_source": "źródło spisu treści",
        "dismissed": "czy odrzucona",
        "is_branded": "czy brandowe",
        "is_commercial": "czy komercyjne",
        "is_informational": "czy informacyjne",
        "is_local": "czy lokalne",
        "is_transactional": "czy transakcyjne",
        "issue_type": "problem",
        "keyword": "fraza",
        "keyword_difficulty": "trudność frazy",
        "keyword_match_type": "dopasowanie frazy",
        "keyword_negative": "wykluczenie frazy",
        "keyword_text": "słowo kluczowe",
        "landing_page": "strona wejścia",
        "metric_bucket": "zakres",
        "modified_gmt": "data zmiany",
        "page": "strona",
        "query": "zapytanie",
        "recommendation_campaign_count": "liczba kampanii",
        "recommendation_id": "identyfikator rekomendacji",
        "recommendation_resource_name": "zasób rekomendacji",
        "recommendation_type": "typ rekomendacji",
        "reporting_context": "kontekst",
        "resolution": "rozwiązanie",
        "scope": "zakres",
        "search_term": "wyszukiwane hasło",
        "search_term_status": "status wyszukiwanego hasła",
        "severity": "status",
        "site_kind": "typ serwisu",
        "source_medium": "źródło",
        "source_url": "URL źródłowy",
        "status": "status",
        "sum_traffic": "ruch według Ahrefs",
        "canonical_url": "adres kanoniczny",
        "target_domain": "domena docelowa",
        "target_keyword_limit": "limit fraz",
        "target_keyword_sample_size": "próbka fraz",
        "target_mode": "zakres domen",
        "title_or_h1": "tytuł albo H1",
        "volume": "wolumen",
        "wordpress_connector": "źródło WordPress",
        "wordpress_content_host": "host treści",
        "wordpress_content_type": "typ treści WordPress",
        "wordpress_content_url": "adres treści WordPress",
        "wordpress_host_alias_applied": "dopasowanie aliasu hosta",
        "wordpress_inventory_source": "źródło spisu WordPress",
        "wordpress_match_confidence": "pewność dopasowania WordPress",
        "wordpress_matched_path": "dopasowana ścieżka WordPress",
        "wordpress_matched_url_key": "dopasowany adres WordPress",
        "wordpress_modified_gmt": "data zmiany w WordPress",
        "wordpress_requested_path": "sprawdzana ścieżka WordPress",
        "wordpress_requested_url_key": "sprawdzany adres WordPress",
        "wordpress_status": "status WordPress",
    }
    return labels.get(value, "wymiar")


def _metric_dimension_value_label(key: str, value: str) -> str:
    text = str(value or "").strip()
    labels = {
        "active_places": "aktywne miejsca",
        "authority_summary": "autorytet domeny",
        "BROAD": "dopasowanie szerokie",
        "competitor_visibility": "widoczność konkurencji",
        "competitor_page": "strona konkurencji",
        "DAILY": "dziennie",
        "DISABLED": "wyłączone",
        "ENABLED": "aktywne",
        "DISPLAY_EXPANSION_OPT_IN": "włączenie rozszerzenia na sieć reklamową",
        "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "dynamiczne rozszerzenie obrazów",
        "exact": "dokładne porównanie",
        "false": "nie",
        "False": "nie",
        "FREE_LISTINGS": "bezpłatne wyniki produktowe",
        "gbp_visibility": "profil firmy w Google",
        "indexed": "w indeksie",
        "local_rankings": "lokalne pozycje",
        "MERCHANT_ACTION": "wymaga działania po stronie Merchant",
        "content_gap": "luka treści",
        "missing_potentially_required_attribute": ("brak potencjalnie wymaganego atrybutu"),
        "n:certification": "certyfikacja",
        "n:image_link": "link do grafiki",
        "n:availability": "dostępność",
        "n:unit_pricing_measure": "miara ceny jednostkowej",
        "NONE": "brak dodatkowego statusu",
        "NOT_IMPACTED": "bez wpływu",
        "organic_keyword_gap": "luka fraz organicznych",
        "pages": "strony",
        "path_fallback": "dopasowanie po ścieżce",
        "PAUSED": "wstrzymane",
        "PERFORMANCE_MAX": "Performance Max",
        "place_inventory": "spis miejsc",
        "posts": "wpisy",
        "primary": "ekologus.pl",
        "public_sitemap": "publiczna mapa strony",
        "reviews": "opinie",
        "SEARCH": "kampania w wyszukiwarce",
        "SEARCH_PARTNERS_OPT_IN": "włączenie partnerów wyszukiwania",
        "shop": "sklep",
        "SHOPPING_ADS": "reklamy produktowe",
        "sitemap": "mapa strony",
        "subdomains": "subdomeny",
        "true": "tak",
        "True": "tak",
        "availability_updated": "zaktualizowana dostępność",
        "image_too_small_for_high_resolution": "grafika za mała do wysokiej rozdzielczości",
        "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": "poprawa siły zasobów Performance Max",
    }
    if key == "connector_id":
        return source_connector_label(value)
    if key == "wordpress_connector":
        return source_connector_label(value)
    if key.endswith("_id") or key in {
        "recommendation_resource_name",
    }:
        return "dostępny w szczegółach technicznych"
    if text in labels:
        return labels[text]
    if text.upper() == "PL":
        return "Polska"
    if text == "(not set)":
        return "brak wartości w danych źródłowych"
    if text == "(organic)":
        return "ruch organiczny"
    if (
        key
        in {
            "campaign_name",
            "ad_group_name",
            "best_position",
            "budget_name",
            "canonical_url",
            "content_url",
            "competitor_domain",
            "competitor_target_mode",
            "cpc",
            "keyword",
            "keyword_difficulty",
            "keyword_text",
            "landing_page",
            "modified_gmt",
            "page",
            "query",
            "recommendation_campaign_count",
            "search_term",
            "source_medium",
            "source_url",
            "sum_traffic",
            "target_domain",
            "target_keyword_limit",
            "target_keyword_sample_size",
            "title_or_h1",
            "volume",
            "best_position_url",
            "wordpress_content_host",
            "wordpress_content_url",
            "wordpress_matched_path",
            "wordpress_matched_url_key",
            "wordpress_modified_gmt",
            "wordpress_requested_path",
            "wordpress_requested_url_key",
        }
        and text
    ):
        return text
    return "wartość wymiaru do sprawdzenia"


class Opportunity(BaseModel):
    id: str
    type: str
    title: str
    domain: OpportunityDomain
    domain_label: str = ""
    source_connectors: list[str] = Field(min_length=1)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)
    evidence_summary_label: str = ""
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    metrics: list[MetricFact] = Field(default_factory=list)
    human_diagnosis: str = Field(min_length=1)
    recommended_action: str
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    expert_rule_ids: list[str] = Field(default_factory=list)
    playbook_ids: list[str] = Field(default_factory=list)
    knowledge_summary_label: str = ""
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
    event_type_label: str = ""
    actor: str
    created_at: datetime = Field(default_factory=utc_now)
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    redacted: bool = True


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
    created_at: datetime = Field(default_factory=utc_now)
    audit_event_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
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
    write_authorization_status: Literal[
        "missing_audit_trace",
        "audit_actor_mismatch",
        "available",
    ] | None = None
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
    adapter_result: dict[str, Any] | None = None


class ActionPreviewRequest(BaseModel):
    requested_by: str | None = None
    max_items: int = Field(default=8, ge=1, le=50)


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
    "/content-planner": "Treści",
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
    kind_label: str = ""
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    summary: str
    next_step: str
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""
    blocker_reason: str | None = None

    @model_validator(mode="after")
    def fill_marketer_labels(self) -> MarketingBriefItem:
        if not self.kind_label:
            self.kind_label = _marketing_brief_kind_label(self.kind)
        if not self.priority_label:
            self.priority_label = _marketing_priority_label(self.priority)
        if not self.source_connector_labels:
            self.source_connector_labels = [
                _marketing_brief_connector_label(connector_id)
                for connector_id in self.source_connectors
            ]
        if not self.evidence_summary_label:
            self.evidence_summary_label = _marketing_brief_evidence_count_label(
                len(self.evidence_ids)
            )
        if not self.action_summary_label:
            self.action_summary_label = _marketing_brief_action_count_label(len(self.action_ids))
        if not self.risk_label:
            self.risk_label = _marketing_risk_label(self.risk)
        return self


def _marketing_brief_kind_label(kind: str) -> str:
    return {
        "metric": "fakt z danych",
        "blocker": "blokada",
        "action": "akcja do sprawdzenia",
        "recommendation": "rekomendacja",
    }.get(kind, "element do sprawdzenia")


def _marketing_brief_connector_label(connector_id: str) -> str:
    return {
        "google_ads": "Google Ads",
        "google_search_console": "Google Search Console",
        "google_analytics_4": "GA4",
        "google_merchant_center": "Merchant Center",
        "merchant_center": "Merchant Center",
        "ahrefs": "Ahrefs",
        "localo": "Localo",
        "wordpress_ekologus": "WordPress ekologus.pl",
        "wordpress_sklep": "WordPress sklep.ekologus.pl",
        "linkedin": "LinkedIn",
        "facebook": "Facebook",
    }.get(connector_id, "źródło danych WILQ")


def _marketing_brief_evidence_count_label(count: int) -> str:
    if count == 0:
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _marketing_brief_action_count_label(count: int) -> str:
    if count == 0:
        return "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    if count == 1:
        return "1 akcja do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} akcje do sprawdzenia"
    return f"{count} akcji do sprawdzenia"


def _marketing_priority_label(priority: int) -> str:
    if priority <= 15:
        return "najpierw"
    if priority <= 25:
        return "wysoki priorytet"
    if priority <= 45:
        return "do sprawdzenia"
    return "niżej w kolejce"


def _marketing_risk_label(risk: ActionRisk | str) -> str:
    value = risk.value if isinstance(risk, ActionRisk) else risk
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
        "critical": "krytyczne ryzyko",
    }
    return labels.get(value, "ryzyko do sprawdzenia")


def _tactical_domain_label(domain: OpportunityDomain) -> str:
    labels = {
        OpportunityDomain.gsc_seo: "Treści i GSC",
        OpportunityDomain.ga4: "GA4",
        OpportunityDomain.merchant: "Merchant",
        OpportunityDomain.content: "Treści",
    }
    return labels.get(domain, "powiązany obszar")


def _tactical_intent_label(intent: str) -> str:
    labels = {
        "content_refresh": "odświeżenie treści",
        "content_create": "nowa treść",
        "content_merge": "scalenie treści",
        "content_block": "blokada treści",
        "landing_page_quality": "jakość strony wejścia",
        "tracking_gap": "problem pomiaru",
        "merchant_feed_triage": "kolejność oceny pliku produktowego",
        "traffic_quality_review": "jakość ruchu",
    }
    return labels.get(intent, "zadanie do sprawdzenia")


def _tactical_dimension_label(value: str) -> str:
    labels = {
        "query": "zapytanie",
        "page": "strona",
        "landing_page": "strona wejścia",
        "source_medium": "źródło ruchu",
        "campaign_name": "kampania",
        "issue_type": "typ problemu",
        "affected_attribute": "atrybut",
        "country": "kraj",
        "reporting_context": "kontekst",
        "wordpress_match": "WordPress",
        "wordpress_match_confidence": "pewność dopasowania",
        "gsc_page_query_count": "liczba zapytań GSC",
        "target_mode": "zakres domen",
        "wordpress_connector": "źródło WordPress",
        "wordpress_content_host": "host treści",
        "wordpress_content_type": "typ treści WordPress",
        "wordpress_content_url": "adres treści WordPress",
        "wordpress_host_alias_applied": "dopasowanie aliasu hosta",
        "wordpress_inventory_source": "źródło spisu WordPress",
        "wordpress_matched_path": "dopasowana ścieżka WordPress",
        "wordpress_matched_url_key": "dopasowany adres WordPress",
        "wordpress_modified_gmt": "data zmiany w WordPress",
        "wordpress_requested_path": "sprawdzana ścieżka WordPress",
        "wordpress_requested_url_key": "sprawdzany adres WordPress",
        "wordpress_status": "status WordPress",
    }
    return labels.get(value, "wymiar do sprawdzenia")


def _tactical_dimension_value_label(key: str, value: str) -> str:
    labels_by_key = {
        "wordpress_match": {
            "found": "znaleziono w WordPress",
            "missing": "niepotwierdzone w WordPress",
        },
        "wordpress_match_confidence": {
            "exact_url": "dokładny adres URL",
            "same_path": "ten sam adres ścieżki",
            "missing": "dopasowanie niepotwierdzone",
        },
        "reporting_context": {
            "ALL_CONTEXTS": "wszystkie miejsca emisji",
            "FREE_LISTINGS": "bezpłatne wyniki",
            "SHOPPING_ADS": "reklamy produktowe",
        },
        "country": {
            "PL": "Polska",
            "pl": "Polska",
        },
        "target_mode": {
            "subdomains": "subdomeny",
        },
        "wordpress_connector": {
            "wordpress_ekologus": "WordPress ekologus.pl",
            "wordpress_sklep": "WordPress sklep.ekologus.pl",
        },
        "wordpress_content_type": {
            "sitemap": "mapa strony",
            "post": "wpis",
            "page": "strona",
        },
        "wordpress_status": {
            "indexed": "w indeksie",
            "publish": "opublikowane",
            "draft": "szkic",
        },
        "wordpress_host_alias_applied": {
            "false": "nie",
            "False": "nie",
            "true": "tak",
            "True": "tak",
        },
        "wordpress_inventory_source": {
            "public_sitemap": "publiczna mapa strony",
        },
    }
    text = str(value or "").strip()
    if key in labels_by_key and text in labels_by_key[key]:
        return labels_by_key[key][text]
    if (
        key
        in {
            "campaign_name",
            "landing_page",
            "page",
            "query",
            "source_medium",
            "wordpress_content_host",
            "wordpress_content_url",
            "wordpress_matched_path",
            "wordpress_matched_url_key",
            "wordpress_modified_gmt",
            "wordpress_requested_path",
            "wordpress_requested_url_key",
        }
        and text
    ):
        return text
    return "wartość do sprawdzenia"


def _blocked_claim_label(value: str) -> str:
    return blocked_claim_label(value)


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
    domain_label: str = ""
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
    intent_label: str = ""
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""
    source_connectors: list[str] = Field(min_length=1)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    dimensions: dict[str, str] = Field(default_factory=dict)
    dimension_labels: dict[str, str] = Field(default_factory=dict)
    dimension_value_labels: dict[str, str] = Field(default_factory=dict)
    diagnosis: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""

    @field_validator("source_connectors", "evidence_ids")
    @classmethod
    def require_nonblank_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("Tactical queue trace IDs must not be blank")
        return value

    @model_validator(mode="after")
    def fill_operator_labels(self) -> TacticalQueueItem:
        if not self.domain_label:
            self.domain_label = _tactical_domain_label(self.domain)
        if not self.intent_label:
            self.intent_label = _tactical_intent_label(self.intent)
        if not self.priority_label:
            self.priority_label = _marketing_priority_label(self.priority)
        if not self.risk_label:
            self.risk_label = _marketing_risk_label(self.risk)
        if not self.source_connector_labels:
            self.source_connector_labels = [
                _marketing_brief_connector_label(connector_id)
                for connector_id in self.source_connectors
            ]
        if not self.evidence_summary_label:
            self.evidence_summary_label = _marketing_brief_evidence_count_label(
                len(self.evidence_ids)
            )
        if not self.action_summary_label:
            self.action_summary_label = _marketing_brief_action_count_label(len(self.action_ids))
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                _blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.dimension_labels:
            self.dimension_labels = {key: _tactical_dimension_label(key) for key in self.dimensions}
        if not self.dimension_value_labels:
            self.dimension_value_labels = {
                key: _tactical_dimension_value_label(key, value)
                for key, value in self.dimensions.items()
            }
        return self


class TacticalQueueGroup(BaseModel):
    id: str
    title: str
    meta: str
    diagnosis: str
    next_step: str
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_operator_labels(self) -> TacticalQueueGroup:
        if not self.priority_label:
            self.priority_label = _marketing_priority_label(self.priority)
        if not self.risk_label:
            self.risk_label = _marketing_risk_label(self.risk)
        if not self.source_connector_labels:
            self.source_connector_labels = [
                _marketing_brief_connector_label(connector_id)
                for connector_id in self.source_connectors
            ]
        if not self.evidence_summary_label:
            self.evidence_summary_label = _marketing_brief_evidence_count_label(
                len(self.evidence_ids)
            )
        if not self.action_summary_label:
            self.action_summary_label = _marketing_brief_action_count_label(len(self.action_ids))
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                _blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        return self


class TacticalQueueResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    items: list[TacticalQueueItem] = Field(default_factory=list)
    compact_groups: list[TacticalQueueGroup] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)


class AdsDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class AdsBlockedHandoff(BaseModel):
    id: str = "ads_oauth_blocked_handoff"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    marketer_message: str
    repair_steps: list[str] = Field(default_factory=list)
    allowed_demo_claims: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""


class AdsCampaignMetricRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    clicks: int | None = None
    clicks_label: str = ""
    impressions: int | None = None
    impressions_label: str = ""
    cost_micros: int | None = None
    cost_label: str = ""
    conversions: float | None = None
    conversions_label: str = ""
    conversion_value: float | None = None
    conversion_value_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak celu"
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "niski sygnał"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str = ""
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    human_review_gate_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsCampaignMetricRow:
        if not self.campaign_status_label:
            self.campaign_status_label = ads_campaign_status_label(self.campaign_status)
        if not self.advertising_channel_type_label:
            self.advertising_channel_type_label = ads_channel_type_label(
                self.advertising_channel_type
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.clicks_label:
            self.clicks_label = _operator_number_label(
                self.clicks,
                missing_label="brak odczytu kliknięć Ads",
            )
        if not self.impressions_label:
            self.impressions_label = _operator_number_label(
                self.impressions,
                missing_label="brak odczytu wyświetleń Ads",
            )
        if not self.cost_label:
            self.cost_label = _operator_micros_label(
                self.cost_micros,
                missing_label="brak odczytu kosztu Ads",
            )
        if not self.conversions_label:
            self.conversions_label = _operator_number_label(
                self.conversions,
                missing_label="brak odczytu konwersji Ads",
            )
        if not self.conversion_value_label:
            self.conversion_value_label = _operator_number_label(
                self.conversion_value,
                missing_label="brak odczytu wartości konwersji Ads",
            )
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        if not self.human_review_gate_summary_label:
            self.human_review_gate_summary_label = required_validation_count_label(
                self.human_review_gate_labels or self.human_review_gates
            )
        return self


def _operator_number_label(
    value: int | float | None,
    *,
    missing_label: str,
    max_fraction_digits: int = 2,
) -> str:
    if value is None:
        return missing_label
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    text = f"{value:,.{max_fraction_digits}f}".rstrip("0").rstrip(".")
    return text.replace(",", " ").replace(".", ",")


def _operator_micros_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{_operator_number_label(value / 1_000_000, missing_label=missing_label)} jedn. konta"


def _operator_percent_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{_operator_number_label(value * 100, missing_label=missing_label)}%"


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
    status_label: str = ""
    summary: str
    allowed_uses: list[str] = Field(default_factory=list)
    allowed_use_labels: list[str] = Field(default_factory=list)
    blocked_uses: list[str] = Field(default_factory=list)
    blocked_use_labels: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    missing_requirement_labels: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    policy_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    apply_allowed: bool = False
    destructive: bool = False

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsBusinessTargetInterpretation:
        if not self.policy_summary_label:
            self.policy_summary_label = policy_count_label(self.policy_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AdsStrategyReviewReadinessContract(BaseModel):
    id: str = "ads_strategy_review_readiness_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    latest_review_status: Literal[
        "missing",
        "approved_for_prepare",
        "needs_changes",
        "rejected",
        "deferred",
    ] = "missing"
    latest_review_status_label: str = ""
    latest_review_outcome: ActionReviewOutcome | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    current_context: dict[str, Any] = Field(default_factory=dict)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    required_validation_summary_label: str = ""
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    apply_allowed: bool = False
    destructive: bool = False
    next_step: str

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsStrategyReviewReadinessContract:
        if not self.required_validation_summary_label:
            self.required_validation_summary_label = required_validation_count_label(
                self.required_validation
            )
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsBusinessContextReadContract(BaseModel):
    id: str = "ads_business_context_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
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
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    target_interpretation: AdsBusinessTargetInterpretation
    strategy_review_readiness_contract: AdsStrategyReviewReadinessContract
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
    target_status_label: str = "brak celu"
    target_review_priority: int = 90
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsDerivedKpiRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


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
    safety_contract: Literal["campaign_budget_apply_safety_v1"] = "campaign_budget_apply_safety_v1"
    status: Literal["blocked"] = "blocked"
    status_label: str = ""
    reason: str
    max_allowed_delta_percent: float = 0.3
    current_budget_amount_micros: int | None = None
    proposed_budget_amount_micros: int | None = None
    proposed_delta_percent: float | None = None
    missing_requirements: list[str] = Field(default_factory=list)
    missing_requirement_labels: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
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
    operation_type_label: str = ""
    current_budget_amount_micros: int | None = None
    proposed_budget_amount_micros: int | None = None
    proposed_budget_delta_micros: int | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    safety_review: AdsBudgetApplySafetyReview
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsBudgetPacingRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    budget_id: str | None = None
    budget_name: str | None = None
    budget_period: str | None = None
    budget_period_label: str = ""
    budget_status: str | None = None
    budget_status_label: str = ""
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
    preview_card: ActionPreviewCardViewModel | None = None
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsBudgetPacingRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsSharedBudgetCampaignShare(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
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
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsSharedBudgetDistributionRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsBudgetPacingReadContract(BaseModel):
    id: str = "ads_budget_pacing_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    empty_state_message: str = ""
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
    recommendation_type_label: str = ""
    campaign_id: str | None = None
    campaign_budget_id: str | None = None
    operation_type: Literal["ApplyRecommendationOperation"] = "ApplyRecommendationOperation"
    operation_type_label: str = ""
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsRecommendationRow(BaseModel):
    recommendation_id: str | None = None
    recommendation_resource_name: str | None = None
    recommendation_type: str
    recommendation_type_label: str = ""
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "normalne"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    human_review_gate_summary_label: str = ""
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
    preview_card: ActionPreviewCardViewModel | None = None
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsRecommendationRow:
        if not self.human_review_gate_summary_label:
            self.human_review_gate_summary_label = required_validation_count_label(
                self.human_review_gate_labels or self.human_review_gates
            )
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsRecommendationsReadContract(BaseModel):
    id: str = "ads_recommendations_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
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
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    search_impression_share: float | None = None
    search_budget_lost_impression_share: float | None = None
    search_rank_lost_impression_share: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsImpressionShareRow:
        if not self.blocked_claim_labels:
            self.blocked_claim_labels = [
                blocked_claim_label(claim) for claim in self.blocked_claims
            ]
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsImpressionShareReadContract(BaseModel):
    id: str = "ads_impression_share_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    empty_state_message: str = ""
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    impression_share_rows: list[AdsImpressionShareRow] = Field(default_factory=list)
    next_step: str


class AdsCampaignTriageRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str | None = None
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str | None = None
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "niski sygnał"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    next_step: str
    target_status: Literal[
        "within_target",
        "outside_target",
        "spend_without_conversions",
        "insufficient_data",
        "no_target",
    ] = "no_target"
    target_status_label: str = "brak celu"
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    ctr: float | None = None
    average_cpc_micros: float | None = None
    conversion_rate: float | None = None
    cost_per_conversion_micros: float | None = None
    roas: float | None = None
    spend_to_budget_ratio_7d: float | None = None
    search_budget_lost_impression_share: float | None = None
    recommendation_count: int = 0
    recommendation_types: list[str] = Field(default_factory=list)
    has_budget_apply_preview: bool = False
    has_recommendation_apply_preview: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    source_metric_names: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    human_review_gate_summary_label: str = ""

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsCampaignTriageRow:
        if not self.campaign_status_label:
            self.campaign_status_label = ads_campaign_status_label(self.campaign_status)
        if not self.advertising_channel_type_label:
            self.advertising_channel_type_label = ads_channel_type_label(
                self.advertising_channel_type
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        if not self.human_review_gate_summary_label:
            self.human_review_gate_summary_label = required_validation_count_label(
                self.human_review_gate_labels or self.human_review_gates
            )
        return self


class AdsCampaignTriageReadContract(BaseModel):
    id: str = "ads_campaign_triage_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    triage_rows: list[AdsCampaignTriageRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    next_step: str


class AdsOptimizerReadinessItem(BaseModel):
    id: str
    label: str = ""
    title: str
    status: Literal["ready", "blocked"]
    status_label: str = ""
    summary: str
    next_step: str
    source_contract_ids: list[str] = Field(default_factory=list)
    source_contract_summary_label: str = ""
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    risk: ActionRisk = ActionRisk.medium
    risk_label: str = ""

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsOptimizerReadinessItem:
        if not self.source_contract_summary_label:
            self.source_contract_summary_label = source_contract_count_label(
                self.source_contract_ids
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsOptimizerReadinessContract(BaseModel):
    id: str = "ads_optimizer_readiness_contract"
    status: Literal["review_ready", "blocked"]
    status_label: str = ""
    mode: Literal["review_only"] = "review_only"
    mode_label: str = ""
    title: str
    summary: str
    ready_area_count: int = 0
    blocked_area_count: int = 0
    readiness_items: list[AdsOptimizerReadinessItem] = Field(default_factory=list)
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsOptimizerReadinessContract:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsChangeHistoryRow(BaseModel):
    change_event_id: str | None = None
    change_date_time: str | None = None
    change_resource_id: str | None = None
    change_resource_type: str | None = None
    change_resource_type_label: str = ""
    change_resource_label: str = ""
    resource_change_operation: str | None = None
    resource_change_operation_label: str = ""
    client_type: str | None = None
    client_type_label: str = ""
    campaign_id: str | None = None
    campaign_label: str = ""
    changed_field_count: int | None = None
    changed_fields: list[str] = Field(default_factory=list)
    changed_field_labels: list[str] = Field(default_factory=list)
    changed_field_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsChangeHistoryRow:
        if not self.change_resource_label:
            self.change_resource_label = _ads_change_resource_display_label(
                self.change_resource_type_label,
                self.change_resource_id,
            )
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(None, self.campaign_id)
        if not self.changed_field_summary_label:
            if self.changed_field_labels:
                self.changed_field_summary_label = ", ".join(self.changed_field_labels[:4])
            else:
                self.changed_field_summary_label = f"{self.changed_field_count or 0} pól"
        return self


class AdsChangeHistoryReadContract(BaseModel):
    id: str = "ads_change_history_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    allowed_metric_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    change_history_rows: list[AdsChangeHistoryRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    next_step: str


class AdsChangeImpactReadinessRow(BaseModel):
    change_event_id: str | None = None
    change_event_label: str = ""
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    change_date_time: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    changed_field_labels: list[str] = Field(default_factory=list)
    current_campaign_metrics_available: bool = False
    pre_window_available: bool = False
    post_window_available: bool = False
    current_clicks: int | None = None
    current_impressions: int | None = None
    current_cost_micros: int | None = None
    current_conversions: float | None = None
    current_conversion_value: float | None = None
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsChangeImpactReadinessRow:
        if not self.change_event_label:
            self.change_event_label = _ads_change_event_display_label(self.change_event_id)
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsChangeImpactReadinessContract(BaseModel):
    id: str = "ads_change_impact_readiness_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    allowed_metric_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    readiness_rows: list[AdsChangeImpactReadinessRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsChangeImpactReadinessContract:
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


def _ads_campaign_display_label(
    campaign_name: str | None,
    campaign_id: str | None,
) -> str:
    name = (campaign_name or "").strip()
    if name:
        return name
    if campaign_id:
        return "kampania do sprawdzenia w szczegółach technicznych"
    return "brak kampanii w odczycie"


def _ads_change_event_display_label(change_event_id: str | None) -> str:
    if change_event_id:
        return "zmiana do sprawdzenia w szczegółach technicznych"
    return "brak identyfikatora zmiany w odczycie"


def _ads_change_resource_display_label(
    resource_type_label: str | None,
    change_resource_id: str | None,
) -> str:
    resource = (resource_type_label or "").strip() or "zasób zmiany"
    if change_resource_id:
        return f"{resource} do sprawdzenia w szczegółach technicznych"
    return f"{resource} bez identyfikatora w odczycie"


def _ads_ad_group_display_label(
    ad_group_name: str | None,
    ad_group_id: str | None,
) -> str:
    name = (ad_group_name or "").strip()
    if name:
        return name
    if ad_group_id:
        return "grupa reklam do sprawdzenia w szczegółach technicznych"
    return "brak grupy reklam w odczycie"


class AdsSearchTermMetricRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    search_term_status: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermMetricRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermsReadContract(BaseModel):
    id: str = "ads_search_terms_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    next_step: str


class AdsSearchTermReviewRow(BaseModel):
    search_term: str
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    search_term_status: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermReviewRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermCampaignReviewRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    search_term_count: int = 0
    zero_conversion_search_term_count: int = 0
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermCampaignReviewRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermReviewSummaryContract(BaseModel):
    id: str = "ads_search_term_review_summary_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    total_search_term_count: int = 0
    zero_conversion_search_term_count: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    total_cost_micros: int = 0
    total_conversions: float = 0.0
    top_cost_search_terms: list[AdsSearchTermReviewRow] = Field(default_factory=list)
    campaign_review_rows: list[AdsSearchTermCampaignReviewRow] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsSearchTermReviewSummaryContract:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


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
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> AdsSearchTermNgramRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermNgramReadContract(BaseModel):
    id: str = "ads_search_term_ngram_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
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
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    search_term_status: str | None = None
    clicks_90d: int | None = None
    impressions_90d: int | None = None
    cost_micros_90d: int | None = None
    conversions_90d: float | None = None
    conversion_value_90d: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsSearchTermSafetyRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsSearchTermSafetyReadContract(BaseModel):
    id: str = "ads_search_term_safety_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    safety_rows: list[AdsSearchTermSafetyRow] = Field(default_factory=list)
    next_step: str


class AdsKeywordMatchContextRow(BaseModel):
    keyword_text: str
    match_type: str
    match_type_label: str = ""
    criterion_id: str | None = None
    criterion_status: str | None = None
    criterion_status_label: str = ""
    negative: bool | None = None
    negative_label: str = ""
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsKeywordMatchContextRow:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsKeywordMatchContextReadContract(BaseModel):
    id: str = "ads_keyword_match_context_read_contract"
    status: Literal["ready", "blocked"]
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
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
    operation_type: Literal["custom_segment_targeting_review"] = "custom_segment_targeting_review"
    reason: str
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentApplySafetyReview(BaseModel):
    id: str
    custom_segment_preview_id: str
    safety_contract: Literal["custom_segment_apply_safety_v1"] = "custom_segment_apply_safety_v1"
    status: Literal["blocked"] = "blocked"
    status_label: str = "zablokowane"
    reason: str
    missing_requirements: list[str] = Field(default_factory=list)
    missing_requirement_labels: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    audit_required: bool = True
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class AdsCustomSegmentPayloadPreview(BaseModel):
    id: str
    custom_segment_name: str
    member_type: Literal["KEYWORD"] = "KEYWORD"
    member_type_label: str = "słowa kluczowe"
    source_terms: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    campaign_name: str | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    targeting_preview: list[AdsCustomSegmentTargetingPreview] = Field(default_factory=list)
    safety_review: AdsCustomSegmentApplySafetyReview
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
    evidence_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsCustomSegmentAudienceForecastRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsCustomSegmentAudienceForecastReadContract(BaseModel):
    id: str = "ads_custom_segment_audience_forecast_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    checked_candidate_count: int = 0
    forecast_row_count: int = 0
    forecast_rows: list[AdsCustomSegmentAudienceForecastRow] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    next_step: str

    @model_validator(mode="after")
    def fill_operator_labels(self) -> AdsCustomSegmentAudienceForecastReadContract:
        if not self.status_label:
            self.status_label = _ads_read_contract_status_label(self.status)
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


def default_ads_custom_segment_audience_forecast_contract() -> (
    AdsCustomSegmentAudienceForecastReadContract
):
    return AdsCustomSegmentAudienceForecastReadContract(
        status="blocked",
        title="Prognoza i rozmiar odbiorców segmentów",
        summary=("Brak propozycji segmentów do sprawdzenia prognozy albo rozmiaru odbiorców."),
        missing_read_contracts=["custom_segment_candidates", "forecast_or_audience_size"],
        operator_review_gates=["forecast_or_audience_size", "human_confirm_before_apply"],
        blocked_claims=[
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
        ],
        next_step=("Najpierw zbuduj propozycje segmentów z realnych wyszukiwanych haseł."),
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
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    idea_rows: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_operator_labels(self) -> AdsKeywordPlannerReadContract:
        if not self.status_label:
            self.status_label = _ads_read_contract_status_label(self.status)
        return self


class AdsCustomSegmentSourceQuality(BaseModel):
    total_terms: int = 0
    accepted_terms: int = 0
    rejected_terms: int = 0
    missing_metric_terms: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    rejection_reason_labels: dict[str, int] = Field(default_factory=dict)


class AdsCustomSegmentCandidate(BaseModel):
    id: str
    name: str
    intent: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "normalne"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
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
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
    confidence_label: str = "niska"
    validation_status: Literal["pending_validation", "blocked"] = "pending_validation"
    validation_status_label: str = "do sprawdzenia"
    payload_preview: AdsCustomSegmentPayloadPreview | None = None
    preview_card: ActionPreviewCardViewModel | None = None
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_summary_labels(self) -> AdsCustomSegmentCandidate:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class AdsCustomSegmentsReadContract(BaseModel):
    id: str = "ads_custom_segments_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    candidates: list[AdsCustomSegmentCandidate] = Field(default_factory=list)
    payload_preview: list[AdsCustomSegmentPayloadPreview] = Field(default_factory=list)
    audience_forecast_read_contract: AdsCustomSegmentAudienceForecastReadContract = Field(
        default_factory=default_ads_custom_segment_audience_forecast_contract
    )
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_summary_label: str = ""
    next_step: str

    @model_validator(mode="after")
    def fill_operator_labels(self) -> AdsCustomSegmentsReadContract:
        if not self.status_label:
            self.status_label = _ads_read_contract_status_label(self.status)
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gates
            )
        return self


def _ads_read_contract_status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
    }
    return labels.get(status, "status do sprawdzenia")


class AdsNegativeKeywordPayloadPreview(BaseModel):
    id: str
    search_term: str
    negative_keyword_text: str
    match_type: Literal["EXACT"]
    match_type_label: str = ""
    level: Literal["ad_group", "campaign_review_required"]
    level_label: str = ""
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_metric_names: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsNegativeKeywordPayloadPreview:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        return self


class AdsNegativeKeywordCandidate(BaseModel):
    id: str
    search_term: str
    review_priority: Literal["pilne", "wysokie", "normalne", "niski sygnał"] = "normalne"
    review_score: int = Field(default=0, ge=0, le=100)
    review_reason: str
    human_review_gates: list[str] = Field(default_factory=list)
    human_review_gate_labels: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_label: str = ""
    ad_group_id: str | None = None
    ad_group_name: str | None = None
    ad_group_label: str = ""
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
    preview_card: ActionPreviewCardViewModel | None = None
    required_checks: list[str] = Field(default_factory=list)
    required_check_labels: list[str] = Field(default_factory=list)
    safety_status: Literal[
        "needs_90_day_review",
        "read_ready_needs_human_review",
        "blocked",
    ] = "needs_90_day_review"
    safety_status_label: str = ""
    validation_status: Literal["pending_validation", "blocked"] = "pending_validation"
    validation_status_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def hydrate_display_labels(self) -> AdsNegativeKeywordCandidate:
        if not self.campaign_label:
            self.campaign_label = _ads_campaign_display_label(
                self.campaign_name,
                self.campaign_id,
            )
        if not self.ad_group_label:
            self.ad_group_label = _ads_ad_group_display_label(
                self.ad_group_name,
                self.ad_group_id,
            )
        return self


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
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsNegativeKeywordsReadContract:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


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
        "review_campaign_triage",
    ]
    status: Literal["ready", "blocked"]
    status_label: str = ""
    decision_type_label: str = ""
    title: str
    summary: str
    start_here_summary: str = ""
    measurement_plan: str = ""
    rationale: str
    next_step: str
    priority: int = Field(default=50, ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_metrics: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    campaign_rows: list[AdsCampaignMetricRow] = Field(default_factory=list)
    campaign_triage_rows: list[AdsCampaignTriageRow] = Field(default_factory=list)
    derived_kpi_rows: list[AdsDerivedKpiRow] = Field(default_factory=list)
    budget_rows: list[AdsBudgetPacingRow] = Field(default_factory=list)
    shared_budget_distribution_rows: list[AdsSharedBudgetDistributionRow] = Field(
        default_factory=list
    )
    budget_apply_preview: list[AdsBudgetApplyPreview] = Field(default_factory=list)
    recommendation_rows: list[AdsRecommendationRow] = Field(default_factory=list)
    recommendation_apply_preview: list[AdsRecommendationApplyPreview] = Field(default_factory=list)
    impression_share_rows: list[AdsImpressionShareRow] = Field(default_factory=list)
    change_history_rows: list[AdsChangeHistoryRow] = Field(default_factory=list)
    search_term_rows: list[AdsSearchTermMetricRow] = Field(default_factory=list)
    search_term_ngram_rows: list[AdsSearchTermNgramRow] = Field(default_factory=list)
    search_term_safety_rows: list[AdsSearchTermSafetyRow] = Field(default_factory=list)
    keyword_match_context_rows: list[AdsKeywordMatchContextRow] = Field(default_factory=list)
    keyword_planner_idea_rows: list[AdsKeywordPlannerIdeaRow] = Field(default_factory=list)
    custom_segment_candidates: list[AdsCustomSegmentCandidate] = Field(default_factory=list)
    custom_segment_payload_preview: list[AdsCustomSegmentPayloadPreview] = Field(
        default_factory=list
    )
    custom_segment_audience_forecast_rows: list[AdsCustomSegmentAudienceForecastRow] = Field(
        default_factory=list
    )
    negative_keyword_candidates: list[AdsNegativeKeywordCandidate] = Field(default_factory=list)
    negative_keyword_payload_preview: list[AdsNegativeKeywordPayloadPreview] = Field(
        default_factory=list
    )
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    risk_label: str = ""
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsDecisionItem:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        return self


class AdsOperatorSummary(BaseModel):
    id: Literal["ads_operator_summary"] = "ads_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    campaign_count: int = 0
    search_term_count: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    total_cost_micros: int = 0
    total_conversions: float = 0.0
    total_conversion_value: float = 0.0
    ready_area_count: int = 0
    blocked_area_count: int = 0
    allowed_metrics: list[str] = Field(default_factory=list)
    allowed_metric_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    operator_review_gate_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    top_blocked_claim_labels: list[str] = Field(default_factory=list)
    top_blocked_claim_summary_label: str = ""

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AdsOperatorSummary:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.operator_review_gate_summary_label:
            self.operator_review_gate_summary_label = required_validation_count_label(
                self.operator_review_gate_labels or self.operator_review_gates
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(
                self.blocked_claim_labels or self.blocked_claims
            )
        if not self.top_blocked_claim_labels:
            self.top_blocked_claim_labels = list(self.blocked_claim_labels or self.blocked_claims)
        if not self.top_blocked_claim_summary_label:
            self.top_blocked_claim_summary_label = blocked_claim_count_label(
                self.top_blocked_claim_labels
            )
        return self


class AdsFreshnessAssessment(BaseModel):
    state: Literal["fresh", "stale", "missing", "blocked"]
    state_label: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    latest_refresh_id: str | None = None
    latest_refresh_completed_at: datetime | None = None
    age_hours: float | None = None
    stale_after_hours: int = 48
    requires_refresh: bool
    summary: str
    next_step: str


class AdsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    live_data_status_label: str = ""
    live_data_available: bool
    freshness_assessment: AdsFreshnessAssessment
    campaign_read_contract: AdsCampaignReadContract
    account_currency_read_contract: AdsAccountCurrencyReadContract
    business_context_read_contract: AdsBusinessContextReadContract
    derived_kpi_read_contract: AdsDerivedKpiReadContract
    budget_pacing_read_contract: AdsBudgetPacingReadContract
    recommendations_read_contract: AdsRecommendationsReadContract
    impression_share_read_contract: AdsImpressionShareReadContract
    campaign_triage_read_contract: AdsCampaignTriageReadContract
    optimizer_readiness_contract: AdsOptimizerReadinessContract
    change_history_read_contract: AdsChangeHistoryReadContract
    change_impact_readiness_contract: AdsChangeImpactReadinessContract
    search_terms_read_contract: AdsSearchTermsReadContract
    search_term_review_summary_contract: AdsSearchTermReviewSummaryContract
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract
    keyword_planner_read_contract: AdsKeywordPlannerReadContract
    custom_segments_read_contract: AdsCustomSegmentsReadContract
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract
    operator_summary: AdsOperatorSummary
    decision_queue: list[AdsDecisionItem] = Field(default_factory=list)
    sections: list[AdsDiagnosticSection] = Field(default_factory=list)
    blocked_handoff: AdsBlockedHandoff | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
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
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenAdGroupAdRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class DemandGenCreativeAssetRow(BaseModel):
    asset_id: str | None = None
    asset_type: str | None = None
    field_type: str | None = None
    impressions: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenCreativeAssetRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class DemandGenLandingQualityRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    landing_page: str
    landing_page_label: str = ""
    source_medium: str | None = None
    source_medium_label: str = ""
    active_users: int | None = None
    active_users_label: str = ""
    sessions: int | None = None
    sessions_label: str = ""
    engagement_rate: float | None = None
    engagement_rate_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenLandingQualityRow:
        if not self.landing_page_label:
            self.landing_page_label = self.landing_page or "brak strony wejścia w raporcie"
        if not self.source_medium_label:
            self.source_medium_label = self.source_medium or "brak źródła ruchu"
        if not self.active_users_label:
            self.active_users_label = _operator_number_label(
                self.active_users,
                missing_label="brak odczytu aktywnych użytkowników GA4",
            )
        if not self.sessions_label:
            self.sessions_label = _operator_number_label(
                self.sessions,
                missing_label="brak odczytu sesji GA4",
            )
        if not self.engagement_rate_label:
            self.engagement_rate_label = _operator_percent_label(
                self.engagement_rate,
                missing_label="brak odczytu zaangażowania GA4",
            )
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class DemandGenCampaignModeReviewRow(BaseModel):
    campaign_id: str | None = None
    campaign_name: str
    campaign_status: str | None = None
    campaign_status_label: str = ""
    advertising_channel_type: str | None = None
    advertising_channel_type_label: str = ""
    review_required: bool = False
    review_status_label: str = ""
    reason: str
    reason_label: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""

    @model_validator(mode="after")
    def fill_summary_labels(self) -> DemandGenCampaignModeReviewRow:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        return self


class MerchantDiagnosticSection(BaseModel):
    id: str
    label: str = ""
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""


class MerchantIssueCluster(BaseModel):
    id: str
    issue_type: str
    issue_type_label: str | None = None
    severity: str
    severity_label: str | None = None
    resolution: str | None = None
    resolution_label: str | None = None
    affected_attribute: str | None = None
    affected_attribute_label: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    reporting_context_label: str
    product_count: int = 0
    reported_issue_summary_label: str = ""
    count_semantics: Literal["reported_issue_occurrences"] = "reported_issue_occurrences"
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_titles: list[str] = Field(default_factory=list)
    sample_unavailable_reason: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    action_id: str | None = None
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""
    next_step: str

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> MerchantIssueCluster:
        if not self.reported_issue_summary_label:
            self.reported_issue_summary_label = reported_issue_occurrence_count_label(
                self.product_count
            )
        return self


class MerchantDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_issue_cluster",
        "review_feed_status",
        "review_product_state_mapping",
        "review_price_impact_readiness",
        "block_until_vendor_read",
    ]
    decision_type_label: str = ""
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    title: str
    summary: str | None = None
    cluster_id: str | None = None
    issue_cluster_ids: list[str] = Field(default_factory=list)
    issue_type: str | None = None
    issue_type_label: str | None = None
    severity: str | None = None
    severity_label: str | None = None
    resolution: str | None = None
    resolution_label: str | None = None
    affected_attribute: str | None = None
    affected_attribute_label: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    reporting_context_label: str | None = None
    product_count: int | None = None
    issue_count: int | None = None
    count_semantics: Literal["reported_issue_occurrences"] = "reported_issue_occurrences"
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_titles: list[str] = Field(default_factory=list)
    change_preview: list[dict[str, Any]] = Field(default_factory=list)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    why_it_matters: str | None = None
    operator_action: str | None = None
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""

    @model_validator(mode="after")
    def fill_operator_aliases(self) -> MerchantDecisionItem:
        if not self.priority_label:
            self.priority_label = _marketing_priority_label(self.priority)
        if self.why_it_matters is None:
            self.why_it_matters = self.rationale
        if self.operator_action is None:
            self.operator_action = self.next_step
        return self


class MerchantOperatorSummary(BaseModel):
    id: Literal["merchant_operator_summary"] = "merchant_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    top_issue_cluster_ids: list[str] = Field(default_factory=list)
    top_tactical_item_ids: list[str] = Field(default_factory=list)
    reported_issue_occurrences: int = 0
    decision_source: Literal["decision_queue"] = "decision_queue"
    decision_source_label: str = "kolejka decyzji Merchant"
    drilldown_source: Literal["issue_clusters"] = "issue_clusters"
    drilldown_source_label: str = "grupy problemów pliku produktowego"
    count_semantics: Literal["reported_issue_occurrences"] = "reported_issue_occurrences"
    count_semantics_label: str = "wystąpienia problemów w raportach"
    issue_types: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantFreshnessAssessment(BaseModel):
    state: Literal["fresh", "stale", "missing", "blocked"]
    state_label: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    latest_refresh_id: str | None = None
    latest_refresh_completed_at: datetime | None = None
    age_hours: float | None = None
    stale_after_hours: int = 48
    requires_refresh: bool
    summary: str
    next_step: str


class MerchantUnknownFact(BaseModel):
    id: str
    title: str
    reason: str
    impact: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantProductSampleReadiness(BaseModel):
    status: Literal["ready", "blocked"]
    status_label: str = ""
    sample_products_available: bool = False
    sample_count: int = 0
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_product_titles: list[str] = Field(default_factory=list)
    sample_summary_label: str = ""
    sample_title_labels: list[str] = Field(default_factory=list)
    current_read_contract: Literal["merchant_aggregate_product_statuses"] = (
        "merchant_aggregate_product_statuses"
    )
    required_read_contracts: list[str] = Field(default_factory=list)
    source_endpoint: str
    summary: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantProductPerformanceRow(BaseModel):
    product_id: str
    title_label: str = ""
    product_reference_label: str = ""
    sample_title: str | None = None
    issue_type: str | None = None
    issue_type_label: str | None = None
    affected_attribute: str | None = None
    affected_attribute_label: str | None = None
    country: str | None = None
    reporting_context: str | None = None
    reporting_context_label: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    ads_product_title: str | None = None
    ads_product_status: str | None = None
    ads_product_status_label: str = ""
    ads_product_availability: str | None = None
    ads_product_availability_label: str = ""
    ads_product_price_micros: int | None = None
    ads_product_price_label: str = ""
    ads_product_currency_code: str | None = None
    ads_product_price_collected_at: datetime | None = None
    ads_product_previous_price_micros: int | None = None
    ads_product_previous_price_collected_at: datetime | None = None
    ads_product_previous_price_evidence_id: str | None = None
    ads_product_price_delta_micros: int | None = None
    ads_product_price_delta_percent: float | None = None
    ads_clicks: int | None = None
    ads_clicks_label: str = ""
    ads_cost_micros: int | None = None
    ads_cost_label: str = ""
    ads_conversions: float | None = None
    ads_conversions_label: str = ""
    ads_conversion_value: float | None = None
    ads_conversion_value_label: str = ""
    ga4_ecommerce_purchases: float | None = None
    ga4_ecommerce_purchases_label: str = ""
    ga4_purchase_revenue: float | None = None
    ga4_purchase_revenue_label: str = ""
    missing_metrics: list[str] = Field(default_factory=list)
    missing_metric_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantProductPerformanceReadiness(BaseModel):
    id: Literal["merchant_product_performance_readiness"] = "merchant_product_performance_readiness"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    joined_product_count: int = 0
    merchant_sample_count: int = 0
    ads_product_fact_count: int = 0
    ga4_product_fact_count: int = 0
    current_read_contracts: list[str] = Field(default_factory=list)
    required_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    join_key_candidates: list[str] = Field(default_factory=list)
    sample_product_ids: list[str] = Field(default_factory=list)
    sample_product_summary_label: str = ""
    performance_rows: list[MerchantProductPerformanceRow] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    summary: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantPriceImpactReadiness(BaseModel):
    id: Literal["merchant_price_impact_readiness"] = "merchant_price_impact_readiness"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    products_with_current_price: int = 0
    products_with_previous_price: int = 0
    products_with_price_change: int = 0
    products_with_unchanged_price_history: int = 0
    products_with_performance_metrics: int = 0
    current_read_contracts: list[str] = Field(default_factory=list)
    required_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    change_preview: list[dict[str, Any]] = Field(default_factory=list)
    preview_cards: list[ActionPreviewCardViewModel] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    summary: str
    next_step: str
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class MerchantDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    live_data_available: bool
    live_data_status_label: str = ""
    product_count: int | None = None
    issue_count: int | None = None
    freshness_assessment: MerchantFreshnessAssessment
    unknowns: list[MerchantUnknownFact] = Field(default_factory=list)
    product_sample_readiness: MerchantProductSampleReadiness
    product_performance_readiness: MerchantProductPerformanceReadiness
    price_impact_readiness: MerchantPriceImpactReadiness
    operator_summary: MerchantOperatorSummary
    issue_clusters: list[MerchantIssueCluster] = Field(default_factory=list)
    decision_queue: list[MerchantDecisionItem] = Field(default_factory=list)
    sections: list[MerchantDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
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
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class ContentAhrefsCandidateRow(BaseModel):
    id: str
    topic: str
    gap_type: str
    gap_type_label: str = ""
    relevance_status: Literal["relevant", "review", "off_topic"]
    relevance_status_label: str = ""
    relevance_score: int
    business_relevance_reasons: list[str] = Field(default_factory=list)
    business_relevance_reason_labels: list[str] = Field(default_factory=list)
    gsc_demand: Literal["present", "missing"]
    gsc_demand_label: str = ""
    wordpress_inventory_match: Literal["present", "missing"]
    wordpress_inventory_match_label: str = ""
    gsc_overlap_terms: list[str] = Field(default_factory=list)
    wordpress_overlap_urls: list[str] = Field(default_factory=list)
    keyword: str | None = None
    competitor_domain: str | None = None
    source_url: str | None = None
    referenced_public_url: str | None = None
    metric_name: str
    metric_value: int | float | str
    evidence_ids: list[str] = Field(default_factory=list)
    next_step: str


class ContentDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "block_until_vendor_read",
        "refresh_or_merge",
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
        "block_as_tracking_not_content",
        "review_ahrefs_gap_records",
    ]
    status: Literal["ready", "blocked"] = "ready"
    decision_type_label: str = ""
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
    wordpress_match_label: str | None = None
    wordpress_match_confidence: str | None = None
    wordpress_match_confidence_label: str | None = None
    source_public_url: str | None = None
    preview_url: str | None = None
    intended_final_url: str | None = None
    final_canonical_url: str | None = None
    inventory_gate_status: str | None = None
    inventory_gate_status_label: str | None = None
    canonical_gate_status: str | None = None
    canonical_gate_status_label: str | None = None
    duplicate_gate_status: str | None = None
    duplicate_gate_status_label: str | None = None
    content_gate_summary: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    ahrefs_candidate_rows: list[ContentAhrefsCandidateRow] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentDecisionItem:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentOperatorSummary(BaseModel):
    id: Literal["content_operator_summary"] = "content_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    confirmed_wordpress_count: int = 0
    missing_wordpress_count: int = 0
    current_site_match_count: int = 0
    decision_type_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentOperatorSummary:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentMarketerDecision(BaseModel):
    id: str
    technical_decision_id: str
    status: Literal["ready", "blocked"]
    decision: str
    mode_label: str
    why_it_matters: str
    safe_next_action: str
    review_card_label: str = "Karta decyzji dla Wilka"
    review_decision_after_review: str
    review_question_for_wilku: str
    review_next_safe_click: str
    review_action_ids: list[str] = Field(default_factory=list)
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    content_angle: str | None = None
    h1_direction: str | None = None
    h2_direction: list[str] = Field(default_factory=list)
    faq_direction: list[str] = Field(default_factory=list)
    cta_direction: str | None = None
    source_facts: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    evidence_summary: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    measurement_plan: str
    source_public_url: str | None = None
    preview_url: str | None = None
    intended_final_url: str | None = None
    final_canonical_url: str | None = None

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentMarketerDecision:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentPreflightItem(BaseModel):
    id: str
    technical_decision_id: str
    recommended_mode: Literal["preserve", "refresh", "merge", "create", "block"]
    recommended_mode_label: str = ""
    status: Literal["allowed", "review_required", "blocked"]
    status_label: str = ""
    create_allowed: bool = False
    draft_allowed: bool = False
    wordpress_draft_allowed: bool = False
    sales_brief_allowed: bool = False
    source_public_url: str | None = None
    preview_url: str | None = None
    intended_final_url: str | None = None
    final_canonical_url: str | None = None
    inventory_gate_status: str | None = None
    inventory_gate_status_label: str | None = None
    canonical_gate_status: str | None = None
    canonical_gate_status_label: str | None = None
    duplicate_gate_status: str | None = None
    duplicate_gate_status_label: str | None = None
    claim_gate_status: str
    claim_gate_status_label: str = ""
    service_fit_status: str
    service_fit_status_label: str = ""
    similar_existing_urls: list[str] = Field(default_factory=list)
    query_overlap_summary: str
    blocked_claims: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    next_step: str

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentPreflightItem:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentPreflightResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    primary_item: ContentPreflightItem | None = None
    items: list[ContentPreflightItem] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    blocker_count: int = 0

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> ContentPreflightResponse:
        if not self.source_connector_labels:
            self.source_connector_labels = source_connector_labels(self.source_connectors)
        return self


class ContentGscSearchAnalyticsContract(BaseModel):
    source_connector: Literal["google_search_console"] = "google_search_console"
    evidence_ids: list[str] = Field(default_factory=list)
    data_availability_checked: bool = False
    date_availability_status: str = ""
    expected_data_delay_days_min: int = 2
    expected_data_delay_days_max: int = 3
    availability_date_start: str | None = None
    availability_date_end: str | None = None
    detail_date_start: str | None = None
    detail_date_end: str | None = None
    latest_available_detail_date: str | None = None
    search_type: str = ""
    detail_dimensions: str = ""
    detail_data_completeness: str = ""
    read_granularity: Literal["single_day_latest_available"] = "single_day_latest_available"
    api_recommended_page_size: int = 25000
    api_daily_row_cap_per_search_type: int = 50000
    query_page_row_limit: int | None = None
    query_page_max_rows: int | None = None
    query_page_rows_truncated: bool = False
    aggregate_date_start: str | None = None
    aggregate_date_end: str | None = None
    aggregate_dimensions: str = ""
    aggregate_aggregation_type: str = ""
    aggregate_data_completeness: str = ""
    aggregate_row_count: int | None = None
    aggregate_clicks: int | None = None
    aggregate_impressions: int | None = None
    aggregate_ctr: float | None = None
    aggregate_average_position: float | None = None
    aggregate_summary_label: str = ""
    summary_label: str = ""
    partial_detail_warning_label: str = ""
    paging_label: str = ""
    official_limits_label: str = ""
    wilq_internal_cap_label: str = ""


class ContentFreshnessAssessment(BaseModel):
    state: Literal["fresh", "stale", "missing", "blocked"]
    state_label: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    stale_after_hours: int = 48
    requires_refresh: bool
    missing_connector_ids: list[str] = Field(default_factory=list)
    blocked_connector_ids: list[str] = Field(default_factory=list)
    stale_connector_ids: list[str] = Field(default_factory=list)
    connector_labels_requiring_refresh: list[str] = Field(default_factory=list)
    summary: str
    next_step: str


class ContentDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connectors: list[ConnectorStatus]
    latest_refreshes: list[ConnectorRefreshRun] = Field(default_factory=list)
    live_data_available: bool
    live_data_status_label: str = ""
    freshness_assessment: ContentFreshnessAssessment
    gsc_search_analytics_contract: ContentGscSearchAnalyticsContract | None = None
    query_page_count: int = 0
    matched_inventory_count: int = 0
    operator_summary: ContentOperatorSummary
    marketer_decision: ContentMarketerDecision | None = None
    decision_queue: list[ContentDecisionItem] = Field(default_factory=list)
    sections: list[ContentDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0


class Ga4TrackingQualityPayloadPreview(BaseModel):
    id: str
    preview_contract: Literal["ga4_tracking_quality_review_v1"]
    operation_type: Literal["tracking_quality_review"]
    operation_type_label: str = ""
    landing_page: str | None = None
    landing_page_label: str = ""
    source_medium: str | None = None
    source_medium_label: str = ""
    campaign_name: str | None = None
    campaign_name_label: str = ""
    tracking_dimension_gaps: list[Literal["landing_page", "source_medium", "campaign_name"]] = (
        Field(default_factory=list)
    )
    tracking_dimension_gap_labels: list[str] = Field(default_factory=list)
    metric_snapshot: dict[str, float | int | str] = Field(default_factory=dict)
    metric_snapshot_labels: dict[str, str] = Field(default_factory=dict)
    reason: str
    required_validation: list[str] = Field(default_factory=list)
    required_validation_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    api_mutation_ready: bool = False
    apply_allowed: bool = False
    destructive: bool = False


class Ga4DiagnosticSection(BaseModel):
    id: str
    label: str = ""
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    tactical_items: list[TacticalQueueItem] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""


class Ga4DecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "fix_measurement",
        "review_traffic_quality",
        "review_landing_mapping",
    ]
    decision_type_label: str = ""
    title: str
    status: Literal["ready", "blocked"] = "ready"
    status_label: str = ""
    priority: int = Field(default=50, ge=1, le=100)
    metric_tiles: dict[str, float | int | str] = Field(default_factory=dict)
    landing_page: str | None = None
    landing_page_label: str = ""
    source_medium: str | None = None
    source_medium_label: str = ""
    campaign_name: str | None = None
    campaign_name_label: str = ""
    wordpress_match: str | None = None
    wordpress_match_label: str | None = None
    wordpress_match_confidence: str | None = None
    wordpress_match_confidence_label: str | None = None
    wordpress_content_url: str | None = None
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    rationale: str
    next_step: str
    risk: ActionRisk = ActionRisk.low
    risk_label: str = ""


class Ga4ConversionReadinessContract(BaseModel):
    id: Literal["ga4_conversion_readiness_contract"] = "ga4_conversion_readiness_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    allowed_metrics: list[str] = Field(default_factory=list)
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    conversion_like_metric_count: int = 0
    dimensioned_behavior_metric_count: int = 0
    landing_group_count: int = 0
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium

    @model_validator(mode="after")
    def hydrate_operator_labels(self) -> Ga4ConversionReadinessContract:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        return self


class Ga4FreshnessAssessment(BaseModel):
    state: Literal["fresh", "stale", "missing", "blocked"]
    state_label: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    latest_refresh_id: str | None = None
    latest_refresh_completed_at: datetime | None = None
    age_hours: float | None = None
    stale_after_hours: int = 48
    requires_refresh: bool
    summary: str
    next_step: str


class Ga4OperatorSummary(BaseModel):
    id: Literal["ga4_operator_summary"] = "ga4_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    measurement_issue_count: int = 0
    wordpress_missing_count: int = 0
    conversion_readiness_status: Literal["ready", "blocked"]
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)


class Ga4DiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str = ""
    live_data_available: bool
    live_data_status_label: str = ""
    landing_group_count: int = 0
    low_engagement_count: int = 0
    wordpress_match_count: int = 0
    freshness_assessment: Ga4FreshnessAssessment
    conversion_readiness_contract: Ga4ConversionReadinessContract
    operator_summary: Ga4OperatorSummary
    decision_queue: list[Ga4DecisionItem] = Field(default_factory=list)
    sections: list[Ga4DiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0
    decision_blocker_count: int = 0


class LocaloAccessProbe(BaseModel):
    status: Literal["access_ready", "access_blocked", "unknown"]
    status_label: str = ""
    source_run_id: str | None = None
    mcp_initialize_status: int | None = None
    access_check_label: str = ""
    authorization_code_supported: bool | None = None
    authorization_code_supported_label: str = ""
    authorization_readiness_label: str = ""
    pkce_s256_supported: bool | None = None
    pkce_s256_supported_label: str = ""
    secure_readiness_label: str = ""
    access_token_present: bool | None = None
    access_token_present_label: str = ""
    credential_readiness_label: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    summary: str


class LocaloDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class LocaloReadContractStatus(BaseModel):
    id: Literal[
        "place_inventory",
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
        "local_tasks",
    ]
    id_label: str = ""
    status: Literal["ready", "missing"]
    status_label: str = ""
    evidence_kind: str
    metric_fact_names: list[str] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    next_step: str


class LocaloDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "access_ready_wait_for_visibility_facts",
        "fix_access",
        "review_local_visibility",
        "block_visibility_claims",
    ]
    decision_type_label: str = ""
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    rationale: str
    next_step: str
    access_status: Literal["access_ready", "access_blocked", "unknown"]
    access_status_label: str = ""
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_evidence: list[str] = Field(default_factory=list)
    allowed_evidence_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    read_contract_statuses: list[LocaloReadContractStatus] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    action_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low


class LocaloOperatorSummary(BaseModel):
    id: Literal["localo_operator_summary"] = "localo_operator_summary"
    title: str
    summary: str
    next_step: str
    review_card_label: str = "Karta review Localo"
    review_decision_after_review: str
    review_question_for_operator: str
    review_next_safe_click: str
    review_action_ids: list[str] = Field(default_factory=list)
    top_decision_ids: list[str] = Field(default_factory=list)
    access_status: Literal["access_ready", "access_blocked", "unknown"]
    access_status_label: str = ""
    visibility_fact_count: int = 0
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    read_contract_statuses: list[LocaloReadContractStatus] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def hydrate_operator_summary_labels(self) -> LocaloOperatorSummary:
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        return self


class LocaloDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    access_probe: LocaloAccessProbe
    live_data_available: bool
    visibility_fact_count: int = 0
    read_contract_statuses: list[LocaloReadContractStatus] = Field(default_factory=list)
    operator_summary: LocaloOperatorSummary
    decision_queue: list[LocaloDecisionItem] = Field(default_factory=list)
    sections: list[LocaloDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    blocker_count: int = 0


class AhrefsDiagnosticSection(BaseModel):
    id: str
    title: str
    status: Literal["ready", "blocked", "missing"]
    status_label: str = ""
    summary: str
    diagnosis: str
    next_step: str
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsDiagnosticSection:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AhrefsDecisionItem(BaseModel):
    id: str
    decision_type: Literal[
        "review_authority_context",
        "review_gap_records",
        "run_authority_read",
        "block_gap_claims",
    ]
    status: Literal["ready", "blocked"]
    status_label: str = ""
    decision_type_label: str = ""
    title: str
    summary: str
    rationale: str
    next_step: str
    priority: int = Field(ge=1, le=100)
    priority_label: str = ""
    metric_tiles: dict[str, int | float | str] = Field(default_factory=dict)
    allowed_evidence: list[str] = Field(default_factory=list)
    allowed_evidence_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    knowledge_card_ids: list[str] = Field(default_factory=list)
    expert_rule_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    risk: ActionRisk = ActionRisk.low

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsDecisionItem:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AhrefsGapRecord(BaseModel):
    id: str
    gap_type: Literal[
        "competitor_page",
        "content_gap",
        "backlink_gap",
        "organic_keyword_gap",
        "top_page_gap",
    ]
    gap_type_label: str = ""
    title: str
    summary: str
    source_url: str | None = None
    referenced_public_url: str | None = None
    competitor_domain: str | None = None
    keyword: str | None = None
    metric_facts: list[MetricFact] = Field(default_factory=list)
    metric_fact_labels: dict[str, str] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium


class AhrefsGapReadContract(BaseModel):
    id: Literal["ahrefs_gap_read_contract"] = "ahrefs_gap_read_contract"
    status: Literal["ready", "blocked"]
    status_label: str = ""
    title: str
    summary: str
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contract_summary_label: str = ""
    allowed_evidence: list[str] = Field(default_factory=list)
    allowed_evidence_labels: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)
    blocked_claim_summary_label: str = ""
    operator_review_gates: list[str] = Field(default_factory=list)
    operator_review_gate_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    gap_records: list[AhrefsGapRecord] = Field(default_factory=list)
    gap_record_count: int = 0
    cross_check_status: Literal["api_backed", "manual_required", "missing"] = "missing"
    cross_check_status_label: str = ""
    cross_check_summary: str = ""
    cross_check_next_step: str = ""
    cross_check_gsc_match_count: int = 0
    cross_check_wordpress_match_count: int = 0
    cross_check_source_connectors: list[str] = Field(default_factory=list)
    cross_check_evidence_ids: list[str] = Field(default_factory=list)
    cross_check_candidates: list[ContentAhrefsCandidateRow] = Field(default_factory=list)
    next_step: str
    risk: ActionRisk = ActionRisk.medium

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsGapReadContract:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        if not self.missing_read_contract_summary_label:
            self.missing_read_contract_summary_label = missing_contract_count_label(
                self.missing_read_contracts
            )
        if not self.blocked_claim_summary_label:
            self.blocked_claim_summary_label = blocked_claim_count_label(self.blocked_claims)
        return self


class AhrefsOperatorSummary(BaseModel):
    id: Literal["ahrefs_operator_summary"] = "ahrefs_operator_summary"
    title: str
    summary: str
    next_step: str
    top_decision_ids: list[str] = Field(default_factory=list)
    gap_read_status: Literal["ready", "blocked"]
    gap_read_status_label: str = ""
    authority_fact_count: int = 0
    gap_fact_count: int = 0
    available_read_contracts: list[str] = Field(default_factory=list)
    available_read_contract_labels: list[str] = Field(default_factory=list)
    missing_read_contracts: list[str] = Field(default_factory=list)
    missing_read_contract_labels: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocked_claims: list[str] = Field(default_factory=list)
    blocked_claim_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsOperatorSummary:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


class AhrefsDiagnosticsResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    language: Literal["pl-PL"] = "pl-PL"
    strict_instruction: str
    connector: ConnectorStatus
    connector_status_label: str = ""
    latest_refresh: ConnectorRefreshRun | None = None
    latest_refresh_status_label: str | None = None
    live_data_status_label: str = ""
    live_data_available: bool
    authority_fact_count: int = 0
    gap_fact_count: int = 0
    gap_read_contract: AhrefsGapReadContract
    operator_summary: AhrefsOperatorSummary
    decision_queue: list[AhrefsDecisionItem] = Field(default_factory=list)
    sections: list[AhrefsDiagnosticSection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_summary_label: str = ""
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    blocker_count: int = 0

    @model_validator(mode="after")
    def fill_trace_summary_labels(self) -> AhrefsDiagnosticsResponse:
        if not self.evidence_summary_label:
            self.evidence_summary_label = evidence_count_label(self.evidence_ids)
        if not self.action_summary_label:
            self.action_summary_label = action_count_label(self.action_ids)
        return self


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
