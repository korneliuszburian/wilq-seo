"""Parent-safe observer for explicit deferred generation authority."""

from __future__ import annotations

from wilq.content.planning.generation_intent import (
    build_planning_generation_intent_proposal,
    planning_generation_intent_action,
)


def test_planning_action_authorizes_only_exact_post_audit_dispatch() -> None:
    proposal = build_planning_generation_intent_proposal(
        work_item_id="wi_exact",
        content_kind="service",
        service_card_id="card_exact",
        packet_id="content_research_packet_v2_" + "a" * 24,
        packet_digest="a" * 64,
        raw_planning_input_digest="b" * 64,
        projected_planning_input_digest="c" * 64,
        selected_fact_ids=("fact_exact",),
        evidence_ids=("ev_exact",),
    )
    action = planning_generation_intent_action(proposal)

    assert action.payload.get("dispatch_after_apply_audit") is True
    assert action.payload.get("model_enqueued_at_apply") is False
    assert action.payload.get("generation_performed_at_apply") is False
    assert proposal.snapshot.dispatch_after_apply_audit is True
