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


def test_root_planning_validator_exposes_safe_reason_category() -> None:
    payload = {
        "language": "pl-PL",
        "service_card_id": "service-bdo",
        "target_reader": "firma",
        "buyer_problem": "problem",
        "buyer_trigger": "trigger",
        "search_intent": "informational",
        "angle": "angle",
        "value_proposition": "value",
        "page_assets": {
            "title": "title",
            "h1": "h1",
            "lead": "lead",
            "meta_title": "meta",
            "meta_description": "description",
        },
        "sections": [
                {
                    "heading": "Zakres",
                    "purpose": "purpose",
                    "reader_question": "question",
                    "inventory_disposition": "create",
                    "evidence_ids": ["ev"],
                "claim_ids": [],
            }
        ],
        "measurement_plan": {
            "metrics_to_watch": [],
            "baseline_evidence_ids": [],
            "observation_rule": "",
            "success_claim_rule": "",
        },
    }
    try:
        ContentPlanningModelOutput.model_validate(payload)
    except ValidationError as error:
        codes = _validation_source_codes(error)
    else:  # pragma: no cover
        raise AssertionError("invalid planning output unexpectedly validated")

    assert "schema:$:value_error:missing_measurement_observation_rule" in codes
