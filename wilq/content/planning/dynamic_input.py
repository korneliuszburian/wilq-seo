from __future__ import annotations

import json
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger, ContentClaimLedgerEntry
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryResolution
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.measurement.aggregates import (
    MeasurementPeriodComparison,
    compare_exact_page_metric_periods,
)
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
    assessment_status,
    build_planning_inventory,
    build_source_assessments,
    build_source_facts,
    planning_source_connectors,
    usable_query_portfolio,
    validate_source_assessment_membership,
)
from wilq.content.planning.internal_link_candidates import (
    ContentPlanningInternalLinkCandidate,
    load_content_internal_link_candidates,
)
from wilq.content.workflow.demand_evidence import (
    ContentSearchDemandEvidence,
    build_content_search_demand_evidence,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import (
    ContentPlanningProposal,
    build_content_planning_proposal,
)
from wilq.schemas import ContentFreshnessAssessment

if TYPE_CHECKING:
    from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse

ContentPlanningInputBlockerCode = Literal[
    "unknown_service_card",
    "service_selection_not_confirmed",
    "service_card_not_approved",
    "service_context_mismatch",
    "missing_planning_foundation",
    "missing_wordpress_section_inventory",
    "missing_wordpress_full_inventory",
    "wordpress_material_review_required",
    "stale_planning_sources",
    "blocked_planning_sources",
]


class ContentPlanningInputBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentPlanningInputBlockerCode
    label: str
    reason: str
    next_step: str


class ContentPlanningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["wilq_content_planning_input_v6"] = "wilq_content_planning_input_v6"
    criteria_version: Literal["wilq_people_first_planning_v4"] = "wilq_people_first_planning_v4"
    inventory_mapping_policy: Literal["wilq_inventory_mapping_v6"] = "wilq_inventory_mapping_v6"
    planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_id: str = Field(min_length=1)
    goal: Literal["refresh_existing"] = "refresh_existing"
    final_canonical_url: str = Field(min_length=1)
    service_candidates: list[ContentWorkItemServiceCandidate] = Field(min_length=1)
    confirmed_service_card_id: str = Field(min_length=1)
    service_label: str = Field(min_length=1)
    inventory: ContentPlanningInventory
    internal_link_candidates: list[ContentPlanningInternalLinkCandidate] = Field(
        default_factory=list
    )
    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str = Field(min_length=1)
    source_facts: list[ContentPlanningSourceFact] = Field(default_factory=list)
    source_assessments: list[ContentPlanningSourceAssessment] = Field(min_length=10)
    query_portfolio: ContentSearchDemandEvidence
    claim_ledger: list[ContentClaimLedgerEntry] = Field(default_factory=list)
    measurement_metrics: list[str] = Field(default_factory=list)
    metric_comparisons: list[MeasurementPeriodComparison] = Field(default_factory=list)
    measurement_baseline_evidence_ids: list[str] = Field(default_factory=list)
    measurement_observation_rule: str = Field(min_length=1)
    measurement_success_claim_rule: str = Field(min_length=1)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    baseline_cta_direction: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_complete_source_assessments(self) -> ContentPlanningInput:
        validate_source_assessment_membership(self.source_assessments)
        return self


class ContentPlanningInputSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    final_canonical_url: str = Field(min_length=1)
    service_label: str = Field(min_length=1)
    inventory_status: Literal["available", "missing"]
    content_inventory_status: Literal["available", "missing"]
    acf_section_inventory_status: Literal["available", "missing"]
    source_assessments: list[ContentPlanningSourceAssessment] = Field(min_length=10)
    source_fact_count: int = Field(ge=0)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    evidence_id_count: int = Field(ge=0)
    knowledge_card_count: int = Field(ge=0)
    measurement_metrics: list[str] = Field(default_factory=list)
    metric_comparisons: list[MeasurementPeriodComparison] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_complete_source_assessments(self) -> ContentPlanningInputSummary:
        validate_source_assessment_membership(self.source_assessments)
        return self


class ContentPlanningInputBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planning_input: ContentPlanningInput | None = None
    blockers: list[ContentPlanningInputBlocker] = Field(default_factory=list)


def content_planning_input_summary(
    planning_input: ContentPlanningInput,
) -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        final_canonical_url=planning_input.final_canonical_url,
        service_label=planning_input.service_label,
        inventory_status=planning_input.inventory.status,
        content_inventory_status=planning_input.inventory.content_status,
        acf_section_inventory_status=planning_input.inventory.acf_section_status,
        source_assessments=planning_input.source_assessments,
        source_fact_count=len(planning_input.source_facts),
        source_fact_ids=sorted(
            {
                source_fact_id
                for fact in planning_input.source_facts
                for source_fact_id in fact.source_fact_ids
            }
        ),
        source_material_ids=sorted(
            {
                source_material_id
                for fact in planning_input.source_facts
                for source_material_id in fact.source_material_ids
            }
        ),
        evidence_id_count=len(planning_input.evidence_ids),
        knowledge_card_count=len(planning_input.knowledge_card_ids),
        measurement_metrics=planning_input.measurement_metrics,
        metric_comparisons=planning_input.metric_comparisons,
    )


def planning_generation_blockers(
    blockers: list[ContentPlanningInputBlocker],
) -> list[ContentPlanningInputBlocker]:
    """Block plan generation only for blockers that make planning unsafe.

    A public rendered `the_content` read is sufficient to build a reviewable
    plan. Its REST/ACF provenance still blocks an initial full draft, which is
    enforced by the draft seam consuming the unfiltered result.
    """
    return [
        blocker
        for blocker in blockers
        if blocker.code != "wordpress_material_review_required"
    ]


def build_content_planning_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    service_card_id: str,
) -> ContentPlanningInputBuildResult:
    planning = snapshot.planning_workspace
    brief = snapshot.sales_brief.sales_brief_result.brief
    draft = snapshot.draft_package.draft_package_result.draft_package
    baseline = None
    if planning is not None and brief is not None and draft is not None:
        # A generated proposal is an output, never an input to its own
        # fixed-point digest. Rebuild demand from the exact metric facts so
        # GET and the queued worker cannot diverge after a proposal exists.
        demand = build_content_search_demand_evidence(
            metric_facts=snapshot.preflight.item.metric_facts,
            source_page=snapshot.preflight.item.source_public_url,
            final_canonical_url=brief.final_canonical_url,
            service_card_id=service_card_id,
            draft=draft,
            freshness=snapshot.freshness_assessment,
            inventory_section_headings=snapshot.preflight.item.wordpress_section_headings,
        )
        baseline = build_content_planning_proposal(
            brief=brief,
            draft=draft,
            service_profile=snapshot.service_profile_context,
            search_demand=demand,
        )
    return build_content_planning_input_from_components(
        item=snapshot.preflight.item,
        service_profile=snapshot.service_profile_context,
        inventory_resolution=snapshot.preflight.inventory_resolution,
        brief=brief,
        draft=draft,
        baseline_proposal=baseline,
        freshness=snapshot.freshness_assessment,
        claim_ledger=snapshot.claim_ledger,
        service_card_id=service_card_id,
        existing_content_material_reviewed=(
            snapshot.preflight.item.wordpress_content_material_confidence
            != "review_required"
            or (
                snapshot.planning_workspace is not None
                and snapshot.planning_workspace.scope_decision is not None
                and "existing_content_provenance"
                in snapshot.planning_workspace.scope_decision.checked_items
            )
        ),
    )


def build_content_planning_input_from_components(
    *,
    item: ContentWorkItem,
    service_profile: ContentWorkItemServiceProfileContext,
    inventory_resolution: ContentInventoryResolution,
    brief: ContentSalesBrief | None,
    draft: ContentDraftPackage | None,
    baseline_proposal: ContentPlanningProposal | None,
    freshness: ContentFreshnessAssessment,
    claim_ledger: ContentClaimLedger,
    service_card_id: str,
    existing_content_material_reviewed: bool = False,
) -> ContentPlanningInputBuildResult:
    candidate, blocker = _resolve_service_candidate(service_profile, service_card_id)
    if blocker is not None:
        return ContentPlanningInputBuildResult(blockers=[blocker])
    if brief is None or draft is None or baseline_proposal is None:
        return ContentPlanningInputBuildResult(blockers=[_foundation_blocker()])
    assert candidate is not None
    inventory = build_planning_inventory(item, inventory_resolution)
    source_assessments = build_source_assessments(
        item=item,
        inventory=inventory,
        service_profile=service_profile,
        freshness=freshness,
        brief=brief,
        demand=baseline_proposal.search_demand,
        service_lifecycle=candidate.lifecycle_status,
    )
    blockers = _readiness_blockers(
        service_profile=service_profile,
        service_lifecycle=candidate.lifecycle_status,
        inventory=inventory,
        freshness=freshness,
        source_assessments=source_assessments,
        existing_content_material_reviewed=existing_content_material_reviewed,
    )
    source_facts = build_source_facts(brief, source_assessments, service_profile)
    metric_comparisons = compare_exact_page_metric_periods(
        item.metric_facts,
        content_url=brief.final_canonical_url,
    )
    payload = _planning_payload(
        item=item,
        service_profile=service_profile,
        candidate=candidate,
        brief=brief,
        baseline=baseline_proposal,
        inventory=inventory,
        source_facts=source_facts,
        source_assessments=source_assessments,
        claim_ledger=claim_ledger,
        metric_comparisons=metric_comparisons,
    )
    # Criteria are part of the fixed point. A quality-gate change must make
    # older proposals stale instead of allowing same-input idempotency to
    # preserve a plan produced under weaker rules.
    digest = _digest(
        {
            "schema_name": "wilq_content_planning_input_v6",
            "criteria_version": "wilq_people_first_planning_v4",
            "inventory_mapping_policy": "wilq_inventory_mapping_v6",
            **payload,
        }
    )
    return ContentPlanningInputBuildResult(
        planning_input=ContentPlanningInput.model_validate(
            {"planning_input_digest": digest, **payload}
        ),
        blockers=blockers,
    )


def _resolve_service_candidate(
    service_profile: ContentWorkItemServiceProfileContext,
    service_card_id: str,
) -> tuple[ContentWorkItemServiceCandidate | None, ContentPlanningInputBlocker | None]:
    candidate = next(
        (
            item
            for item in service_profile.service_candidates
            if item.service_card_id == service_card_id
        ),
        None,
    )
    if candidate is None:
        return None, _blocker(
            "unknown_service_card",
            "Usługa nie należy do tego work itemu",
            "Wybrana karta nie wynika z dokładnego dopasowania strony i wiedzy WILQ.",
            "Wybierz jedną z kandydatur zwróconych przez bieżący snapshot.",
        )
    if service_profile.service_card_id != service_card_id:
        return None, _blocker(
            "service_context_mismatch",
            "Wybór usługi jest nieaktualny",
            "Bieżący snapshot nie jest jeszcze związany z wybraną kartą usługi.",
            "Zapisz wybór usługi w review zakresu i odśwież snapshot.",
        )
    return candidate, None


def _foundation_blocker() -> ContentPlanningInputBlocker:
    return _blocker(
        "missing_planning_foundation",
        "Brakuje kompletnego wejścia do planu",
        "Sales Brief, preserve-first package albo plan bazowy jest zablokowany.",
        "Usuń blokery wiedzy, inventory i briefu przed uruchomieniem Codexa.",
    )


def _readiness_blockers(
    *,
    service_profile: ContentWorkItemServiceProfileContext,
    service_lifecycle: str,
    inventory: ContentPlanningInventory,
    freshness: ContentFreshnessAssessment,
    source_assessments: list[ContentPlanningSourceAssessment],
    existing_content_material_reviewed: bool,
) -> list[ContentPlanningInputBlocker]:
    blockers: list[ContentPlanningInputBlocker] = []
    if not service_profile.service_selection_confirmed:
        blockers.append(
            _blocker(
                "service_selection_not_confirmed",
                "Usługa wymaga potwierdzenia",
                "Model nie może planować na podstawie domyślnego dopasowania "
                "bez decyzji człowieka.",
                "Zatwierdź zakres i wskaż kartę usługi.",
            )
        )
    if service_lifecycle != "approved_current":
        blockers.append(
            _blocker(
                "service_card_not_approved",
                "Karta usługi wymaga owner review",
                "Plan modelowy nie może użyć karty, która nie ma statusu approved_current.",
                "Zakończ owner review Service Profile; nie obchodź tej bramki promptem.",
            )
        )
    if inventory.status == "missing":
        blockers.append(
            _blocker(
                "missing_wordpress_section_inventory",
                "Brakuje sekcji istniejącej strony",
                "Refresh wymaga decyzji preserve/merge/rewrite dla inventory WordPress.",
                "Odśwież publiczny inventory WordPress i wróć do planowania.",
            )
        )
    elif inventory.content_status != "available":
        blockers.append(
            _blocker(
                "missing_wordpress_full_inventory",
                "Brakuje pełnej treści istniejącej strony",
                "Same nagłówki nie wystarczają do bezpiecznej decyzji zachowaj/scal/przepisz.",
                "Odczytaj aktualną treść główną i układ strony WordPress przed planowaniem.",
            )
        )
    if (
        inventory.content_text
        and inventory.material_confidence == "review_required"
        and not existing_content_material_reviewed
    ):
        blockers.append(
            _blocker(
                "wordpress_material_review_required",
                "Materiał strony wymaga potwierdzenia",
                "Treść została odczytana z wyrenderowanego the_content, ale nie ma jeszcze "
                "źródłowo związanej reprezentacji REST/ACF.",
                "Potwierdź zakres odczytanego materiału albo udostępnij dokładne pola WordPress "
                "przed generowaniem planu.",
            )
        )
    stale_sources = [
        assessment.source
        for assessment in source_assessments
        if assessment.status == "stale"
    ]
    if stale_sources:
        blockers.append(
            _blocker(
                "stale_planning_sources",
                "Źródła planu nie są świeże",
                "Dokładnie powiązane źródła wymagają odświeżenia: "
                f"{', '.join(stale_sources)}.",
                freshness.next_step,
            )
        )
    blocked_sources = [
        assessment.source
        for assessment in source_assessments
        if assessment.status == "blocked"
    ]
    if blocked_sources and not any(
        blocker.code in {"service_card_not_approved", "stale_planning_sources"}
        for blocker in blockers
    ):
        blockers.append(
            _blocker(
                "blocked_planning_sources",
                "Źródło wymaga dokładnego powiązania",
                "Co najmniej jedno dostępne źródło nie ma jeszcze bezpiecznego "
                f"powiązania z tą stroną: {', '.join(blocked_sources)}.",
                "Dodaj typed landing/service match albo usuń niedopasowany fakt z wejścia.",
            )
        )
    return blockers


def _planning_payload(
    *,
    item: ContentWorkItem,
    service_profile: ContentWorkItemServiceProfileContext,
    candidate: ContentWorkItemServiceCandidate,
    brief: ContentSalesBrief,
    baseline: ContentPlanningProposal,
    inventory: ContentPlanningInventory,
    source_facts: list[ContentPlanningSourceFact],
    source_assessments: list[ContentPlanningSourceAssessment],
    claim_ledger: ContentClaimLedger,
    metric_comparisons: list[MeasurementPeriodComparison],
) -> dict[str, object]:
    query_portfolio = usable_query_portfolio(baseline.search_demand, source_assessments)
    evidence_ids = _planning_evidence_ids(
        inventory=inventory,
        service_profile=service_profile,
        source_facts=source_facts,
        source_assessments=source_assessments,
        claim_ledger=claim_ledger,
    )
    internal_link_candidates = load_content_internal_link_candidates(
        brief.internal_link_direction,
        allowed_evidence_ids=evidence_ids,
    )
    return {
        "work_item_id": item.id,
        "final_canonical_url": brief.final_canonical_url,
        "service_candidates": service_profile.service_candidates,
        "confirmed_service_card_id": candidate.service_card_id,
        "service_label": candidate.service_label,
        "inventory": inventory,
        "internal_link_candidates": internal_link_candidates,
        "target_reader": brief.target_reader,
        "buyer_problem": brief.buyer_problem,
        "buyer_trigger": brief.buyer_trigger,
        "search_intent": brief.search_intent,
        "source_facts": source_facts,
        "source_assessments": source_assessments,
        "query_portfolio": query_portfolio,
        "claim_ledger": claim_ledger.entries,
        "measurement_metrics": brief.measurement_plan.metrics_to_watch,
        "metric_comparisons": metric_comparisons,
        "measurement_baseline_evidence_ids": [
            evidence_id
            for evidence_id in brief.measurement_plan.baseline_evidence_ids
            if evidence_id in evidence_ids
        ],
        "measurement_observation_rule": brief.measurement_plan.earliest_verdict_note,
        "measurement_success_claim_rule": brief.measurement_plan.success_claim_rule,
        "knowledge_card_ids": brief.knowledge_card_ids,
        "evidence_ids": evidence_ids,
        "source_connectors": planning_source_connectors(
            inventory=inventory,
            service_profile=service_profile,
            demand=query_portfolio,
            source_facts=source_facts,
            assessments=source_assessments,
        ),
        "baseline_cta_direction": baseline.cta_direction,
    }


def _planning_evidence_ids(
    *,
    inventory: ContentPlanningInventory,
    service_profile: ContentWorkItemServiceProfileContext,
    source_facts: list[ContentPlanningSourceFact],
    source_assessments: list[ContentPlanningSourceAssessment],
    claim_ledger: ContentClaimLedger,
) -> list[str]:
    return _unique(
        [
            *(
                inventory.evidence_ids
                if assessment_status(source_assessments, "wordpress") == "used"
                else []
            ),
            *(
                service_profile.evidence_ids
                if assessment_status(source_assessments, "service_profile") == "used"
                else []
            ),
            *(evidence_id for fact in source_facts for evidence_id in fact.evidence_ids),
            *(
                evidence_id
                for item in source_assessments
                if item.status == "used"
                for evidence_id in item.evidence_ids
            ),
            *(
                evidence_id
                for entry in claim_ledger.entries
                if entry.status in {"allowed_with_evidence", "allowed_general"}
                for evidence_id in entry.evidence_ids
            ),
        ]
    )


def _digest(payload: dict[str, object]) -> str:
    serialized = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in payload.items()
    }
    canonical = json.dumps(
        serialized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(f"Unsupported planning input value: {type(value).__name__}")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _blocker(
    code: ContentPlanningInputBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentPlanningInputBlocker:
    return ContentPlanningInputBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )


__all__ = [
    "ContentPlanningInput",
    "ContentPlanningInputBlocker",
    "ContentPlanningInputBuildResult",
    "ContentPlanningInputSummary",
    "ContentPlanningInventory",
    "ContentPlanningSourceAssessment",
    "build_content_planning_input",
    "content_planning_input_summary",
    "planning_generation_blockers",
]
