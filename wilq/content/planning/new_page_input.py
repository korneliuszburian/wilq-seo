from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from hashlib import sha256

from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.knowledge.work_item_service_profile import ContentWorkItemServiceCandidate
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    ContentPlanningInputBuildResult,
)
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
)
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPageOverlapGuard,
    ContentNewPagePlanningFoundation,
    new_page_overlap_digest,
)


def build_new_page_planning_input(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation | None,
    overlap_guard: ContentNewPageOverlapGuard,
    service_card: ContentKnowledgeCard | None,
    source_facts_loader: Callable[[], Iterable[ContentSourceFact]],
) -> ContentPlanningInputBuildResult:
    """Build one exact planning input without inventing existing-page facts."""

    blocker = _current_foundation_blocker(brief, foundation, overlap_guard, service_card)
    if blocker is not None:
        return ContentPlanningInputBuildResult(blockers=[blocker])
    assert foundation is not None
    assert service_card is not None
    source_facts = _source_facts(service_card, source_facts_loader())
    if not source_facts:
        return ContentPlanningInputBuildResult(blockers=[_blocker(
            "missing_new_page_service_fact",
            "Brakuje zatwierdzonego faktu usługi",
            "Wybrany kontekst usługi nie ma zatwierdzonego faktu źródłowego do użycia w planie.",
            "Uzupełnij albo zatwierdź fakt źródłowy tej usługi przed planowaniem.",
        )])
    payload = _payload(brief, foundation, service_card, source_facts)
    digest = _digest({
        "schema_name": "wilq_content_planning_input_v7",
        "criteria_version": "wilq_people_first_planning_v5",
        "inventory_mapping_policy": "wilq_inventory_mapping_v7",
        **payload,
    })
    return ContentPlanningInputBuildResult(
        planning_input=ContentPlanningInput.model_validate(
            {"planning_input_digest": digest, **payload}
        )
    )


def _current_foundation_blocker(
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation | None,
    overlap_guard: ContentNewPageOverlapGuard,
    service_card: ContentKnowledgeCard | None,
) -> ContentPlanningInputBlocker | None:
    if foundation is None:
        return _blocker(
            "missing_planning_foundation",
            "Brakuje zapisanej podstawy planowania",
            "Nowa strona wymaga exact briefu, kontroli pokrycia i ręcznego wyboru usługi.",
            "Zapisz podstawę planowania po sprawdzeniu pokrycia serwisu.",
        )
    if (
        foundation.brief_id != brief.brief_id
        or foundation.brief_digest != brief.brief_digest
        or foundation.overlap_digest != new_page_overlap_digest(overlap_guard)
        or overlap_guard.disposition != "no_conflict"
    ):
        return _blocker(
            "new_page_foundation_stale",
            "Podstawa planowania nie jest już aktualna",
            "Brief albo kontrola pokrycia zmieniły się od czasu potwierdzenia podstawy.",
            "Odczytaj brief, sprawdź pokrycie ponownie i zapisz aktualną podstawę.",
        )
    if (
        service_card is None
        or service_card.id != foundation.service_card_id
        or service_card.lifecycle_status != "approved_current"
        or _digest(service_card.model_dump(mode="json")) != foundation.service_card_digest
    ):
        return _blocker(
            "new_page_foundation_stale",
            "Kontekst usługi nie jest już aktualny",
            "Zatwierdzony kontekst usługi zmienił się albo nie jest już dostępny do planowania.",
            "Wybierz ponownie aktualny zatwierdzony kontekst usługi.",
        )
    return None


def _payload(
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    service_card: ContentKnowledgeCard,
    source_facts: list[ContentPlanningSourceFact],
) -> dict[str, object]:
    candidate = ContentWorkItemServiceCandidate(
        service_card_id=service_card.id,
        service_label=service_card.title,
        lifecycle_status="approved_current",
        lifecycle_label="zatwierdzona wiedza",
        matched_terms=[brief.service],
        match_reasons=["Kontekst usługi został wybrany ręcznie w podstawie planowania."],
        recommended=True,
    )
    evidence_ids = _unique([
        *foundation.overlap_evidence_ids,
        *foundation.service_evidence_ids,
        *(evidence_id for fact in source_facts for evidence_id in fact.evidence_ids),
    ])
    return {
        "work_item_id": foundation.work_item_id,
        "goal": "new_page",
        "final_canonical_url": None,
        "proposed_ia_location": brief.proposed_ia_location,
        "new_page_foundation": foundation,
        "service_candidates": [candidate],
        "confirmed_service_card_id": service_card.id,
        "service_label": service_card.title,
        "inventory": ContentPlanningInventory(
            status="not_applicable",
            content_status="not_applicable",
            acf_section_status="not_applicable",
            note="Nowa strona nie ma jeszcze istniejącej treści ani inventory WordPress.",
        ),
        "internal_link_candidates": [],
        "target_reader": brief.audience,
        "buyer_problem": brief.purpose,
        "buyer_trigger": brief.purpose,
        "search_intent": brief.search_intent,
        "source_facts": source_facts,
        "source_assessments": _source_assessments(service_card, source_facts),
        "query_portfolio": ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step=(
                "Nowa strona nie ma jeszcze publicznego URL-a; nie przypisujemy jej "
                "historycznych zapytań ani metryk."
            ),
        ),
        "claim_ledger": [],
        "measurement_metrics": [],
        "metric_comparisons": [],
        "measurement_baseline_evidence_ids": [],
        "measurement_observation_rule": (
            "Pomiar może zacząć się dopiero po osobnym potwierdzeniu publicznego wdrożenia."
        ),
        "measurement_success_claim_rule": (
            "Plan nie może twierdzić o wyniku SEO ani skuteczności przed pomiarem."
        ),
        "knowledge_card_ids": [service_card.id],
        "evidence_ids": evidence_ids,
        "source_connectors": _unique([
            *service_card.source_connectors,
            *(fact.source_connector for fact in source_facts),
        ]),
        "baseline_cta_direction": (
            service_card.cta_patterns[0]
            if service_card.cta_patterns
            else "Kierunek CTA wymaga decyzji człowieka przed szkicem."
        ),
    }


def _source_facts(
    service_card: ContentKnowledgeCard,
    source_facts: Iterable[ContentSourceFact],
) -> list[ContentPlanningSourceFact]:
    return [
        ContentPlanningSourceFact(
            fact_id=f"planning_source_fact_{fact.source_id}",
            summary=fact.extracted_fact,
            source_connector=fact.source_connectors[0],
            evidence_ids=fact.evidence_ids,
            knowledge_card_ids=[service_card.id],
            source_fact_ids=[fact.source_id],
            source_material_ids=service_card.source_material_ids,
        )
        for fact in source_facts
        if fact.target_card_id == service_card.id
        and fact.review_status == "approved"
        and fact.evidence_ids
        and fact.source_connectors
    ]


def _source_assessments(
    service_card: ContentKnowledgeCard,
    source_facts: list[ContentPlanningSourceFact],
) -> list[ContentPlanningSourceAssessment]:
    service_evidence_ids = _unique([
        evidence_id for fact in source_facts for evidence_id in fact.evidence_ids
    ])
    return [
        ContentPlanningSourceAssessment(
            source=source,
            status="used" if source == "service_profile" else "not_applicable",
            reason=(
                "Zatwierdzony kontekst usługi jest źródłem planu nowej strony."
                if source == "service_profile"
                else (
                    "Nowa strona nie ma jeszcze własnego publicznego wdrożenia "
                    "ani danych tego źródła."
                )
            ),
            evidence_ids=service_evidence_ids if source == "service_profile" else [],
            knowledge_card_ids=[service_card.id] if source == "service_profile" else [],
        )
        for source in sorted(PLANNING_SOURCE_NAMES)
    ]


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
) -> ContentPlanningInputBlocker:
    return ContentPlanningInputBlocker(code=code, label=label, reason=reason, next_step=next_step)


def _digest(payload: object) -> str:
    canonical = json.dumps(
        payload,
        default=_json_default,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _json_default(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Unsupported planning input value: {type(value).__name__}")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["build_new_page_planning_input"]
