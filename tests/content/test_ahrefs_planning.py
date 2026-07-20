from __future__ import annotations

from wilq.content.planning import ahrefs_overlap
from wilq.content.planning.ahrefs import (
    ahrefs_cross_source_candidate_rows,
    ahrefs_gap_record_decisions,
)
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
    assert candidate.gsc_cross_check.strength == "exact"
    assert candidate.gsc_cross_check.evidence_ids == ["ev_gsc_bdo"]
    assert candidate.wordpress_cross_check.strength == "exact"
    assert candidate.wordpress_cross_check.evidence_ids == ["ev_wp_bdo"]
    assert candidate.source_connectors == [
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert candidate.evidence_ids == ["ev_ahrefs_bdo", "ev_gsc_bdo", "ev_wp_bdo"]


def test_ahrefs_gap_record_decision_keeps_weak_overlap_manual_without_action() -> None:
    decisions = ahrefs_gap_record_decisions(
        [
            _fact(
                "ahrefs_content_gap_count",
                evidence_id="ev_ahrefs_mieszalnik_ibc",
                gap_type="content_gap",
                keyword="mieszalnik IBC",
                source_url="https://denios.pl/mieszalnik-ibc/",
                competitor_domain="denios.pl",
            ),
            _fact(
                "impressions",
                source_connector="google_search_console",
                evidence_id="ev_gsc_kontener_ibc",
                query="kontener IBC odpady",
                page="https://www.ekologus.pl/kontener-ibc/",
            ),
            _fact(
                "content_object_seen",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_lejek_ibc",
                title="Lejek do kontenerów IBC",
                content_url="https://www.ekologus.pl/lejek-do-kontenerow-ibc/",
            ),
        ],
        ["act_prepare_content_refresh_queue"],
        knowledge_card_ids=("card_ahrefs_content_gap_playbook",),
        expert_rule_ids=("content_brief_rules_v1",),
    )

    assert len(decisions) == 1
    decision = decisions[0]
    candidate = decision.ahrefs_candidate_rows[0]
    assert candidate.gsc_demand == "missing"
    assert candidate.wordpress_inventory_match == "missing"
    assert candidate.gsc_cross_check.strength == "weak"
    assert candidate.wordpress_cross_check.strength == "weak"
    assert candidate.gsc_overlap_terms == []
    assert candidate.wordpress_overlap_urls == []
    assert decision.metric_tiles["Powiązanie z GSC"] == 0
    assert decision.metric_tiles["Powiązanie z WordPress"] == 0
    assert decision.action_ids == []
    assert "słabe podobieństwo" in candidate.next_step
    assert "potwierdzenia popytu ani duplikatu" in candidate.next_step


def test_candidate_rows_compile_cross_source_records_once_for_a_batch(monkeypatch) -> None:
    gsc_record_calls = 0
    wordpress_record_calls = 0
    original_gsc_records = ahrefs_overlap._gsc_records
    original_wordpress_records = ahrefs_overlap._wordpress_records

    def count_gsc_records(facts):
        nonlocal gsc_record_calls
        gsc_record_calls += 1
        return original_gsc_records(facts)

    def count_wordpress_records(facts):
        nonlocal wordpress_record_calls
        wordpress_record_calls += 1
        return original_wordpress_records(facts)

    monkeypatch.setattr(ahrefs_overlap, "_gsc_records", count_gsc_records)
    monkeypatch.setattr(ahrefs_overlap, "_wordpress_records", count_wordpress_records)

    rows = ahrefs_cross_source_candidate_rows(
        [
            _fact(
                "ahrefs_content_gap_count",
                evidence_id="ev_ahrefs_bdo_1",
                gap_type="content_gap",
                keyword="bdo odpady",
                competitor_domain="denios.pl",
            ),
            _fact(
                "ahrefs_content_gap_count",
                evidence_id="ev_ahrefs_bdo_2",
                gap_type="content_gap",
                keyword="odpady bdo",
                competitor_domain="denios.pl",
            ),
        ],
        [
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
    )

    assert len(rows) == 2
    assert gsc_record_calls == 1
    assert wordpress_record_calls == 1


def test_candidate_rows_can_return_full_mapping_set_beyond_display_limit() -> None:
    gap_facts = [
        _fact(
            "ahrefs_content_gap_count",
            evidence_id=f"ev_ahrefs_bdo_{index}",
            gap_type="content_gap",
            keyword=f"bdo odpady {index}",
            competitor_domain="denios.pl",
        )
        for index in range(7)
    ]

    display_rows = ahrefs_cross_source_candidate_rows(gap_facts, [], limit=6)
    mapping_rows = ahrefs_cross_source_candidate_rows(gap_facts, [], limit=None)

    assert len(display_rows) == 6
    assert len(mapping_rows) == 7
    assert {row.mapping_key for row in display_rows}.issubset(
        {row.mapping_key for row in mapping_rows}
    )
