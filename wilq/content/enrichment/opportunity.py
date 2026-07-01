from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.workflow.decision_mapping import content_work_item_from_decision
from wilq.content.workflow.queue import (
    ContentWorkItemQueueCandidate,
    ContentWorkItemQueueResponse,
)
from wilq.schemas import ContentAhrefsCandidateRow, ContentDecisionItem, ContentDiagnosticsResponse

ContentOpportunityEnrichmentStatus = Literal["ready", "blocked"]
ContentOpportunityIntent = Literal[
    "informational_service",
    "service_comparison",
    "compliance_risk",
    "measurement_fix",
    "gap_review",
    "unknown",
]
ContentOpportunitySignalKind = Literal[
    "gsc_query",
    "gsc_page",
    "ga4_behavior",
    "ahrefs_gap",
    "ads_search_term",
    "merchant_service_signal",
    "wordpress_inventory",
    "measurement",
]


class ContentOpportunityEnrichmentBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    reason: str
    next_step: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentOpportunitySourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    signal_kind: ContentOpportunitySignalKind
    label: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    metric_value: int | float | str | None = None
    source_url: str | None = None


class ContentOpportunityMeasurementBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready_to_plan", "blocked"]
    label: str
    reason: str
    metrics_to_watch: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentOpportunityEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    work_item_id: str
    decision_id: str
    status: ContentOpportunityEnrichmentStatus
    title: str
    topic: str
    recommended_mode: str
    intent: ContentOpportunityIntent
    intent_label: str
    buyer_problem: str
    buyer_trigger: str
    service_fit: str
    cta_hypothesis: str
    source_facts: list[ContentOpportunitySourceFact] = Field(default_factory=list)
    measurement_baseline: ContentOpportunityMeasurementBaseline
    blockers: list[ContentOpportunityEnrichmentBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    safe_next_step: str


class ContentOpportunityEnrichmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrichment: ContentOpportunityEnrichment | None = None
    blockers: list[ContentOpportunityEnrichmentBlocker] = Field(default_factory=list)


def build_content_opportunity_enrichment_response(
    diagnostics: ContentDiagnosticsResponse,
    work_item_id: str,
    *,
    queue: ContentWorkItemQueueResponse | None = None,
) -> ContentOpportunityEnrichmentResponse:
    decision = _decision_for_work_item(diagnostics.decision_queue, work_item_id)
    if decision is None:
        return ContentOpportunityEnrichmentResponse(
            blockers=[
                ContentOpportunityEnrichmentBlocker(
                    code="missing_work_item",
                    label="Brak tematu w kolejce",
                    reason="WILQ nie widzi tego work itemu w aktualnej kolejce contentowej.",
                    next_step="Odśwież kolejkę treści i wybierz temat zwrócony przez WILQ API.",
                )
            ]
        )
    candidate = _candidate_for_work_item(queue, work_item_id) if queue is not None else None
    enrichment = build_content_opportunity_enrichment(decision, candidate=candidate)
    return ContentOpportunityEnrichmentResponse(
        enrichment=enrichment,
        blockers=enrichment.blockers,
    )


def build_content_opportunity_enrichment(
    decision: ContentDecisionItem,
    *,
    candidate: ContentWorkItemQueueCandidate | None = None,
) -> ContentOpportunityEnrichment:
    item = content_work_item_from_decision(decision)
    blockers = _enrichment_blockers(decision, candidate)
    source_facts = _source_facts(decision)
    measurement_baseline = _measurement_baseline(decision)
    status: ContentOpportunityEnrichmentStatus = "blocked" if blockers else "ready"
    intent = _intent(decision)
    return ContentOpportunityEnrichment(
        id=f"content_opportunity_enrichment_{item.id}",
        work_item_id=item.id,
        decision_id=decision.id,
        status=status,
        title=decision.title,
        topic=decision.primary_query or decision.title,
        recommended_mode=(
            "block" if candidate is None and blockers else candidate.recommended_mode
            if candidate is not None
            else _recommended_mode_from_decision(decision)
        ),
        intent=intent,
        intent_label=_intent_label(intent),
        buyer_problem=_buyer_problem(decision),
        buyer_trigger=_buyer_trigger(decision),
        service_fit=_service_fit(decision),
        cta_hypothesis=_cta_hypothesis(decision),
        source_facts=source_facts,
        measurement_baseline=measurement_baseline,
        blockers=blockers,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        safe_next_step=_safe_next_step(decision, blockers),
    )


def _decision_for_work_item(
    decisions: list[ContentDecisionItem],
    work_item_id: str,
) -> ContentDecisionItem | None:
    for decision in decisions:
        if f"content_work_item_{decision.id}" == work_item_id:
            return decision
    return None


def _candidate_for_work_item(
    queue: ContentWorkItemQueueResponse,
    work_item_id: str,
) -> ContentWorkItemQueueCandidate | None:
    for candidate in queue.candidates:
        if candidate.work_item_id == work_item_id:
            return candidate
    return None


def _enrichment_blockers(
    decision: ContentDecisionItem,
    candidate: ContentWorkItemQueueCandidate | None,
) -> list[ContentOpportunityEnrichmentBlocker]:
    blockers: list[ContentOpportunityEnrichmentBlocker] = []
    if not decision.evidence_ids:
        blockers.append(
            _blocker(
                code="missing_evidence",
                label="Brak dowodów",
                reason="Nie da się wzbogacić tematu bez evidence IDs z WILQ API.",
                next_step="Odśwież źródła GSC, WordPress, GA4 albo Ahrefs i wróć do kolejki.",
                decision=decision,
            )
        )
    if not decision.source_connectors:
        blockers.append(
            _blocker(
                code="missing_source_connector",
                label="Brak źródła danych",
                reason="Temat nie ma source connectora, więc WILQ nie może uzasadnić wniosku.",
                next_step="Podłącz lub odśwież connector i nie twórz rekomendacji z promptu.",
                decision=decision,
            )
        )
    final_url = decision.final_canonical_url or decision.intended_final_url
    if final_url is None:
        blockers.append(
            _blocker(
                code="missing_final_canonical",
                label="Brak finalnego adresu",
                reason="Nie ma publicznego finalnego URL-a, pod który można budować treść.",
                next_step="Najpierw ustal publiczny canonical dla tematu.",
                decision=decision,
            )
        )
    elif content_url_host(final_url) not in CONTENT_SOURCE_SITE_HOSTS:
        blockers.append(
            _blocker(
                code="invalid_final_canonical",
                label="Adres nie jest publicznym canonicalem",
                reason="Adres dev albo preview nie może być SEO evidence ani targetem treści.",
                next_step="Ustaw publiczny adres na ekologus.pl albo zablokuj tworzenie treści.",
                decision=decision,
            )
        )
    if candidate is not None:
        blockers.extend(
            ContentOpportunityEnrichmentBlocker(
                code=blocker.code,
                label=blocker.label,
                reason=blocker.reason,
                next_step=blocker.next_step,
                evidence_ids=blocker.evidence_ids,
                source_connectors=blocker.source_connectors,
            )
            for blocker in candidate.blockers
        )
    if _service_fit(decision) == "blocked":
        blockers.append(
            _blocker(
                code="missing_service_fit",
                label="Brak dopasowania do usługi",
                reason="WILQ nie widzi, jak ten temat mapuje się na usługę Ekologus.",
                next_step=(
                    "Dodaj kartę usługi albo zablokuj szkic, "
                    "zamiast tworzyć ogólny SEO tekst."
                ),
                decision=decision,
            )
        )
    return _deduplicate_blockers(blockers)


def _source_facts(decision: ContentDecisionItem) -> list[ContentOpportunitySourceFact]:
    facts: list[ContentOpportunitySourceFact] = []
    gsc_evidence_ids = _evidence_ids_for_connector(decision, "google_search_console")
    wordpress_evidence_ids = _evidence_ids_for_connector(decision, "wordpress_ekologus")
    if decision.queries:
        facts.append(
            ContentOpportunitySourceFact(
                id=f"source_fact_queries_{decision.id}",
                signal_kind="gsc_query",
                label="Zapytania GSC",
                summary="; ".join(decision.queries[:4]),
                evidence_ids=gsc_evidence_ids,
                source_connectors=_connectors(decision, "google_search_console"),
            )
        )
    if decision.total_impressions is not None:
        facts.append(
            ContentOpportunitySourceFact(
                id=f"source_fact_gsc_impressions_{decision.id}",
                signal_kind="gsc_page",
                label="Wyświetlenia GSC",
                summary=f"GSC pokazuje {decision.total_impressions} wyświetleń dla klastra.",
                evidence_ids=gsc_evidence_ids,
                source_connectors=_connectors(decision, "google_search_console"),
                metric_value=decision.total_impressions,
                source_url=decision.source_public_url or decision.page,
            )
        )
    if decision.total_clicks is not None:
        facts.append(
            ContentOpportunitySourceFact(
                id=f"source_fact_gsc_clicks_{decision.id}",
                signal_kind="gsc_page",
                label="Kliknięcia GSC",
                summary=f"GSC pokazuje {decision.total_clicks} kliknięć dla klastra.",
                evidence_ids=gsc_evidence_ids,
                source_connectors=_connectors(decision, "google_search_console"),
                metric_value=decision.total_clicks,
                source_url=decision.source_public_url or decision.page,
            )
        )
    if decision.wordpress_match:
        facts.append(
            ContentOpportunitySourceFact(
                id=f"source_fact_wordpress_{decision.id}",
                signal_kind="wordpress_inventory",
                label="Spis WordPress",
                summary=decision.wordpress_match_label
                or "WordPress inventory wskazuje istniejącą treść do preserve-first.",
                evidence_ids=wordpress_evidence_ids,
                source_connectors=_connectors(decision, "wordpress_ekologus"),
                source_url=decision.source_public_url or decision.page,
            )
        )
    facts.extend(_ahrefs_source_facts(decision.ahrefs_candidate_rows))
    if not facts and decision.summary:
        facts.append(
            ContentOpportunitySourceFact(
                id=f"source_fact_summary_{decision.id}",
                signal_kind="measurement",
                label="Podsumowanie WILQ",
                summary=decision.summary,
                evidence_ids=decision.evidence_ids,
                source_connectors=decision.source_connectors,
                source_url=decision.source_public_url or decision.page,
            )
        )
    return facts


def _evidence_ids_for_connector(
    decision: ContentDecisionItem,
    connector_id: str,
) -> list[str]:
    matched = [
        evidence_id
        for evidence_id in decision.evidence_ids
        if f"_{connector_id}_" in evidence_id or evidence_id.endswith(f"_{connector_id}")
    ]
    return matched or decision.evidence_ids


def _ahrefs_source_facts(
    rows: list[ContentAhrefsCandidateRow],
) -> list[ContentOpportunitySourceFact]:
    facts: list[ContentOpportunitySourceFact] = []
    for index, row in enumerate(rows[:3], start=1):
        facts.append(
            ContentOpportunitySourceFact(
                id=f"source_fact_ahrefs_gap_{row.id or index}",
                signal_kind="ahrefs_gap",
                label=row.gap_type_label or "Luka Ahrefs",
                summary=(
                    f"{row.topic}: {row.relevance_status_label or row.relevance_status}; "
                    f"{'; '.join(row.business_relevance_reasons[:2])}"
                ).strip("; "),
                evidence_ids=row.evidence_ids,
                source_connectors=["ahrefs"],
                metric_value=row.metric_value,
                source_url=row.source_url or row.referenced_public_url,
            )
        )
    return facts


def _measurement_baseline(decision: ContentDecisionItem) -> ContentOpportunityMeasurementBaseline:
    metrics: list[str] = []
    if decision.total_clicks is not None:
        metrics.append("gsc_clicks")
    if decision.total_impressions is not None:
        metrics.append("gsc_impressions")
    if "google_analytics_4" in decision.source_connectors:
        metrics.append("ga4_engaged_sessions")
    measurement_connectors = [
        connector
        for connector in decision.source_connectors
        if connector in {"google_search_console", "google_analytics_4", "ahrefs"}
    ]
    if not metrics or not measurement_connectors:
        return ContentOpportunityMeasurementBaseline(
            status="blocked",
            label="brak bazy pomiaru",
            reason="WILQ nie ma jeszcze metryk i connectorów potrzebnych do późniejszej oceny.",
            metrics_to_watch=metrics,
            source_connectors=measurement_connectors,
            evidence_ids=decision.evidence_ids,
        )
    return ContentOpportunityMeasurementBaseline(
        status="ready_to_plan",
        label="baza pomiaru do zaplanowania",
        reason="WILQ może zaplanować późniejszy pomiar, ale nie może claimować efektu teraz.",
        metrics_to_watch=metrics,
        source_connectors=measurement_connectors,
        evidence_ids=decision.evidence_ids,
    )


def _intent(decision: ContentDecisionItem) -> ContentOpportunityIntent:
    text = " ".join([decision.title, decision.primary_query or "", *decision.queries]).lower()
    if decision.decision_type == "block_as_tracking_not_content":
        return "measurement_fix"
    if decision.decision_type == "review_ahrefs_gap_records":
        return "gap_review"
    if any(token in text for token in ["bdo", "odpady", "sprawozd", "obowiązk", "kontrol"]):
        return "compliance_risk"
    if any(token in text for token in ["cennik", "firma", "usługa", "obsługa"]):
        return "service_comparison"
    if decision.queries or decision.total_impressions is not None:
        return "informational_service"
    return "unknown"


def _intent_label(intent: ContentOpportunityIntent) -> str:
    labels = {
        "informational_service": "intencja informacyjno-usługowa",
        "service_comparison": "intencja porównania usługi",
        "compliance_risk": "intencja ryzyka lub obowiązku",
        "measurement_fix": "problem pomiaru, nie temat do pisania",
        "gap_review": "luka contentowa do review",
        "unknown": "intencja niepotwierdzona",
    }
    return labels[intent]


def _buyer_problem(decision: ContentDecisionItem) -> str:
    if decision.summary:
        return decision.summary
    primary = decision.primary_query or (
        decision.queries[0] if decision.queries else decision.title
    )
    return f"Użytkownik szuka bezpiecznej odpowiedzi w temacie: {primary}."


def _buyer_trigger(decision: ContentDecisionItem) -> str:
    intent = _intent(decision)
    if intent == "compliance_risk":
        return "obawa przed błędem formalnym, terminem albo kontrolą"
    if intent == "gap_review":
        return "konkurencja lub Ahrefs pokazuje lukę wymagającą sprawdzenia"
    if decision.total_impressions:
        return "widoczny popyt w GSC na istniejący temat"
    return "potrzeba sprawdzenia tematu przed kontaktem z Ekologus"


def _service_fit(decision: ContentDecisionItem) -> str:
    text = " ".join([decision.title, decision.primary_query or "", *decision.queries]).lower()
    if any(token in text for token in ["bdo", "odpady", "środowisk", "sprawozd", "pozwolen"]):
        return "obsługa środowiskowa i zgodność obowiązków"
    if decision.decision_type == "review_ahrefs_gap_records" and decision.ahrefs_candidate_rows:
        relevant_rows = [
            row for row in decision.ahrefs_candidate_rows if row.relevance_status != "off_topic"
        ]
        if relevant_rows:
            return "temat do mapowania na usługę Ekologus po review Ahrefs"
    if decision.source_public_url or decision.final_canonical_url:
        return "sprawdzenie dopasowania do oferty Ekologus przed szkicem"
    return "blocked"


def _cta_hypothesis(decision: ContentDecisionItem) -> str:
    intent = _intent(decision)
    if intent == "measurement_fix":
        return "Nie twórz CTA treściowego; napraw pomiar albo atrybucję."
    if intent == "compliance_risk":
        return "Zaproponuj konsultację obowiązków bez gwarancji uniknięcia kar lub wyniku."
    if intent == "gap_review":
        return "Najpierw sprawdź dopasowanie luki do usługi, potem dopiero kieruj do kontaktu."
    return "Zaproponuj kontakt z Ekologus w celu sprawdzenia sytuacji firmy."


def _safe_next_step(
    decision: ContentDecisionItem,
    blockers: list[ContentOpportunityEnrichmentBlocker],
) -> str:
    if blockers:
        return blockers[0].next_step
    if decision.decision_type == "refresh_or_merge":
        return "Przygotuj preserve-first brief na bazie istniejącego URL-a i dowodów."
    if decision.decision_type == "review_ahrefs_gap_records":
        return "Przejrzyj lukę Ahrefs i potwierdź dopasowanie do usługi przed szkicem."
    return decision.next_step


def _recommended_mode_from_decision(decision: ContentDecisionItem) -> str:
    modes = {
        "refresh_or_merge": "refresh",
        "merge_create_after_inventory_check": "merge",
        "inventory_check_before_create": "create",
        "block_as_tracking_not_content": "block",
        "review_ahrefs_gap_records": "block",
        "block_until_vendor_read": "block",
    }
    return modes[decision.decision_type]


def _blocker(
    *,
    code: str,
    label: str,
    reason: str,
    next_step: str,
    decision: ContentDecisionItem,
) -> ContentOpportunityEnrichmentBlocker:
    return ContentOpportunityEnrichmentBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
    )


def _deduplicate_blockers(
    blockers: list[ContentOpportunityEnrichmentBlocker],
) -> list[ContentOpportunityEnrichmentBlocker]:
    deduplicated: dict[str, ContentOpportunityEnrichmentBlocker] = {}
    for blocker in blockers:
        deduplicated.setdefault(blocker.code, blocker)
    return list(deduplicated.values())


def _connectors(decision: ContentDecisionItem, preferred: str) -> list[str]:
    if preferred in decision.source_connectors:
        return [preferred]
    return decision.source_connectors[:1]
