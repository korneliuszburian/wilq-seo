from __future__ import annotations

from wilq.content.preflight.marketer_view import (
    build_content_marketer_decision,
    build_content_preflight_item,
    content_marketer_blocked_claims,
)
from wilq.schemas import ContentDecisionItem


def _refresh_decision() -> ContentDecisionItem:
    return ContentDecisionItem(
        id="content_decision_bdo",
        title="SEO: odśwież BDO",
        decision_type="refresh_or_merge",
        status="ready",
        priority=20,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        source_public_url="https://www.ekologus.pl/bdo/",
        final_canonical_url="https://www.ekologus.pl/bdo/",
        wordpress_match="found",
        wordpress_match_label="potwierdzony",
        inventory_gate_status="confirmed_current_inventory",
        canonical_gate_status="public_canonical_confirmed",
        duplicate_gate_status="existing_public_content_requires_refresh_or_merge",
        primary_query="bdo odpady",
        query_count=3,
        total_clicks=12,
        total_impressions=300,
        aggregate_ctr=0.04,
        blocked_claims=["wzrost liczby leadów"],
        rationale="WordPress potwierdza istniejący URL.",
        next_step="Przygotuj plan odświeżenia.",
    )


def test_marketer_view_builds_preserve_first_decision_copy() -> None:
    marketer_decision = build_content_marketer_decision([_refresh_decision()], [])

    assert marketer_decision is not None
    assert marketer_decision.decision == (
        "Zachowaj istniejącą treść i przygotuj odświeżenie albo scalenie, "
        "zamiast pisać nowy tekst od zera."
    )
    assert marketer_decision.mode_label == "zachować i odświeżyć"
    assert marketer_decision.metric_tiles == {
        "Zapytania": 3,
        "Kliknięcia": 12,
        "Wyświetlenia": 300,
        "CTR": "4.00%",
    }
    assert marketer_decision.final_canonical_url == "https://www.ekologus.pl/bdo/"
    assert "wzrost liczby leadów" in marketer_decision.blocked_claims


def test_marketer_view_preflight_blocks_draft_but_allows_sales_brief_for_refresh() -> None:
    item = build_content_preflight_item(_refresh_decision())

    assert item.recommended_mode == "refresh"
    assert item.recommended_mode_label == "odświeżyć"
    assert item.status == "review_required"
    assert item.create_allowed is False
    assert item.draft_allowed is False
    assert item.wordpress_draft_allowed is False
    assert item.sales_brief_allowed is True
    assert item.inventory_gate_status_label == "spis potwierdzony na obecnej stronie"
    assert item.evidence_summary_label


def test_content_marketer_blocked_claims_keeps_unknown_claims_generic() -> None:
    assert content_marketer_blocked_claims(["raw_unknown_claim"]) == [
        "obietnica do sprawdzenia"
    ]
