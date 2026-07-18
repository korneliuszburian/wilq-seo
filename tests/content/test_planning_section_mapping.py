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
