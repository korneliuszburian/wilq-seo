from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from wilq.operator_labels import blocked_claim_label

from .core import ActionRisk, MetricFact, OpportunityDomain, utc_now


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
