from wilq.content.workflow.decision_mapping import content_sales_brief_seed_from_decision
from wilq.schemas import ContentDecisionItem


def test_existing_inventory_headings_are_used_instead_of_query_placeholder_titles():
    decision = ContentDecisionItem(
        id="inventory_outsourcing",
        decision_type="refresh_or_merge",
        title="Doradztwo i outsourcing środowiskowy",
        queries=["doradztwo środowiskowe", "outsourcing ekologiczny"],
        wordpress_section_headings=[
            "Korzyści ze współpracy z nami",
            "Doradztwo ekologiczne",
        ],
        evidence_ids=["ev_wp"],
        source_connectors=["wordpress_ekologus"],
        rationale="Istniejąca treść wymaga odświeżenia.",
        next_step="Sprawdź materiał.",
        source_public_url="https://www.ekologus.pl/oferta/doradztwo/",
        final_canonical_url="https://www.ekologus.pl/oferta/doradztwo/",
        intended_final_url="https://www.ekologus.pl/oferta/doradztwo/",
        inventory_gate_status="confirmed_current_inventory",
        duplicate_gate_status="checked",
    )

    seed = content_sales_brief_seed_from_decision(decision)

    assert seed.h2_direction == [
        "Korzyści ze współpracy z nami",
        "Doradztwo ekologiczne",
    ]
    assert all("Co wiemy z zapytań" not in heading for heading in seed.h2_direction)


def test_inventory_heading_cleanup_drops_related_navigation_noise():
    decision = ContentDecisionItem(
        id="inventory_bdo",
        decision_type="refresh_or_merge",
        title="BDO dla przedsiębiorcy",
        queries=["bdo co to"],
        wordpress_section_headings=[
            "Poniżej przedstawiamy często zadawane pytania dotyczące BDO:",
            "Kto musi złożyć wniosek o wpis do Rejestru?",
            "Zaufali nam między innymi",
            "Może Cię również zainteresować",
            "Oferta Pomiary Emisji",
        ],
        evidence_ids=["ev_wp"],
        source_connectors=["wordpress_ekologus"],
        rationale="Istniejąca treść wymaga odświeżenia.",
        next_step="Sprawdź materiał.",
        source_public_url="https://www.ekologus.pl/bdo/",
        final_canonical_url="https://www.ekologus.pl/bdo/",
        intended_final_url="https://www.ekologus.pl/bdo/",
        inventory_gate_status="confirmed_current_inventory",
        duplicate_gate_status="checked",
    )

    seed = content_sales_brief_seed_from_decision(decision)

    assert seed.h2_direction == [
        "Najczęstsze pytania dotyczące BDO",
        "Kto musi złożyć wniosek o wpis do Rejestru?",
    ]


def test_inventory_heading_cleanup_drops_dated_testimonial_rows():
    decision = ContentDecisionItem(
        id="inventory_packaging",
        decision_type="refresh_or_merge",
        title="Gospodarka opakowaniami",
        queries=["gospodarka opakowaniami"],
        wordpress_section_headings=[
            "Obowiązki przedsiębiorcy",
            "SERTOP Sp. z o.o. [2013 r.]",
            "Jak przygotować dokumenty?",
        ],
        evidence_ids=["ev_wp"],
        source_connectors=["wordpress_ekologus"],
        rationale="Istniejąca treść wymaga odświeżenia.",
        next_step="Sprawdź materiał.",
        source_public_url="https://www.ekologus.pl/informacja-o-opakowaniach/",
        final_canonical_url="https://www.ekologus.pl/informacja-o-opakowaniach/",
        intended_final_url="https://www.ekologus.pl/informacja-o-opakowaniach/",
        inventory_gate_status="confirmed_current_inventory",
        duplicate_gate_status="checked",
    )

    seed = content_sales_brief_seed_from_decision(decision)

    assert seed.h2_direction == [
        "Obowiązki przedsiębiorcy",
        "Jak przygotować dokumenty?",
    ]
