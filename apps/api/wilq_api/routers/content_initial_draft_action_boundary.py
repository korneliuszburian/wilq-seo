"""Typed public blocker for draft writes without an ActionObject."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from wilq.content.drafts.initial_draft_response import initial_draft_packet_fields
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftConflictResponse,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
    ContentWorkItemInitialDraftRequest,
)


def initial_draft_action_required_response(
    work_item_id: str,
    request: ContentWorkItemInitialDraftRequest,
) -> JSONResponse:
    next_step = "Przygotuj ActionObject dla pełnego szkicu z dokładnym planem i pakietem v3."
    blocker = ContentInitialDraftBlocker(
        code="initial_draft_action_required",
        label="Pełny szkic wymaga ActionObject",
        reason="Ten punkt API nie ma zatwierdzonej akcji uruchomienia pełnego szkicu.",
        next_step=next_step,
        owner="WILQ content workflow",
    )
    exact = request if isinstance(request, ContentInitialDraftRequest) else None
    response = ContentInitialDraftResponse(
        status="conflict",
        work_item_id=work_item_id,
        proposal_id=None if exact is None else exact.expected_proposal_id,
        **initial_draft_packet_fields(
            research_packet_id=None if exact is None else exact.research_packet_id,
            research_packet_digest=None if exact is None else exact.research_packet_digest,
        ),
        blockers=[blocker],
        safe_next_step=next_step,
    )
    conflict = ContentInitialDraftConflictResponse.model_validate(
        response.model_dump(mode="python")
    )
    return JSONResponse(status_code=409, content=conflict.model_dump(mode="json"))


__all__ = ["initial_draft_action_required_response"]
