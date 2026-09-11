import pytest
from pydantic import ValidationError

from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.subject import ContentPlanningSubject


def test_service_planning_request_remains_v1_compatible() -> None:
    request = ContentPlanningProposalRequest(
        service_card_id="service_card",
        expected_planning_input_digest="a" * 64,
        requested_by="wilku",
    )

    assert ContentPlanningSubject(service_card_id=request.service_card_id).subject_key == (
        "service_card"
    )


def test_editorial_planning_request_has_neutral_subject() -> None:
    subject = ContentPlanningSubject(
        content_kind="editorial",
        service_card_id=None,
    )

    assert subject.subject_key == "editorial"


@pytest.mark.parametrize(
    ("content_kind", "service_card_id"),
    [("service", None), ("editorial", "fake_service")],
)
def test_planning_request_rejects_subject_identity_mismatch(
    content_kind: str,
    service_card_id: str | None,
) -> None:
    with pytest.raises(ValidationError, match="service identity"):
        ContentPlanningSubject(
            content_kind=content_kind,
            service_card_id=service_card_id,
        )
