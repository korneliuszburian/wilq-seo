from pydantic import ValidationError

from wilq.content.planning.generated_proposal import _validation_source_codes
from wilq.content.planning.generated_proposal_contracts import ContentPlanningModelOutput


def test_invalid_planning_output_exposes_schema_location_without_model_text() -> None:
    try:
        ContentPlanningModelOutput.model_validate_json("{\"sections\": []}")
    except ValidationError as error:
        codes = _validation_source_codes(error)
    else:  # pragma: no cover - the model must reject this payload
        raise AssertionError("invalid planning output unexpectedly validated")

    assert any(code.startswith("schema:service_card_id:") for code in codes)
    assert all("sections\": []" not in code for code in codes)
