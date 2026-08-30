from __future__ import annotations

import pytest
from pydantic import ValidationError

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftRequest
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping

WORK_ITEM_ID = "content_work_item_refresh"
SERVICE_CARD_ID = "ekologus_service_operat_wodnoprawny"
RUN_DIGEST = "a" * 64
DECISION_DIGEST = "b" * 64
ROW_DIGEST = "c" * 64
INPUT_DIGEST = "d" * 64


@pytest.mark.parametrize(
    "model",
    [ContentPlanningProposalRequest, ContentInitialDraftRequest],
)
@pytest.mark.parametrize(
    "authorization_pair",
    [
        {
            "refresh_preparation_authorization_id": "content_refresh_preparation_authorization_abc",
            "expected_refresh_preparation_authorization_digest": None,
        },
        {
            "refresh_preparation_authorization_id": None,
            "expected_refresh_preparation_authorization_digest": "e" * 64,
        },
    ],
)
def test_generation_requests_reject_partial_refresh_authorization_pairs(
    model: object,
    authorization_pair: dict[str, str | None],
) -> None:
    if model is ContentPlanningProposalRequest:
        payload = {
            "service_card_id": SERVICE_CARD_ID,
            "expected_planning_input_digest": INPUT_DIGEST,
            "requested_by": "wilku",
        }
    else:
        payload = {
            "expected_proposal_id": "content_planning_proposal_test",
            "expected_planning_digest": "e" * 64,
            "expected_planning_input_digest": INPUT_DIGEST,
            "requested_by": "wilku",
        }
    with pytest.raises(ValidationError, match="authorization ID and digest"):
        model.model_validate({**payload, **authorization_pair})  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "model",
    [ContentPlanningProposalRequest, ContentInitialDraftRequest],
)
def test_generation_requests_accept_explicit_null_refresh_authorization_pair(model: object) -> None:
    payload: dict[str, object]
    if model is ContentPlanningProposalRequest:
        payload = {
            "service_card_id": SERVICE_CARD_ID,
            "expected_planning_input_digest": INPUT_DIGEST,
            "requested_by": "wilku",
        }
    else:
        payload = {
            "expected_proposal_id": "content_planning_proposal_test",
            "expected_planning_digest": "e" * 64,
            "expected_planning_input_digest": INPUT_DIGEST,
            "requested_by": "wilku",
        }
    parsed = model.model_validate(  # type: ignore[union-attr]
        {
            **payload,
            "refresh_preparation_authorization_id": None,
            "expected_refresh_preparation_authorization_digest": None,
        }
    )

    assert parsed.refresh_preparation_authorization_id is None
    assert parsed.expected_refresh_preparation_authorization_digest is None


@pytest.mark.parametrize(
    "regeneration",
    [
        {"regenerate_stale_mapping": True},
        {"regenerate_after_review": True, "operator_hint": "Popraw wskazane mapowanie."},
    ],
)
def test_refresh_authorization_cannot_authorize_another_planning_turn(
    regeneration: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="cannot authorize plan regeneration"):
        ContentPlanningProposalRequest(
            service_card_id=SERVICE_CARD_ID,
            expected_planning_input_digest=INPUT_DIGEST,
            requested_by="wilku",
            refresh_preparation_authorization_id="content_refresh_preparation_authorization_test",
            expected_refresh_preparation_authorization_digest="e" * 64,
            **regeneration,
        )


@pytest.mark.parametrize(
    "operator",
    [
        "Bearer secret",
        "Basic d2lsa3U6c2VjcmV0",
        "wilku\nother",
        "https://wilku:secret@example.test",
        "/private/operator",
        "token operator",
    ],
)
def test_refresh_authorization_rejects_unsafe_operator_identity(operator: str) -> None:
    with pytest.raises(ValidationError, match="safe visible local operator identity"):
        ContentRefreshPreparationAuthorizationRequest(
            expected_production_classification_run_digest=RUN_DIGEST,
            expected_production_classification_decision_set_digest=DECISION_DIGEST,
            expected_production_classification_source_packet_row_digest=ROW_DIGEST,
            expected_planning_input_digest=INPUT_DIGEST,
            service_card_id=SERVICE_CARD_ID,
            authorized_by=operator,
            acknowledged_classification_blocker_codes=["lineage_needs_review"],
        )


def test_refresh_receipt_identifiers_survive_safe_redaction() -> None:
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=_classification_binding(),
        planning_input_digest=INPUT_DIGEST,
        service_card_id=SERVICE_CARD_ID,
        acknowledged_classification_blocker_codes=["lineage_needs_review"],
        authorized_by="Wilku zespół",
        authorized_at=utc_now(),
    )

    redacted = redact_mapping(
        {
            "authorization_id": authorization.authorization_id,
            "authorization_digest": authorization.authorization_digest,
            "expected_refresh_preparation_authorization_digest": authorization.authorization_digest,
            "canonical_path": authorization.canonical_path,
            "public_url": authorization.public_url,
            "authorized_by": authorization.authorized_by,
            "refresh_preparation_binding": authorization.binding.model_dump(mode="json"),
        }
    )

    assert redacted["authorization_id"] == authorization.authorization_id
    assert redacted["authorization_digest"] == authorization.authorization_digest
    assert redacted["expected_refresh_preparation_authorization_digest"] == (
        authorization.authorization_digest
    )
    assert redacted["canonical_path"] == authorization.canonical_path
    assert redacted["public_url"] == authorization.public_url
    assert redacted["authorized_by"] == authorization.authorized_by
    assert redacted["refresh_preparation_binding"] == authorization.binding.model_dump(mode="json")


def _classification_binding() -> ContentRefreshPreparationClassificationBinding:
    return ContentRefreshPreparationClassificationBinding(
        classification_run_id="content_production_classification_test",
        classification_run_digest=RUN_DIGEST,
        decision_set_digest=DECISION_DIGEST,
        source_packet_row_digest=ROW_DIGEST,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        classification_blocker_codes=["lineage_needs_review"],
    )
