import pytest
from pydantic import ValidationError

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence


def _input_payload() -> dict[str, object]:
    return {
        "planning_input_digest": "a" * 64,
        "work_item_id": "content_work_item_editorial",
        "final_canonical_url": "https://www.ekologus.pl/artykul/",
        "inventory": ContentPlanningInventory(
            status="available",
            content_status="available",
            acf_section_status="missing",
        ),
        "target_reader": "Osoba szukająca rzetelnej odpowiedzi.",
        "buyer_problem": "Brak uporządkowanej informacji.",
        "buyer_trigger": "Potrzeba sprawdzenia aktualnego tematu.",
        "search_intent": "informational",
        "source_assessments": [
            ContentPlanningSourceAssessment(
                source=source,
                status="missing",
                reason="Źródło nie jest wymagane w tym modelowym teście.",
            )
            for source in sorted(PLANNING_SOURCE_NAMES)
        ],
        "query_portfolio": ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Użyj dokładnych danych strony, gdy są dostępne.",
        ),
        "measurement_observation_rule": "Nie przypisuj skutku bez pomiaru.",
        "measurement_success_claim_rule": "Wynik wymaga zamkniętego okna pomiaru.",
        "baseline_cta_direction": "Przejdź do powiązanego materiału.",
    }


def test_editorial_planning_input_has_no_service_identity() -> None:
    planning_input = ContentPlanningInput.model_validate(
        {**_input_payload(), "content_kind": "editorial"}
    )

    assert planning_input.service_candidates == []
    assert planning_input.confirmed_service_card_id is None
    assert planning_input.service_label is None


def test_service_planning_input_still_requires_service_identity() -> None:
    with pytest.raises(ValidationError, match="exact service identity"):
        ContentPlanningInput.model_validate(_input_payload())
