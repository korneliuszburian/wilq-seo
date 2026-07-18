from __future__ import annotations

from wilq.briefing.content_diagnostics import GSC_CONTENT_EXPERT_RULE_IDS
from wilq.content.planning.decisions import (
    ContentDecisionMetrics,
    content_decision_metric_tiles,
    content_decision_metrics,
    content_decision_priority,
    content_decision_sort_key,
    content_decision_status,
    content_decision_summary,
    content_decision_title,
    format_percent,
    gsc_content_decisions,
    int_dimension,
    polish_count_word,
    slug,
    wordpress_match_tile,
)
from wilq.schemas import ContentDecisionItem, MetricFact, OpportunityDomain, TacticalQueueItem


def _metric_fact(name: str, value: int | float | str, **dimensions: str) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="last_28_days",
        source_connector="google_search_console",
        evidence_id=f"ev_{name}_{dimensions.get('query', 'page')}",
        dimensions=dimensions,
    )


def test_gsc_content_diagnostics_do_not_claim_unavailable_trend_rules() -> None:
    assert "seo_content_decay_v1" not in GSC_CONTENT_EXPERT_RULE_IDS
    assert "seo_cannibalization_v1" not in GSC_CONTENT_EXPERT_RULE_IDS


def test_content_decision_metrics_aggregate_gsc_and_pick_primary_query() -> None:
    metrics = content_decision_metrics(
        [
            _metric_fact("impressions", 1200, query="bdo odpady"),
            _metric_fact("clicks", 36, query="bdo odpady"),
            _metric_fact("average_position", 5.2, query="bdo odpady"),
            _metric_fact("impressions", 900, query="zielony ład"),
            _metric_fact("clicks", 50, query="zielony ład"),
            _metric_fact("average_position", 3.1, query="zielony ład"),
        ],
        ["fallback query"],
    )

    assert metrics.primary_query == "bdo odpady"
    assert metrics.total_impressions == 2100
    assert metrics.total_clicks == 86
    assert metrics.aggregate_ctr == 86 / 2100
    assert metrics.best_average_position == 3.1


def test_content_decision_refresh_summary_defends_preserve_first_logic() -> None:
    metrics = ContentDecisionMetrics(
        primary_query="bdo odpady",
        total_clicks=12,
        total_impressions=300,
        aggregate_ctr=0.04,
        best_average_position=8.2,
    )

    assert content_decision_status("refresh_or_merge") == "ready"
    assert content_decision_priority("refresh_or_merge", metrics, query_count=3) == 21
    assert content_decision_title("refresh_or_merge", "/bdo", 3, metrics) == (
        "URL /bdo: sprawdź istniejącą treść (3 zapytań)"
    )
    assert content_decision_metric_tiles(
        "refresh_or_merge",
        metrics,
        3,
        "found",
        wordpress_section_count=4,
        wordpress_section_inventory_status="available",
    ) == {
        "zapytania": 3,
        "WP": "znaleziono",
        "sekcje WP": 4,
        "wyświetlenia": 300,
        "kliknięcia": 12,
        "CTR": "4.00%",
        "pozycja": 8.2,
    }
    assert content_decision_metric_tiles("refresh_or_merge", metrics, 3, "found")[
        "sekcje WP"
    ] == "brak odczytu sekcji"
    assert "aktualny URL" in content_decision_summary(
        "refresh_or_merge",
        metrics,
        "found",
        wordpress_section_headings=["Obowiązki przedsiębiorcy"],
    )
    assert "Obowiązki przedsiębiorcy" in content_decision_summary(
        "refresh_or_merge",
        metrics,
        "found",
        wordpress_section_headings=["Obowiązki przedsiębiorcy"],
    )
    assert "samego zapytania" in content_decision_summary("refresh_or_merge", metrics, "found")


def test_content_decision_create_candidate_is_blocked_until_inventory_review() -> None:
    metrics = ContentDecisionMetrics(
        primary_query=None,
        total_clicks=None,
        total_impressions=80,
        aggregate_ctr=None,
        best_average_position=None,
    )

    assert content_decision_status("inventory_check_before_create") == "blocked"
    assert content_decision_metric_tiles(
        "inventory_check_before_create",
        metrics,
        1,
        "missing",
    )["tryb"] == "blokada nowej treści"
    assert "blokuje plan nowej treści" in content_decision_summary(
        "inventory_check_before_create",
        metrics,
        "missing",
    )


def test_content_decision_sort_key_places_ready_high_priority_first() -> None:
    ready = ContentDecisionItem(
        id="content_decision_ready",
        title="Ready",
        decision_type="refresh_or_merge",
        status="ready",
        priority=20,
        total_impressions=100,
        query_count=2,
        reason="Gotowe.",
        rationale="Jest evidence.",
        next_step="Sprawdź plan.",
        evidence_ids=["ev_ready"],
        source_connectors=["google_search_console"],
    )
    blocked = ContentDecisionItem(
        id="content_decision_blocked",
        title="Blocked",
        decision_type="inventory_check_before_create",
        status="blocked",
        priority=1,
        total_impressions=1000,
        query_count=10,
        reason="Zablokowane.",
        rationale="Brak spisu.",
        next_step="Sprawdź WordPress.",
        evidence_ids=["ev_blocked"],
        source_connectors=["google_search_console"],
    )

    assert sorted([blocked, ready], key=content_decision_sort_key) == [ready, blocked]


def test_content_planning_format_helpers_keep_marketer_copy_stable() -> None:
    item = TacticalQueueItem(
        id="queue_content_bdo",
        title="BDO",
        domain=OpportunityDomain.gsc_seo,
        intent="content_refresh",
        priority=20,
        source_connectors=["google_search_console"],
        evidence_ids=["ev_content_bdo"],
        diagnosis="GSC ma popyt.",
        next_step="Sprawdź plan.",
        dimensions={"count": "7", "bad": "x"},
    )

    assert wordpress_match_tile("missing") == "niepotwierdzono w WordPress"
    assert format_percent(0.1234) == "12.34%"
    assert polish_count_word(3, "rekord", "rekordy", "rekordów") == "rekordy"
    assert int_dimension(item, "count", 1) == 7
    assert int_dimension(item, "bad", 1) == 1
    assert slug("BDO: odpady / firma") == "bdo__odpady___firma"


def test_gsc_content_decisions_preserve_existing_public_url_before_create() -> None:
    item = TacticalQueueItem(
        id="queue_content_bdo",
        title="BDO",
        domain=OpportunityDomain.gsc_seo,
        intent="content_refresh",
        priority=20,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_content_bdo"],
        metric_facts=[
            _metric_fact(
                "impressions",
                500,
                query="bdo odpady",
                page="https://www.ekologus.pl/bdo/",
            ),
            _metric_fact(
                "clicks",
                20,
                query="bdo odpady",
                page="https://www.ekologus.pl/bdo/",
            ),
        ],
        diagnosis="GSC pokazuje popyt, WordPress potwierdza stronę.",
        next_step="Sprawdź plan.",
        blocked_claims=["wzrost leadów"],
        action_ids=["act_prepare_content_refresh_queue"],
        dimensions={
            "page": "https://www.ekologus.pl/bdo/",
            "query": "bdo odpady",
            "wordpress_match": "found",
            "wordpress_match_confidence": "exact_url",
            "wordpress_content_url": "https://ekologus.dev.proudsite.pl/bdo/",
            "wordpress_requested_path": "/bdo",
            "gsc_page_query_count": "1",
        },
    )

    decisions = gsc_content_decisions(
        [item],
        knowledge_card_ids=("card_gsc_seo_content_playbook",),
        expert_rule_ids=("seo_query_page_matrix_v1",),
    )

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.decision_type == "refresh_or_merge"
    assert decision.status == "ready"
    assert decision.source_public_url == "https://www.ekologus.pl/bdo/"
    assert decision.final_canonical_url == "https://www.ekologus.pl/bdo/"
    assert decision.preview_url is None
    assert decision.inventory_gate_status == "confirmed_current_inventory"
    assert decision.duplicate_gate_status == "existing_public_content_requires_refresh_or_merge"
    assert decision.blocked_claims == ["wzrost leadów"]
    assert decision.action_ids == ["act_prepare_content_refresh_queue"]
