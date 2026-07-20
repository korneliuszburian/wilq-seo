from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.canonical.metric_dimensions import metric_dimensions_match_landing
from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.inventory.records import resolve_content_inventory
from wilq.content.measurement.aggregates import compare_exact_page_metric_periods
from wilq.content.preflight.workflow import (
    ContentPreflightVerdict,
    ContentPreflightVerdictStatus,
    build_content_preflight_verdict,
)
from wilq.content.workflow.decision_mapping import (
    _usable_inventory_headings,
    content_inventory_record_from_decision,
    content_work_item_from_decision,
)
from wilq.content.workflow.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.models import (
    ContentWorkflowBlocker,
    content_workflow_blockers,
)
from wilq.operator_labels import source_connector_labels
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
)

ContentQueueRecommendedMode = Literal["preserve", "refresh", "merge", "create", "block"]
ContentQueueStatus = Literal["ready", "blocked"]
ContentQueueMeasurementStatus = Literal["ready_to_plan", "blocked"]
PRIMARY_CONTENT_CONNECTORS = ("google_search_console", "wordpress_ekologus")

_MINIMUM_ACTIONABLE_CANDIDATES = 3
_HARD_WORKFLOW_BLOCKERS = {
    "missing_evidence",
    "missing_source_connector",
    "missing_final_canonical",
    "invalid_final_canonical",
    "missing_inventory_resolution",
    "duplicate_gate_not_checked",
    "duplicate_or_canonical_risk",
}


class ContentWorkItemQueueBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    reason: str
    next_step: str
    decision_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentWorkItemQueueMeasurementReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentQueueMeasurementStatus
    label: str
    reason: str
    source_connectors: list[str] = Field(default_factory=list)


class ContentWorkItemQueueSearchMetrics(BaseModel):
    """Small, page-scoped metric projection intended for the operator's first screen."""

    model_config = ConfigDict(extra="forbid")

    impressions: int | None = None
    clicks: int | None = None
    ctr: float | None = None
    best_average_position: float | None = None
    query_count: int = 0
    primary_query: str | None = None
    comparison_status: Literal["available", "not_available", "ambiguous"] = "not_available"
    comparison_reason: str = "Brakuje dwóch dokładnych okresów do uczciwego porównania."
    comparison_periods: list[str] = Field(default_factory=list)
    comparison_evidence_ids: list[str] = Field(default_factory=list)


class ContentWorkItemQueueGa4Metric(BaseModel):
    """One exact landing-page GA4 fact for the queue's compact first screen."""

    model_config = ConfigDict(extra="forbid")

    name: str
    metric_label: str
    value: float | int | str
    period: str
    evidence_id: str
    freshness_state: Literal["fresh", "stale", "unknown"]


class ContentWorkItemQueueGa4Metrics(BaseModel):
    """Bounded GA4 projection; unrelated landing facts never enter the card."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "missing"] = "missing"
    metrics: list[ContentWorkItemQueueGa4Metric] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentWorkItemQueuePageInventory(BaseModel):
    """What WILQ has actually read about the existing page, without raw page text."""

    model_config = ConfigDict(extra="forbid")

    title_or_h1: str | None = None
    section_count: int | None = None
    section_headings: list[str] = Field(default_factory=list)
    section_inventory_status: Literal["available", "missing"] = "missing"
    content_inventory_status: Literal["available", "missing"] = "missing"
    content_summary: str | None = None
    content_word_count: int | None = None
    acf_section_inventory_status: Literal["available", "missing"] = "missing"
    acf_section_inventory_note: str | None = None
    acf_section_count: int | None = None
    acf_section_headings: list[str] = Field(default_factory=list)


class ContentWorkItemQueueCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    decision_id: str
    title: str
    topic: str
    priority: int
    recommended_mode: ContentQueueRecommendedMode
    recommended_mode_label: str
    status_label: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    action_summary_label: str = ""
    source_public_url: str | None = None
    final_canonical_url: str | None = None
    intended_final_url: str | None = None
    preview_url: str | None = None
    preflight_status: ContentPreflightVerdictStatus
    preflight_status_label: str
    duplicate_canonical_risk_summary: str
    measurement_readiness: ContentWorkItemQueueMeasurementReadiness
    search_metrics: ContentWorkItemQueueSearchMetrics = Field(
        default_factory=ContentWorkItemQueueSearchMetrics
    )
    ga4_metrics: ContentWorkItemQueueGa4Metrics = Field(
        default_factory=ContentWorkItemQueueGa4Metrics
    )
    page_inventory: ContentWorkItemQueuePageInventory = Field(
        default_factory=ContentWorkItemQueuePageInventory
    )
    safe_next_step: str
    freshness_assessment: ContentFreshnessAssessment
    blockers: list[ContentWorkItemQueueBlocker] = Field(default_factory=list)


class ContentWorkItemQueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue_status: ContentQueueStatus
    candidate_count: int
    actionable_candidate_count: int
    minimum_actionable_candidate_count: int = _MINIMUM_ACTIONABLE_CANDIDATES
    operator_summary: str
    freshness_assessment: ContentFreshnessAssessment
    candidates: list[ContentWorkItemQueueCandidate] = Field(default_factory=list)
    blockers: list[ContentWorkItemQueueBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


def build_content_work_item_queue_response(
    diagnostics: ContentDiagnosticsResponse,
    *,
    minimum_actionable_candidates: int = _MINIMUM_ACTIONABLE_CANDIDATES,
    selected_work_item_id: str | None = None,
) -> ContentWorkItemQueueResponse:
    candidates = [
        _candidate_from_decision(decision, diagnostics.freshness_assessment)
        for decision in sorted(diagnostics.decision_queue, key=lambda item: item.priority)
    ]
    if selected_work_item_id and not any(
        candidate.work_item_id == selected_work_item_id for candidate in candidates
    ):
        inventory_decision = inventory_decision_for_work_item(selected_work_item_id)
        if inventory_decision is not None:
            candidates.append(
                build_content_work_item_queue_candidate(
                    inventory_decision, diagnostics.freshness_assessment
                )
            )
            candidates.sort(key=lambda candidate: (candidate.priority, candidate.work_item_id))
    actionable_count = sum(1 for candidate in candidates if candidate.recommended_mode != "block")
    blockers: list[ContentWorkItemQueueBlocker] = []
    freshness_blocker = _primary_freshness_blocker(diagnostics.freshness_assessment)
    if freshness_blocker is not None:
        blockers.append(freshness_blocker)
    if actionable_count < minimum_actionable_candidates:
        blockers.append(
            ContentWorkItemQueueBlocker(
                code="not_enough_actionable_candidates",
                label="Za mało tematów gotowych do pracy",
                reason=(
                    "WILQ nie ma jeszcze wystarczającej liczby kandydatów z dowodami, "
                    "źródłami danych i publicznym adresem docelowym."
                ),
                next_step=(
                    "Odśwież GSC, WordPress, GA4 albo Ahrefs i nie twórz sztucznej "
                    "kolejki bez dowodów."
                ),
                evidence_ids=_unique(
                    evidence_id
                    for candidate in candidates
                    for evidence_id in candidate.evidence_ids
                ),
                source_connectors=_unique(
                    connector
                    for candidate in candidates
                    for connector in candidate.source_connectors
                ),
            )
        )

    return ContentWorkItemQueueResponse(
        queue_status="blocked" if blockers else "ready",
        candidate_count=len(candidates),
        actionable_candidate_count=actionable_count,
        minimum_actionable_candidate_count=minimum_actionable_candidates,
        operator_summary=_operator_summary(
            actionable_count,
            len(candidates),
            blockers,
            freshness_blocker=freshness_blocker is not None,
            freshness_assessment=diagnostics.freshness_assessment,
        ),
        freshness_assessment=diagnostics.freshness_assessment,
        candidates=candidates,
        blockers=blockers,
        evidence_ids=_unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        source_connectors=_unique(
            connector for candidate in candidates for connector in candidate.source_connectors
        ),
    )


def build_selected_content_work_item_queue_response(
    decision: ContentDecisionItem,
    freshness_assessment: ContentFreshnessAssessment,
) -> ContentWorkItemQueueResponse:
    """Build the first-screen queue response without full diagnostics/action reads."""
    candidate = build_content_work_item_queue_candidate(decision, freshness_assessment)
    blockers = list(candidate.blockers)
    freshness_blocker = _primary_freshness_blocker(freshness_assessment)
    if freshness_blocker is not None and not any(
        blocker.code == freshness_blocker.code for blocker in blockers
    ):
        blockers.append(freshness_blocker)
    return ContentWorkItemQueueResponse(
        queue_status="blocked" if blockers else "ready",
        candidate_count=1,
        actionable_candidate_count=(
            0 if candidate.recommended_mode == "block" else 1
        ),
        minimum_actionable_candidate_count=1,
        operator_summary=(
            "Wybrana strona jest gotowa do sprawdzenia decyzji."
            if not blockers
            else "Wybrana strona ma blocker przed przygotowaniem decyzji."
        ),
        freshness_assessment=freshness_assessment,
        candidates=[candidate],
        blockers=blockers,
        evidence_ids=candidate.evidence_ids,
        source_connectors=candidate.source_connectors,
    )


def build_content_work_item_queue_candidate(
    decision: ContentDecisionItem,
    freshness_assessment: ContentFreshnessAssessment,
) -> ContentWorkItemQueueCandidate:
    """Build one queue candidate without rebuilding the whole diagnostics queue."""
    return _candidate_from_decision(decision, freshness_assessment)


def _candidate_from_decision(
    decision: ContentDecisionItem,
    freshness_assessment: ContentFreshnessAssessment,
) -> ContentWorkItemQueueCandidate:
    item = content_work_item_from_decision(decision)
    inventory_record = content_inventory_record_from_decision(decision)
    inventory_resolution = resolve_content_inventory(
        [] if inventory_record is None else [inventory_record],
        duplicate_risk="clear" if inventory_record is not None else "unknown",
    )
    preflight = build_content_preflight_verdict(item, inventory_resolution)
    blockers = _candidate_blockers(decision, preflight, freshness_assessment)
    mode = _recommended_mode(decision, preflight, blockers)
    comparisons = compare_exact_page_metric_periods(
        decision.metric_facts,
        content_url=decision.final_canonical_url or decision.page or "",
    )
    comparison = next(
        (item for item in comparisons if item.source_connector == "google_search_console"),
        None,
    )
    comparison_periods = (
        [comparison.baseline_period, comparison.comparison_period]
        if comparison is not None
        and comparison.baseline_period is not None
        and comparison.comparison_period is not None
        else []
    )
    ga4_metrics = _ga4_metrics_for_decision(
        decision,
        content_url=decision.final_canonical_url or decision.page or "",
    )
    raw_inventory_headings = (
        decision.wordpress_acf_section_headings
        if decision.wordpress_acf_section_inventory_status == "available"
        and decision.wordpress_acf_section_headings
        else decision.wordpress_section_headings
    )
    inventory_headings = _usable_inventory_headings(raw_inventory_headings)
    return ContentWorkItemQueueCandidate(
        work_item_id=item.id,
        decision_id=decision.id,
        title=decision.title,
        topic=decision.primary_query or decision.title,
        priority=decision.priority,
        recommended_mode=mode,
        recommended_mode_label=_mode_label(mode),
        status_label=_candidate_status_label(mode, preflight, decision),
        reason=_candidate_reason(decision, preflight, blockers),
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        # Persisted decisions may carry labels from an older connector set.
        # Rebuild this operator projection from the authoritative connector IDs
        # so a newly used source (for example Google Ads) cannot disappear from
        # the marketer-facing snapshot.
        source_connector_labels=source_connector_labels(decision.source_connectors),
        action_ids=decision.action_ids,
        action_summary_label=decision.action_summary_label,
        source_public_url=decision.source_public_url or decision.page,
        final_canonical_url=decision.final_canonical_url,
        intended_final_url=decision.intended_final_url or decision.final_canonical_url,
        preview_url=decision.preview_url,
        preflight_status=preflight.status,
        preflight_status_label=_preflight_status_label(preflight.status),
        duplicate_canonical_risk_summary=_duplicate_canonical_summary(decision, blockers),
        measurement_readiness=_measurement_readiness(decision),
        search_metrics=ContentWorkItemQueueSearchMetrics(
            impressions=decision.total_impressions,
            clicks=decision.total_clicks,
            ctr=decision.aggregate_ctr,
            best_average_position=decision.best_average_position,
            query_count=decision.query_count,
            primary_query=decision.primary_query,
            comparison_status=(
                comparison.status if comparison is not None else "not_available"
            ),
            comparison_reason=(
                comparison.reason
                if comparison is not None
                else "Brakuje dwóch dokładnych okresów do uczciwego porównania."
            ),
            comparison_periods=comparison_periods,
            comparison_evidence_ids=(comparison.evidence_ids if comparison is not None else []),
        ),
        ga4_metrics=ga4_metrics,
        page_inventory=ContentWorkItemQueuePageInventory(
            title_or_h1=decision.wordpress_title_or_h1,
            section_count=len(inventory_headings) if inventory_headings else 0,
            section_headings=inventory_headings,
            section_inventory_status="available" if inventory_headings else "missing",
            content_inventory_status=decision.wordpress_content_inventory_status,
            content_summary=decision.wordpress_content_summary,
            content_word_count=decision.wordpress_content_word_count,
            acf_section_inventory_status=decision.wordpress_acf_section_inventory_status,
            acf_section_inventory_note=decision.wordpress_acf_section_inventory_note,
            acf_section_count=decision.wordpress_acf_section_count,
            acf_section_headings=decision.wordpress_acf_section_headings,
        ),
        safe_next_step=_safe_next_step(decision, preflight, blockers),
        freshness_assessment=freshness_assessment,
        blockers=blockers,
    )


def _ga4_metrics_for_decision(
    decision: ContentDecisionItem,
    *,
    content_url: str,
) -> ContentWorkItemQueueGa4Metrics:
    facts = [
        fact
        for fact in decision.metric_facts
        if fact.source_connector == "google_analytics_4"
        and metric_dimensions_match_landing(
            fact.dimensions,
            content_url,
            allow_relative_path=True,
        )
    ]
    # Keep the queue compact and deterministic while retaining every metric name
    # once per period. The full fact lineage remains available in the snapshot.
    selected: list[ContentWorkItemQueueGa4Metric] = []
    seen: set[tuple[str, str]] = set()
    for fact in facts:
        key = (fact.name, fact.period)
        if key in seen:
            continue
        seen.add(key)
        selected.append(
            ContentWorkItemQueueGa4Metric(
                name=fact.name,
                metric_label=fact.metric_label,
                value=fact.value,
                period=fact.period,
                evidence_id=fact.evidence_id,
                freshness_state=fact.freshness_state,
            )
        )
    selected.sort(key=lambda fact: (fact.name, fact.period, fact.evidence_id))
    return ContentWorkItemQueueGa4Metrics(
        status="available" if selected else "missing",
        metrics=selected[:8],
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in selected[:8])),
    )


def _candidate_blockers(
    decision: ContentDecisionItem,
    preflight: ContentPreflightVerdict,
    freshness_assessment: ContentFreshnessAssessment,
) -> list[ContentWorkItemQueueBlocker]:
    item = content_work_item_from_decision(decision).model_copy(
        update={"preflight_status": preflight.status}
    )
    workflow_blockers = [
        _queue_blocker_from_workflow_blocker(blocker, decision)
        for blocker in content_workflow_blockers(item, "prepare_sales_brief")
        if blocker.code in _HARD_WORKFLOW_BLOCKERS
    ]
    preflight_blockers = [
        ContentWorkItemQueueBlocker(
            code=blocker.code,
            label=blocker.label,
            reason=blocker.reason,
            next_step=blocker.next_step,
            decision_id=decision.id,
            evidence_ids=decision.evidence_ids,
            source_connectors=decision.source_connectors,
        )
        for blocker in preflight.blockers
        if blocker.blocks_current_stage
    ]
    freshness_blocker = _primary_freshness_blocker(
        freshness_assessment,
        decision_id=decision.id,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
    )
    return _deduplicate_blockers(
        [
            *([freshness_blocker] if freshness_blocker is not None else []),
            *preflight_blockers,
            *workflow_blockers,
        ]
    )


def _recommended_mode(
    decision: ContentDecisionItem,
    preflight: ContentPreflightVerdict,
    blockers: list[ContentWorkItemQueueBlocker],
) -> ContentQueueRecommendedMode:
    if decision.status == "blocked" or preflight.status == "blocked" or blockers:
        return "block"
    if decision.decision_type == "refresh_or_merge":
        return "refresh"
    if decision.decision_type == "merge_create_after_inventory_check":
        return "merge"
    if decision.decision_type == "inventory_check_before_create":
        return "create"
    if decision.decision_type == "block_as_tracking_not_content":
        return "block"
    if decision.decision_type == "review_ahrefs_gap_records":
        return "block"
    return "preserve"


def _mode_label(mode: ContentQueueRecommendedMode) -> str:
    labels = {
        "preserve": "zachowaj istniejący adres",
        "refresh": "odśwież istniejącą treść",
        "merge": "scal z istniejącą treścią",
        "create": "utwórz dopiero po sprawdzeniu",
        "block": "zablokuj pisanie",
    }
    return labels[mode]


def _candidate_status_label(
    mode: ContentQueueRecommendedMode,
    preflight: ContentPreflightVerdict,
    decision: ContentDecisionItem,
) -> str:
    if decision.wordpress_content_inventory_status != "available":
        return "materiał wymaga odczytu"
    if mode == "block":
        return "wymaga sprawdzenia przed pisaniem"
    if preflight.status == "plan_allowed":
        return "gotowe do planu"
    if preflight.status == "brief_allowed":
        return "gotowe do briefu"
    return _preflight_status_label(preflight.status)


def _candidate_reason(
    decision: ContentDecisionItem,
    preflight: ContentPreflightVerdict,
    blockers: list[ContentWorkItemQueueBlocker],
) -> str:
    if blockers:
        return blockers[0].reason
    if decision.summary:
        return decision.summary
    return preflight.next_step


def _duplicate_canonical_summary(
    decision: ContentDecisionItem,
    blockers: list[ContentWorkItemQueueBlocker],
) -> str:
    if blockers:
        return blockers[0].reason
    labels = [
        decision.inventory_gate_status_label,
        decision.canonical_gate_status_label,
        decision.duplicate_gate_status_label,
    ]
    summary = "; ".join(label for label in labels if label)
    if summary:
        return summary
    return "Brama adresu i duplikacji wymaga sprawdzenia przed tworzeniem nowej treści."


def _measurement_readiness(
    decision: ContentDecisionItem,
) -> ContentWorkItemQueueMeasurementReadiness:
    final_url = decision.final_canonical_url or decision.intended_final_url
    if final_url is None or content_url_host(final_url) not in CONTENT_SOURCE_SITE_HOSTS:
        return ContentWorkItemQueueMeasurementReadiness(
            status="blocked",
            label="pomiar zablokowany",
            reason=(
                "Nie można przygotować okna pomiaru bez publicznego finalnego adresu "
                "kanonicznego."
            ),
            source_connectors=[],
        )
    measurement_connectors = [
        connector
        for connector in decision.source_connectors
        if connector in {"google_search_console", "google_analytics_4", "ahrefs"}
    ]
    return ContentWorkItemQueueMeasurementReadiness(
        status="ready_to_plan",
        label="pomiar do zaplanowania",
        reason=(
            "WILQ może przygotować okno pomiaru po szkicu, ale nie może twierdzić, "
            "że treść zadziałała przed końcem obserwacji."
        ),
        source_connectors=measurement_connectors or decision.source_connectors,
    )


def _safe_next_step(
    decision: ContentDecisionItem,
    preflight: ContentPreflightVerdict,
    blockers: list[ContentWorkItemQueueBlocker],
) -> str:
    if blockers:
        return blockers[0].next_step
    return decision.next_step or preflight.next_step


def _preflight_status_label(status: ContentPreflightVerdictStatus) -> str:
    labels = {
        "blocked": "zablokowane",
        "plan_allowed": "można planować",
        "brief_allowed": "można przygotować brief",
        "draft_allowed": "można przygotować szkic",
        "handoff_allowed": "można przekazać szkic",
    }
    return labels[status]


def _operator_summary(
    actionable_count: int,
    candidate_count: int,
    blockers: list[ContentWorkItemQueueBlocker],
    *,
    freshness_blocker: bool,
    freshness_assessment: ContentFreshnessAssessment,
) -> str:
    if freshness_blocker:
        freshness_label = (
            f"{freshness_assessment.state_label[:1].upper()}"
            f"{freshness_assessment.state_label[1:]}"
        )
        return (
            f"Gotowe do pracy: {actionable_count} z {candidate_count} tematów. "
            f"{freshness_label}. "
            f"{freshness_assessment.next_step}"
        )
    if blockers:
        return (
            f"Gotowe do pracy: {actionable_count} z {candidate_count} tematów. "
            "Wybierz gotowy temat albo odśwież źródła; zablokowanych tematów "
            "nie pisz bez adresu, sekcji i dowodów."
        )
    return (
        f"Gotowe do pracy: {actionable_count} z {candidate_count} tematów. "
        "Wybierz stronę z adresem, źródłami i następnym krokiem, a blokady "
        "traktuj jako stop przed pisaniem."
    )


def _primary_freshness_blocker(
    freshness_assessment: ContentFreshnessAssessment,
    *,
    decision_id: str | None = None,
    evidence_ids: list[str] | None = None,
    source_connectors: list[str] | None = None,
) -> ContentWorkItemQueueBlocker | None:
    relevant_connectors = set(source_connectors or PRIMARY_CONTENT_CONNECTORS)
    primary_ids = relevant_connectors.intersection(PRIMARY_CONTENT_CONNECTORS)
    stale_primary = primary_ids.intersection(freshness_assessment.stale_connector_ids)
    missing_primary = primary_ids.intersection(freshness_assessment.missing_connector_ids)
    blocked_primary = primary_ids.intersection(freshness_assessment.blocked_connector_ids)
    if not stale_primary and not missing_primary and not blocked_primary:
        return None
    return ContentWorkItemQueueBlocker(
        code="content_sources_require_refresh",
        label="Źródła tej decyzji wymagają odświeżenia",
        reason=freshness_assessment.summary,
        next_step=freshness_assessment.next_step,
        decision_id=decision_id,
        evidence_ids=list(evidence_ids or []),
        source_connectors=list(source_connectors or PRIMARY_CONTENT_CONNECTORS),
    )


def _queue_blocker_from_workflow_blocker(
    blocker: ContentWorkflowBlocker,
    decision: ContentDecisionItem,
) -> ContentWorkItemQueueBlocker:
    return ContentWorkItemQueueBlocker(
        code=blocker.code,
        label=blocker.label,
        reason=blocker.reason,
        next_step=blocker.next_step,
        decision_id=decision.id,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
    )


def _deduplicate_blockers(
    blockers: list[ContentWorkItemQueueBlocker],
) -> list[ContentWorkItemQueueBlocker]:
    deduplicated: dict[str, ContentWorkItemQueueBlocker] = {}
    for blocker in blockers:
        deduplicated.setdefault(blocker.code, blocker)
    return list(deduplicated.values())


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
