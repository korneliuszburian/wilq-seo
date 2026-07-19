import pytest

from wilq.content.knowledge.cards import match_content_knowledge_cards
from wilq.content.workflow.models import ContentWorkItem


def test_article_navigation_copy_does_not_bind_a_service_card() -> None:
    item = ContentWorkItem(
        id="content_work_item_investment_plans_article",
        topic=(
            "Czy przygotowane wieloletnie plany inwestycyjne z zakresu gospodarki "
            "odpadami spełniają nowe wymagania prawne?"
        ),
        source_public_url=(
            "https://www.ekologus.pl/czy-przygotowane-wieloletnie-plany-inwestycyjne-"
            "z-zakresu-gospodarki-odpadami-spelniaja-nowe-wymagania-prawne/"
        ),
        final_canonical_url=(
            "https://www.ekologus.pl/czy-przygotowane-wieloletnie-plany-inwestycyjne-"
            "z-zakresu-gospodarki-odpadami-spelniaja-nowe-wymagania-prawne/"
        ),
        wordpress_content_text=(
            "Nawigacja: doradztwo środowiskowe i outsourcing ekologiczny. "
            "Treść artykułu dotyczy planów inwestycyjnych."
        ),
        wordpress_title_or_h1=(
            "Czy przygotowane wieloletnie plany inwestycyjne z zakresu gospodarki "
            "odpadami spełniają nowe wymagania prawne?"
        ),
        wordpress_section_headings=[
            "Doradztwo środowiskowe i EKO-consulting",
            "Wymagania prawne",
            "Plany inwestycyjne",
        ],
        evidence_ids=["ev_wp_article"],
        source_connectors=["wordpress_ekologus"],
    )

    match = match_content_knowledge_cards(item)

    assert match.service_card is None
    assert all(
        candidate.card.id
        != "ekologus_service_environmental_consulting_outsourcing"
        for candidate in match.service_candidates
    )


def test_inflected_page_topic_matches_service_fit_stem() -> None:
    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_packaging_article",
            topic="Gospodarka opakowaniami",
            source_public_url=(
                "https://www.ekologus.pl/informacja-o-opakowaniach-i-odpadach-"
                "opakowaniowych-oraz-o-oplacie-produktowej/"
            ),
            final_canonical_url=(
                "https://www.ekologus.pl/informacja-o-opakowaniach-i-odpadach-"
                "opakowaniowych-oraz-o-oplacie-produktowej/"
            ),
            evidence_ids=["ev_wp_packaging_article"],
            source_connectors=["wordpress_ekologus"],
        )
    )

    assert any(
        candidate.card.id == "ekologus_service_waste_packaging_obligations"
        and "opakowani" in candidate.matched_terms
        for candidate in match.service_candidates
    )


def test_inflected_documentation_query_exposes_reviewable_service_candidate() -> None:
    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_integrated_permit_analysis",
            topic="Analiza pozwolenia zintegrowanego",
            source_public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
            final_canonical_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
            wordpress_content_text=(
                "Firma przygotuje niezbędną dokumentacji potrzebną do analizy "
                "pozwolenia zintegrowanego."
            ),
            wordpress_content_source_kind="wordpress_rest",
            wordpress_content_extraction_region="wordpress_rest.content",
            evidence_ids=["ev_wp_integrated_permit_analysis"],
            source_connectors=["wordpress_ekologus"],
        )
    )

    assert any(
        candidate.card.id == "ekologus_service_environmental_compliance_audit"
        and "dokumentacja" in candidate.matched_terms
        for candidate in match.service_candidates
    )


@pytest.mark.parametrize(
    ("url", "expected_card_id"),
    [
        (
            "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
            "ekologus_service_bdo_reporting",
        ),
        (
            "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
            "ekologus_service_environmental_consulting_outsourcing",
        ),
    ],
)
def test_exact_service_landings_keep_typed_url_lineage(
    url: str, expected_card_id: str
) -> None:
    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_exact_service_landing",
            topic="Wybrana strona usługi",
            source_public_url=url,
            final_canonical_url=url,
            wordpress_content_text="Treść strony zawiera dane usługi.",
            evidence_ids=["ev_wp_exact_service"],
            source_connectors=["wordpress_ekologus"],
        )
    )

    assert match.service_card is not None
    assert match.service_card.id == expected_card_id
