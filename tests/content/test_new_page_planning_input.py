from __future__ import annotations

import wilq.content.planning.dynamic_input as planning_input_module
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import build_new_page_planning_input
from wilq.content.workflow.new_page import (
    ContentNewPageBriefInput,
    ContentNewPageFoundationCommand,
    ContentNewPageOverlapGuard,
    build_new_page_brief,
    build_new_page_planning_foundation,
    new_page_overlap_digest,
)


def test_new_page_planning_input_requires_current_foundation_without_existing_page_facts(
    monkeypatch,
) -> None:
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
    assert result.planning_input.goal == "new_page"
    assert result.planning_input.final_canonical_url is None
    assert result.planning_input.inventory.status == "not_applicable"
    assert result.planning_input.metric_comparisons == []
    assert result.planning_input.measurement_baseline_evidence_ids == []
    assert result.planning_input.new_page_foundation == foundation
    assert result.planning_input.confirmed_service_card_id == service_card.id

    stale = build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard.model_copy(update={"evidence_ids": ["ev_inventory_changed"]}),
        service_card=service_card,
    )

    assert stale.planning_input is None
    assert [blocker.code for blocker in stale.blockers] == ["new_page_foundation_stale"]
