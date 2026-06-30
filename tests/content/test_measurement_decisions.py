from __future__ import annotations

from wilq.content.measurement.decisions import ga4_tracking_gap_decisions
from wilq.schemas import MetricFact, OpportunityDomain, TacticalQueueItem


def _ga4_fact(name: str, value: int | float | str, **dimensions: str) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="last_28_days",
        source_connector="google_analytics_4",
        evidence_id=f"ev_ga4_{name}",
        dimensions=dimensions,
    )


def test_ga4_tracking_gap_decision_blocks_content_rewrite_claims() -> None:
    item = TacticalQueueItem(
        id="queue_ga4_not_set",
        title="GA4: braki kampanii",
        domain=OpportunityDomain.ga4,
        intent="tracking_gap",
        priority=12,
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_ga4_tracking_gap"],
        metric_facts=[
            _ga4_fact("sessions", 120, campaign="(not set)"),
            _ga4_fact("sessions", 120, campaign="(not set)"),
        ],
        diagnosis="GA4 pokazuje brak wymiaru kampanii.",
        next_step="Sprawdź tracking.",
        blocked_claims=["ocena kampanii"],
        action_ids=["act_review_ga4_tracking_quality"],
    )

    decisions = ga4_tracking_gap_decisions(
        [item, item],
        knowledge_card_ids=("card_ga4_behavior_diagnostics_playbook",),
        expert_rule_ids=("ga4_diagnostics_v1",),
    )

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.decision_type == "block_as_tracking_not_content"
    assert decision.status == "blocked"
    assert decision.metric_tiles == {"blokady": 1, "dowody": 1, "braki pomiaru": 1}
    assert decision.source_connectors == ["google_analytics_4"]
    assert decision.evidence_ids == ["ev_ga4_tracking_gap"]
    assert decision.action_ids == ["act_review_ga4_tracking_quality"]
    assert decision.knowledge_card_ids == ["card_ga4_behavior_diagnostics_playbook"]
    assert decision.expert_rule_ids == ["ga4_diagnostics_v1"]
    assert decision.blocked_claims == [
        "ocena kampanii",
        "przepisanie treści",
        "wzrost konwersji",
        "zwrot z reklam",
    ]
    assert "problem pomiaru" in decision.rationale
    assert "zamiast tworzyć rewrite treści" in decision.next_step


def test_ga4_tracking_gap_decision_ignores_non_tracking_content_items() -> None:
    item = TacticalQueueItem(
        id="queue_content_bdo",
        title="BDO",
        domain=OpportunityDomain.gsc_seo,
        intent="content_refresh",
        priority=20,
        source_connectors=["google_search_console"],
        evidence_ids=["ev_content_bdo"],
        diagnosis="GSC pokazuje popyt.",
        next_step="Sprawdź plan.",
    )

    assert (
        ga4_tracking_gap_decisions(
            [item],
            knowledge_card_ids=("card_ga4_behavior_diagnostics_playbook",),
            expert_rule_ids=("ga4_diagnostics_v1",),
        )
        == []
    )
