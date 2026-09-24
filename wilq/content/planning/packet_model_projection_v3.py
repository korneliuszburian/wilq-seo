"""Whitelisted current v3 packet projection for an exact planning model turn."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from wilq.codex.app_server import CodexAppServerStructuredTurnRequest
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_turn import (
    _placement_contract,
    _planning_instruction,
    content_planning_output_schema,
)
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
    ContentPlanningSourceName,
    ContentPlanningSourceProvenance,
)
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.planning.packet_input_binding import bind_packet_identity_to_planning_input
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Preview
from wilq.content.workflow.source_pack_v3 import SourcePackV3Preview


@dataclass(frozen=True, slots=True)
class ResearchPacketV3ModelProjection:
    packet: ResearchPacketV3Preview
    planning_input: ContentPlanningInput
    selected_source_facts: tuple[ContentSourceFact, ...]
    intent_context_digest: str | None = None


class ResearchPacketV3ModelProjectionBlocked(ValueError):
    def __init__(self, code: str, safe_next_step: str) -> None:
        super().__init__(code)
        self.code = code
        self.safe_next_step = safe_next_step


def project_planning_input_for_packet_v3(
    planning_input: ContentPlanningInput,
    *,
    packet: ResearchPacketV3Preview,
    source_pack: SourcePackV3Preview,
    source_facts: tuple[ContentSourceFact, ...],
) -> ResearchPacketV3ModelProjection:
    """Rebuild a planning input from only the current approved v3 packet."""

    _validate_projection_identity(planning_input, packet, source_pack)
    selected = _select_current_v3_facts(packet, source_facts)
    allowed_evidence = _packet_model_evidence(packet, selected)
    internal_links = _packet_model_links(packet, allowed_evidence)
    bound = _project_planning_input(
        planning_input,
        packet=packet,
        selected=selected,
        allowed_evidence=allowed_evidence,
        internal_links=internal_links,
    )
    return ResearchPacketV3ModelProjection(
        packet=packet,
        planning_input=bound,
        selected_source_facts=selected,
    )


def _validate_projection_identity(
    planning_input: ContentPlanningInput,
    packet: ResearchPacketV3Preview,
    source_pack: SourcePackV3Preview,
) -> None:
    if (
        packet.status != "ready"
        or source_pack.status != "ready"
        or packet.preview_hash is None
        or packet.page_url is None
        or packet.canonical_path is None
        or packet.planning_context is None
        or packet.content_kind is None
        or packet.work_item_id != planning_input.work_item_id
        or source_pack.work_item_id != planning_input.work_item_id
        or packet.source_pack_id != source_pack.source_pack_id
        or packet.source_pack_hash != source_pack.source_pack_hash
        or source_pack.page_url != packet.page_url
        or source_pack.canonical_path != packet.canonical_path
        or planning_input.final_canonical_url != packet.page_url
        or planning_input.content_kind != packet.content_kind
        or planning_input.confirmed_service_card_id != packet.service_card_id
    ):
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_model_identity_mismatch",
            "Odtwórz exact input dla bieżącej strony i zatwierdzonego pakietu v3.",
        )

    if planning_input.content_kind == "service" and (
        source_pack.service_binding is None
        or source_pack.service_binding.card_id != planning_input.confirmed_service_card_id
        or source_pack.service_binding.binding_url != packet.page_url
    ):
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_service_binding_mismatch",
            "Odczytaj dokładne powiązanie usługi dla zatwierdzonego pakietu v3.",
        )

    if planning_input.research_packet_id is not None:
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_model_input_already_bound",
            "Odbuduj surowy planning input przed projekcją zatwierdzonego pakietu v3.",
        )


def _select_current_v3_facts(
    packet: ResearchPacketV3Preview,
    source_facts: tuple[ContentSourceFact, ...],
) -> tuple[ContentSourceFact, ...]:
    selected_ids = tuple(sorted(fact.source_fact_id for fact in packet.selected_facts))
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_selected_facts_invalid",
            "Odczytaj ponownie selected official facts zatwierdzonego pakietu v3.",
        )
    registry = {fact.source_id: fact for fact in source_facts}
    if len(registry) != len(source_facts):
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_registry_conflict",
            "Usuń niejednoznaczność rejestru official facts przed generowaniem planu.",
        )
    selected: list[ContentSourceFact] = []
    for selected_fact in packet.selected_facts:
        fact = registry.get(selected_fact.source_fact_id)
        exact = fact is not None and (
            fact.review_status == "approved"
            and fact.privacy_class == "commit_safe"
            and fact.official_source is True
            and fact.source_type == "legal_update"
            and fact.regulatory_profile_id == packet.regulatory_profile_id
            and fact.regulatory_profile_version == packet.regulatory_profile_version
            and packet.canonical_path in fact.applicable_canonical_paths
            and bool(fact.evidence_ids)
            and bool(fact.source_connectors)
            and canonical_json_digest(fact.model_dump(mode="json")) == selected_fact.fact_digest
            and fact.extracted_fact == selected_fact.text
            and fact.source_url_or_path == selected_fact.source_reference
            and fact.freshness_date == selected_fact.freshness_date
            and tuple(sorted(set(fact.source_connectors))) == selected_fact.source_connectors
            and tuple(sorted(set(fact.evidence_ids))) == selected_fact.evidence_ids
            and tuple(sorted(set(fact.regulatory_requirement_ids)))
            == selected_fact.regulatory_requirement_ids
        )
        if not exact or fact is None:
            raise ResearchPacketV3ModelProjectionBlocked(
                "research_packet_v3_registry_drift",
                "Zatwierdzone official facts zmieniły się; przygotuj i zatwierdź nowy pakiet v3.",
            )
        selected.append(fact)

    required_ids = {requirement.requirement_id for requirement in packet.legal_requirements}
    fact_requirement_ids = {
        requirement_id
        for fact in selected
        for requirement_id in fact.regulatory_requirement_ids
    }
    if required_ids != fact_requirement_ids:
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_requirement_fact_mismatch",
            "Powiąż każde wymaganie z dokładnym official fact przed generowaniem planu.",
        )
    facts_by_id = {fact.source_id: fact for fact in selected}
    for requirement in packet.legal_requirements:
        bound_facts = set(requirement.source_fact_ids)
        if not bound_facts or not bound_facts.issubset(facts_by_id):
            raise ResearchPacketV3ModelProjectionBlocked(
                "research_packet_v3_requirement_evidence_mismatch",
                "Odczytaj ponownie wymagania i evidence zatwierdzonego pakietu v3.",
            )
        evidence = {
            evidence_id
            for fact_id in bound_facts
            for evidence_id in facts_by_id[fact_id].evidence_ids
        }
        if not set(requirement.evidence_ids).issubset(evidence):
            raise ResearchPacketV3ModelProjectionBlocked(
                "research_packet_v3_requirement_evidence_mismatch",
                "Odczytaj ponownie wymagania i evidence zatwierdzonego pakietu v3.",
            )
    return tuple(selected)


def _packet_model_evidence(
    packet: ResearchPacketV3Preview,
    selected: tuple[ContentSourceFact, ...],
) -> set[str]:
    allowed_evidence = set(packet.verification_evidence_ids)
    allowed_evidence.update(
        evidence_id for fact in selected for evidence_id in fact.evidence_ids
    )
    allowed_evidence.update(
        evidence_id for link in packet.internal_links for evidence_id in link.evidence_ids
    )
    allowed_evidence.update(
        evidence_id
        for requirement in packet.legal_requirements
        for evidence_id in requirement.evidence_ids
    )
    return allowed_evidence


def _packet_model_links(
    packet: ResearchPacketV3Preview,
    allowed_evidence: set[str],
) -> list[ContentPlanningInternalLinkCandidate]:
    internal_links = [
        ContentPlanningInternalLinkCandidate(
            target_url=link.target_url,
            anchor_hint=link.anchor_hint,
            source_connector=link.source_connector,
            evidence_ids=list(link.evidence_ids),
        )
        for link in packet.internal_links
        if set(link.evidence_ids).issubset(allowed_evidence)
    ]
    if len(internal_links) != len(packet.internal_links):
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_link_evidence_mismatch",
            "Odczytaj ponownie linki i evidence zatwierdzonego pakietu v3.",
        )
    return internal_links


def _project_planning_input(
    planning_input: ContentPlanningInput,
    *,
    packet: ResearchPacketV3Preview,
    selected: tuple[ContentSourceFact, ...],
    allowed_evidence: set[str],
    internal_links: list[ContentPlanningInternalLinkCandidate],
) -> ContentPlanningInput:
    if packet.preview_hash is None or packet.planning_context is None or packet.page_url is None:
        raise ResearchPacketV3ModelProjectionBlocked(
            "research_packet_v3_model_identity_mismatch",
            "Odczytaj ponownie exact planning context zatwierdzonego pakietu v3.",
        )
    context = packet.planning_context
    packet_digest = packet.preview_hash
    selected_facts, provenance = _project_v3_source_facts(selected)
    regulatory_coverage = _project_v3_regulatory_coverage(packet, selected)
    inventory = _project_v3_inventory(planning_input.inventory)
    projection = planning_input.model_copy(
        update={
            "research_packet_id": f"content_research_packet_v3_{packet_digest[:24]}",
            "research_packet_digest": packet_digest,
            "final_canonical_url": packet.page_url,
            "target_reader": context.target_reader,
            "buyer_problem": context.buyer_problem,
            "buyer_trigger": context.buyer_trigger,
            "search_intent": (
                context.search_intent
                or "Brak zatwierdzonej intencji wyszukiwania w pakiecie v3."
            ),
            "inventory": inventory,
            "source_facts": selected_facts,
            "source_provenance": provenance,
            "source_assessments": _v3_source_assessments(),
            "regulatory_coverage": regulatory_coverage,
            "query_portfolio": ContentSearchDemandEvidence(
                status="missing",
                optional_ads_status="not_exactly_mapped",
                safe_next_step="Brak popytu w zatwierdzonym pakiecie v3.",
            ),
            "claim_ledger": [],
            "measurement_metrics": [],
            "metric_comparisons": [],
            "measurement_baseline_evidence_ids": [],
            "knowledge_card_ids": [],
            "evidence_ids": sorted(allowed_evidence),
            "source_connectors": sorted({
                *(connector for fact in selected for connector in fact.source_connectors),
                *(link.source_connector for link in packet.internal_links),
            }),
            "baseline_cta_direction": packet.cta_direction,
            "minimum_cta_blocks": packet.minimum_cta_blocks,
            "required_cta_patterns": list(packet.required_cta_patterns),
            "internal_link_candidates": internal_links,
        }
    )
    return bind_packet_identity_to_planning_input(
        projection,
        work_item_id=packet.work_item_id,
        packet_id=f"content_research_packet_v3_{packet_digest[:24]}",
        packet_digest=packet_digest,
    )


def _project_v3_source_facts(
    selected: tuple[ContentSourceFact, ...],
) -> tuple[list[ContentPlanningSourceFact], list[ContentPlanningSourceProvenance]]:
    planning_facts = [
        ContentPlanningSourceFact(
            fact_id=f"planning_research_packet_v3_fact_{fact.source_id}",
            summary=fact.extracted_fact,
            source_connector=sorted(set(fact.source_connectors))[0],
            evidence_ids=sorted(set(fact.evidence_ids)),
            source_fact_ids=[fact.source_id],
            source_material_ids=[],
            regulatory_requirement_ids=sorted(set(fact.regulatory_requirement_ids)),
        )
        for fact in selected
    ]
    provenance = [
        ContentPlanningSourceProvenance(
            source_fact_id=fact.source_id,
            source_url_or_path=fact.source_url_or_path,
            freshness_date=fact.freshness_date,
            reviewer=fact.reviewer,
            evidence_ids=sorted(set(fact.evidence_ids)),
        )
        for fact in selected
    ]
    return planning_facts, provenance


def _project_v3_regulatory_coverage(
    packet: ResearchPacketV3Preview,
    selected: tuple[ContentSourceFact, ...],
) -> ContentRegulatoryCoverage:
    selected_ids = tuple(fact.source_id for fact in selected)
    regulatory_coverage = ContentRegulatoryCoverage(
        applicability_status="required",
        profile_id=packet.regulatory_profile_id,
        profile_version=packet.regulatory_profile_version,
        canonical_path=packet.canonical_path,
        requirements=[
            ContentRegulatoryRequirement(
                id=requirement.requirement_id,
                label=requirement.label,
                reason="Wymaganie przypisane do zatwierdzonego pakietu v3.",
            )
            for requirement in packet.legal_requirements
        ],
        requirement_coverage=[
            ContentRegulatoryRequirementCoverage(
                requirement_id=requirement.requirement_id,
                source_fact_ids=list(requirement.source_fact_ids),
                evidence_ids=list(requirement.evidence_ids),
            )
            for requirement in packet.legal_requirements
        ],
        source_fact_ids=list(selected_ids),
        evidence_ids=sorted({
            evidence_id
            for requirement in packet.legal_requirements
            for evidence_id in requirement.evidence_ids
        }),
        source_facts=list(selected),
    )
    return regulatory_coverage


def _project_v3_inventory(
    inventory: ContentPlanningInventory,
) -> ContentPlanningInventory:
    return inventory.model_copy(
        update={
            "title_or_h1": None,
            "content_summary": None,
            "content_text": None,
            "material_confidence": "review_required",
            "source_field_lineage": [],
            "sections": [],
            "evidence_ids": [],
            "source_connectors": [],
            "note": "Bieżąca treść WordPress nie wchodzi do zatwierdzonego model contextu v3.",
        }
    )


def _v3_source_assessments() -> list[ContentPlanningSourceAssessment]:
    source_assessments = [
        ContentPlanningSourceAssessment(
            source=cast(ContentPlanningSourceName, source),
            status="missing",
            reason="Źródło nie wchodzi do zatwierdzonego model projection v3.",
        )
        for source in sorted(PLANNING_SOURCE_NAMES)
    ]
    return source_assessments


def content_planning_turn_request_v3(
    projection: ResearchPacketV3ModelProjection,
    *,
    operator_hint: str,
) -> CodexAppServerStructuredTurnRequest:
    """Build a turn whose context is limited to the exact approved v3 packet."""

    planning_input = projection.planning_input
    packet = projection.packet
    payload = planning_input.model_dump(mode="json", exclude_none=True)
    if packet.demand_evidence_status == "missing":
        payload.pop("search_intent", None)
    portfolio = payload.get("query_portfolio")
    if (
        packet.demand_evidence_status == "missing"
        and isinstance(portfolio, dict)
        and any(
            portfolio.get(key)
            for key in ("gsc_query_rows", "ads_term_rows", "keyword_planner_rows", "evidence_ids")
        )
    ):
        raise ValueError("v3 model projection cannot carry missing demand rows.")
    packet_binding = {
        "packet_id": planning_input.research_packet_id,
        "packet_digest": planning_input.research_packet_digest,
        "approval_preview_hash": packet.preview_hash,
        "demand_evidence_status": packet.demand_evidence_status,
        "selected_fact_ids": [fact.source_fact_id for fact in packet.selected_facts],
        "legal_requirement_ids": [
            requirement.requirement_id for requirement in packet.legal_requirements
        ],
    }
    application_context = json.dumps(
        {
            "operation": "propose_content_plan",
            "work_item_id": planning_input.work_item_id,
            "planning_input_digest": planning_input.planning_input_digest,
            "research_packet_binding": packet_binding,
            "content_kind": planning_input.content_kind,
            "service_card_id": planning_input.confirmed_service_card_id,
            "input_schema": planning_input.schema_name,
            "criteria_version": planning_input.criteria_version,
            "scope_rules": {
                "preserve_lineage": True,
                "do_not_approve": True,
                "do_not_write_vendor": True,
                "publish_ready": False,
            },
            "placement_contract": _placement_contract(planning_input),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    untrusted_context = json.dumps(
        {
            "planning_input": payload,
            "planning_input_coverage": {"rows_available": 0, "rows_included": 0},
            "research_packet_binding": packet_binding,
            "operator_hint": operator_hint,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return CodexAppServerStructuredTurnRequest(
        instruction=_planning_instruction(planning_input),
        application_context=application_context,
        untrusted_context=untrusted_context,
        output_schema=content_planning_output_schema(planning_input),
    )


__all__ = [
    "ResearchPacketV3ModelProjection",
    "ResearchPacketV3ModelProjectionBlocked",
    "content_planning_turn_request_v3",
    "project_planning_input_for_packet_v3",
]
