from __future__ import annotations

import json
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger, ContentClaimLedgerEntry
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryResolution
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.measurement.aggregates import (
    MeasurementPeriodComparison,
    compare_exact_page_metric_periods,
)
from wilq.content.planning.generation_readiness import planning_generation_blockers
from wilq.content.planning.input_payload import refresh_planning_payload
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
    assessment_status,
    build_planning_inventory,
    build_source_assessments,
    build_source_facts,
    validate_source_assessment_membership,
)
from wilq.content.planning.input_summary import ContentPlanningInputSummary
from wilq.content.planning.internal_link_candidates import (
    ContentPlanningInternalLinkCandidate,
    load_content_internal_link_candidates,
)
from wilq.content.regulatory.planning import regulatory_planning_source_facts
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    regulatory_content_coverage,
    regulatory_coverage_gap,
    regulatory_review_candidates,
)
from wilq.content.workflow.demand_evidence import (
    ContentSearchDemandEvidence,
    build_content_search_demand_evidence,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPageDocumentIdentity,
    ContentNewPageOverlapGuard,
    ContentNewPagePlanningFoundation,
    build_new_page_document_identity,
)
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
    "missing_approved_service_fact",
    "service_context_mismatch",
    "missing_planning_foundation",
    "missing_wordpress_section_inventory",
    "missing_wordpress_full_inventory",
    "wordpress_material_review_required",
    "stale_planning_sources",
    "blocked_planning_sources",
    "new_page_foundation_stale",
    "missing_new_page_service_fact",
    "missing_regulatory_source_coverage",
]

# A refresh plan cannot be grounded without the current page, the approved
# service boundary and its exact organic-demand evidence. Other assessed
# sources remain visible in the input and may enrich a plan when exact, but a
# missing, stale or failed optional integration must not invent demand or
# prevent a grounded content repair from proceeding.
_REQUIRED_EXACT_PLANNING_SOURCES = frozenset({"wordpress", "service_profile", "gsc"})


class ContentPlanningInputBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentPlanningInputBlockerCode
    label: str
    reason: str
    next_step: str


class ContentPlanningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["wilq_content_planning_input_v7"] = "wilq_content_planning_input_v7"
    criteria_version: Literal["wilq_people_first_planning_v5"] = "wilq_people_first_planning_v5"
    inventory_mapping_policy: Literal["wilq_inventory_mapping_v7"] = "wilq_inventory_mapping_v7"
    planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_id: str = Field(min_length=1)
    goal: Literal["refresh_existing", "new_page"] = "refresh_existing"
    final_canonical_url: str | None = None
    proposed_ia_location: str | None = None
    new_page_foundation: ContentNewPagePlanningFoundation | None = None
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
    regulatory_coverage: ContentRegulatoryCoverage = Field(
        default_factory=ContentRegulatoryCoverage
    )
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
        if self.goal == "refresh_existing":
            if not self.final_canonical_url or not self.final_canonical_url.strip():
                raise ValueError("Refresh planning requires final_canonical_url.")
            if self.new_page_foundation is not None:
                raise ValueError("Refresh planning cannot carry a new-page foundation.")
            if self.inventory.status == "not_applicable":
                raise ValueError("Refresh planning requires existing-page inventory.")
        else:
            if self.final_canonical_url is not None:
                raise ValueError("New-page planning cannot claim a public canonical URL.")
            if (
                self.new_page_foundation is None
                or self.proposed_ia_location is None
                or len(self.proposed_ia_location.strip()) < 3
            ):
                raise ValueError("New-page planning requires exact foundation and IA location.")
            if self.inventory.status != "not_applicable":
                raise ValueError("New-page planning cannot carry existing-page inventory.")
            if self.metric_comparisons or self.measurement_baseline_evidence_ids:
                raise ValueError("New-page planning cannot carry a page measurement baseline.")
        return self


class ContentPlanningInputBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planning_input: ContentPlanningInput | None = None
    blockers: list[ContentPlanningInputBlocker] = Field(default_factory=list)


class ContentPlanningInputReadinessResponse(BaseModel):
    """Read-only readiness of one exact planning input.

    This is deliberately smaller than a generated proposal: it tells the
    operator whether WILQ can construct the exact input to planning, but it
    neither calls Codex nor persists a plan.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "blocked"]
    work_item_id: str | None = None
    planning_input_digest: str | None = None
    input_summary: ContentPlanningInputSummary | None = None
    new_page_document_identity: ContentNewPageDocumentIdentity | None = None
    blockers: list[ContentPlanningInputBlocker] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_input_when_ready(self) -> ContentPlanningInputReadinessResponse:
        if self.status == "ready" and (
            self.work_item_id is None
            or self.planning_input_digest is None
            or self.input_summary is None
        ):
            raise ValueError("Ready planning input requires its exact identity and summary.")
        if self.status == "blocked" and self.planning_input_digest is not None:
            raise ValueError("Blocked planning input cannot expose a usable digest.")
        if self.input_summary is not None and self.input_summary.goal == "new_page":
            if self.status == "ready" and self.new_page_document_identity is None:
                raise ValueError(
                    "Ready new-page planning input requires its exact document identity."
                )
            if (
                self.new_page_document_identity is not None
                and self.new_page_document_identity.work_item_id != self.work_item_id
            ):
                raise ValueError("New-page document identity must match the planning work item.")
            if (
                self.new_page_document_identity is not None
                and
                self.new_page_document_identity.proposed_ia_location
                != self.input_summary.proposed_ia_location
            ):
                raise ValueError("New-page document identity must match the planning IA location.")
        elif self.new_page_document_identity is not None:
            raise ValueError("Refresh planning cannot carry a new-page document identity.")
        return self


def content_planning_input_readiness(
    result: ContentPlanningInputBuildResult,
    *,
    work_item_id: str | None = None,
) -> ContentPlanningInputReadinessResponse:
    generation_blockers = planning_generation_blockers(result.blockers)
    if result.planning_input is None or generation_blockers:
        input_summary = (
            content_planning_input_summary(result.planning_input)
            if result.planning_input is not None
            else None
        )
        return ContentPlanningInputReadinessResponse(
            status="blocked",
            work_item_id=(
                result.planning_input.work_item_id
                if result.planning_input is not None
                else work_item_id
            ),
            input_summary=input_summary,
            blockers=generation_blockers,
            safe_next_step=(
                generation_blockers[0].next_step
                if generation_blockers
                else "Odczytaj ponownie podstawę planowania przed przygotowaniem planu."
            ),
        )
    planning_input = result.planning_input
    return ContentPlanningInputReadinessResponse(
        status="ready",
        work_item_id=planning_input.work_item_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        new_page_document_identity=(
            build_new_page_document_identity(
                foundation=planning_input.new_page_foundation,
                proposed_ia_location=planning_input.proposed_ia_location,
            )
            if planning_input.goal == "new_page"
            and planning_input.new_page_foundation is not None
            and planning_input.proposed_ia_location is not None
            else None
        ),
        blockers=result.blockers,
        safe_next_step=(
            "Wejście do planu jest gotowe. W kolejnym kroku można przygotować "
            "propozycję planu dla tej dokładnej podstawy."
        ),
    )


def content_planning_input_summary(
    planning_input: ContentPlanningInput,
) -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        goal=planning_input.goal,
        final_canonical_url=planning_input.final_canonical_url,
        proposed_ia_location=planning_input.proposed_ia_location,
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
        source_fact_previews=list(planning_input.source_facts),
        regulatory_profile_id=planning_input.regulatory_coverage.profile_id,
        regulatory_profile_version=planning_input.regulatory_coverage.profile_version,
        regulatory_requirement_ids=[
            requirement.id for requirement in planning_input.regulatory_coverage.requirements
        ],
        regulatory_source_fact_ids=planning_input.regulatory_coverage.source_fact_ids,
        regulatory_requirement_coverage=planning_input.regulatory_coverage.requirement_coverage,
        regulatory_review_candidates=regulatory_review_candidates(
            service_card_id=planning_input.confirmed_service_card_id,
            coverage=planning_input.regulatory_coverage,
        ),
        evidence_id_count=len(planning_input.evidence_ids),
        knowledge_card_count=len(planning_input.knowledge_card_ids),
        measurement_metrics=planning_input.measurement_metrics,
        metric_comparisons=planning_input.metric_comparisons,
    )


def build_new_page_planning_input(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation | None,
    overlap_guard: ContentNewPageOverlapGuard,
    service_card: ContentKnowledgeCard | None,
) -> ContentPlanningInputBuildResult:
    """Build a new-page input without coupling refresh planning to its inputs."""

    from wilq.content.planning.new_page_input import build_new_page_planning_input as build

    return build(
        brief=brief,
        foundation=foundation,
        overlap_guard=overlap_guard,
        service_card=service_card,
        source_facts_loader=ekologus_source_facts,
    )


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
            inventory_section_headings=_resolved_inventory_section_headings(
                snapshot.preflight.item,
                snapshot.preflight.inventory_resolution,
            ),
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


def _resolved_inventory_section_headings(
    item: ContentWorkItem,
    inventory_resolution: ContentInventoryResolution,
) -> list[str]:
    """Return the one inventory projection used by planning and query mapping."""
    inventory = build_planning_inventory(item, inventory_resolution)
    return [section.heading for section in inventory.sections]


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
    if candidate is None:
        return ContentPlanningInputBuildResult(blockers=[_foundation_blocker()])
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
    regulatory_coverage = regulatory_content_coverage(
        service_card_id=candidate.service_card_id,
        source_facts=ekologus_source_facts(),
    )
    blockers = _readiness_blockers(
        service_profile=service_profile,
        service_lifecycle=candidate.lifecycle_status,
        inventory=inventory,
        freshness=freshness,
        source_assessments=source_assessments,
        existing_content_material_reviewed=existing_content_material_reviewed,
        regulatory_coverage=regulatory_coverage,
    )
    source_facts = [
        *build_source_facts(brief, source_assessments, service_profile),
        *regulatory_planning_source_facts(
            regulatory_coverage,
            knowledge_card_ids=service_profile.knowledge_card_ids,
            source_material_ids=service_profile.source_material_ids,
        ),
    ]
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
        regulatory_coverage=regulatory_coverage,
        claim_ledger=claim_ledger,
        metric_comparisons=metric_comparisons,
    )
    # Criteria are part of the fixed point. A quality-gate change must make
    # older proposals stale instead of allowing same-input idempotency to
    # preserve a plan produced under weaker rules.
    digest = _digest(
        {
            "schema_name": "wilq_content_planning_input_v7",
            "criteria_version": "wilq_people_first_planning_v5",
            "inventory_mapping_policy": "wilq_inventory_mapping_v7",
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
    regulatory_coverage: ContentRegulatoryCoverage,
) -> list[ContentPlanningInputBlocker]:
    service_blockers = _service_readiness_blockers(service_profile, service_lifecycle)
    inventory_blockers = _inventory_readiness_blockers(
        inventory, existing_content_material_reviewed
    )
    regulatory_gap = regulatory_coverage_gap(regulatory_coverage)
    return [
        *service_blockers,
        *inventory_blockers,
        *_source_readiness_blockers(
            freshness,
            source_assessments,
            preceding_blocker_codes={
                blocker.code for blocker in [*service_blockers, *inventory_blockers]
            },
        ),
        *(
            [
                _blocker(
                    "missing_regulatory_source_coverage",
                    regulatory_gap.label,
                    regulatory_gap.reason,
                    regulatory_gap.next_step,
                )
            ]
            if regulatory_gap is not None
            else []
        ),
    ]


def _service_readiness_blockers(
    service_profile: ContentWorkItemServiceProfileContext,
    service_lifecycle: str,
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
    approved_source_fact_ids = {
        fact.source_id
        for fact in ekologus_source_facts()
        if fact.review_status == "approved"
    }
    unresolved_source_fact_ids = sorted(
        set(service_profile.source_fact_ids) - approved_source_fact_ids
    )
    if unresolved_source_fact_ids:
        blockers.append(
            _blocker(
                "missing_approved_service_fact",
                "Brakuje zatwierdzonego faktu usługi",
                "Karta usługi wskazuje source_fact_id, którego WILQ nie ma w rejestrze approved; "
                "plan nie może użyć generycznego fallbacku jako dowodu.",
                "Uzupełnij albo zatwierdź dokładny source fact w rejestrze WILQ "
                "i odśwież snapshot.",
            )
        )
    return blockers


def _inventory_readiness_blockers(
    inventory: ContentPlanningInventory,
    existing_content_material_reviewed: bool,
) -> list[ContentPlanningInputBlocker]:
    blockers: list[ContentPlanningInputBlocker] = []
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
    return blockers


def _source_readiness_blockers(
    freshness: ContentFreshnessAssessment,
    source_assessments: list[ContentPlanningSourceAssessment],
    *,
    preceding_blocker_codes: set[ContentPlanningInputBlockerCode],
) -> list[ContentPlanningInputBlocker]:
    blockers: list[ContentPlanningInputBlocker] = []
    stale_sources = [
        assessment.source
        for assessment in source_assessments
        if (
            assessment.source in _REQUIRED_EXACT_PLANNING_SOURCES
            and assessment.status == "stale"
        )
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
        if (
            assessment.source in _REQUIRED_EXACT_PLANNING_SOURCES
            and assessment.status == "blocked"
        )
    ]
    if blocked_sources and not (
        {"service_card_not_approved", "stale_planning_sources"}
        & {*preceding_blocker_codes, *(blocker.code for blocker in blockers)}
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
    regulatory_coverage: ContentRegulatoryCoverage,
    claim_ledger: ContentClaimLedger,
    metric_comparisons: list[MeasurementPeriodComparison],
) -> dict[str, object]:
    evidence_ids = _planning_evidence_ids(
        inventory=inventory,
        service_profile=service_profile,
        source_facts=source_facts,
        source_assessments=source_assessments,
        claim_ledger=claim_ledger,
    )
    return refresh_planning_payload(
        item=item,
        service_profile=service_profile,
        candidate=candidate,
        brief=brief,
        baseline=baseline,
        inventory=inventory,
        source_facts=source_facts,
        source_assessments=source_assessments,
        regulatory_coverage=regulatory_coverage,
        claim_ledger=claim_ledger,
        metric_comparisons=metric_comparisons,
        evidence_ids=evidence_ids,
        internal_link_candidates_loader=lambda directions, allowed_evidence_ids: (
            load_content_internal_link_candidates(
                directions,
                allowed_evidence_ids=allowed_evidence_ids,
            )
        ),
    )


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
    "ContentPlanningInputReadinessResponse",
    "ContentPlanningInputSummary",
    "ContentPlanningInventory",
    "ContentPlanningSourceAssessment",
    "build_content_planning_input",
    "build_new_page_planning_input",
    "content_planning_input_readiness",
    "content_planning_input_summary",
    "planning_generation_blockers",
]
