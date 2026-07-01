from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.inventory.records import resolve_content_inventory
from wilq.content.preflight.workflow import (
    ContentPreflightVerdict,
    ContentPreflightVerdictStatus,
    build_content_preflight_verdict,
)
from wilq.content.workflow.decision_mapping import (
    content_inventory_record_from_decision,
    content_work_item_from_decision,
)
from wilq.content.workflow.models import (
    ContentWorkflowBlocker,
    content_workflow_blockers,
)
from wilq.schemas import ContentDecisionItem, ContentDiagnosticsResponse

ContentQueueRecommendedMode = Literal["preserve", "refresh", "merge", "create", "block"]
ContentQueueStatus = Literal["ready", "blocked"]
ContentQueueMeasurementStatus = Literal["ready_to_plan", "blocked"]

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
    source_public_url: str | None = None
    final_canonical_url: str | None = None
    intended_final_url: str | None = None
    preview_url: str | None = None
    preflight_status: ContentPreflightVerdictStatus
    preflight_status_label: str
    duplicate_canonical_risk_summary: str
    measurement_readiness: ContentWorkItemQueueMeasurementReadiness
    safe_next_step: str
    blockers: list[ContentWorkItemQueueBlocker] = Field(default_factory=list)


class ContentWorkItemQueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue_status: ContentQueueStatus
    candidate_count: int
    actionable_candidate_count: int
    minimum_actionable_candidate_count: int = _MINIMUM_ACTIONABLE_CANDIDATES
    operator_summary: str
    candidates: list[ContentWorkItemQueueCandidate] = Field(default_factory=list)
    blockers: list[ContentWorkItemQueueBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


def build_content_work_item_queue_response(
    diagnostics: ContentDiagnosticsResponse,
    *,
    minimum_actionable_candidates: int = _MINIMUM_ACTIONABLE_CANDIDATES,
) -> ContentWorkItemQueueResponse:
    candidates = [
        _candidate_from_decision(decision)
        for decision in sorted(diagnostics.decision_queue, key=lambda item: item.priority)
    ]
    actionable_count = sum(1 for candidate in candidates if candidate.recommended_mode != "block")
    blockers: list[ContentWorkItemQueueBlocker] = []
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
        operator_summary=_operator_summary(actionable_count, len(candidates), blockers),
        candidates=candidates,
        blockers=blockers,
        evidence_ids=_unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        source_connectors=_unique(
            connector for candidate in candidates for connector in candidate.source_connectors
        ),
    )


def _candidate_from_decision(decision: ContentDecisionItem) -> ContentWorkItemQueueCandidate:
    item = content_work_item_from_decision(decision)
    inventory_record = content_inventory_record_from_decision(decision)
    inventory_resolution = resolve_content_inventory(
        [] if inventory_record is None else [inventory_record],
        duplicate_risk="clear" if inventory_record is not None else "unknown",
    )
    preflight = build_content_preflight_verdict(item, inventory_resolution)
    blockers = _candidate_blockers(decision, preflight)
    mode = _recommended_mode(decision, preflight, blockers)
    return ContentWorkItemQueueCandidate(
        work_item_id=item.id,
        decision_id=decision.id,
        title=decision.title,
        topic=decision.primary_query or decision.title,
        priority=decision.priority,
        recommended_mode=mode,
        recommended_mode_label=_mode_label(mode),
        status_label=_candidate_status_label(mode, preflight),
        reason=_candidate_reason(decision, preflight, blockers),
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        source_connector_labels=decision.source_connector_labels,
        source_public_url=decision.source_public_url or decision.page,
        final_canonical_url=decision.final_canonical_url,
        intended_final_url=decision.intended_final_url or decision.final_canonical_url,
        preview_url=decision.preview_url,
        preflight_status=preflight.status,
        preflight_status_label=_preflight_status_label(preflight.status),
        duplicate_canonical_risk_summary=_duplicate_canonical_summary(decision, blockers),
        measurement_readiness=_measurement_readiness(decision),
        safe_next_step=_safe_next_step(decision, preflight, blockers),
        blockers=blockers,
    )


def _candidate_blockers(
    decision: ContentDecisionItem,
    preflight: ContentPreflightVerdict,
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
    return _deduplicate_blockers([*preflight_blockers, *workflow_blockers])


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
) -> str:
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
) -> str:
    if blockers:
        return (
            f"WILQ widzi {candidate_count} kandydatów, ale tylko {actionable_count} "
            "ma komplet bramek do pracy. Nie tworzymy sztucznej kolejki bez dowodów."
        )
    return (
        f"WILQ widzi {candidate_count} kandydatów i {actionable_count} może przejść "
        "do planu bez omijania dowodów, finalnego adresu i sprawdzenia wstępnego."
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
