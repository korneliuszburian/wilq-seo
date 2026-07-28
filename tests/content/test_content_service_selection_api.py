from __future__ import annotations

from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.workflow.api import _gate_candidate_on_service_binding
from wilq.content.workflow.queue import ContentWorkItemQueueCandidate


def test_unbound_service_candidate_cannot_look_plan_ready() -> None:
    candidate = ContentWorkItemQueueCandidate.model_construct(
        decision_id="decision_unbound",
        evidence_ids=["ev_page"],
        source_connectors=["google_search_console"],
        blockers=[],
        recommended_mode="refresh",
        preflight_status="plan_allowed",
    )
    context = ContentWorkItemServiceProfileContext.not_evaluated(
        reason="Brakuje karty usługi.",
        safe_next_step="Sprawdź kartę usługi.",
    ).model_copy(update={"binding_status": "unbound"})

    gated = _gate_candidate_on_service_binding(
        candidate,
        service_profile_context=context,
    )

    assert gated.recommended_mode == "block"
    assert gated.preflight_status == "blocked"
    assert gated.blockers[0].code == "missing_service_binding"
