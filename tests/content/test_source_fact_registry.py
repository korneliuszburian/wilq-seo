from typing import get_args

from wilq.content.knowledge.cards import compile_source_facts_to_knowledge_cards
from wilq.content.knowledge.source_facts import (
    ContentSourceFactRegistry,
    SourceFactPrivacyClass,
    SourceFactReviewStatus,
    SourceFactScope,
    SourceFactType,
    ekologus_seed_source_facts,
)

SERVICE_PAGE_FACTS = {
    "ekologus_service_environmental_consulting_outsourcing": (
        "doradztwo",
        "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
        "ekologus_public_consulting_outsourcing_offer_2026_07_01",
    ),
    "ekologus_service_environmental_training": (
        "szkolenia",
        "https://www.ekologus.pl/oferta/szkolenia/",
        "ekologus_public_training_offer_2026_07_01",
    ),
    "ekologus_service_operat_wodnoprawny": (
        "opracowania_dokumentacji",
        "https://www.ekologus.pl/oferta/opracowania-dokumentacji-ekspertyz/",
        "ekologus_public_water_permit_documentation_2026_07_02",
    ),
    "ekologus_service_remediation_monitoring": (
        "pomiary_i_analizy",
        "https://www.ekologus.pl/oferta/pomiary-i-analizy/",
        "ekologus_public_remediation_offer_2026_07_01",
    ),
}

SERVICE_PAGE_DATED_FACT_END = {
    "ekologus_service_environmental_consulting_outsourcing": 30,
    "ekologus_service_environmental_training": 29,
    "ekologus_service_operat_wodnoprawny": 24,
    "ekologus_service_remediation_monitoring": 34,
}


def test_service_pages_have_substantive_approved_public_source_facts() -> None:
    facts = list(ekologus_seed_source_facts())
    registry = ContentSourceFactRegistry(facts=facts, fact_count=len(facts))
    source_ids = [fact.source_id for fact in registry.facts]
    facts_by_id = {fact.source_id: fact for fact in registry.facts}
    cards_by_id = {
        card.id: card for card in compile_source_facts_to_knowledge_cards(registry.facts)
    }

    assert registry.fact_count == len(registry.facts)
    assert len(source_ids) == len(set(source_ids))
    assert len(facts_by_id) == registry.fact_count
    assert all(fact.source_type in get_args(SourceFactType) for fact in registry.facts)
    assert all(
        fact.privacy_class in get_args(SourceFactPrivacyClass) for fact in registry.facts
    )
    assert all(fact.scope in get_args(SourceFactScope) for fact in registry.facts)
    assert all(
        fact.review_status in get_args(SourceFactReviewStatus) for fact in registry.facts
    )

    for target_card_id, (
        source_slug,
        source_url,
        original_source_id,
    ) in SERVICE_PAGE_FACTS.items():
        card_facts = [
            fact for fact in registry.facts if fact.target_card_id == target_card_id
        ]
        substantive_facts = [
            fact
            for fact in card_facts
            if fact.source_type == "public_site"
            and fact.source_connectors == ["public_site"]
            and len(fact.extracted_fact) > 40
        ]
        assert len(substantive_facts) >= 10
        normalized_facts = [
            fact.extracted_fact.strip().casefold() for fact in substantive_facts
        ]
        assert len(normalized_facts) == len(set(normalized_facts))

        original_fact = facts_by_id[original_source_id]
        new_source_prefix = f"ekologus_public_{source_slug}_2026_08_13_"
        expected_source_ids = {
            f"ekologus_public_{source_slug}_2026_08_13_{number}"
            for number in range(
                1,
                SERVICE_PAGE_DATED_FACT_END[target_card_id] + 1,
            )
        }
        prefixed_facts = [
            fact
            for fact in registry.facts
            if fact.source_id.startswith(new_source_prefix)
        ]
        current_source_ids = {fact.source_id for fact in prefixed_facts}
        assert current_source_ids == expected_source_ids
        assert all(fact.target_card_id == target_card_id for fact in prefixed_facts)

        compiled_card = cards_by_id[target_card_id]
        assert current_source_ids <= set(compiled_card.source_fact_ids)
        assert source_url in compiled_card.source_lineage

        for source_id in current_source_ids:
            fact = facts_by_id[source_id]
            assert fact.extracted_fact.strip()
            assert len(fact.extracted_fact) > 40
            assert fact.source_type == "public_site"
            assert fact.privacy_class == "commit_safe"
            assert fact.source_url_or_path == source_url
            assert fact.scope == "service"
            assert fact.freshness_date == "2026-08-13"
            assert 0.7 <= fact.confidence <= 0.85
            assert fact.review_status == "approved"
            assert fact.reviewer == "Korneliusz Burian"
            assert fact.evidence_ids == ["ev_content_service_profile_source_facts"]
            assert fact.source_connectors == ["public_site"]
            assert fact.blocked_claims == original_fact.blocked_claims
            assert fact.target_card_id == original_fact.target_card_id
            assert fact.target_card_type == original_fact.target_card_type
            assert fact.target_card_title == original_fact.target_card_title
            assert fact.service_fit_terms
            assert fact.buyer_problem_terms
            assert fact.buyer_triggers
