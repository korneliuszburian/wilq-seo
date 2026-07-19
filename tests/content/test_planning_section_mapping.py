from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningModelSection,
)
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningInventorySection,
)
from wilq.content.planning.section_mapping import (
    build_inventory_mapping,
    canonicalize_model_inventory_headings,
)


def test_existing_inventory_is_mapped_without_requiring_model_to_repeat_heading() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_01",
                    heading="Korzyści ze współpracy",
                    evidence_ids=["ev_wp"],
                ),
                ContentPlanningInventorySection(
                    section_id="inventory_02",
                    heading="Zakres doradztwa",
                    evidence_ids=["ev_wp"],
                ),
            ]
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Korzyści współpracy",
                purpose="Odpowiedzieć na potrzebę czytelnika.",
                reader_question="Co zyskuje firma?",
                inventory_disposition="rewrite",
                inventory_heading=None,
            ),
            ContentPlanningModelSection.model_construct(
                heading="Nowy następny krok",
                purpose="Wyjaśnić kolejny krok.",
                reader_question="Co dalej?",
                inventory_disposition="create",
                inventory_heading=None,
            ),
        ]
    )

    canonical = canonicalize_model_inventory_headings(planning_input, output)
    assert canonical.sections[0].inventory_heading == "Korzyści ze współpracy"
    assert canonical.sections[0].inventory_section_id == "inventory_01"
    mappings = build_inventory_mapping(
        planning_input,
        canonical,
        ["plan_01", "plan_02"],
    )

    assert mappings[0].status == "mapped"
    assert mappings[0].mapped_section_id == "plan_01"
    assert mappings[0].disposition == "rewrite"
    assert mappings[1].status == "unmapped"
    assert mappings[1].mapped_section_id is None


def test_fuzzy_mapping_is_one_to_one_and_never_reuses_a_plan_section() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_01", heading="Zakres usług", evidence_ids=["ev_wp"]
                ),
                ContentPlanningInventorySection(
                    section_id="inventory_02", heading="Zakres wsparcia", evidence_ids=["ev_wp"]
                ),
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Zakres usług",
                purpose="Wyjaśnić zakres.",
                reader_question="Jaki jest zakres?",
                inventory_disposition="rewrite",
                inventory_heading=None,
            )
        ]
    )

    mappings = build_inventory_mapping(planning_input, output, ["plan_01"])

    assert sum(item.status == "mapped" for item in mappings) == 1
    assert sum(item.status == "unmapped" for item in mappings) == 1


def test_stable_inventory_id_wins_when_the_plan_renames_a_section() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_acf_07",
                    heading="Jak wygląda współpraca",
                    evidence_ids=["ev_wp"],
                )
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Co otrzymuje firma na początku współpracy",
                purpose="Wyjaśnić pierwszy etap.",
                reader_question="Co dzieje się na początku?",
                inventory_disposition="rewrite",
                inventory_section_id="inventory_acf_07",
                inventory_heading=None,
            )
        ]
    )

    canonical = canonicalize_model_inventory_headings(planning_input, output)
    assert canonical.sections[0].inventory_heading == "Jak wygląda współpraca"
    mappings = build_inventory_mapping(planning_input, canonical, ["plan_01"])
    assert mappings[0].status == "mapped"
    assert mappings[0].mapped_section_id == "plan_01"


def test_unique_existing_heading_is_upgraded_to_stable_inventory_id() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_the_content_02",
                    heading="Najczęstsze pytania",
                    evidence_ids=["ev_wp"],
                )
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Najczęstsze pytania",
                purpose="Odpowiedzieć na pytania czytelnika.",
                reader_question="Co trzeba wiedzieć?",
                inventory_disposition="rewrite",
                inventory_heading="Najczęstsze pytania",
            )
        ]
    )

    canonical = canonicalize_model_inventory_headings(planning_input, output)

    assert canonical.sections[0].inventory_section_id == "inventory_the_content_02"


def test_decorative_or_dated_inventory_is_explicitly_excluded_for_review() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_event",
                    heading="13 marca 2020 — szkolenie dla przedsiębiorców",
                    evidence_ids=["ev_wp"],
                )
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Nowa odpowiedź dla czytelnika",
                purpose="Wyjaśnić temat.",
                reader_question="Co powinien wiedzieć czytelnik?",
                inventory_disposition="create",
            )
        ]
    )

    mappings = build_inventory_mapping(planning_input, output, ["plan_01"])
    assert mappings[0].status == "excluded"
    assert mappings[0].disposition == "remove_review_required"
    assert mappings[0].reason == "dated_or_event_inventory"


def test_model_remove_review_disposition_is_not_presented_as_article_mapping() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_clients",
                    heading="Zaufali nam",
                    evidence_ids=["ev_wp"],
                )
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Jak zweryfikować doświadczenie?",
                purpose="Pozostawić referencje do osobnego review.",
                reader_question="Czy referencje są aktualne?",
                inventory_disposition="remove_review_required",
                inventory_section_id="inventory_clients",
            )
        ]
    )

    mappings = build_inventory_mapping(planning_input, output, ["plan_01"])

    assert mappings[0].status == "excluded"
    assert mappings[0].disposition == "remove_review_required"
    assert mappings[0].reason == "navigation_or_promotional_inventory"


def test_footer_tail_after_related_content_is_excluded_without_model_rows():
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_related",
                    heading="Może Cię również zainteresować",
                    evidence_ids=["ev_wp"],
                ),
                ContentPlanningInventorySection(
                    section_id="inventory_service_1",
                    heading="Dokumentacje środowiskowe",
                    evidence_ids=["ev_wp"],
                ),
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Nowa odpowiedź dla czytelnika",
                purpose="Wyjaśnić temat.",
                reader_question="Co powinien wiedzieć czytelnik?",
                inventory_disposition="create",
            )
        ]
    )

    mappings = build_inventory_mapping(planning_input, output, ["plan_01"])

    assert [item.status for item in mappings] == ["excluded", "excluded"]
    assert all(item.reason == "navigation_or_promotional_inventory" for item in mappings)


def test_footer_tail_cannot_be_reintroduced_by_a_similar_model_section():
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_related",
                    heading="Może Cię również zainteresować",
                    evidence_ids=["ev_wp"],
                ),
                ContentPlanningInventorySection(
                    section_id="inventory_footer",
                    heading="Doradztwo środowiskowe i EKO–consulting",
                    evidence_ids=["ev_wp"],
                ),
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Doradztwo środowiskowe i EKO–consulting",
                purpose="Nawigacja do oferty.",
                reader_question="Czy potrzebuję usługi?",
                inventory_disposition="rewrite",
                inventory_section_id="inventory_footer",
            )
        ]
    )

    mappings = build_inventory_mapping(planning_input, output, ["plan_01"])

    assert mappings[1].status == "excluded"
    assert mappings[1].mapped_section_id is None
    assert mappings[1].reason == "navigation_or_promotional_inventory"


def test_faq_lead_inventory_is_excluded_for_review_when_model_omits_it() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            sections=[
                ContentPlanningInventorySection(
                    section_id="inventory_faq_lead",
                    heading="Poniżej przedstawiamy często zadawane pytania dotyczące BDO:",
                    evidence_ids=["ev_wp"],
                )
            ],
        )
    )
    output = ContentPlanningModelOutput.model_construct(
        sections=[
            ContentPlanningModelSection.model_construct(
                heading="Odpowiedź dla czytelnika",
                purpose="Zbudować użyteczną sekcję.",
                reader_question="Co trzeba wiedzieć?",
                inventory_disposition="create",
            )
        ]
    )

    mappings = build_inventory_mapping(planning_input, output, ["plan_01"])

    assert mappings[0].status == "excluded"
    assert mappings[0].disposition == "remove_review_required"
    assert mappings[0].reason == "navigation_or_promotional_inventory"
