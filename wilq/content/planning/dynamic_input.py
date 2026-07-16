from __future__ import annotations

import json
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger, ContentClaimLedgerEntry
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryResolution
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import (
    ContentPlanningProposal,
    build_content_planning_proposal,
)
from wilq.schemas import ContentFreshnessAssessment

if TYPE_CHECKING:
    from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse

ContentPlanningSourceStatus = Literal[
    "used",
    "not_applicable",
    "missing",
    "stale",
    "blocked",
]
ContentPlanningSourceName = Literal[
    "wordpress",
    "service_profile",
    "gsc",
    "ga4",
    "google_ads",
    "ahrefs",
    "keyword_planner",
    "merchant",
    "localo",
    "social",
]
ContentPlanningInputBlockerCode = Literal[
    "unknown_service_card",
    "service_selection_not_confirmed",
    "service_card_not_approved",
    "service_context_mismatch",
    "missing_planning_foundation",
    "missing_wordpress_section_inventory",
    "stale_planning_sources",
]


class ContentPlanningInputBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentPlanningInputBlockerCode
    label: str
    reason: str
    next_step: str


class ContentPlanningInventorySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    recommended_disposition: Literal["preserve"] = "preserve"
    evidence_ids: list[str] = Field(default_factory=list)


class ContentPlanningInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "missing"]
    title_or_h1: str | None = None
    content_summary: str | None = None
    word_count: int | None = Field(default=None, ge=0)
    sections: list[ContentPlanningInventorySection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    note: str = ""


class ContentPlanningSourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_connector: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    knowledge_card_ids: list[str] = Field(default_factory=list)


class ContentPlanningSourceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: ContentPlanningSourceName
    status: ContentPlanningSourceStatus
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)


class ContentPlanningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["wilq_content_planning_input_v1"] = "wilq_content_planning_input_v1"
    criteria_version: Literal["wilq_people_first_planning_v1"] = "wilq_people_first_planning_v1"
    planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_id: str = Field(min_length=1)
    goal: Literal["refresh_existing"] = "refresh_existing"
    final_canonical_url: str = Field(min_length=1)
    service_candidates: list[ContentWorkItemServiceCandidate] = Field(min_length=1)
    confirmed_service_card_id: str = Field(min_length=1)
    service_label: str = Field(min_length=1)
    inventory: ContentPlanningInventory
    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str = Field(min_length=1)
    source_facts: list[ContentPlanningSourceFact] = Field(default_factory=list)
    source_assessments: list[ContentPlanningSourceAssessment] = Field(min_length=10)
    query_portfolio: ContentSearchDemandEvidence
    claim_ledger: list[ContentClaimLedgerEntry] = Field(default_factory=list)
    measurement_metrics: list[str] = Field(default_factory=list)
    measurement_baseline_evidence_ids: list[str] = Field(default_factory=list)
    measurement_observation_rule: str = Field(min_length=1)
    measurement_success_claim_rule: str = Field(min_length=1)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    baseline_proposal: ContentPlanningProposal


class ContentPlanningInputBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planning_input: ContentPlanningInput | None = None
    blockers: list[ContentPlanningInputBlocker] = Field(default_factory=list)


def build_content_planning_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    service_card_id: str,
) -> ContentPlanningInputBuildResult:
    planning = snapshot.planning_workspace
    brief = snapshot.sales_brief.sales_brief_result.brief
    draft = snapshot.draft_package.draft_package_result.draft_package
    baseline = (
        None
        if planning is None or brief is None or draft is None
        else build_content_planning_proposal(
            brief=brief,
            draft=draft,
            service_profile=snapshot.service_profile_context,
            search_demand=planning.proposal.search_demand,
        )
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
) -> ContentPlanningInputBuildResult:
    candidate, blocker = _resolve_service_candidate(service_profile, service_card_id)
    if blocker is not None:
        return ContentPlanningInputBuildResult(blockers=[blocker])
    if brief is None or draft is None or baseline_proposal is None:
        return ContentPlanningInputBuildResult(blockers=[_foundation_blocker()])
    assert candidate is not None
    inventory = _inventory(item, inventory_resolution)
    blockers = _readiness_blockers(
        service_profile=service_profile,
        service_lifecycle=candidate.lifecycle_status,
        inventory=inventory,
        freshness=freshness,
    )
    source_facts = _source_facts(brief)
    source_assessments = _source_assessments(
        item=item,
        inventory_resolution=inventory_resolution,
        service_profile=service_profile,
        freshness=freshness,
        brief=brief,
        demand=baseline_proposal.search_demand,
        service_lifecycle=candidate.lifecycle_status,
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
    )
    digest = _digest(payload)
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
    if freshness.state != "fresh":
        blockers.append(
            _blocker(
                "stale_planning_sources",
                "Źródła planu nie są świeże",
                freshness.summary,
                freshness.next_step,
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
) -> dict[str, object]:
    evidence_ids = _planning_evidence_ids(
        brief=brief,
        baseline=baseline,
        inventory=inventory,
        service_profile=service_profile,
        source_assessments=source_assessments,
        claim_ledger=claim_ledger,
    )
    return {
        "work_item_id": item.id,
        "final_canonical_url": brief.final_canonical_url,
        "service_candidates": service_profile.service_candidates,
        "confirmed_service_card_id": candidate.service_card_id,
        "service_label": candidate.service_label,
        "inventory": inventory,
        "target_reader": brief.target_reader,
        "buyer_problem": brief.buyer_problem,
        "buyer_trigger": brief.buyer_trigger,
        "search_intent": brief.search_intent,
        "source_facts": source_facts,
        "source_assessments": source_assessments,
        "query_portfolio": baseline.search_demand,
        "claim_ledger": claim_ledger.entries,
        "measurement_metrics": brief.measurement_plan.metrics_to_watch,
        "measurement_baseline_evidence_ids": brief.measurement_plan.baseline_evidence_ids,
        "measurement_observation_rule": brief.measurement_plan.earliest_verdict_note,
        "measurement_success_claim_rule": brief.measurement_plan.success_claim_rule,
        "knowledge_card_ids": brief.knowledge_card_ids,
        "evidence_ids": evidence_ids,
        "source_connectors": _unique([*brief.source_connectors, *baseline.source_connectors]),
        "baseline_proposal": baseline,
    }


def _planning_evidence_ids(
    *,
    brief: ContentSalesBrief,
    baseline: ContentPlanningProposal,
    inventory: ContentPlanningInventory,
    service_profile: ContentWorkItemServiceProfileContext,
    source_assessments: list[ContentPlanningSourceAssessment],
    claim_ledger: ContentClaimLedger,
) -> list[str]:
    return _unique(
        [
            *brief.evidence_ids,
            *baseline.evidence_ids,
            *inventory.evidence_ids,
            *service_profile.evidence_ids,
            *brief.measurement_plan.baseline_evidence_ids,
            *(evidence_id for item in source_assessments for evidence_id in item.evidence_ids),
            *(evidence_id for entry in claim_ledger.entries for evidence_id in entry.evidence_ids),
        ]
    )


def _inventory(
    item: ContentWorkItem,
    inventory_resolution: ContentInventoryResolution,
) -> ContentPlanningInventory:
    evidence_ids = inventory_resolution.evidence_ids
    headings = item.wordpress_section_headings
    return ContentPlanningInventory(
        status="available" if headings else "missing",
        title_or_h1=item.wordpress_title_or_h1,
        content_summary=item.wordpress_content_summary,
        word_count=item.wordpress_content_word_count,
        sections=[
            ContentPlanningInventorySection(
                section_id=f"inventory_section_{index:02d}",
                heading=heading,
                evidence_ids=evidence_ids,
            )
            for index, heading in enumerate(headings, start=1)
        ],
        evidence_ids=evidence_ids,
        source_connectors=inventory_resolution.source_connectors,
        note=item.wordpress_content_inventory_note or "",
    )


def _source_facts(
    brief: ContentSalesBrief,
) -> list[ContentPlanningSourceFact]:
    return [
        ContentPlanningSourceFact(
            fact_id=f"planning_fact_{index:02d}",
            summary=fact.summary,
            source_connector=fact.source_connector,
            evidence_ids=[fact.evidence_id],
            knowledge_card_ids=brief.knowledge_card_ids,
        )
        for index, fact in enumerate(brief.source_facts, start=1)
    ]


def _source_assessments(
    *,
    item: ContentWorkItem,
    inventory_resolution: ContentInventoryResolution,
    service_profile: ContentWorkItemServiceProfileContext,
    freshness: ContentFreshnessAssessment,
    brief: ContentSalesBrief,
    demand: ContentSearchDemandEvidence,
    service_lifecycle: str,
) -> list[ContentPlanningSourceAssessment]:
    fact_kinds = {fact.source_connector for fact in brief.source_facts}
    freshness_state = freshness.state
    common_status: ContentPlanningSourceStatus = (
        "stale"
        if freshness_state == "stale"
        else "blocked"
        if freshness_state == "blocked"
        else "missing"
    )
    gsc_evidence = [
        evidence_id for row in demand.gsc_query_rows for evidence_id in row.evidence_ids
    ]
    ads_evidence = [evidence_id for row in demand.ads_term_rows for evidence_id in row.evidence_ids]
    planner_evidence = [
        evidence_id for row in demand.keyword_planner_rows for evidence_id in row.evidence_ids
    ]
    return [
        *_primary_source_assessments(
            item=item,
            inventory_resolution=inventory_resolution,
            service_profile=service_profile,
            service_lifecycle=service_lifecycle,
            knowledge_ids=brief.knowledge_card_ids,
            fact_kinds=fact_kinds,
            common_status=common_status,
            gsc_evidence=gsc_evidence,
            ads_evidence=ads_evidence,
        ),
        *_optional_source_assessments(
            item=item,
            brief=brief,
            fact_kinds=fact_kinds,
            planner_evidence=planner_evidence,
        ),
    ]


def _primary_source_assessments(
    *,
    item: ContentWorkItem,
    inventory_resolution: ContentInventoryResolution,
    service_profile: ContentWorkItemServiceProfileContext,
    service_lifecycle: str,
    knowledge_ids: list[str],
    fact_kinds: set[str],
    common_status: ContentPlanningSourceStatus,
    gsc_evidence: list[str],
    ads_evidence: list[str],
) -> list[ContentPlanningSourceAssessment]:
    return [
        _assessment(
            "wordpress",
            "used" if item.wordpress_section_headings else "missing",
            "Publiczne inventory strony jest wejściem do decyzji zachowaj/scal/przepisz."
            if item.wordpress_section_headings
            else "Brakuje publicznych nagłówków istniejącej strony.",
            inventory_resolution.evidence_ids,
        ),
        _assessment(
            "service_profile",
            "used" if service_lifecycle == "approved_current" else "blocked",
            "Zatwierdzona karta usługi ogranicza odbiorcę, problemy, CTA i twierdzenia."
            if service_lifecycle == "approved_current"
            else "Karta usługi nie ma owner review.",
            service_profile.evidence_ids,
            knowledge_ids,
        ),
        _assessment(
            "gsc",
            "used" if gsc_evidence else common_status,
            "Dokładne zapytania tej strony są wejściem planu."
            if gsc_evidence
            else "Brak dokładnych zapytań GSC dla strony.",
            gsc_evidence,
        ),
        _assessment(
            "ga4",
            "used" if "google_analytics_4" in fact_kinds else "missing",
            "Dokładny sygnał zachowania landing page jest dostępny."
            if "google_analytics_4" in fact_kinds
            else "Brak dokładnego sygnału GA4 dla tej strony.",
        ),
        _assessment(
            "google_ads",
            "used" if ads_evidence else "not_applicable",
            "Dokładne terminy Ads pasują do termu, strony i usługi."
            if ads_evidence
            else "Brak ścisłego mapowania termu, strony i usługi; Ads nie zasila planu.",
            ads_evidence,
        ),
    ]


def _optional_source_assessments(
    *,
    item: ContentWorkItem,
    brief: ContentSalesBrief,
    fact_kinds: set[str],
    planner_evidence: list[str],
) -> list[ContentPlanningSourceAssessment]:
    is_product = "wordpress_sklep" in item.source_connectors
    has_local_intent = "lokal" in brief.search_intent.casefold()
    return [
        _assessment(
            "ahrefs",
            "used" if "ahrefs" in fact_kinds else "missing",
            "Sprawdzony sygnał Ahrefs dotyczy tej strony."
            if "ahrefs" in fact_kinds
            else "Brak dokładnego, cross-source sygnału Ahrefs dla tej strony.",
        ),
        _assessment(
            "keyword_planner",
            "used" if planner_evidence else "missing",
            "Dokładne metryki Keyword Planner są dostępne."
            if planner_evidence
            else "Brak developer tokena albo exact term mappingu; nie zgadujemy wolumenu.",
            planner_evidence,
        ),
        _assessment(
            "merchant",
            "used" if is_product else "not_applicable",
            "Strona produktowa może użyć dokładnych faktów Merchant."
            if is_product
            else "To nie jest strona produktowa.",
        ),
        _assessment(
            "localo",
            "missing" if has_local_intent else "not_applicable",
            "Lokalna intencja wymaga dokładnego sygnału Localo."
            if has_local_intent
            else "Strona nie ma potwierdzonej lokalnej intencji.",
        ),
        _assessment(
            "social",
            "not_applicable",
            "Social może ponownie użyć dopiero zatwierdzonej treści; nie zmienia planu strony.",
        ),
    ]


def _assessment(
    source: ContentPlanningSourceName,
    status: ContentPlanningSourceStatus,
    reason: str,
    evidence_ids: list[str] | None = None,
    knowledge_card_ids: list[str] | None = None,
) -> ContentPlanningSourceAssessment:
    return ContentPlanningSourceAssessment(
        source=source,
        status=status,
        reason=reason,
        evidence_ids=_unique(evidence_ids or []),
        knowledge_card_ids=_unique(knowledge_card_ids or []),
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
    "ContentPlanningInventory",
    "ContentPlanningSourceAssessment",
    "build_content_planning_input",
]
