import pytest

from wilq.content.knowledge import cards as knowledge_cards
from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    match_content_knowledge_cards,
    select_content_knowledge_service_card,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.schemas import MetricFact


def test_exact_binding_url_binds_with_neutral_page_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_url = "https://www.ekologus.pl/oferta/usluga-123/"
    card = ContentKnowledgeCard(
        id="service_exact_binding",
        card_type="service",
        title="Szkolenia specjalistyczne",
        summary="Karta testowa dokładnego powiązania.",
        service_fit_terms=["szkolenia specjalistyczne"],
        service_binding_urls=[binding_url],
        evidence_ids=["ev_service_exact_binding"],
        source_connectors=["wordpress_ekologus"],
        confidence=0.9,
        freshness="reviewed_2026-08-28",
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: (card,),
    )

    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_exact_binding",
            topic="Neutralny temat",
            wordpress_title_or_h1="Neutralny tytuł",
            source_public_url=binding_url,
            final_canonical_url=binding_url,
        )
    )

    assert match.service_card is not None
    assert match.service_card.id == "service_exact_binding"
    assert [candidate.card.id for candidate in match.service_candidates] == [
        "service_exact_binding"
    ]

    selected = select_content_knowledge_service_card(match, "service_exact_binding")

    assert selected.service_card is not None
    assert selected.service_card.id == "service_exact_binding"


def test_ambiguous_exact_binding_is_blocked_without_ranking_a_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_url = "https://www.ekologus.pl/oferta/wspolny-adres/"
    first = ContentKnowledgeCard(
        id="service_first_exact_binding",
        card_type="service",
        title="Pierwsza karta",
        summary="Pierwsza karta testowa.",
        service_binding_urls=[binding_url],
        evidence_ids=["ev_service_ambiguous_binding"],
        source_connectors=["wordpress_ekologus"],
        confidence=0.9,
        freshness="reviewed_2026-08-28",
    )
    second = first.model_copy(
        update={
            "id": "service_second_exact_binding",
            "title": "Druga karta",
            "summary": "Druga karta testowa.",
        }
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: (first, second),
    )

    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_ambiguous_binding",
            topic="Neutralny temat",
            source_public_url=binding_url,
            final_canonical_url=binding_url,
        )
    )

    assert match.service_card is None
    assert match.recommended_service_card_id is None
    assert [
        blocker.code for blocker in match.blockers if blocker.code == "ambiguous_service_binding"
    ] == ["ambiguous_service_binding"]


@pytest.mark.parametrize("missing_field", ["evidence_ids", "source_connectors", "freshness"])
def test_exact_binding_without_source_provenance_stays_unbound(
    missing_field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_url = "https://www.ekologus.pl/oferta/niezweryfikowana-usluga/"
    values: dict[str, object] = {
        "evidence_ids": ["ev_service_provenance"],
        "source_connectors": ["wordpress_ekologus"],
        "freshness": "reviewed_2026-08-28",
    }
    values[missing_field] = [] if missing_field != "freshness" else ""
    card = ContentKnowledgeCard(
        id="service_missing_provenance",
        card_type="service",
        title="Niezweryfikowana usługa",
        summary="Karta bez kompletnego śladu.",
        service_binding_urls=[binding_url],
        confidence=0.9,
        **values,
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: (card,),
    )

    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_missing_provenance",
            topic="Neutralny temat",
            source_public_url=binding_url,
            final_canonical_url=binding_url,
        )
    )

    assert match.service_card is None
    assert match.recommended_service_card_id is None
    selected = select_content_knowledge_service_card(match, card.id)
    assert selected.service_card is None
    assert "service_card_provenance_missing" in {blocker.code for blocker in selected.blockers}


def test_unverified_exact_binding_keeps_a_valid_duplicate_from_being_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_url = "https://www.ekologus.pl/oferta/wspolny-adres-bez-dowodu/"
    verified = ContentKnowledgeCard(
        id="service_verified_duplicate",
        card_type="service",
        title="Zweryfikowana karta",
        summary="Karta z pełnym śladem.",
        service_binding_urls=[binding_url],
        evidence_ids=["ev_service_verified_duplicate"],
        source_connectors=["wordpress_ekologus"],
        confidence=0.9,
        freshness="reviewed_2026-08-28",
    )
    unverified = verified.model_copy(
        update={
            "id": "service_unverified_duplicate",
            "title": "Karta bez śladu",
            "evidence_ids": [],
        }
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: (verified, unverified),
    )

    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_duplicate_provenance",
            topic="Neutralny temat",
            source_public_url=binding_url,
            final_canonical_url=binding_url,
        )
    )

    assert match.service_card is None
    assert match.recommended_service_card_id is None
    assert "ambiguous_service_binding" in {blocker.code for blocker in match.blockers}


@pytest.mark.parametrize(
    "item_url",
    [
        "https://www.ekologus.pl/oferta/a/b/",
        "https://www.ekologus.pl/oferta/a-b/?wariant=inny",
        "https://attacker@www.ekologus.pl/oferta/a-b/",
        "https://@www.ekologus.pl/oferta/a-b/",
        "https://:@www.ekologus.pl/oferta/a-b/",
        " https://www.ekologus.pl/oferta/a-b/ ",
    ],
)
def test_binding_url_comparison_preserves_path_and_query(
    monkeypatch: pytest.MonkeyPatch,
    item_url: str,
) -> None:
    card = ContentKnowledgeCard(
        id="service_hyphenated_binding",
        card_type="service",
        title="Karta z dokładnym adresem",
        summary="Karta testowa dokładnego adresu.",
        service_binding_urls=["https://www.ekologus.pl/oferta/a-b/"],
        confidence=0.9,
        freshness="reviewed_2026-08-28",
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: (card,),
    )

    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_different_path",
            topic="Neutralny temat",
            source_public_url=item_url,
            final_canonical_url=item_url,
        )
    )

    assert match.service_card is None
    assert match.service_candidates == []


def test_source_lineage_url_does_not_authorize_binding_or_page_body_matching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage_url = "https://www.ekologus.pl/artykul-zrodlowy/"
    card = ContentKnowledgeCard(
        id="service_lineage_only",
        card_type="service",
        title="Usługa tylko ze źródłem",
        summary="Karta testowa pochodzenia bez powiązania.",
        service_fit_terms=["specjalistyczne szkolenia"],
        source_lineage=[lineage_url],
        confidence=0.9,
        freshness="reviewed_2026-08-28",
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: (card,),
    )

    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_lineage_only",
            topic="Neutralny temat",
            wordpress_title_or_h1="Neutralny tytuł",
            source_public_url=lineage_url,
            final_canonical_url=lineage_url,
            wordpress_content_text="Specjalistyczne szkolenia dla zespołu.",
        )
    )

    assert card.service_binding_urls == []
    assert match.service_card is None
    assert match.service_candidates == []


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
        wordpress_content_source_kind="wordpress_rest",
        wordpress_content_extraction_region="wordpress_rest.content",
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
        candidate.card.id != "ekologus_service_environmental_consulting_outsourcing"
        for candidate in match.service_candidates
    )


def test_gsc_service_query_is_only_a_reviewable_candidate_for_a_career_page() -> None:
    page = "https://www.ekologus.pl/kariera/"
    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_career",
            topic="Kariera w Ekologus",
            source_public_url=page,
            final_canonical_url=page,
            evidence_ids=["ev_gsc_career_bdo"],
            source_connectors=["google_search_console"],
            metric_facts=[
                MetricFact(
                    name="impressions",
                    value=12,
                    period="last_28_days",
                    source_connector="google_search_console",
                    evidence_id="ev_gsc_career_bdo",
                    dimensions={"page": page, "query": "bdo ewidencja odpadów"},
                )
            ],
        )
    )

    assert match.service_card is None
    assert any(
        candidate.card.id == "ekologus_service_bdo_reporting"
        for candidate in match.service_candidates
    )

    selected = select_content_knowledge_service_card(match, "ekologus_service_bdo_reporting")

    assert selected.service_card is not None
    assert selected.service_card.id == "ekologus_service_bdo_reporting"
    assert "missing_service_card" not in {blocker.code for blocker in selected.blockers}


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


def test_non_service_page_body_does_not_expose_a_service_candidate() -> None:
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

    assert match.service_card is None
    assert all(
        candidate.card.id != "ekologus_service_environmental_compliance_audit"
        for candidate in match.service_candidates
    )


def test_specific_page_intent_is_candidate_only_without_exact_binding() -> None:
    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_operat_page",
            topic="Operat wodnoprawny – wszystko co musisz wiedzieć",
            source_public_url=(
                "https://www.ekologus.pl/operat-wodnoprawny-wszystko-co-musisz-wiedziec/"
            ),
            final_canonical_url=(
                "https://www.ekologus.pl/operat-wodnoprawny-wszystko-co-musisz-wiedziec/"
            ),
            wordpress_content_text=(
                "Tekst wspomina też o decyzjach administracyjnych i terminach."
            ),
            wordpress_content_source_kind="wordpress_rest",
            wordpress_content_extraction_region="wordpress_rest.content",
            evidence_ids=["ev_wp_operat_page"],
            source_connectors=["wordpress_ekologus"],
        )
    )

    assert match.service_card is None
    assert match.buyer_problem_cards == []
    assert any(
        candidate.card.id == "ekologus_service_operat_wodnoprawny"
        for candidate in match.service_candidates
    )


def test_single_short_generic_term_does_not_bind_an_unrelated_service() -> None:
    match = match_content_knowledge_cards(
        ContentWorkItem(
            id="content_work_item_zoning_article",
            topic="Rewolucja w decyzjach o warunkach zabudowy od 2026",
            source_public_url=(
                "https://www.ekologus.pl/rewolucja-w-decyzjach-o-warunkach-"
                "zabudowy-co-zmienia-sie-od-2026/"
            ),
            final_canonical_url=(
                "https://www.ekologus.pl/rewolucja-w-decyzjach-o-warunkach-"
                "zabudowy-co-zmienia-sie-od-2026/"
            ),
            evidence_ids=["ev_wp_zoning_article"],
            source_connectors=["wordpress_ekologus"],
        )
    )

    assert all(
        candidate.card.id != "ekologus_service_eko_opieka_calendar"
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
            "https://ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
            "ekologus_service_bdo_reporting",
        ),
        (
            "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
            "ekologus_service_environmental_consulting_outsourcing",
        ),
        (
            "https://www.ekologus.pl/",
            "ekologus_service_homepage_overview",
        ),
        (
            "https://www.ekologus.pl/oferta/szkolenia/",
            "ekologus_service_environmental_training",
        ),
        (
            "https://www.ekologus.pl/oferta/opracowania-dokumentacji-ekspertyz/",
            "ekologus_service_operat_wodnoprawny",
        ),
        (
            "https://www.ekologus.pl/oferta/pomiary-i-analizy/",
            "ekologus_service_remediation_monitoring",
        ),
        (
            "https://www.ekologus.pl/oferta/rekultywacje-i-remediacje/",
            "ekologus_service_remediation_monitoring",
        ),
    ],
)
def test_observed_exact_service_binding_urls_select_their_card(
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
    assert match.service_card.service_binding_urls
