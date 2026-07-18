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
        wordpress_section_headings=["Wymagania prawne", "Plany inwestycyjne"],
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
