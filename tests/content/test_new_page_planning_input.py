from __future__ import annotations

from copy import deepcopy

import pytest

import wilq.content.planning.dynamic_input as planning_input_module
from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputSummary,
    build_new_page_planning_input,
    content_planning_input_summary,
)
from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPageBriefInput,
    ContentNewPageFoundationCommand,
    ContentNewPageOverlapGuard,
    ContentNewPagePlanningFoundation,
    build_new_page_brief,
    build_new_page_planning_foundation,
    new_page_overlap_digest,
)


def _ready_new_page_input(
    monkeypatch,
) -> tuple[
    ContentPlanningInput,
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
    ContentNewPageOverlapGuard,
    ContentKnowledgeCard,
]:
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Audyt inwestycji liniowej",
            purpose="Wyjaśnić przygotowanie audytu dla inwestycji liniowej.",
            service="Dokumentacja inwestycji",
            audience="Inwestor przygotowujący przedsięwzięcie",
            search_intent="audyt inwestycji liniowej",
            proposed_ia_location="Usługi → Dokumentacja",
        )
    )
    guard = ContentNewPageOverlapGuard(
        disposition="no_conflict",
        label="Brak bezpośredniego pokrycia",
        reason="Katalog nie pokazuje bezpośredniego pokrycia.",
        caveat="To nie jest dowód braku wszystkich duplikatów.",
        evidence_ids=["ev_inventory_new_page"],
    )
    service_card = next(
        card for card in ekologus_content_knowledge_cards() if card.card_type == "service"
    ).model_copy(
        update={
            "id": "knowledge_service_new_page",
            "lifecycle_status": "approved_current",
            "cta_patterns": ["Zaproponuj bezpieczny kontakt z ekspertem."],
            "evidence_ids": ["ev_service_new_page"],
            "source_connectors": ["public_site"],
        }
    )
    foundation = build_new_page_planning_foundation(
        brief=brief,
        guard=guard,
        command=ContentNewPageFoundationCommand(
            expected_brief_digest=brief.brief_digest,
            expected_overlap_digest=new_page_overlap_digest(guard),
            service_card_id=service_card.id,
            confirmed_by="Wilku",
        ),
        service_card=service_card,
    )
    source_fact = ContentSourceFact(
        source_id="fact_service_new_page",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path="https://www.ekologus.pl/oferta/",
        extracted_fact="Ekologus pomaga inwestorom w dokumentacji środowiskowej.",
        scope="service",
        freshness_date="2026-07-28",
        confidence=0.9,
        review_status="approved",
        reviewer="Wilku",
        evidence_ids=["ev_service_new_page"],
        source_connectors=["public_site"],
        target_card_id=service_card.id,
        target_card_type="service",
        target_card_title=service_card.title,
    )
    monkeypatch.setattr(planning_input_module, "ekologus_source_facts", lambda: (source_fact,))

    result = build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
    )

    assert result.blockers == []
    assert result.planning_input is not None
    return result.planning_input, brief, foundation, guard, service_card


def test_new_page_planning_input_requires_current_foundation_without_existing_page_facts(
    monkeypatch,
) -> None:
    planning_input, brief, foundation, guard, service_card = _ready_new_page_input(monkeypatch)

    assert planning_input.goal == "new_page"
    assert planning_input.final_canonical_url is None
    assert planning_input.inventory.status == "not_applicable"
    assert planning_input.metric_comparisons == []
    assert planning_input.measurement_baseline_evidence_ids == []
    assert planning_input.new_page_foundation == foundation
    assert planning_input.confirmed_service_card_id == "knowledge_service_new_page"

    stale = build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard.model_copy(update={"evidence_ids": ["ev_inventory_changed"]}),
        service_card=service_card,
    )

    assert stale.planning_input is None
    assert [blocker.code for blocker in stale.blockers] == ["new_page_foundation_stale"]


def test_new_page_planning_input_rejects_existing_page_identity_and_inventory(
    monkeypatch,
) -> None:
    planning_input, *_ = _ready_new_page_input(monkeypatch)
    payload = planning_input.model_dump(mode="json")

    invalid_payloads = [
        {**payload, "final_canonical_url": "https://www.ekologus.pl/istniejaca/"},
        {**payload, "proposed_ia_location": "   "},
        {**payload, "proposed_ia_location": "x"},
        {
            **payload,
            "inventory": {
                **payload["inventory"],
                "content_status": "available",
            },
        },
        {
            **payload,
            "inventory": {
                **payload["inventory"],
                "content_text": "Treść istniejącej strony.",
            },
        },
        {
            **payload,
            "metric_comparisons": [
                {
                    "source_connector": "google_search_console",
                    "status": "available",
                    "reason": "Istniejące porównanie strony.",
                }
            ],
        },
    ]
    refresh_payload = deepcopy(payload)
    refresh_payload.update(
        {
            "goal": "refresh_existing",
            "final_canonical_url": "https://www.ekologus.pl/istniejaca/",
            "new_page_foundation": None,
        }
    )
    invalid_payloads.append(refresh_payload)

    for invalid_payload in invalid_payloads:
        with pytest.raises(ValueError):
            ContentPlanningInput.model_validate(invalid_payload)

    valid_refresh_payload = deepcopy(payload)
    valid_refresh_payload.update(
        {
            "goal": "refresh_existing",
            "final_canonical_url": "https://www.ekologus.pl/istniejaca/",
            "new_page_foundation": None,
            "inventory": {
                "status": "missing",
                "content_status": "missing",
                "acf_section_status": "missing",
            },
        }
    )
    assert ContentPlanningInput.model_validate(valid_refresh_payload).goal == "refresh_existing"
    with pytest.raises(ValueError):
        ContentPlanningInput.model_validate(
            valid_refresh_payload | {"final_canonical_url": "   "}
        )


def test_new_page_planning_input_summary_rejects_contradictory_work_kind(
    monkeypatch,
) -> None:
    planning_input, *_ = _ready_new_page_input(monkeypatch)
    summary = content_planning_input_summary(planning_input)
    for update in (
        {"final_canonical_url": "https://www.ekologus.pl/istniejaca/"},
        {"proposed_ia_location": None},
        {"proposed_ia_location": "   "},
        {"proposed_ia_location": "x"},
        {"inventory_status": "available"},
        {
            "metric_comparisons": [
                {
                    "source_connector": "google_search_console",
                    "status": "available",
                    "reason": "Istniejące porównanie strony.",
                }
            ]
        },
    ):
        with pytest.raises(ValueError):
            ContentPlanningInputSummary.model_validate(
                summary.model_dump(mode="json") | update
            )

    with pytest.raises(ValueError):
        ContentPlanningInputSummary.model_validate(
            summary.model_dump(mode="json")
            | {
                "goal": "refresh_existing",
                "final_canonical_url": "https://www.ekologus.pl/istniejaca/",
            }
        )

    historical_refresh_summary = summary.model_dump(mode="json")
    historical_refresh_summary.pop("goal")
    historical_refresh_summary.update(
        {
            "final_canonical_url": "https://www.ekologus.pl/istniejaca/",
            "proposed_ia_location": None,
            "inventory_status": "missing",
            "content_inventory_status": "missing",
            "acf_section_inventory_status": "missing",
        }
    )
    assert ContentPlanningInputSummary.model_validate(
        historical_refresh_summary
    ).goal == "refresh_existing"
    with pytest.raises(ValueError):
        ContentPlanningInputSummary.model_validate(
            historical_refresh_summary | {"final_canonical_url": "   "}
        )
