from __future__ import annotations

import pytest

from wilq.content.knowledge.cards import ContentKnowledgeCard, ContentKnowledgeCardMatch
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
    _cta_patterns,
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


def test_cta_pattern_projection_falls_back_to_matched_cta_cards() -> None:
    service_card = ContentKnowledgeCard.model_construct(cta_patterns=[])
    cta_card = ContentKnowledgeCard.model_construct(cta_patterns=["reviewed CTA"])
    match = ContentKnowledgeCardMatch.model_construct(
        work_item_id="work-item",
        service_card=service_card,
        cta_cards=[cta_card],
    )

    assert _cta_patterns(match, service_card) == ["reviewed CTA"]


def test_python_service_profile_rejects_blank_cta_patterns() -> None:
    payload = ContentWorkItemServiceProfileContext.not_evaluated().model_dump()
    payload["cta_patterns"] = ["   "]
    with pytest.raises(ValueError, match="CTA patterns"):
        ContentWorkItemServiceProfileContext.model_validate(payload)


def test_python_service_profile_caps_cta_patterns_at_four() -> None:
    payload = ContentWorkItemServiceProfileContext.not_evaluated().model_dump()
    payload["cta_patterns"] = [f"pattern-{index}" for index in range(5)]
    with pytest.raises(ValueError, match="at most 4 items"):
        ContentWorkItemServiceProfileContext.model_validate(payload)
