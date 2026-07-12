from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from wilq.operator_labels import (
    connector_refresh_status_label,
    credential_field_count_label,
    credential_source_count_label,
    evidence_count_label,
    metric_fact_label,
    source_connector_label,
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
    queued = "queued"
    running = "running"
    completed = "completed"
    blocked = "blocked"
    failed = "failed"


class ConnectorRefreshJobState(StrEnum):
    queued = "queued"
    running = "running"
    ready = "ready"
    stale = "stale"
    partial = "partial"
    failed = "failed"
    blocked = "blocked"
    unknown = "unknown"


class ConnectorRefreshTriggerReason(StrEnum):
    eligible_stale = "eligible_stale"
    not_stale = "not_stale"
    active_run = "active_run"
    cooldown = "cooldown"
    missing_credentials = "missing_credentials"
    not_configured = "not_configured"
    read_unavailable = "read_unavailable"
    partial_read = "partial_read"
    failed_read = "failed_read"
    blocked_read = "blocked_read"
    unknown_state = "unknown_state"


class ConnectorRefreshTriggerPolicy(BaseModel):
    eligible: bool = False
    reason: ConnectorRefreshTriggerReason = ConnectorRefreshTriggerReason.unknown_state
    reason_label: str = "Automatyczne odświeżenie wymaga sprawdzenia."
    safe_next_step: str = "Sprawdź stan źródła przed automatycznym odczytem."
    cooldown_seconds: int = 900


class ConnectorRefreshState(BaseModel):
    state: ConnectorRefreshJobState = ConnectorRefreshJobState.unknown
    state_label: str = "stan odświeżenia do sprawdzenia"
    refresh_allowed: bool = False
    last_run_id: str | None = None
    last_run_status: ConnectorRefreshStatus | None = None
    last_run_started_at: datetime | None = None
    last_run_completed_at: datetime | None = None
    safe_next_step: str = "Sprawdź stan źródła przed użyciem danych w decyzji."
    affected_decisions: list[str] = Field(default_factory=list)
    automatic_refresh: ConnectorRefreshTriggerPolicy = Field(
        default_factory=ConnectorRefreshTriggerPolicy
    )


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


class KnowledgeTaxonomyType(StrEnum):
    client_truth = "client_truth"
    expert_operating = "expert_operating"
    platform_trap = "platform_trap"
    workspace_memory = "workspace_memory"
    observed_outcome = "observed_outcome"


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
    refresh_state: ConnectorRefreshState = Field(default_factory=ConnectorRefreshState)
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
    run_async: bool = False


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


def _metric_dimension_value_labels() -> dict[str, str]:
    return {
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


METRIC_DIMENSION_VALUE_LABELS = _metric_dimension_value_labels()


def _metric_dimension_value_label(key: str, value: str) -> str:
    text = str(value or "").strip()
    labels = METRIC_DIMENSION_VALUE_LABELS
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
