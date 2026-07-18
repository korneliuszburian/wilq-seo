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
