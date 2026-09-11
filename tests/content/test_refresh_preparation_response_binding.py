from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.content.test_refresh_preparation_authority import _summary
from tests.content.test_refresh_preparation_contracts import (
    INPUT_DIGEST,
    SERVICE_CARD_ID,
    WORK_ITEM_ID,
    _classification_binding,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalResponse,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    build_content_refresh_preparation_authorization,
)
from wilq.schemas.core import utc_now


def test_planning_response_requires_exact_top_and_nested_refresh_binding() -> None:
    binding = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=_classification_binding(),
        planning_input_digest=INPUT_DIGEST,
        service_card_id=SERVICE_CARD_ID,
        acknowledged_classification_blocker_codes=["lineage_needs_review"],
        authorized_by="wilku",
        authorized_at=utc_now(),
    ).binding
    proposal = ContentPlanningProposal(
        work_item_id=WORK_ITEM_ID,
        planning_digest="e" * 64,
        proposal_id="content_planning_proposal_refresh",
        planning_input_digest=INPUT_DIGEST,
        final_canonical_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        service_card_id=SERVICE_CARD_ID,
        target_reader="Firma",
        buyer_problem="Brak pewności.",
        buyer_trigger="Zmiana obowiązków.",
        search_intent="Informacyjny.",
        cta_direction="Skonsultuj sytuację.",
        sections=[ContentPlanningSection(heading="Zakres", purpose="Wyjaśnia zakres.")],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak dokładnych danych.",
        ),
        refresh_preparation_binding=binding,
    )
    response = ContentPlanningProposalResponse(
        status="ready",
        work_item_id=WORK_ITEM_ID,
        service_card_id=SERVICE_CARD_ID,
        planning_input_digest=INPUT_DIGEST,
        input_summary=_summary(),
        proposal=proposal,
        refresh_preparation_binding=binding,
        safe_next_step="Sprawdź plan.",
    )

    assert response.refresh_preparation_binding == binding
    with pytest.raises(ValidationError, match="requires its response refresh binding"):
        ContentPlanningProposalResponse(
            status="ready",
            work_item_id=WORK_ITEM_ID,
            service_card_id=SERVICE_CARD_ID,
            planning_input_digest=INPUT_DIGEST,
            input_summary=_summary(),
            proposal=proposal,
            safe_next_step="Sprawdź plan.",
        )
    with pytest.raises(ValidationError, match="must match its proposal"):
        ContentPlanningProposalResponse(
            status="ready",
            work_item_id=WORK_ITEM_ID,
            service_card_id=SERVICE_CARD_ID,
            planning_input_digest=INPUT_DIGEST,
            input_summary=_summary(),
            proposal=proposal.model_copy(update={"refresh_preparation_binding": None}),
            refresh_preparation_binding=binding,
            safe_next_step="Sprawdź plan.",
        )
    with pytest.raises(ValidationError, match="must match its exact identity"):
        ContentPlanningProposalResponse(
            status="blocked",
            work_item_id="content_work_item_foreign",
            service_card_id=SERVICE_CARD_ID,
            planning_input_digest=INPUT_DIGEST,
            input_summary=_summary(),
            refresh_preparation_binding=binding,
            blockers=[
                ContentPlanningProposalBlocker(
                    code="refresh_preparation_proposal_binding_mismatch",
                    label="Binding nie pasuje",
                    reason="Fixture sprawdza identity.",
                    next_step="Odśwież context.",
                )
            ],
            safe_next_step="Odśwież context.",
        )
