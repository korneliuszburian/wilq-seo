from __future__ import annotations

from wilq.content.planning.ahrefs import ahrefs_gap_record_decisions
from wilq.schemas import MetricFact


def _fact(
    name: str,
    *,
    source_connector: str = "ahrefs",
    evidence_id: str | None = None,
    **dimensions: str,
) -> MetricFact:
    return MetricFact(
        name=name,
        value=1,
        period="last_28_days",
        source_connector=source_connector,
        evidence_id=evidence_id or f"ev_{name}_{dimensions.get('keyword', 'fact')}",
        dimensions=dimensions,
    )


def test_ahrefs_gap_record_decisions_returns_empty_without_ahrefs_gap_facts() -> None:
    assert (
        ahrefs_gap_record_decisions(
            [
                _fact(
                    "impressions",
                    source_connector="google_search_console",
                    evidence_id="ev_gsc_bdo",
                    query="bdo odpady",
                    page="https://www.ekologus.pl/bdo/",
                )
            ],
            ["act_prepare_content_refresh_queue"],
            knowledge_card_ids=("card_ahrefs_content_gap_playbook",),
            expert_rule_ids=("content_brief_rules_v1",),
        )
        == []
    )


def test_ahrefs_gap_record_decisions_filters_relevant_candidates_before_content_plan() -> None:
    decisions = ahrefs_gap_record_decisions(
        [
            _fact(
                "ahrefs_content_gap_count",
                evidence_id="ev_ahrefs_bdo",
                gap_type="content_gap",
                keyword="bdo odpady",
                competitor_domain="denios.pl",
            ),
            _fact(
                "ahrefs_content_gap_count",
                evidence_id="ev_ahrefs_oc",
                gap_type="content_gap",
                keyword="kalkulator oc",
                competitor_domain="cuk.pl",
            ),
            _fact(
                "impressions",
                source_connector="google_search_console",
                evidence_id="ev_gsc_bdo",
                query="bdo odpady",
                page="https://www.ekologus.pl/bdo/",
            ),
            _fact(
                "content_object_seen",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_bdo",
                title="BDO odpady",
                content_url="https://www.ekologus.pl/bdo/",
            ),
        ],
        ["act_prepare_content_refresh_queue", "act_review_ga4_tracking_quality"],
        knowledge_card_ids=("card_ahrefs_content_gap_playbook",),
        expert_rule_ids=("content_brief_rules_v1",),
    )

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.id == "content_decision_ahrefs_gap_records_review"
    assert decision.decision_type == "review_ahrefs_gap_records"
    assert decision.status == "ready"
    assert decision.metric_tiles["pasujące"] == 1
    assert decision.metric_tiles["poza zakresem"] == 1
    assert decision.metric_tiles["Powiązanie z GSC"] == 1
    assert decision.metric_tiles["Powiązanie z WordPress"] == 1
    assert decision.queries == ["bdo odpady"]
    assert decision.action_ids == ["act_prepare_content_refresh_queue"]
    assert decision.knowledge_card_ids == ["card_ahrefs_content_gap_playbook"]
    assert "wzrost ruchu" in decision.blocked_claims
    assert len(decision.ahrefs_candidate_rows) == 1
    candidate = decision.ahrefs_candidate_rows[0]
    assert candidate.topic == "bdo odpady"
    assert candidate.relevance_status == "relevant"
    assert candidate.gsc_demand_label == "jest w GSC"
    assert candidate.wordpress_inventory_match_label == "jest w WordPress"
